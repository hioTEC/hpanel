"""Phase C step 1: dotpanel.leaks happy-path coverage.

Each test creates a tmp git repo, drops candidate files, and asserts the
exit code matches the IC-4 contract:

    0   clean
    2   not-a-git-repo / usage
    3   violations
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dotpanel.leaks import check_leaks


def _git_init(repo: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    # Required because git status without an upstream is fine, but we want a
    # known starting state.
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )


class LeaksTests(unittest.TestCase):
    def test_not_a_git_repo_exits_2(self) -> None:
        with TemporaryDirectory() as t:
            rc, violations = check_leaks(Path(t), mode="generic")
            self.assertEqual(rc, 2)
            self.assertEqual(violations, [])

    def test_unknown_mode_exits_2(self) -> None:
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            rc, _ = check_leaks(repo, mode="weird")
            self.assertEqual(rc, 2)

    def test_clean_repo_exits_0(self) -> None:
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            (repo / "README.md").write_text("hello\n")
            rc, violations = check_leaks(repo, mode="generic")
            self.assertEqual(rc, 0, msg=f"unexpected violations: {violations}")

    def test_env_file_at_root_refused_generic(self) -> None:
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            (repo / ".env").write_text("SECRET=xyz\n")
            rc, violations = check_leaks(repo, mode="generic")
            self.assertEqual(rc, 3)
            self.assertIn(".env", violations)

    def test_pem_at_root_refused_generic(self) -> None:
        # v4 used `git status --porcelain --untracked-files=normal`, which only
        # surfaces untracked directory names (not files inside them) until the
        # operator has explicitly added the file. We preserve that contract:
        # untracked .pem files at the repo root *are* flagged.
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            (repo / "secret.pem").write_text("--BEGIN--\n")
            rc, violations = check_leaks(repo, mode="generic")
            self.assertEqual(rc, 3)
            self.assertIn("secret.pem", violations)

    def test_lock_file_passes_generic_but_refused_synced(self) -> None:
        # package-lock.json is a legit lock file that generic mode must allow,
        # but synced mode (used for dotfiles/dotpanel) refuses *.lock.
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            (repo / "package-lock.json").write_text("{}\n")
            rc, _ = check_leaks(repo, mode="generic")
            self.assertEqual(rc, 0)
            (repo / "scheduler.lock").write_text("pid 1\n")
            rc, violations = check_leaks(repo, mode="synced")
            self.assertEqual(rc, 3)
            self.assertIn("scheduler.lock", violations)

    def test_identity_yaml_refused_synced(self) -> None:
        with TemporaryDirectory() as t:
            repo = Path(t)
            _git_init(repo)
            (repo / "identity.yaml").write_text("name: leaked\n")
            rc, violations = check_leaks(repo, mode="synced")
            self.assertEqual(rc, 3)
            self.assertIn("identity.yaml", violations)


if __name__ == "__main__":
    unittest.main()
