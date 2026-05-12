"""Phase C step 6: dotpanel.sync — checkpointed pull + flock + rebase conflict.

Tests focus on the hard concurrency surfaces:
- State file write/load cycle (atomic via tmp+rename)
- flock: second mutating invocation observes the lock and exits 2
- Rebase-in-progress detection (.git/REBASE_HEAD present)
- Partial-repo pull recovery: state pinned at pull-only after a failed repo,
  resume picks up at the next-unpulled repo
- push leak-check enforcement
- unlock semantics (only removes stale locks)
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import dotpanel.sync as sync_mod
from dotpanel.config import (
    PathsSection,
    SubstrateConfig,
    SyncRepo,
    SyncSection,
)
from dotpanel.sync import (
    PULL_PHASES,
    ResolvedRepo,
    SyncLock,
    SyncLockError,
    SyncState,
    _clear_state,
    _git_has_rebase_in_progress,
    _load_state,
    _phase_pull_only,
    _precheck_repos,
    _save_state,
    cmd_post_reload,
    cmd_pull_only,
    cmd_push,
    cmd_resume,
    cmd_status,
    cmd_unlock,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    """Initialize a minimal local git repo with one commit."""
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "test"],
        check=True,
    )
    (path / "README.md").write_text("# test\n")
    subprocess.run(
        ["git", "-C", str(path), "add", "-A"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
    )


def _make_resolved_repo(label: str, path: Path) -> ResolvedRepo:
    return ResolvedRepo(label=label, path=path, raw_path=str(path))


def _writable_home(tmpdir: Path) -> Path:
    """Build a HOME-like tmp dir with .dotpanel/ subdir."""
    home = tmpdir / "home"
    (home / ".dotpanel").mkdir(parents=True)
    return home


def _patch_state_home(home: Path) -> contextlib.ExitStack:
    """Redirect _state_dir/_state_path/_lock_path to point under `home`."""
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.object(
        sync_mod, "_state_dir",
        side_effect=lambda h=None: (h or home) / sync_mod.STATE_DIR_REL,
    ))
    stack.enter_context(mock.patch.object(
        sync_mod, "_state_path",
        side_effect=lambda h=None: (h or home) / sync_mod.STATE_DIR_REL / sync_mod.STATE_FILE,
    ))
    stack.enter_context(mock.patch.object(
        sync_mod, "_lock_path",
        side_effect=lambda h=None: (h or home) / sync_mod.STATE_DIR_REL / sync_mod.LOCK_FILE,
    ))
    return stack


# ---------------------------------------------------------------------------
# SyncState (pure)
# ---------------------------------------------------------------------------


class SyncStateTests(unittest.TestCase):
    def test_fresh_state_starts_at_precheck(self) -> None:
        s = SyncState.fresh()
        self.assertEqual(s.phase, "precheck")
        self.assertTrue(s.is_active())

    def test_done_state_inactive(self) -> None:
        s = SyncState(phase="done")
        self.assertFalse(s.is_active())

    def test_atomic_write_and_load(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                state = SyncState.fresh()
                state.repos_pulled = ["dotfiles"]
                _save_state(state)
                loaded = _load_state()
                self.assertEqual(loaded.phase, state.phase)
                self.assertEqual(loaded.repos_pulled, ["dotfiles"])

    def test_load_state_returns_done_when_file_missing(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                loaded = _load_state()
                self.assertEqual(loaded.phase, "done")
                self.assertFalse(loaded.is_active())

    def test_load_state_returns_done_when_file_corrupt(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                (home / sync_mod.STATE_DIR_REL / sync_mod.STATE_FILE
                 ).write_text("not json {")
                loaded = _load_state()
                self.assertEqual(loaded.phase, "done")

    def test_clear_state(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                _save_state(SyncState.fresh())
                _clear_state()
                p = home / sync_mod.STATE_DIR_REL / sync_mod.STATE_FILE
                self.assertFalse(p.exists())


# ---------------------------------------------------------------------------
# SyncLock (flock) — H8 concurrency guard
# ---------------------------------------------------------------------------


class SyncLockTests(unittest.TestCase):
    def test_acquires_and_releases(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                with SyncLock():
                    # File exists during the lock.
                    self.assertTrue(
                        (home / sync_mod.STATE_DIR_REL / sync_mod.LOCK_FILE).exists()
                    )
                # File still exists after the lock (open-then-close pattern);
                # the lock itself is released by close().

    def test_second_acquire_in_same_process_via_subprocess(self) -> None:
        """Hold the lock; spawn a subprocess that tries to acquire — expect SyncLockError."""
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                with SyncLock():
                    # Try to acquire from a child python process; redirect state_dir
                    # via env so the child sees the same lock path.
                    code = textwrap.dedent(f"""
                        import os, sys
                        sys.path.insert(0, {str(Path.cwd())!r})
                        from pathlib import Path
                        import dotpanel.sync as s
                        # Repoint state paths via monkey-patch
                        home = Path({str(home)!r})
                        s._state_dir = lambda h=None: home / s.STATE_DIR_REL
                        s._state_path = lambda h=None: home / s.STATE_DIR_REL / s.STATE_FILE
                        s._lock_path = lambda h=None: home / s.STATE_DIR_REL / s.LOCK_FILE
                        try:
                            with s.SyncLock():
                                print("acquired")
                                sys.exit(0)
                        except s.SyncLockError as exc:
                            print("blocked")
                            sys.exit(7)
                    """).strip()
                    cp = subprocess.run(
                        [sys.executable, "-c", code],
                        capture_output=True, text=True,
                        cwd=str(Path(__file__).resolve().parents[1]),
                    )
                    self.assertEqual(cp.returncode, 7, msg=cp.stdout + cp.stderr)
                    self.assertIn("blocked", cp.stdout)

    def test_unlock_removes_stale_lock(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                # Write a lock file with a pid that is definitely dead.
                p = home / sync_mod.STATE_DIR_REL / sync_mod.LOCK_FILE
                p.write_text("999999\n")  # very-high pid, unlikely to be alive
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = cmd_unlock()
                self.assertEqual(rc, 0)
                self.assertFalse(p.exists())

    def test_unlock_refuses_live_pid(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                p = home / sync_mod.STATE_DIR_REL / sync_mod.LOCK_FILE
                p.write_text(f"{os.getpid()}\n")  # our own pid is alive
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = cmd_unlock()
                self.assertEqual(rc, 2)
                self.assertTrue(p.exists())


# ---------------------------------------------------------------------------
# Precheck + rebase detection
# ---------------------------------------------------------------------------


class PrecheckTests(unittest.TestCase):
    def test_clean_repos_pass(self) -> None:
        with TemporaryDirectory() as t:
            r = Path(t) / "r1"
            r.mkdir()
            _init_git_repo(r)
            issues = _precheck_repos([_make_resolved_repo("r1", r)])
            self.assertEqual(issues, [])

    def test_detects_index_lock(self) -> None:
        with TemporaryDirectory() as t:
            r = Path(t) / "r1"
            r.mkdir()
            _init_git_repo(r)
            (r / ".git" / "index.lock").write_text("")
            issues = _precheck_repos([_make_resolved_repo("r1", r)])
            self.assertTrue(any("index.lock" in i for i in issues))

    def test_detects_rebase_in_progress(self) -> None:
        with TemporaryDirectory() as t:
            r = Path(t) / "r1"
            r.mkdir()
            _init_git_repo(r)
            (r / ".git" / "REBASE_HEAD").write_text("deadbeef\n")
            self.assertTrue(_git_has_rebase_in_progress(r))
            issues = _precheck_repos([_make_resolved_repo("r1", r)])
            self.assertTrue(any("rebase in progress" in i for i in issues))


# ---------------------------------------------------------------------------
# pull-only: partial-repo failure + resume continuation
# ---------------------------------------------------------------------------


class PullOnlyTests(unittest.TestCase):
    def _setup_two_local_repos(self, root: Path) -> tuple[Path, Path]:
        """Make two repos that look like they have an upstream (we'll mock pull)."""
        r1 = root / "r1"
        r2 = root / "r2"
        r1.mkdir()
        r2.mkdir()
        _init_git_repo(r1)
        _init_git_repo(r2)
        return r1, r2

    def test_partial_failure_pins_state_and_resume_continues(self) -> None:
        with TemporaryDirectory() as t:
            tmp = Path(t)
            r1, r2 = self._setup_two_local_repos(tmp)
            repos = [
                _make_resolved_repo("repo1", r1),
                _make_resolved_repo("repo2", r2),
            ]

            # First call: simulate `git pull` succeeding for repo1, failing for repo2.
            state = SyncState.fresh()
            call_log: list[Path] = []
            real_run = subprocess.run  # capture original BEFORE patching

            def fake_run(cmd, **kwargs):
                if isinstance(cmd, list) and "pull" in cmd:
                    target = Path(cmd[2])
                    call_log.append(target)
                    if target == r2:
                        return subprocess.CompletedProcess(cmd, 1)
                    return subprocess.CompletedProcess(cmd, 0)
                return real_run(cmd, **kwargs)

            with mock.patch("dotpanel.sync.subprocess.run", side_effect=fake_run):
                rc, pulled, failed = _phase_pull_only(repos, state)
            self.assertEqual(rc, 2)
            self.assertEqual(pulled, ["repo1"])
            self.assertEqual(failed, ["repo2"])
            self.assertEqual(len(call_log), 2)  # tried both

            # Second call: simulate retry — repo1 should be SKIPPED (already in pulled),
            # repo2 should be attempted again.
            state.repos_pulled = pulled
            state.repos_failed = failed
            call_log.clear()

            def fake_run2(cmd, **kwargs):
                if isinstance(cmd, list) and "pull" in cmd:
                    target = Path(cmd[2])
                    call_log.append(target)
                    return subprocess.CompletedProcess(cmd, 0)
                return real_run(cmd, **kwargs)

            with mock.patch("dotpanel.sync.subprocess.run", side_effect=fake_run2):
                rc, pulled, failed = _phase_pull_only(repos, state)
            self.assertEqual(rc, 0)
            self.assertEqual(pulled, ["repo1", "repo2"])
            self.assertEqual(failed, [])
            # Only repo2 should have been attempted on retry (repo1 already done).
            self.assertEqual(call_log, [r2])

    def test_rebase_conflict_during_pull(self) -> None:
        """If git pull fails AND REBASE_HEAD exists, surface a manual-recovery msg."""
        with TemporaryDirectory() as t:
            tmp = Path(t)
            r1 = tmp / "r1"
            r1.mkdir()
            _init_git_repo(r1)
            repos = [_make_resolved_repo("r1", r1)]
            real_run = subprocess.run

            def fake_run(cmd, **kwargs):
                if isinstance(cmd, list) and "pull" in cmd:
                    # Simulate rebase conflict: failed pull + leftover REBASE_HEAD.
                    (r1 / ".git" / "REBASE_HEAD").write_text("deadbeef\n")
                    return subprocess.CompletedProcess(cmd, 1)
                return real_run(cmd, **kwargs)

            state = SyncState.fresh()
            with mock.patch("dotpanel.sync.subprocess.run", side_effect=fake_run):
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc, pulled, failed = _phase_pull_only(repos, state)
            self.assertEqual(rc, 2)
            self.assertEqual(failed, ["r1"])
            self.assertIn("rebase conflict", err.getvalue())


# ---------------------------------------------------------------------------
# push: leak-check enforcement
# ---------------------------------------------------------------------------


class PushLeakCheckTests(unittest.TestCase):
    def _make_substrate(self, repo_path: Path,
                        leak_mode: str = "synced") -> SubstrateConfig:
        """Build a SubstrateConfig with one repo + leak_mode_overrides."""
        cfg = SubstrateConfig(root=repo_path)
        cfg.sync = SyncSection(
            repos=[SyncRepo(path=str(repo_path), label="repo1")],
            leak_mode_default="generic",
            leak_mode_overrides={str(repo_path): leak_mode},
        )
        return cfg

    def test_leak_check_refuses_push_with_violation(self) -> None:
        with TemporaryDirectory() as t:
            tmp = Path(t)
            r = tmp / "repo"
            r.mkdir()
            _init_git_repo(r)
            # Add a .env file (generic leak refuse pattern).
            (r / ".env").write_text("SECRET=42\n")
            subprocess.run(["git", "-C", str(r), "add", ".env"], check=True)

            home = _writable_home(tmp)
            with _patch_state_home(home), mock.patch(
                "dotpanel.sync._resolve_substrate",
                return_value=self._make_substrate(r),
            ):
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    rc = cmd_push()
            self.assertEqual(rc, 2)


# ---------------------------------------------------------------------------
# post-reload: configure check
# ---------------------------------------------------------------------------


class PostReloadTests(unittest.TestCase):
    def test_post_reload_no_configure_short_circuit(self) -> None:
        with TemporaryDirectory() as t:
            home = _writable_home(Path(t))
            with _patch_state_home(home):
                # Set up a state where post-reload is the next phase.
                state = SyncState.fresh()
                state.phase = "reload"
                _save_state(state)
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = cmd_post_reload(no_configure=True)
                self.assertEqual(rc, 0)
                # State file cleared on success.
                self.assertFalse(
                    (home / sync_mod.STATE_DIR_REL / sync_mod.STATE_FILE).exists()
                )


# ---------------------------------------------------------------------------
# Lock interaction with mutating subcommands
# ---------------------------------------------------------------------------


class LockedMutationTests(unittest.TestCase):
    def test_push_refuses_when_lock_held(self) -> None:
        with TemporaryDirectory() as t:
            tmp = Path(t)
            r = tmp / "repo"
            r.mkdir()
            _init_git_repo(r)
            home = _writable_home(tmp)
            cfg = SubstrateConfig(root=r)
            cfg.sync = SyncSection(
                repos=[SyncRepo(path=str(r), label="repo1")],
                leak_mode_default="generic",
                leak_mode_overrides={},
            )
            with _patch_state_home(home), mock.patch(
                "dotpanel.sync._resolve_substrate", return_value=cfg,
            ):
                with SyncLock():
                    with contextlib.redirect_stdout(io.StringIO()), \
                         contextlib.redirect_stderr(io.StringIO()):
                        rc = cmd_push()
                self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
