"""Phase C step 2: dotpanel.context happy-path coverage."""
from __future__ import annotations

import json
import os
import unittest
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

from dotpanel.context import (
    gather_context,
    render_env,
    render_markdown,
    resolve_identity,
    resolve_machine_os,
)


_IDENTITY_YAML = """\
name:
  chinese: "测试者"
handle: testop
email: test@example.com
languages: [en, zh]
git:
  name: Test Operator
  email: test@example.com
focus: dotpanel-test
"""

_MACHINES_YAML = """\
version: "1.0"

dev_machines: []

servers:
  - name: testbox
    os: Linux 6.x
    user: test
"""


class IdentityTests(unittest.TestCase):
    def test_resolve_identity_round_trips(self) -> None:
        with TemporaryDirectory() as t:
            persona = Path(t) / "persona"
            persona.mkdir()
            (persona / "identity.yaml").write_text(_IDENTITY_YAML)
            data = resolve_identity(persona)
            self.assertEqual(data["chinese"], "测试者")
            self.assertEqual(data["handle"], "testop")
            self.assertEqual(data["email"], "test@example.com")
            self.assertEqual(data["focus"], "dotpanel-test")

    def test_missing_identity_yaml_raises(self) -> None:
        with TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):
                resolve_identity(Path(t))


class MachineOsTests(unittest.TestCase):
    def test_machine_os_lookup(self) -> None:
        with TemporaryDirectory() as t:
            yml = Path(t) / "machines.yaml"
            yml.write_text(_MACHINES_YAML)
            self.assertEqual(resolve_machine_os(yml, "testbox"), "Linux 6.x")

    def test_missing_machine_id_returns_unknown(self) -> None:
        with TemporaryDirectory() as t:
            yml = Path(t) / "machines.yaml"
            yml.write_text(_MACHINES_YAML)
            self.assertEqual(resolve_machine_os(yml, "no-such-machine"), "unknown")


class RenderTests(unittest.TestCase):
    def _ctx(self, t: str) -> dict:
        persona = Path(t) / "persona"
        infra = Path(t) / "infra"
        persona.mkdir()
        infra.mkdir()
        (persona / "identity.yaml").write_text(_IDENTITY_YAML)
        (infra / "machines.yaml").write_text(_MACHINES_YAML)
        # Note: machine-id resolution uses ~/.machine-id; for the env render
        # we don't need it set — render_env just embeds whatever is in ctx.
        return gather_context(Path(t), persona, infra)

    def test_render_env_exports_all_vars(self) -> None:
        with TemporaryDirectory() as t:
            out = render_env(self._ctx(t))
            self.assertIn('AGENT_PERSON="测试者"', out)
            self.assertIn("AGENT_HANDLE=", out)
            self.assertIn("AGENT_EMAIL=", out)
            self.assertIn("DOTPANEL_SUBSTRATE=", out)

    def test_render_markdown_includes_paths_table(self) -> None:
        with TemporaryDirectory() as t:
            out = render_markdown(self._ctx(t))
            self.assertIn("## Who I Am", out)
            self.assertIn("### Paths", out)
            self.assertIn("identity.yaml", out)
            self.assertIn("voice.md", out)


if __name__ == "__main__":
    unittest.main()
