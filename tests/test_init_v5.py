"""Tests for `dotpanel init` v5 seed template (per design)."""
from __future__ import annotations

import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from dotpanel.cli import DotpanelPaths, cmd_init, _seed_v5_substrate_skeleton


def _seed_minimal_dotpanel(root: Path, home: Path) -> DotpanelPaths:
    """Build minimum dotpanel tree so cmd_init can run without unrelated FAILs."""
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
    return DotpanelPaths(root=root, home=home)


class SeedV5SubstrateSkeletonTests(unittest.TestCase):
    """The _seed_v5_substrate_skeleton helper produces the v5 expected layout."""

    def test_creates_skills_dir_and_readme(self) -> None:
        with TemporaryDirectory() as t:
            substrate = Path(t)
            _seed_v5_substrate_skeleton(substrate)
            self.assertTrue((substrate / "skills").is_dir())
            self.assertTrue((substrate / "skills" / "README.md").is_file())
            body = (substrate / "skills" / "README.md").read_text()
            self.assertIn("Substrate skills", body)
            self.assertIn("override", body.lower())

    def test_creates_tools_bin_and_example_template(self) -> None:
        with TemporaryDirectory() as t:
            substrate = Path(t)
            _seed_v5_substrate_skeleton(substrate)
            self.assertTrue((substrate / "tools" / "bin").is_dir())
            template = substrate / "tools" / "bin" / "example-backup.sh.template"
            self.assertTrue(template.is_file())
            body = template.read_text()
            self.assertIn("#!/usr/bin/env bash", body)
            self.assertIn("dotpanel secrets run", body)

    def test_creates_minimal_dotpanel_toml(self) -> None:
        with TemporaryDirectory() as t:
            substrate = Path(t)
            _seed_v5_substrate_skeleton(substrate)
            toml = substrate / ".dotpanel.toml"
            self.assertTrue(toml.is_file())
            body = toml.read_text()
            self.assertIn('schema_version = "1.0"', body)
            self.assertIn('[paths]', body)
            self.assertIn('persona = "persona"', body)

    def test_idempotent_does_not_clobber_existing_toml(self) -> None:
        with TemporaryDirectory() as t:
            substrate = Path(t)
            existing = substrate / ".dotpanel.toml"
            existing.write_text("[dotpanel]\nschema_version = \"1.0\"\n# operator note\n")
            _seed_v5_substrate_skeleton(substrate)
            # File preserved verbatim.
            self.assertEqual(
                existing.read_text(),
                "[dotpanel]\nschema_version = \"1.0\"\n# operator note\n",
            )

    def test_idempotent_re_run_does_not_error(self) -> None:
        with TemporaryDirectory() as t:
            substrate = Path(t)
            _seed_v5_substrate_skeleton(substrate)
            # Second invocation must not crash; existing files are kept.
            _seed_v5_substrate_skeleton(substrate)
            self.assertTrue((substrate / "skills" / "README.md").is_file())


class CmdInitV5Tests(unittest.TestCase):
    """End-to-end: cmd_init lays down the skeleton + persona symlink."""

    def test_init_lays_down_substrate_skeleton(self) -> None:
        with TemporaryDirectory() as t:
            tmp = Path(t)
            dotpanel_src = tmp / "dotpanel-src"
            dotpanel_src.mkdir()
            home = tmp / "home"
            home.mkdir()
            paths = _seed_minimal_dotpanel(dotpanel_src, home)

            # Make a substrate at home/sub with a persona/ subdir.
            substrate = home / "sub"
            persona = substrate / "persona"
            persona.mkdir(parents=True)
            (persona / "voice.md").write_text("# v\n")
            (persona / "identity.yaml").write_text("name: x\n")

            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                cmd_init(paths, persona)

            # Skeleton must be written under the substrate root (persona.parent).
            self.assertTrue((substrate / "skills").is_dir())
            self.assertTrue((substrate / "skills" / "README.md").is_file())
            self.assertTrue((substrate / "tools" / "bin").is_dir())
            self.assertTrue(
                (substrate / "tools" / "bin" / "example-backup.sh.template").is_file()
            )
            self.assertTrue((substrate / ".dotpanel.toml").is_file())

    def test_init_prints_next_steps_hint(self) -> None:
        with TemporaryDirectory() as t:
            tmp = Path(t)
            dotpanel_src = tmp / "dotpanel-src"
            dotpanel_src.mkdir()
            home = tmp / "home"
            home.mkdir()
            paths = _seed_minimal_dotpanel(dotpanel_src, home)

            substrate = home / "sub"
            persona = substrate / "persona"
            persona.mkdir(parents=True)
            (persona / "voice.md").write_text("# v\n")
            (persona / "identity.yaml").write_text("name: x\n")

            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                cmd_init(paths, persona)

            out = stdout.getvalue()
            # init now auto-injects path.sh via inject_shell_rc, so the manual
            # source-line hint is gone; the bootstrap hint covers what's left.
            self.assertIn("dotpanel secrets init --keygen", out)
            self.assertIn("dotpanel configure --harness all", out)
            self.assertIn("dotpanel doctor", out)


if __name__ == "__main__":
    unittest.main()
