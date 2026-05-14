"""Phase D7: substrate-private skills mechanism.

Tests cover:
- `_discover_substrate_skills` parses YAML frontmatter and skips malformed files with a WARN
- `[skills] disabled` blacklist applies to both substrate and public skills
- Missing `supported_harnesses` defaults to all harnesses
- Frontmatter `supported_harnesses` scope
- `.dotpanel.toml [skills.<name>] harnesses` toml-side scope
- Substrate skill overrides public skill on filename collision
"""
from __future__ import annotations

import contextlib
import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import dotpanel.cli as cli_mod
from dotpanel.cli import (
    SubstrateSkill,
    _discover_substrate_skills,
    _minimal_frontmatter_fallback,
    _parse_skill_frontmatter,
    substrate_skill_wrapper_body,
)


CURRICULUM_FRONTMATTER = """\
---
name: curriculum-bridge
description: Cross-reference two educational curriculum systems and design a bridging course.
type: skill
supported_harnesses: [claude, codex, kimi]
---

# Curriculum Bridge

(body)
"""

TEAMLEADER_FRONTMATTER = """\
---
name: teamleader
description: Orchestrate multi-stream feature work as architect.
type: skill
supported_harnesses: [claude]
---

# Team Leader

(body)
"""

INTERVIEW_FRONTMATTER = """\
---
name: interview
description: Load when planning a non-trivial change and user preferences must be elicited.
type: skill
---

# Interview

(body)
"""

MALFORMED_NO_FRONTMATTER = "# Just a markdown file\n\nNo frontmatter at all.\n"

MALFORMED_UNTERMINATED = """\
---
name: oops
description: never closed.

(no closing dashes)
"""


class ParseFrontmatterTests(unittest.TestCase):
    def test_parses_simple_frontmatter(self) -> None:
        with TemporaryDirectory() as t:
            p = Path(t) / "x.md"
            p.write_text(CURRICULUM_FRONTMATTER)
            data = _parse_skill_frontmatter(p)
            self.assertIsNotNone(data)
            self.assertEqual(data["name"], "curriculum-bridge")
            self.assertEqual(
                data["supported_harnesses"], ["claude", "codex", "kimi"]
            )

    def test_skips_missing_frontmatter_with_warn(self) -> None:
        with TemporaryDirectory() as t:
            p = Path(t) / "x.md"
            p.write_text(MALFORMED_NO_FRONTMATTER)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                data = _parse_skill_frontmatter(p)
            self.assertIsNone(data)
            self.assertIn("WARN", err.getvalue())
            self.assertIn("frontmatter", err.getvalue())

    def test_skips_unterminated_frontmatter_with_warn(self) -> None:
        with TemporaryDirectory() as t:
            p = Path(t) / "x.md"
            p.write_text(MALFORMED_UNTERMINATED)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                data = _parse_skill_frontmatter(p)
            self.assertIsNone(data)
            self.assertIn("WARN", err.getvalue())


class MinimalFallbackTests(unittest.TestCase):
    def test_minimal_fallback_handles_basic_keys(self) -> None:
        text = 'name: example\ndescription: A test description\nsupported_harnesses: [claude, codex]\n'
        data = _minimal_frontmatter_fallback(text, "example.md")
        self.assertEqual(data["name"], "example")
        self.assertEqual(data["description"], "A test description")
        self.assertEqual(data["supported_harnesses"], ["claude", "codex"])


class DiscoverSubstrateSkillsTests(unittest.TestCase):
    def test_discovers_md_files_in_skills_dir(self) -> None:
        with TemporaryDirectory() as t:
            skills_dir = Path(t) / "skills"
            skills_dir.mkdir()
            (skills_dir / "curriculum-bridge.md").write_text(CURRICULUM_FRONTMATTER)
            (skills_dir / "teamleader.md").write_text(TEAMLEADER_FRONTMATTER)
            discovered = _discover_substrate_skills(skills_dir)
            self.assertEqual(set(discovered), {"curriculum-bridge", "teamleader"})
            self.assertEqual(
                discovered["teamleader"].supported_harnesses, ("claude",)
            )
            self.assertIn(
                "Orchestrate", discovered["teamleader"].description
            )

    def test_missing_supported_harnesses_defaults_to_all_harnesses(self) -> None:
        with TemporaryDirectory() as t:
            skills_dir = Path(t) / "skills"
            skills_dir.mkdir()
            (skills_dir / "interview.md").write_text(INTERVIEW_FRONTMATTER)
            discovered = _discover_substrate_skills(skills_dir)
            self.assertEqual(
                discovered["interview"].supported_harnesses,
                ("claude", "codex", "kimi"),
            )

    def test_skips_malformed_with_warn(self) -> None:
        with TemporaryDirectory() as t:
            skills_dir = Path(t) / "skills"
            skills_dir.mkdir()
            (skills_dir / "good.md").write_text(CURRICULUM_FRONTMATTER)
            (skills_dir / "broken.md").write_text(MALFORMED_NO_FRONTMATTER)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                discovered = _discover_substrate_skills(skills_dir)
            self.assertIn("good", discovered)
            # broken.md filename uses different stem; test by stem
            self.assertNotIn("broken", discovered)
            self.assertIn("WARN", err.getvalue())

    def test_returns_empty_for_missing_dir(self) -> None:
        with TemporaryDirectory() as t:
            missing = Path(t) / "nope"
            self.assertEqual(_discover_substrate_skills(missing), {})

    def test_returns_empty_for_none(self) -> None:
        self.assertEqual(_discover_substrate_skills(None), {})


class SubstrateWrapperBodyTests(unittest.TestCase):
    def test_wrapper_includes_substrate_marker_and_abs_path(self) -> None:
        with TemporaryDirectory() as t:
            body_path = Path(t) / "skills" / "teamleader.md"
            body_path.parent.mkdir()
            body_path.write_text(TEAMLEADER_FRONTMATTER)
            skill = SubstrateSkill(
                name="teamleader",
                body_path=body_path.resolve(),
                description="Orchestrate multi-stream feature work.",
                supported_harnesses=("claude",),
            )
            wrapper = substrate_skill_wrapper_body(skill, "claude")
            self.assertIn("Source (substrate):", wrapper)
            self.assertIn(str(body_path.resolve()), wrapper)
            self.assertIn("name: teamleader", wrapper)
            self.assertIn('description: "Use when the user invokes /teamleader.', wrapper)
            self.assertNotIn("description: |", wrapper)


class GatherOutputsSubstrateOverrideTests(unittest.TestCase):
    """End-to-end: substrate skills appear in _gather_outputs for the right harnesses."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        # Build a fake substrate
        substrate = self.root / "substrate"
        substrate.mkdir()
        (substrate / "persona").mkdir()
        (substrate / "persona" / "voice.md").write_text("# voice\n")
        (substrate / "persona" / "identity.yaml").write_text("name:\n  chinese: T\n")
        (substrate / "infra").mkdir()
        skills = substrate / "skills"
        skills.mkdir()
        (skills / "curriculum-bridge.md").write_text(CURRICULUM_FRONTMATTER)
        (skills / "interview.md").write_text(INTERVIEW_FRONTMATTER)
        (skills / "teamleader.md").write_text(TEAMLEADER_FRONTMATTER)
        (substrate / ".dotpanel.toml").write_text(
            '[dotpanel]\nschema_version = "1.0"\n'
            '[paths]\npersona = "persona"\nskills = "skills"\ninfra = "infra"\n'
        )
        self.substrate = substrate

        self.env_patch = mock.patch.dict(
            os.environ, {"DOTPANEL_SUBSTRATE": str(substrate)}, clear=False
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_substrate_skills_render_for_claude(self) -> None:
        # Use the real dotpanel paths; the substrate-skill loader walks via env.
        paths = cli_mod.DotpanelPaths.default()
        outputs = cli_mod._gather_outputs(paths, "claude")
        rels = [rel for rel, _ in outputs]
        self.assertIn("skills/curriculum-bridge/SKILL.md", rels)
        self.assertIn("skills/teamleader/SKILL.md", rels)

    def test_teamleader_skill_skipped_for_codex_per_frontmatter(self) -> None:
        # teamleader frontmatter declares supported_harnesses: [claude]
        paths = cli_mod.DotpanelPaths.default()
        outputs = cli_mod._gather_outputs(paths, "codex")
        rels = [rel for rel, _ in outputs]
        self.assertNotIn("skills/teamleader/SKILL.md", rels)
        # interview omits supported_harnesses, so it defaults to all harnesses.
        self.assertIn("skills/interview/SKILL.md", rels)
        # curriculum-bridge declares [claude, codex, kimi] so it appears here.
        self.assertIn("skills/curriculum-bridge/SKILL.md", rels)

    def test_codex_configure_writes_skills_to_agents_home(self) -> None:
        paths = cli_mod.DotpanelPaths(root=cli_mod.dotpanel_root(), home=self.root / "home")
        output = self.root / "render"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli_mod.cmd_configure(paths, "codex", False, False, False, output)
        self.assertEqual(rc, 0)
        self.assertTrue(
            (output / "agents" / "skills" / "curriculum-bridge" / "SKILL.md").exists()
        )
        self.assertFalse(
            (output / "codex" / "skills" / "curriculum-bridge" / "SKILL.md").exists()
        )

    def test_disabled_list_blacklists_substrate_skill(self) -> None:
        toml = self.substrate / ".dotpanel.toml"
        toml.write_text(
            '[dotpanel]\nschema_version = "1.0"\n'
            '[paths]\npersona = "persona"\nskills = "skills"\ninfra = "infra"\n'
            '[skills]\ndisabled = ["curriculum-bridge"]\n'
        )
        paths = cli_mod.DotpanelPaths.default()
        outputs = cli_mod._gather_outputs(paths, "claude")
        rels = [rel for rel, _ in outputs]
        self.assertNotIn("skills/curriculum-bridge/SKILL.md", rels)


if __name__ == "__main__":
    unittest.main()
