"""Phase D5: PATH injection via `dotpanel configure`.

Covers:
- `write_path_sh` writes a whole-file with banner header
- Repeated invocation is idempotent (status="noop" on second call)
- Bundled bin always injected; substrate bin conditional
- `inject_shell_rc` appends one line; second call is noop
- Double-invocation safe (no duplicate lines)
- Detection picks the right rc file from $SHELL
- `--output-dir` mode skips PATH injection entirely
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from dotpanel.cli import (
    PATH_SH_BANNER,
    PATH_SH_REL,
    PATH_SH_SOURCE_LINE,
    _detect_shell_rcs,
    inject_shell_rc,
    write_path_sh,
)


class WritePathShTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.dotpanel_root = self.home / "src" / "dotpanel"
        (self.dotpanel_root / "tools" / "bin").mkdir(parents=True)

    def test_writes_path_sh_with_bundled_only(self) -> None:
        status, target = write_path_sh(self.home, self.dotpanel_root, None)
        self.assertEqual(status, "wrote")
        self.assertEqual(target, self.home / PATH_SH_REL)
        body = target.read_text(encoding="utf-8")
        self.assertIn(PATH_SH_BANNER, body)
        self.assertIn(str(self.dotpanel_root / "tools" / "bin"), body)
        # Banner-managed whole file; only one export line when substrate bin is None.
        export_lines = [line for line in body.splitlines() if line.startswith("export PATH=")]
        self.assertEqual(len(export_lines), 1)

    def test_writes_path_sh_with_substrate_bin(self) -> None:
        substrate_bin = self.home / "dotfiles" / "tools" / "bin"
        substrate_bin.mkdir(parents=True)
        status, target = write_path_sh(
            self.home, self.dotpanel_root, substrate_bin.resolve()
        )
        self.assertEqual(status, "wrote")
        body = target.read_text(encoding="utf-8")
        export_lines = [line for line in body.splitlines() if line.startswith("export PATH=")]
        self.assertEqual(len(export_lines), 2)
        self.assertTrue(any(str(substrate_bin) in line for line in export_lines))

    def test_idempotent_second_call_is_noop(self) -> None:
        status1, target = write_path_sh(self.home, self.dotpanel_root, None)
        self.assertEqual(status1, "wrote")
        body1 = target.read_text(encoding="utf-8")
        status2, target2 = write_path_sh(self.home, self.dotpanel_root, None)
        self.assertEqual(status2, "noop")
        self.assertEqual(target2, target)
        body2 = target.read_text(encoding="utf-8")
        self.assertEqual(body1, body2)

    def test_dry_run_returns_would_no_write(self) -> None:
        status, target = write_path_sh(
            self.home, self.dotpanel_root, None, dry_run=True
        )
        self.assertEqual(status, "would")
        self.assertFalse(target.exists())

    def test_uses_absolute_path_not_tilde(self) -> None:
        # D5 spec: absolute paths baked in at render time so the multi-checkout
        # case doesn't suffer from $HOME expansion drift.
        status, target = write_path_sh(self.home, self.dotpanel_root, None)
        body = target.read_text(encoding="utf-8")
        for line in body.splitlines():
            if line.startswith("export PATH="):
                # Each export line should reference an absolute path, never a tilde.
                self.assertNotIn("~/", line)
                self.assertNotIn("$HOME", line)


class InjectShellRcTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        # Default: simulate bash environment so the bashrc path is chosen.
        self.env_patch = mock.patch.dict(
            os.environ, {"SHELL": "/bin/bash"}, clear=False
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_appends_single_line_to_bashrc(self) -> None:
        # Pre-create .bashrc with some content
        (self.home / ".bashrc").write_text("# existing\nexport FOO=bar\n")
        results = inject_shell_rc(self.home)
        self.assertEqual(len(results), 1)
        status, rc = results[0]
        self.assertEqual(status, "appended")
        self.assertEqual(rc.name, ".bashrc")
        body = rc.read_text(encoding="utf-8")
        self.assertIn(PATH_SH_SOURCE_LINE, body)
        # Original content preserved.
        self.assertIn("export FOO=bar", body)

    def test_second_invocation_is_noop(self) -> None:
        (self.home / ".bashrc").write_text("")
        first = inject_shell_rc(self.home)
        self.assertEqual(first[0][0], "appended")
        second = inject_shell_rc(self.home)
        self.assertEqual(second[0][0], "noop")
        # Verify only one source line in the file (double-invocation safety).
        body = (self.home / ".bashrc").read_text(encoding="utf-8")
        occurrences = body.count(PATH_SH_SOURCE_LINE)
        self.assertEqual(occurrences, 1)

    def test_creates_rc_when_missing(self) -> None:
        # If .bashrc doesn't exist but $SHELL points at bash, the rc is created.
        results = inject_shell_rc(self.home)
        statuses = {s for s, _ in results}
        self.assertIn("appended", statuses)
        self.assertTrue((self.home / ".bashrc").exists())

    def test_dry_run_does_not_write(self) -> None:
        results = inject_shell_rc(self.home, dry_run=True)
        self.assertTrue(all(s == "would" for s, _ in results))
        self.assertFalse((self.home / ".bashrc").exists())

    def test_zsh_detection_from_existing_zshrc(self) -> None:
        (self.home / ".zshrc").write_text("# zsh\n")
        results = inject_shell_rc(self.home)
        rc_paths = {rc.name for _, rc in results}
        self.assertIn(".zshrc", rc_paths)

    def test_both_shells_when_both_rcs_exist(self) -> None:
        (self.home / ".bashrc").write_text("")
        (self.home / ".zshrc").write_text("")
        results = inject_shell_rc(self.home)
        rc_paths = {rc.name for _, rc in results}
        self.assertEqual(rc_paths, {".bashrc", ".zshrc"})

    def test_handles_rc_without_trailing_newline(self) -> None:
        # Tricky edge case: appending to a file that doesn't end in \n
        # must not glue our line onto an existing line.
        (self.home / ".bashrc").write_text("export FOO=bar")  # no trailing \n
        results = inject_shell_rc(self.home)
        self.assertEqual(results[0][0], "appended")
        body = (self.home / ".bashrc").read_text(encoding="utf-8")
        # Source line should appear on its own line.
        self.assertIn(f"\n{PATH_SH_SOURCE_LINE}", body)


class DetectShellRcsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_falls_back_to_bashrc_when_nothing_detected(self) -> None:
        with mock.patch.dict(os.environ, {"SHELL": ""}, clear=False):
            rcs = _detect_shell_rcs(self.home)
        self.assertEqual(rcs, [self.home / ".bashrc"])

    def test_zsh_via_shell_env(self) -> None:
        with mock.patch.dict(os.environ, {"SHELL": "/usr/bin/zsh"}, clear=False):
            rcs = _detect_shell_rcs(self.home)
        self.assertEqual(rcs, [self.home / ".zshrc"])


if __name__ == "__main__":
    unittest.main()
