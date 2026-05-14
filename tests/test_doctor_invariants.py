"""Tests for v5 doctor invariants (IC-SG-4 consolidated table).

Existing v4 invariants (1-6, 13, 15) are exercised by tests/test_cli.py.
This file covers the new v5 invariants:

- 7: `.dotpanel.toml` schema validation (FAIL on SchemaError)
- 8: Path traversal (H9; via schema)
- 9: Backend↔llm_scope coherence (WARN)
- 10: Launcher PATH resolution (WARN; claw/codx)
- 11: `age` + `age-keygen` PATH (FAIL)
- 12: Multi-checkout detection (WARN)
- 14: Stale rename auto-run — covered in test_audit_stale_rename.py
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotpanel.cli import DotpanelPaths, cmd_doctor


def _seed_minimal_dotpanel(root: Path, home: Path) -> DotpanelPaths:
    (root / "protocol" / "skills").mkdir(parents=True)
    (root / "protocol" / "rules").mkdir(parents=True)
    (root / "protocol" / "reference").mkdir(parents=True)
    (root / "protocol" / "workspace.md").write_text("# Universal\n")
    (root / "harness" / "claude" / "templates").mkdir(parents=True)
    (root / "harness" / "claude" / "templates" / "CLAUDE.md").write_text("# c\n")
    (root / "harness" / "claude" / "templates" / "settings.json").write_text("{}\n")
    (root / "harness" / "codex" / "templates").mkdir(parents=True)
    (root / "harness" / "codex" / "templates" / "AGENTS.md").write_text("# a\n")
    (root / "harness" / "codex" / "templates" / "config.toml").write_text("# c\n")
    (root / "harness" / "kimi" / "templates").mkdir(parents=True)
    (root / "harness" / "kimi" / "templates" / "AGENTS.md").write_text("# k\n")
    (root / "pyproject.toml").write_text("# placeholder\n")
    persona = home / "p"
    persona.mkdir(parents=True, exist_ok=True)
    (persona / "voice.md").write_text("# v\n")
    (persona / "identity.yaml").write_text("name: x\n")
    (root / "persona").symlink_to(persona)
    return DotpanelPaths(root=root, home=home)


class AgeBinaryCheckTests(unittest.TestCase):
    """Invariant 11: age + age-keygen must be on PATH (FAIL)."""

    def test_age_present_does_not_fail(self) -> None:
        # On dev machines age is normally present; if it isn't, we can't run
        # this test meaningfully — skip rather than spuriously fail.
        if shutil.which("age") is None or shutil.which("age-keygen") is None:
            self.skipTest("age/age-keygen not installed; skipping presence test")
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("`age` binary not on PATH", combined)

    def test_age_missing_fails(self) -> None:
        # Build a PATH that has nothing but /var/empty (so age won't resolve).
        # Use patch instead of os.environ mutation to keep the override local.
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {"PATH": "/var/empty"}, clear=False):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    rc = cmd_doctor(paths, skip_stale_rename=True)
            self.assertEqual(rc, 2)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertIn("age", combined.lower())


class LauncherPathResolutionTests(unittest.TestCase):
    """Invariant 10: claw/codx must resolve under <root>/tools/bin/ (WARN)."""

    def test_launcher_resolved_to_bundled_passes(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            bundled_bin = paths.root / "tools" / "bin"
            bundled_bin.mkdir(parents=True)
            (bundled_bin / "claw").write_text("#!/bin/sh\necho claw\n")
            (bundled_bin / "claw").chmod(0o755)
            (bundled_bin / "codx").write_text("#!/bin/sh\necho codx\n")
            (bundled_bin / "codx").chmod(0o755)
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {"PATH": f"{bundled_bin}:" + os.environ.get("PATH", "")}):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("shadowing the dotpanel launcher", combined)

    def test_launcher_shadowed_warns(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            bundled_bin = paths.root / "tools" / "bin"
            bundled_bin.mkdir(parents=True)
            (bundled_bin / "claw").write_text("#!/bin/sh\necho claw\n")
            (bundled_bin / "claw").chmod(0o755)
            # A shadow `claw` in another dir, earlier on PATH.
            shadow_dir = Path(t) / "shadow"
            shadow_dir.mkdir()
            (shadow_dir / "claw").write_text("#!/bin/sh\necho shadow\n")
            (shadow_dir / "claw").chmod(0o755)
            (shadow_dir / "codx").write_text("#!/bin/sh\necho c\n")
            (shadow_dir / "codx").chmod(0o755)
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {"PATH": f"{shadow_dir}:{bundled_bin}"}):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertIn("shadowing the dotpanel launcher", combined)


class BackendScopeCoherenceTests(unittest.TestCase):
    """Invariant 9: backend variant key matches at least one llm_scope (WARN)."""

    def _write_toml(self, substrate: Path, body: str) -> None:
        (substrate / ".dotpanel.toml").write_text(body)
        (substrate / "persona").mkdir(parents=True, exist_ok=True)
        (substrate / "persona" / "voice.md").write_text("# v\n")
        (substrate / "persona" / "identity.yaml").write_text("name: x\n")

    def test_orphan_backend_key_warns(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            sub = paths.home / "sub"
            sub.mkdir()
            self._write_toml(sub, """
[dotpanel]
schema_version = "1.0"

[paths]
persona = "persona"

[harness]
enabled = ["claude"]

[secrets]
llm_scope = ["CLAUDE_*"]

[backends.codex]
default = "tencent"

[backends.codex.variants.tencent]
key = "TENCENT_CODEX_KEY"
env_alias = "OPENAI_API_KEY"
""")
            stdout, stderr = StringIO(), StringIO()
            # Mock substrate discovery to return our synthetic substrate.
            with patch.dict(os.environ, {"DOTPANEL_SUBSTRATE": str(sub)}):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertIn("TENCENT_CODEX_KEY", combined)
            self.assertIn("llm_scope", combined)
            self.assertIn("codx --vscode --variant <profile>", combined)

    def test_matching_backend_key_no_warn(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            sub = paths.home / "sub"
            sub.mkdir()
            self._write_toml(sub, """
[dotpanel]
schema_version = "1.0"

[paths]
persona = "persona"

[harness]
enabled = ["claude"]

[secrets]
llm_scope = ["CLAUDE_*", "ANDYFENG_*"]

[backends.claude]
default = "andy"

[backends.claude.variants.andy]
key = "ANDYFENG_CLAUDE_KEY"
env_alias = "ANTHROPIC_AUTH_TOKEN"
""")
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {"DOTPANEL_SUBSTRATE": str(sub)}):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("ANDYFENG_CLAUDE_KEY", combined)


class VSCodeExtensionEnvTests(unittest.TestCase):
    """Invariant 16: VS Code agent extensions need server-env-setup."""

    def test_claude_code_extension_without_setup_warns(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            extension = paths.home / ".vscode-server" / "extensions" / "anthropic.claude-code-1.2.3"
            extension.mkdir(parents=True)

            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertIn("VSCode Claude Code extension", combined)
            self.assertIn("claw --vscode --variant <name>", combined)
            self.assertIn("claw --vscode --official", combined)

    def test_codex_extension_without_setup_warns(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            extension = paths.home / ".vscode-server" / "extensions" / "openai.chatgpt-1.2.3"
            extension.mkdir(parents=True)

            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertIn("VSCode Codex extension", combined)
            self.assertIn("codx --vscode --variant <profile>", combined)
            self.assertIn("codx --vscode --openai", combined)

    def test_existing_setup_suppresses_extension_warnings(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            extensions = paths.home / ".vscode-server" / "extensions"
            (extensions / "anthropic.claude-code-1.2.3").mkdir(parents=True)
            (extensions / "openai.chatgpt-1.2.3").mkdir(parents=True)
            (paths.home / ".vscode-server" / "server-env-setup").write_text("# setup\n")

            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertNotIn("VSCode Claude Code extension", combined)
            self.assertNotIn("VSCode Codex extension", combined)


class SchemaValidationTests(unittest.TestCase):
    """Invariant 7+8: .dotpanel.toml schema + H9 path-traversal."""

    def test_path_traversal_fails(self) -> None:
        with TemporaryDirectory() as t:
            paths = _seed_minimal_dotpanel(Path(t), Path(t))
            sub = paths.home / "sub"
            sub.mkdir()
            (sub / ".dotpanel.toml").write_text("""
[dotpanel]
schema_version = "1.0"

[paths]
persona = "../../etc/passwd"
""")
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {"DOTPANEL_SUBSTRATE": str(sub)}):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    rc = cmd_doctor(paths, skip_stale_rename=True)
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(rc, 2)
            self.assertTrue(
                "escapes substrate root" in combined
                or "schema validation" in combined.lower()
            )


if __name__ == "__main__":
    unittest.main()
