"""dotpanel.sync — repo-aware sync verb.

Subcommands:

    sync status                          (read-only)
    sync diff                            (read-only)
    sync precheck                        (read-only)
    sync push   [--repo L] [--no-leak-check] [--dry-run]
    sync pull   [--no-configure] [--force-restart] [--repo L]
    sync pull-only                       (kernel state machine step)
    sync reload                          (kernel state machine step)
    sync post-reload                     (kernel state machine step; internal)
    sync resume                          (recover from mid-flight crash)
    sync unlock                          (clear stale ~/.dotpanel/sync.lock)
    sync help

Exit codes:
    0  ok
    2  leak refused / git rejected / lock held / usage error
    3  secrets/age unavailable on a repo that needs it
    4  file write failed (state file or path.sh)
    other-nonzero = crash

Concurrency:
    Any mutating subcommand (push, pull, pull-only, reload, resume) acquires a
    non-blocking `flock` on ~/.dotpanel/sync.lock at start. Read-only verbs
    (status, diff, precheck) do not require the lock.

Checkpointed pull (EC-4):
    pull splits into precheck -> pull-only -> reload -> post-reload, with state
    persisted to ~/.dotpanel/sync-state.json after each phase. A mid-flight
    crash leaves a recoverable state. `resume` continues from the next phase.
    Multi-repo coherence is NOT guaranteed (per design); if dotfiles pulls and
    dotpanel pull fails, repos may be at different commits — operator's
    responsibility.

Rebase conflict (EC-4):
    `git pull --rebase --autostash` may leave .git/REBASE_HEAD on conflict.
    pull-only detects this on entry/exit and exits 2 with a manual-recovery
    message. No automatic resolution.
"""
from __future__ import annotations

import argparse
import datetime
import errno
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .config import (
    SchemaError,
    SubstrateConfig,
    SubstrateNotFound,
    SyncRepo,
    find_substrate,
)
from .leaks import cmd_leaks


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

STATE_DIR_REL = ".dotpanel"
STATE_FILE = "sync-state.json"
LOCK_FILE = "sync.lock"

# Stuck-state threshold (per design doc doctor invariant).
STUCK_AGE_SECONDS = 3600


def _state_dir(home: Path | None = None) -> Path:
    home = home or Path(os.path.expanduser("~"))
    return home / STATE_DIR_REL


def _state_path(home: Path | None = None) -> Path:
    return _state_dir(home) / STATE_FILE


def _lock_path(home: Path | None = None) -> Path:
    return _state_dir(home) / LOCK_FILE


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------

@dataclass
class SyncState:
    """In-memory representation of ~/.dotpanel/sync-state.json."""

    phase: str = "done"
    repos_pulled: list[str] = field(default_factory=list)
    repos_failed: list[str] = field(default_factory=list)
    started_at: str = ""
    dotpanel_version_before: str = ""
    dotpanel_version_after: str = ""

    @classmethod
    def fresh(cls) -> "SyncState":
        return cls(
            phase="precheck",
            started_at=_now_iso(),
            dotpanel_version_before=__version__,
            dotpanel_version_after="",
        )

    def is_active(self) -> bool:
        return self.phase != "done"

    def age_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        try:
            started = datetime.datetime.fromisoformat(self.started_at.rstrip("Z"))
        except ValueError:
            return 0.0
        # `started` is naive UTC (we wrote it via strftime). Use a matching
        # naive `now` so the subtraction is consistent.
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return (now - started).total_seconds()


def _now_iso() -> str:
    # Timezone-aware UTC (datetime.utcnow is deprecated since 3.12).
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _load_state(home: Path | None = None) -> SyncState:
    """Read state file. Returns done-state if missing or malformed."""
    p = _state_path(home)
    if not p.is_file():
        return SyncState(phase="done")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SyncState(phase="done")
    return SyncState(
        phase=str(raw.get("phase", "done")),
        repos_pulled=list(raw.get("repos_pulled", []) or []),
        repos_failed=list(raw.get("repos_failed", []) or []),
        started_at=str(raw.get("started_at", "")),
        dotpanel_version_before=str(raw.get("dotpanel_version_before", "")),
        dotpanel_version_after=str(raw.get("dotpanel_version_after", "")),
    )


def _save_state(state: SyncState, home: Path | None = None) -> None:
    """Atomic write: tmp file + fsync + rename."""
    p = _state_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(state), indent=2, sort_keys=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{STATE_FILE}.", dir=str(p.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _clear_state(home: Path | None = None) -> None:
    p = _state_path(home)
    try:
        p.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# flock-based concurrency guard (H8)
# ---------------------------------------------------------------------------

class SyncLockError(Exception):
    """Raised when another process holds the sync lock."""

    def __init__(self, pid: int) -> None:
        super().__init__(f"sync in progress (pid {pid})")
        self.pid = pid


class SyncLock:
    """Non-blocking flock on ~/.dotpanel/sync.lock.

    Writes the current pid into the file body so `sync unlock` can verify
    liveness via os.kill(pid, 0). Lock is released when the file descriptor
    closes (kernel-enforced on local filesystems even on crash).
    """

    def __init__(self, home: Path | None = None) -> None:
        self._home = home
        self._fh: Any = None

    def __enter__(self) -> "SyncLock":
        path = _lock_path(self._home)
        path.parent.mkdir(parents=True, exist_ok=True)
        # O_CREAT|O_RDWR so concurrent attempts share the same inode.
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                # Read recorded pid for the error message.
                pid = _read_lock_pid(path)
                raise SyncLockError(pid) from exc
            raise
        # Write our pid into the file body. Truncate first so stale pids don't
        # linger.
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        self._fh = fd
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self._fh is not None:
            try:
                fcntl.flock(self._fh, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fh)
            except OSError:
                pass
            self._fh = None


def _read_lock_pid(path: Path) -> int:
    try:
        text = path.read_text(encoding="ascii").strip()
        return int(text) if text else 0
    except (OSError, ValueError):
        return 0


def _pid_alive(pid: int) -> bool:
    """True if pid is alive (POSIX signal-0 probe)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by another user; treat as alive.
        return True
    return True


# ---------------------------------------------------------------------------
# Repo helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedRepo:
    label: str
    path: Path
    raw_path: str  # the original [sync] repos.path entry (for leak_mode_overrides lookup)

    def is_git_repo(self) -> bool:
        return _is_git_repo(self.path)


def _resolve_repos(substrate: SubstrateConfig) -> list[ResolvedRepo]:
    """Resolve [sync].repos to absolute paths.

    Repo path strings may use `~` for HOME expansion. We keep the raw string
    so leak_mode_overrides (keyed by raw path) can be looked up later.
    """
    resolved: list[ResolvedRepo] = []
    for entry in substrate.sync.repos:
        raw = entry.path
        path = Path(os.path.expanduser(raw)).resolve()
        label = entry.label or path.name
        resolved.append(ResolvedRepo(label=label, path=path, raw_path=raw))
    return resolved


def _is_git_repo(path: Path) -> bool:
    if not path.is_dir():
        return False
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_status_porcelain(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain", "--branch"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout


def _git_has_clean_tree(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == ""


def _git_has_index_lock(path: Path) -> bool:
    return (path / ".git" / "index.lock").exists()


def _git_has_rebase_in_progress(path: Path) -> bool:
    """True if the repo has a rebase in progress (REBASE_HEAD present)."""
    git_dir = path / ".git"
    return (
        (git_dir / "REBASE_HEAD").exists()
        or (git_dir / "rebase-merge").is_dir()
        or (git_dir / "rebase-apply").is_dir()
    )


def _git_has_head(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def _git_has_upstream(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref",
         "--symbolic-full-name", "@{upstream}"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def _git_ahead_count(path: Path) -> int:
    """Count commits ahead of upstream. Returns 0 if no upstream or on error."""
    if not _git_has_upstream(path):
        return 0
    result = subprocess.run(
        ["git", "-C", str(path), "rev-list", "--count", "@{upstream}..HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def _machine_id() -> str:
    candidates = [
        Path(os.path.expanduser("~/.machine-id")),
    ]
    for c in candidates:
        if c.is_file():
            try:
                return c.read_text(encoding="utf-8").strip() or "unknown"
            except OSError:
                continue
    return "unknown"


# ---------------------------------------------------------------------------
# Substrate lookup with friendly error
# ---------------------------------------------------------------------------

def _resolve_substrate() -> SubstrateConfig:
    try:
        return find_substrate()
    except SubstrateNotFound as exc:
        raise SyncError(
            f"substrate not found: {exc}", exit_code=2
        ) from exc


class SyncError(Exception):
    """Internal control-flow exception. Carries an exit code."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Verb: status (read-only)
# ---------------------------------------------------------------------------

def cmd_status(filter_label: str | None = None) -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    if filter_label:
        repos = [r for r in repos if r.label == filter_label]
        if not repos:
            print(f"FAIL  unknown repo label: {filter_label}", file=sys.stderr)
            return 2

    print("=== Machine ===")
    print(f"  ID: {_machine_id()}")
    print(f"  Platform: {os.uname().sysname}/{os.uname().machine}")

    # Stuck-state surface (also enforced by doctor invariant).
    state = _load_state()
    if state.is_active():
        age = int(state.age_seconds())
        warn = "WARN  " if age > STUCK_AGE_SECONDS else "INFO  "
        print(f"{warn}sync in phase {state.phase!r} (age {age}s)")

    print()
    print("=== Repos ===")
    for r in repos:
        if not r.is_git_repo():
            print(f"  {r.label}: not a git repo at {r.path}")
            continue
        print(f"  {r.label} ({r.path}):")
        for line in _git_status_porcelain(r.path).splitlines():
            print(f"    {line}")

    return 0


# ---------------------------------------------------------------------------
# Verb: diff (read-only)
# ---------------------------------------------------------------------------

def cmd_diff(filter_label: str | None = None) -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    if filter_label:
        repos = [r for r in repos if r.label == filter_label]
        if not repos:
            print(f"FAIL  unknown repo label: {filter_label}", file=sys.stderr)
            return 2

    for r in repos:
        if not r.is_git_repo():
            continue
        print(f"=== {r.label} ({r.path}) ===")
        # Show working-tree diff. ANSI colors stripped (CI-friendly).
        subprocess.run(
            ["git", "-C", str(r.path), "diff", "--color=never"],
            check=False,
        )
        subprocess.run(
            ["git", "-C", str(r.path), "diff", "--cached", "--color=never"],
            check=False,
        )
    return 0


# ---------------------------------------------------------------------------
# Verb: precheck (read-only; mirrors phase 0 of pull state machine)
# ---------------------------------------------------------------------------

def _precheck_repos(repos: Sequence[ResolvedRepo]) -> list[str]:
    """Return a list of issue messages; empty list = all clean."""
    issues: list[str] = []
    for r in repos:
        if not r.is_git_repo():
            # Missing repo is informational, not a precheck failure — caller
            # decides whether to bail.
            continue
        if _git_has_index_lock(r.path):
            issues.append(f"{r.label}: .git/index.lock present")
        if _git_has_rebase_in_progress(r.path):
            issues.append(f"{r.label}: rebase in progress (.git/REBASE_HEAD)")
        # We don't refuse on a dirty tree at precheck — push needs the dirty
        # tree, pull is fine with rebase --autostash. dot v4 didn't refuse
        # either.
    return issues


def cmd_precheck() -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    issues = _precheck_repos(repos)
    if issues:
        for i in issues:
            print(f"FAIL  {i}", file=sys.stderr)
        return 2
    print("OK  precheck clean")
    return 0


# ---------------------------------------------------------------------------
# Verb: push (mutating; needs lock)
# ---------------------------------------------------------------------------

def cmd_push(filter_label: str | None = None, no_leak_check: bool = False,
             dry_run: bool = False) -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    if filter_label:
        repos = [r for r in repos if r.label == filter_label]
        if not repos:
            print(f"FAIL  unknown repo label: {filter_label}", file=sys.stderr)
            return 2

    try:
        with SyncLock():
            return _push_impl(substrate, repos, no_leak_check, dry_run)
    except SyncLockError as exc:
        print(
            f"FAIL  {exc}; wait or 'dotpanel sync unlock' if stale",
            file=sys.stderr,
        )
        return 2


def _leak_mode_for(substrate: SubstrateConfig, repo: ResolvedRepo) -> str:
    overrides = substrate.sync.leak_mode_overrides
    # Check raw-path key first (matches the toml as-written).
    if repo.raw_path in overrides:
        return overrides[repo.raw_path]
    # Fall back to substrate-default.
    return substrate.sync.leak_mode_default


def _push_impl(substrate: SubstrateConfig, repos: Sequence[ResolvedRepo],
               no_leak_check: bool, dry_run: bool) -> int:
    machine = _machine_id()
    pushed_any = False
    for r in repos:
        if not r.is_git_repo():
            print(f"SKIP  {r.label}: not a git repo")
            continue

        if not no_leak_check:
            mode = _leak_mode_for(substrate, r)
            rc = cmd_leaks(r.path, mode)
            if rc != 0:
                print(f"FAIL  {r.label}: leak check refused (mode={mode})",
                      file=sys.stderr)
                return 2

        # Stage + commit pending changes, then push.
        dirty = not _git_has_clean_tree(r.path)
        needs_push = False
        if dirty:
            if dry_run:
                print(f"WOULD-COMMIT-PUSH  {r.label}")
                continue
            print(f"OK  committing {r.label}...")
            subprocess.run(["git", "-C", str(r.path), "add", "-A"], check=True)
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"sync: {machine} {ts}"
            cp = subprocess.run(
                ["git", "-C", str(r.path), "commit", "-m", commit_msg],
                check=False,
            )
            if cp.returncode != 0:
                print(f"FAIL  {r.label}: git commit failed", file=sys.stderr)
                return 2
            needs_push = True
        elif _git_has_head(r.path):
            if _git_has_upstream(r.path):
                if _git_ahead_count(r.path) > 0:
                    needs_push = True
            else:
                needs_push = True

        if not needs_push:
            print(f"OK  {r.label}: nothing to push (clean)")
            continue

        if _git_has_upstream(r.path):
            if dry_run:
                print(f"WOULD-REBASE-PUSH  {r.label}")
                continue
            print(f"OK  rebasing {r.label} before push...")
            cp = subprocess.run(
                ["git", "-C", str(r.path), "pull", "--rebase", "--autostash"],
                check=False,
            )
            if cp.returncode != 0:
                print(f"FAIL  {r.label}: pre-push pull failed", file=sys.stderr)
                return 2

        if dry_run:
            print(f"WOULD-PUSH  {r.label}")
            continue
        print(f"OK  pushing {r.label}...")
        cp = subprocess.run(["git", "-C", str(r.path), "push"], check=False)
        if cp.returncode != 0:
            print(f"FAIL  {r.label}: git push failed", file=sys.stderr)
            return 2
        pushed_any = True

    if not pushed_any and not dry_run:
        print("OK  nothing to push (clean)")
    return 0


# ---------------------------------------------------------------------------
# Verb: pull (mutating, multi-phase; needs lock)
# ---------------------------------------------------------------------------

# Phase ordering used by `pull` and `resume` to compute the next step.
PULL_PHASES = ("precheck", "pull-only", "reload", "post-reload", "done")


def cmd_pull(no_configure: bool = False, force_restart: bool = False) -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)

    try:
        with SyncLock():
            return _pull_impl(substrate, repos, no_configure, force_restart,
                              resuming=False)
    except SyncLockError as exc:
        print(
            f"FAIL  {exc}; wait or 'dotpanel sync unlock' if stale",
            file=sys.stderr,
        )
        return 2


def _pull_impl(substrate: SubstrateConfig, repos: Sequence[ResolvedRepo],
               no_configure: bool, force_restart: bool, *,
               resuming: bool) -> int:
    state = _load_state()
    if force_restart:
        _clear_state()
        state = SyncState.fresh()
    elif state.is_active() and not resuming:
        age = int(state.age_seconds())
        if age < STUCK_AGE_SECONDS:
            print(
                f"FAIL  previous sync incomplete (phase={state.phase!r}, "
                f"age={age}s); run 'dotpanel sync resume' or "
                f"'dotpanel sync pull --force-restart'",
                file=sys.stderr,
            )
            return 2
        # Older than the stuck threshold: clear and restart silently.
        print(
            f"WARN  previous sync abandoned (phase={state.phase!r}, "
            f"age={age}s); starting fresh"
        )
        _clear_state()
        state = SyncState.fresh()
    elif not resuming:
        state = SyncState.fresh()

    return _run_phases_from(state, substrate, repos, no_configure=no_configure)


def _run_phases_from(state: SyncState, substrate: SubstrateConfig,
                     repos: Sequence[ResolvedRepo], *,
                     no_configure: bool) -> int:
    """Drive the phase state machine, starting at state.phase."""
    # Compute the index of the phase to RUN next. When resuming, state.phase
    # records the last *completed* phase; advance to the next one.
    # When starting fresh, state.phase == "precheck" and we run precheck.
    phase_order = PULL_PHASES
    if state.phase not in phase_order:
        print(f"FAIL  unknown sync state phase: {state.phase!r}", file=sys.stderr)
        return 2
    idx = phase_order.index(state.phase)
    while idx < len(phase_order):
        phase = phase_order[idx]
        if phase == "done":
            _clear_state()
            print("OK  sync pull complete")
            return 0
        rc = _run_phase(phase, state, substrate, repos, no_configure=no_configure)
        if rc != 0:
            return rc
        idx += 1
    return 0


def _run_phase(phase: str, state: SyncState, substrate: SubstrateConfig,
               repos: Sequence[ResolvedRepo], *,
               no_configure: bool) -> int:
    """Run a single phase. Updates state.phase on success, persists state."""
    print(f"=== phase: {phase} ===")
    if phase == "precheck":
        issues = _precheck_repos(repos)
        if issues:
            for i in issues:
                print(f"FAIL  {i}", file=sys.stderr)
            return 2
        state.phase = "precheck"
        _save_state(state)
        return 0

    if phase == "pull-only":
        rc, pulled, failed = _phase_pull_only(repos, state)
        state.repos_pulled = pulled
        state.repos_failed = failed
        if rc != 0:
            state.phase = "pull-only"
            _save_state(state)
            return rc
        state.phase = "pull-only"
        _save_state(state)
        return 0

    if phase == "reload":
        rc = _phase_reload(state)
        if rc != 0:
            state.phase = "reload"
            _save_state(state)
            return rc
        state.phase = "reload"
        _save_state(state)
        return 0

    if phase == "post-reload":
        rc = _phase_post_reload(state, no_configure=no_configure)
        # post-reload sets phase=done on success; on failure stays at
        # post-reload so doctor surfaces the stuck state.
        if rc == 0:
            state.phase = "done"
        else:
            state.phase = "post-reload"
        _save_state(state)
        return rc

    print(f"FAIL  unknown phase {phase!r}", file=sys.stderr)
    return 2


def _phase_pull_only(repos: Sequence[ResolvedRepo],
                     state: SyncState) -> tuple[int, list[str], list[str]]:
    """Run `git pull --rebase --autostash` per repo.

    Returns (exit_code, pulled_labels, failed_labels). On the first failing
    repo we stop and record both pulled+failed lists for resume.
    """
    pulled = list(state.repos_pulled)
    failed: list[str] = []
    for r in repos:
        if r.label in pulled:
            continue
        if not r.is_git_repo():
            print(f"SKIP  {r.label}: not a git repo")
            pulled.append(r.label)
            continue
        if _git_has_rebase_in_progress(r.path):
            print(
                f"FAIL  {r.label}: rebase in progress; complete or abort "
                "manually before 'sync resume'",
                file=sys.stderr,
            )
            failed.append(r.label)
            return 2, pulled, failed
        print(f"OK  pulling {r.label}...")
        cp = subprocess.run(
            ["git", "-C", str(r.path), "pull", "--rebase", "--autostash"],
            check=False,
        )
        if cp.returncode != 0:
            # Rebase conflict detection: if .git/REBASE_HEAD now exists,
            # surface a manual-recovery message (EC-4).
            if _git_has_rebase_in_progress(r.path):
                print(
                    f"FAIL  {r.label}: rebase conflict during pull; resolve "
                    "with `git rebase --continue` or `git rebase --abort` "
                    "then 'dotpanel sync resume'",
                    file=sys.stderr,
                )
            else:
                print(f"FAIL  {r.label}: git pull failed (rc={cp.returncode})",
                      file=sys.stderr)
            failed.append(r.label)
            return 2, pulled, failed
        pulled.append(r.label)
    return 0, pulled, failed


def _phase_reload(state: SyncState) -> int:
    """If dotpanel was among repos_pulled, reinstall editable tool and execvp self.

    On execvp success we never return — the new binary picks up post-reload.
    """
    dotpanel_pulled = any("dotpanel" in lbl.lower() for lbl in state.repos_pulled)
    if not dotpanel_pulled:
        print("OK  reload skipped (dotpanel not among pulled repos)")
        return 0

    # Look for an editable source dir to reload from. Bail with WARN if the
    # operator runs from a site-packages install (nothing to reinstall).
    src = Path(os.path.expanduser("~/src/dotpanel"))
    if not src.is_dir():
        print(f"WARN  reload: no editable source at {src}", file=sys.stderr)
        return 0

    if shutil.which("uv"):
        cmd = ["uv", "tool", "install", "--editable", str(src)]
        label = f"uv tool install --editable {src}"
    else:
        cmd = [
            sys.executable, "-m", "pip", "install", "-e", str(src),
            "--quiet", "--break-system-packages",
        ]
        label = f"pip install -e {src}"

    print(f"OK  reload: {label}")
    cp = subprocess.run(cmd, check=False)
    if cp.returncode != 0:
        print(f"FAIL  reload: {label} exited {cp.returncode}",
              file=sys.stderr)
        return 2

    # Persist the post-reload checkpoint BEFORE execvp so the new binary
    # sees phase=reload (last completed) and runs post-reload next.
    state.phase = "reload"
    _save_state(state)

    print("OK  reload: execvp to new binary for post-reload phase")
    # Replace the process; the new binary runs `dotpanel sync post-reload`.
    # Note: caller has the lock held; execvp inherits open fds, so the lock
    # transfers to the new binary's pid. The new binary's post-reload code
    # path does NOT re-acquire the lock (would self-deadlock).
    os.execvp(sys.executable, [sys.executable, "-m", "dotpanel", "sync",
                               "post-reload"])
    # Unreachable.
    return 0


def _phase_post_reload(state: SyncState, *, no_configure: bool) -> int:
    """Verify the new binary, then run configure.

    `configure --check` first; on success, real `configure --harness all`.
    Configure failure leaves phase pinned at post-reload so doctor surfaces
    the stuck state (per design).
    """
    # Record the new binary's version for state-file forensics.
    state.dotpanel_version_after = __version__

    if no_configure:
        print("OK  post-reload: skipping configure (--no-configure)")
        return 0

    # configure --check (validation only)
    print("OK  post-reload: dotpanel configure --check --harness all")
    cp = subprocess.run(
        [sys.executable, "-m", "dotpanel", "configure", "--check",
         "--harness", "all"],
        check=False,
    )
    if cp.returncode != 0:
        print(
            "WARN  post-reload: configure --check failed; "
            "harness adapters NOT regenerated. "
            "Diagnose: dotpanel configure --harness all --check",
            file=sys.stderr,
        )
        # Pull itself exits 0 even if configure fails (per ADR-3 dot
        # integration). We still record the warning above.
        return 0

    print("OK  post-reload: dotpanel configure --harness all")
    cp = subprocess.run(
        [sys.executable, "-m", "dotpanel", "configure", "--harness", "all"],
        check=False,
    )
    if cp.returncode != 0:
        print(
            "WARN  post-reload: configure failed after --check passed; "
            "last-good adapters preserved. Investigate.",
            file=sys.stderr,
        )
        return 0

    return 0


# ---------------------------------------------------------------------------
# Verb: pull-only / reload / post-reload (state-machine entry points)
# ---------------------------------------------------------------------------

def cmd_pull_only() -> int:
    """Run only the pull-only phase. Used by tests and by `resume`.

    Acquires the lock if not already held. The caller (pull / resume) acquires
    the lock at a higher scope.
    """
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    try:
        with SyncLock():
            state = _load_state()
            if not state.is_active():
                state = SyncState.fresh()
                state.phase = "precheck"
                _save_state(state)
            rc, pulled, failed = _phase_pull_only(repos, state)
            state.repos_pulled = pulled
            state.repos_failed = failed
            state.phase = "pull-only"
            _save_state(state)
            return rc
    except SyncLockError as exc:
        print(f"FAIL  {exc}; wait or 'dotpanel sync unlock' if stale",
              file=sys.stderr)
        return 2


def cmd_reload() -> int:
    try:
        with SyncLock():
            state = _load_state()
            if not state.is_active():
                print("FAIL  no in-flight sync state to reload",
                      file=sys.stderr)
                return 2
            rc = _phase_reload(state)
            if rc == 0:
                state.phase = "reload"
                _save_state(state)
            return rc
    except SyncLockError as exc:
        print(f"FAIL  {exc}; wait or 'dotpanel sync unlock' if stale",
              file=sys.stderr)
        return 2


def cmd_post_reload(no_configure: bool = False) -> int:
    # Note: post-reload does NOT acquire the lock — it's invoked via execvp
    # from the reload phase which already holds the lock.
    state = _load_state()
    if not state.is_active():
        # If state is "done" we still try to run configure (allows manual
        # invocation), but quietly.
        pass
    rc = _phase_post_reload(state, no_configure=no_configure)
    if rc == 0:
        state.phase = "done"
        _save_state(state)
        _clear_state()
    else:
        state.phase = "post-reload"
        _save_state(state)
    return rc


# ---------------------------------------------------------------------------
# Verb: resume (mutating; needs lock)
# ---------------------------------------------------------------------------

def cmd_resume(no_configure: bool = False) -> int:
    try:
        substrate = _resolve_substrate()
    except SyncError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return exc.exit_code
    repos = _resolve_repos(substrate)
    state = _load_state()
    if not state.is_active():
        print("OK  no in-flight sync to resume")
        return 0

    # Check for rebase-in-progress on any repo before resuming.
    for r in repos:
        if r.is_git_repo() and _git_has_rebase_in_progress(r.path):
            print(
                f"FAIL  rebase in progress at {r.label} ({r.path}); "
                "complete or abort manually before 'sync resume'",
                file=sys.stderr,
            )
            return 2

    try:
        with SyncLock():
            return _run_phases_from(state, substrate, repos,
                                    no_configure=no_configure)
    except SyncLockError as exc:
        print(f"FAIL  {exc}; wait or 'dotpanel sync unlock' if stale",
              file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Verb: unlock (read+act, no lock)
# ---------------------------------------------------------------------------

def cmd_unlock() -> int:
    path = _lock_path()
    if not path.exists():
        print("OK  no sync lock present")
        return 0
    pid = _read_lock_pid(path)
    if pid > 0 and _pid_alive(pid):
        print(
            f"FAIL  sync in progress (pid {pid}); refusing to unlock",
            file=sys.stderr,
        )
        return 2
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    print(f"OK  removed stale lock (recorded pid={pid})")
    return 0


# ---------------------------------------------------------------------------
# Verb: help
# ---------------------------------------------------------------------------

HELP_TEXT = """\
Usage: dotpanel sync <subcommand> [options]

Read-only:
  status                        Machine + sync-state + per-repo git status
  diff [--repo L]               Show working-tree diff for each repo
  precheck                      Verify all repos are pull-ready (no locks,
                                no in-flight rebases)

Mutating (acquires ~/.dotpanel/sync.lock):
  push  [--repo L] [--no-leak-check] [--dry-run]
        Run `dotpanel leaks` per repo (mode from [sync] leak_mode_overrides),
        commit pending changes, rebase, push.
  pull  [--no-configure] [--force-restart]
        Multi-phase: precheck -> pull-only -> reload (uv tool install --editable
        or venv pip fallback + execvp) -> post-reload (configure --check +
        configure --harness all).
  pull-only                     Phase 1 only: git pull on each repo.
  reload                        Phase 2 only: reinstall editable + execvp.
  post-reload                   Internal — invoked via execvp; runs
                                configure --check + configure --harness all.
  resume [--no-configure]       Continue from the last checkpoint after a
                                mid-flight crash.
  unlock                        Remove a stale ~/.dotpanel/sync.lock when
                                the recorded pid is no longer alive.

State:
  ~/.dotpanel/sync-state.json    Phase checkpoints (atomically written).
  ~/.dotpanel/sync.lock          flock target for concurrency guard (H8).

Exit codes:
  0  ok
  2  leak refused / git rejected / lock held / usage error
  3  secrets/age unavailable on a repo that needs it
  4  file write failed
"""


def cmd_help() -> int:
    print(HELP_TEXT)
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def build_sync_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="sync_command", required=False)

    s_status = sub.add_parser("status", help="machine + repo status")
    s_status.add_argument("--repo", dest="repo_label", default=None)

    s_diff = sub.add_parser("diff", help="working-tree diff per repo")
    s_diff.add_argument("--repo", dest="repo_label", default=None)

    sub.add_parser("precheck", help="verify all repos are pull-ready")

    s_push = sub.add_parser("push", help="leaks check + commit + push")
    s_push.add_argument("--repo", dest="repo_label", default=None)
    s_push.add_argument("--no-leak-check", action="store_true")
    s_push.add_argument("--dry-run", action="store_true")

    s_pull = sub.add_parser("pull", help="multi-phase pull (checkpointed)")
    s_pull.add_argument("--no-configure", action="store_true")
    s_pull.add_argument("--force-restart", action="store_true")

    sub.add_parser("pull-only", help="phase: git pull on each repo")
    sub.add_parser("reload", help="phase: reinstall editable + execvp self")

    s_post = sub.add_parser("post-reload", help="phase: configure (internal)")
    s_post.add_argument("--no-configure", action="store_true")

    s_resume = sub.add_parser("resume", help="resume from last checkpoint")
    s_resume.add_argument("--no-configure", action="store_true")

    sub.add_parser("unlock", help="remove stale sync.lock")
    sub.add_parser("help", help="show this help text")


def dispatch_sync(args: argparse.Namespace) -> int:
    sc = getattr(args, "sync_command", None)
    if sc is None:
        return cmd_help()
    if sc == "status":
        return cmd_status(args.repo_label)
    if sc == "diff":
        return cmd_diff(args.repo_label)
    if sc == "precheck":
        return cmd_precheck()
    if sc == "push":
        return cmd_push(args.repo_label, args.no_leak_check, args.dry_run)
    if sc == "pull":
        return cmd_pull(args.no_configure, args.force_restart)
    if sc == "pull-only":
        return cmd_pull_only()
    if sc == "reload":
        return cmd_reload()
    if sc == "post-reload":
        return cmd_post_reload(args.no_configure)
    if sc == "resume":
        return cmd_resume(args.no_configure)
    if sc == "unlock":
        return cmd_unlock()
    if sc == "help":
        return cmd_help()
    print(f"FAIL  unknown sync subcommand: {sc}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotpanel sync")
    build_sync_parser(parser)
    args = parser.parse_args(argv)
    return dispatch_sync(args)


if __name__ == "__main__":
    raise SystemExit(main())
