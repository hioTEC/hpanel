"""Phase B/C: `.dotpanel.toml` loader + path-traversal validation (H9)."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dotpanel.config import SchemaError, SubstrateNotFound, find_substrate, load_toml


_MINIMAL = """\
[dotpanel]
schema_version = "1.0"

[paths]
persona = "persona"
infra = "infra"
"""


class LoaderTests(unittest.TestCase):
    def _write(self, root: Path, body: str) -> Path:
        toml = root / ".dotpanel.toml"
        toml.write_text(body)
        (root / "persona").mkdir(parents=True, exist_ok=True)
        (root / "infra").mkdir(parents=True, exist_ok=True)
        return toml

    def test_loads_minimal_config(self) -> None:
        with TemporaryDirectory() as t:
            toml = self._write(Path(t), _MINIMAL)
            cfg = load_toml(toml)
            self.assertEqual(cfg.schema_version, "1.0")
            self.assertTrue(cfg.paths is not None)
            self.assertEqual(cfg.paths.persona.name, "persona")

    def test_rejects_path_traversal_in_paths(self) -> None:
        # H9: any [paths.*] field that escapes substrate root is rejected.
        body = '[dotpanel]\nschema_version = "1.0"\n[paths]\npersona = "../../etc/passwd"\n'
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            with self.assertRaises(SchemaError):
                load_toml(toml)

    def test_rejects_absolute_path_outside_age_allowlist(self) -> None:
        body = (
            '[dotpanel]\nschema_version = "1.0"\n'
            '[paths]\nsecret_bundle = "/etc/passwd"\n'
        )
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            with self.assertRaises(SchemaError):
                load_toml(toml)

    def test_allows_age_allowlist_absolute(self) -> None:
        # Only secret_bundle / secret_pubkey may be absolute under ~/.config/age/
        age_dir = Path.home() / ".config" / "age"
        age_dir.mkdir(parents=True, exist_ok=True)
        body = (
            '[dotpanel]\nschema_version = "1.0"\n'
            f'[paths]\nsecret_bundle = "{age_dir}/test.age"\n'
        )
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            cfg = load_toml(toml)
            self.assertIsNotNone(cfg.paths)

    def test_rejects_unsupported_major_version(self) -> None:
        body = '[dotpanel]\nschema_version = "2.0"\n'
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            with self.assertRaises(SchemaError):
                load_toml(toml)

    def test_loads_backends_with_env_alias(self) -> None:
        body = """\
[dotpanel]
schema_version = "1.0"

[backends]
default_provider = "claude"

[backends.claude]
default = "andy"

[backends.claude.variants.andy]
key = "ANDYFENG_CLAUDE_KEY"
env_alias = "ANTHROPIC_AUTH_TOKEN"
base_url = "https://api.example.com"
"""
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            cfg = load_toml(toml)
            self.assertIn("claude", cfg.backends.providers)
            variant = cfg.backends.providers["claude"].variants["andy"]
            self.assertEqual(variant.key, "ANDYFENG_CLAUDE_KEY")
            self.assertEqual(variant.env_alias, "ANTHROPIC_AUTH_TOKEN")
            self.assertEqual(variant.base_url, "https://api.example.com")

    def test_loads_secrets_llm_scope(self) -> None:
        body = (
            '[dotpanel]\nschema_version = "1.0"\n'
            '[secrets]\nllm_scope = ["ANDYFENG_*", "OPENAI_*"]\n'
        )
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            cfg = load_toml(toml)
            self.assertEqual(cfg.secrets.llm_scope, ["ANDYFENG_*", "OPENAI_*"])

    def test_skills_disabled_and_per_skill(self) -> None:
        body = """\
[dotpanel]
schema_version = "1.0"

[skills]
disabled = ["plan"]

[skills.teamleader]
harnesses = ["claude"]
"""
        with TemporaryDirectory() as t:
            toml = Path(t) / ".dotpanel.toml"
            toml.write_text(body)
            cfg = load_toml(toml)
            self.assertIn("plan", cfg.skills.disabled)
            self.assertIn("teamleader", cfg.skills.per_skill)
            self.assertEqual(cfg.skills.per_skill["teamleader"]["harnesses"], ["claude"])


class DiscoveryTests(unittest.TestCase):
    def test_env_override_pointing_at_empty_dir_raises(self) -> None:
        with TemporaryDirectory() as t:
            os.environ["DOTPANEL_SUBSTRATE"] = t
            try:
                with self.assertRaises(SubstrateNotFound):
                    find_substrate()
            finally:
                os.environ.pop("DOTPANEL_SUBSTRATE", None)

    def test_env_override_pointing_at_substrate(self) -> None:
        with TemporaryDirectory() as t:
            root = Path(t)
            (root / "persona").mkdir()
            (root / "infra").mkdir()
            (root / ".dotpanel.toml").write_text(_MINIMAL)
            os.environ["DOTPANEL_SUBSTRATE"] = t
            try:
                cfg = find_substrate()
                self.assertEqual(cfg.root, root.resolve())
            finally:
                os.environ.pop("DOTPANEL_SUBSTRATE", None)


if __name__ == "__main__":
    unittest.main()
