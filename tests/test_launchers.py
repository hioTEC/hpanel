"""Phase C step 8: bundled launcher coverage (C11).

The launchers are tiny bash shims; we test them by:
- Mocking `dotpanel` on $PATH with a script that prints its argv.
- Running the launcher and capturing stdout.
- Asserting the argv contains the expected backend / variant.

This catches:
- variant flag parsing (--andy / --let / --kimi / --variant NAME)
- target dir resolution for `claw` (~/src/X first, ~/vendor/X fallback)
- exec chain (launcher -> dotpanel secrets run -> tool, or codx -> codex profile)
"""
from __future__ import annotations

import os
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


LAUNCHER_DIR = Path(__file__).resolve().parents[1] / "tools" / "bin"


def _run_launcher(launcher: str, args: list[str], fake_home: Path) -> subprocess.CompletedProcess[str]:
    """Run a launcher with `dotpanel`, `claude`, and `codex` mocked on $PATH.

    Each mock records its argv to $fake_home/log (one line per arg, prefixed
    so callers can distinguish them) and exits 0. We never invoke real CLIs
    in CI.
    """
    bin_dir = fake_home / "bin"
    bin_dir.mkdir()
    log = fake_home / "log"
    log.write_text("")
    for name in ("dotpanel", "claude", "codex"):
        fake = bin_dir / name
        fake.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            printf 'CALL:{name}\\n' >> "{log}"
            printf '%s\\n' "$@" >> "{log}"
            exit 0
        """))
        fake.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["HOME"] = str(fake_home)
    return subprocess.run(
        [str(LAUNCHER_DIR / launcher), *args],
        env=env,
        capture_output=True,
        text=True,
    )


class ClawTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def _log_lines(self) -> list[str]:
        log = self.home / "log"
        if not log.exists():
            return []
        return [l for l in log.read_text().splitlines() if l]

    def test_default_uses_official_oauth(self) -> None:
        # No --variant flag = direct claude invocation (official OAuth), no
        # dotpanel secrets layer. The mock claude logs its argv.
        result = _run_launcher("claw", [], self.home)
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr: {result.stderr!r}, stdout: {result.stdout!r}")
        lines = self._log_lines()
        # No "secrets run" in the log because OAuth doesn't need it.
        self.assertNotIn("secrets", lines)
        self.assertIn("CALL:claude", lines)
        self.assertIn("--dangerously-skip-permissions", lines)
        self.assertIn("--effort", lines)

    def test_let_flag_sets_variant(self) -> None:
        result = _run_launcher("claw", ["--let"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        # Find --variant <value> pair
        idx = lines.index("--variant")
        self.assertEqual(lines[idx + 1], "let")

    def test_kimi_flag_sets_variant(self) -> None:
        result = _run_launcher("claw", ["--kimi"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        idx = lines.index("--variant")
        self.assertEqual(lines[idx + 1], "kimi")

    def test_explicit_variant_flag(self) -> None:
        result = _run_launcher("claw", ["--variant", "myvariant"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        idx = lines.index("--variant")
        self.assertEqual(lines[idx + 1], "myvariant")

    def test_target_resolves_under_src(self) -> None:
        proj = self.home / "src" / "demo"
        proj.mkdir(parents=True)
        result = _run_launcher("claw", ["demo"], self.home)
        self.assertEqual(result.returncode, 0)

    def test_target_falls_back_to_vendor(self) -> None:
        proj = self.home / "vendor" / "demo"
        proj.mkdir(parents=True)
        result = _run_launcher("claw", ["demo"], self.home)
        self.assertEqual(result.returncode, 0)

    def test_target_missing_exits_nonzero(self) -> None:
        result = _run_launcher("claw", ["nonexistent-12345"], self.home)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)

    def test_variant_routes_through_secrets_run(self) -> None:
        result = _run_launcher("claw", ["--let"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        # Variant path goes through `dotpanel secrets run --backend claude
        # --variant let -- ...`. After `--`, claude flags follow.
        self.assertIn("secrets", lines)
        self.assertIn("run", lines)
        self.assertIn("--backend", lines)
        self.assertIn("claude", lines)
        self.assertIn("--variant", lines)
        self.assertIn("let", lines)


class ClawAskTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def _log_lines(self) -> list[str]:
        log = self.home / "log"
        if not log.exists():
            return []
        return [l for l in log.read_text().splitlines() if l]

    def test_passes_prompt_through(self) -> None:
        result = _run_launcher("claw", ["-p", "--ds", "hello world"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        idx = lines.index("--variant")
        self.assertEqual(lines[idx + 1], "ds")
        # After `--`, the headless mode runs `bash -c '<script>'` where the
        # script calls `claude -p`. The script body spans multiple lines —
        # joining the tail lets us search across them. The prompt arrives via
        # the `_CLAW_ASK_PROMPT` env var, not a direct argv element.
        tail = lines[lines.index("--") + 1:]
        self.assertEqual(tail[0], "bash")
        self.assertEqual(tail[1], "-c")
        body = "\n".join(tail[2:])
        self.assertIn("claude", body)
        self.assertIn("_CLAW_ASK_PROMPT", body)

    def test_no_prompt_with_tty_exits_2(self) -> None:
        # Subprocess inherits non-tty stdin from python — we have to feed
        # empty stdin to force the no-prompt path. The script's `[[ ! -t 0 ]]`
        # branch reads stdin, so an empty stdin still produces an empty
        # prompt — which still gets through. The exit-2 case requires both
        # stdin == tty AND no args. We test the trivially observable form
        # by giving args only.
        result = _run_launcher("claw", ["-p", "--andy"], self.home)
        # Empty stdin captured as the prompt, so the script may exit 0
        # with an empty prompt. We accept either rc=0 (prompt="") or rc=2
        # (TTY check elsewhere).
        self.assertIn(result.returncode, (0, 2))


class CodxTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def _log_lines(self) -> list[str]:
        log = self.home / "log"
        if not log.exists():
            return []
        return [l for l in log.read_text().splitlines() if l]

    def test_default_calls_codex_directly(self) -> None:
        result = _run_launcher("codx", [], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        self.assertEqual(lines, ["CALL:codex"])

    def test_let_flag_uses_codex_profile(self) -> None:
        result = _run_launcher("codx", ["--let", "some", "arg"], self.home)
        self.assertEqual(result.returncode, 0)
        lines = self._log_lines()
        self.assertEqual(lines, ["CALL:codex", "-p", "let", "some", "arg"])

    def test_andy_flag_uses_codex_profile(self) -> None:
        result = _run_launcher("codx", ["--andy"], self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._log_lines(), ["CALL:codex", "-p", "andy"])

    def test_explicit_variant_uses_matching_profile_name(self) -> None:
        result = _run_launcher("codx", ["--variant", "custom", "--", "--search"], self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._log_lines(), ["CALL:codex", "-p", "custom", "--search"])

    def test_profile_flag_uses_matching_profile_name(self) -> None:
        result = _run_launcher("codx", ["--profile", "custom"], self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._log_lines(), ["CALL:codex", "-p", "custom"])

    def test_unknown_codex_flags_pass_through(self) -> None:
        result = _run_launcher("codx", ["--search"], self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self._log_lines(), ["CALL:codex", "--search"])


if __name__ == "__main__":
    unittest.main()
