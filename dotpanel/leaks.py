"""dotpanel.leaks — secret-leak guard for git working trees.

Exit codes:

- 0  clean
- 2  usage error / not a git repo
- 3  one or more violations (refuse to commit)

Patterns:

Generic (any mode):
    .env*, *.pem, *.key, *id_rsa*, *id_ed25519*,
    credentials, credentials.json, *service-account*.json, .npmrc

Synced mode (substrate + dotpanel + harness homes; stricter):
    .machine-id, identity.yaml          (machine/personal identity — never sync)
    *.lock, *.sock, ide/*               (per-machine runtime: vscode plugin port
                                         locks, scheduler locks, editor sockets)

The patterns operate on `git status --porcelain --untracked-files=normal`
output, so files already ignored by `.gitignore` are not flagged (we only
guard against ones about to be committed or already in the working tree).
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path


GENERIC_REFUSE = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*id_rsa*",
    "*id_ed25519*",
    "credentials",
    "credentials.json",
    "*service-account*.json",
    ".npmrc",
)

SYNCED_REFUSE = (
    ".machine-id",
    "identity.yaml",
    "*.lock",
    "*.sock",
)

# Directory prefixes that are refused under --mode synced.
SYNCED_REFUSE_DIRS = ("ide/",)


def _matches_pattern(path: str, patterns: tuple[str, ...]) -> bool:
    """True if path basename or full path matches any glob in patterns.

    Mirrors the v4 bash case statement which checked both bare basename
    patterns (`.env`) and `*/...` prefixed forms by relying on shell glob
    matching of the full path.
    """
    basename = path.rsplit("/", 1)[-1] if "/" in path else path
    for pat in patterns:
        if fnmatch.fnmatchcase(basename, pat) or fnmatch.fnmatchcase(path, pat):
            return True
        # The v4 script also matched `*/<pat>` for things like `.env*` and
        # `credentials.json` at non-root levels. fnmatch handles that when we
        # match the full path against `*/<pat>`.
        if fnmatch.fnmatchcase(path, f"*/{pat}"):
            return True
    return False


def _matches_dir_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if path.startswith(prefix) or f"/{prefix}" in f"/{path}":
            return True
    return False


def _git_status_files(repo: Path) -> list[str]:
    """Return the list of changed-or-untracked paths from `git status --porcelain`.

    Bash equivalent: `git -C "$dir" status --porcelain --untracked-files=normal | awk '{print $NF}'`.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=normal"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # Status lines look like ` M path/to/file` or `?? path/to/file` —
        # we want the last field.
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            files.append(parts[1])
        else:
            files.append(parts[0])
    return files


def _is_git_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def check_leaks(repo: Path, mode: str = "") -> tuple[int, list[str]]:
    """Run the leak check.

    Returns (exit_code, violations). Exit code is 0 (clean), 2 (not a git repo
    or invalid mode), or 3 (violations).
    """
    if mode not in ("", "synced", "generic"):
        return 2, []
    if not _is_git_repo(repo):
        return 2, []

    patterns = tuple(GENERIC_REFUSE)
    if mode == "synced":
        patterns = patterns + tuple(SYNCED_REFUSE)

    violations: list[str] = []
    for path in _git_status_files(repo):
        if _matches_pattern(path, patterns):
            violations.append(path)
            continue
        if mode == "synced" and _matches_dir_prefix(path, SYNCED_REFUSE_DIRS):
            violations.append(path)

    return (3 if violations else 0), violations


def cmd_leaks(repo: Path, mode: str = "") -> int:
    rc, violations = check_leaks(repo, mode)
    if rc == 2:
        if not _is_git_repo(repo):
            print(f"ERROR: not a git repo: {repo}", file=sys.stderr)
        else:
            print(f"ERROR: unknown mode: {mode}", file=sys.stderr)
        return 2
    if rc == 3:
        print(
            f"REFUSING — secret/credential files in {repo.name} working tree:",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            "These should be .gitignore'd. Resolve before committing.",
            file=sys.stderr,
        )
        return 3
    return 0


def build_leaks_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=("generic", "synced"),
        default="generic",
        help="leak profile (default: generic; synced is stricter, used for dotfiles/dotpanel sync)",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=None,
        help="git working tree to scan (default: $PWD)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotpanel leaks")
    build_leaks_parser(parser)
    args = parser.parse_args(argv)
    repo = args.directory or Path.cwd()
    return cmd_leaks(repo.resolve(), args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
