"""Phase C step 5: dotpanel.secrets — scoped API coverage.

Tests build a fresh age key + bundle in a temp substrate, then exercise
list / edit / run / export / init / rotate-key. The bundle bootstrap test
verifies the IC-SG-3 env_alias path (the bundle key has a descriptive
name like `ANDYFENG_CLAUDE_KEY`, but the child process sees the canonical
`ANTHROPIC_AUTH_TOKEN`).

Skipped automatically if `age` and `age-keygen` are not on $PATH.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from dotpanel import secrets as secrets_mod
from dotpanel.secrets import (
    PROVIDER_BASE_URL_ENV,
    SecretsContext,
    SecretsError,
    _backend_env,
    _matches_any,
    _parse_env_file,
    _parse_run_args,
    _render_export_line,
    cmd_export,
    cmd_init,
    cmd_list,
    cmd_run,
)
from dotpanel.config import BackendVariant, find_substrate


_HAVE_AGE = bool(shutil.which("age") and shutil.which("age-keygen"))


@unittest.skipUnless(_HAVE_AGE, "age / age-keygen not installed")
class FullSecretsFlowTests(unittest.TestCase):
    """End-to-end: init -> add keys -> list -> run -> export -> rotate."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "persona").mkdir()
        (self.root / "persona" / "voice.md").write_text("# voice\n")
        (self.root / "persona" / "identity.yaml").write_text("name:\n  chinese: Tester\n")
        (self.root / "secret").mkdir()

        # Isolate the age key from the operator's real ~/.config/age
        self.fake_home = self.root / "fakehome"
        self.fake_home.mkdir()
        (self.fake_home / ".config").mkdir()
        (self.fake_home / ".config" / "age").mkdir()

        # Patch DEFAULT_AGE_KEY_PATH so init won't touch the real key
        self._patches = [
            mock.patch.object(
                secrets_mod, "DEFAULT_AGE_KEY_PATH",
                str(self.fake_home / ".config" / "age" / "key.txt"),
            ),
            mock.patch.dict(
                os.environ,
                {"DOTPANEL_SUBSTRATE": str(self.root)},
                clear=False,
            ),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])

        # .dotpanel.toml with backend + scope config
        (self.root / ".dotpanel.toml").write_text(textwrap.dedent("""
            [dotpanel]
            schema_version = "1.0"

            [paths]
            persona       = "persona"
            secret_bundle = "secret/.secrets.age"
            secret_pubkey = "secret/.secrets.pub"

            [secrets]
            llm_scope = ["ANDYFENG_*", "OPENAI_*", "DEEPSEEK_*"]

            [backends]
            default_provider = "claude"

            [backends.claude]
            default = "andy"

            [backends.claude.variants.andy]
            key       = "ANDYFENG_CLAUDE_KEY"
            env_alias = "ANTHROPIC_AUTH_TOKEN"
            base_url  = "https://api.example.invalid"
            model     = "claude-fake-test"
            extra_env = { TEST_EXTRA = "yes" }
        """).lstrip())

    def _silent_run(self, fn, *args, **kwargs) -> int:
        """Run a cmd_* helper, translating SecretsError → exit code."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                return fn(*args, **kwargs)
            except SecretsError as exc:
                return exc.exit_code

    def test_init_then_list_empty(self) -> None:
        rc = self._silent_run(cmd_init, True, None, False)
        self.assertEqual(rc, 0)
        # Bundle is created
        self.assertTrue((self.root / "secret" / ".secrets.age").is_file())
        self.assertTrue((self.root / "secret" / ".secrets.pub").is_file())
        # age key landed in fake home, not real $HOME
        self.assertTrue((self.fake_home / ".config" / "age" / "key.txt").is_file())

        rc = self._silent_run(cmd_list, None, True)
        self.assertEqual(rc, 0)

    def test_init_refuses_existing_bundle(self) -> None:
        self.assertEqual(self._silent_run(cmd_init, True, None, False), 0)
        # Second init must refuse
        rc = self._silent_run(cmd_init, True, None, False)
        self.assertEqual(rc, 2)

    def test_init_refuses_existing_age_key(self) -> None:
        # First init succeeds.
        self.assertEqual(self._silent_run(cmd_init, True, None, False), 0)
        # Remove bundle but leave the key; init --keygen should refuse.
        (self.root / "secret" / ".secrets.age").unlink()
        rc = self._silent_run(cmd_init, True, None, False)
        self.assertEqual(rc, 2)

    def test_init_requires_one_arg(self) -> None:
        rc = self._silent_run(cmd_init, False, None, False)
        self.assertEqual(rc, 2)

    def test_run_with_key_injects_value(self) -> None:
        # init then drop a known KEY=VALUE into the bundle.
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"KIMI_API_KEY": "sk-test-value-123"})

        with mock.patch("os.execvpe") as exec_mock:
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_run(keys=["KIMI_API_KEY"], backend=None, variant=None,
                        cmd=["printenv", "KIMI_API_KEY"])
        args, kwargs = exec_mock.call_args
        cmd_argv = args[1]
        passed_env = args[2]
        self.assertEqual(cmd_argv, ["printenv", "KIMI_API_KEY"])
        self.assertEqual(passed_env["KIMI_API_KEY"], "sk-test-value-123")

    def test_run_with_missing_key_exits_2(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"OTHER_KEY": "x"})
        with self.assertRaises(SecretsError) as ctx:
            cmd_run(keys=["NOPE"], backend=None, variant=None, cmd=["printenv"])
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_run_with_backend_uses_env_alias(self) -> None:
        """IC-SG-3: bundle key is ANDYFENG_CLAUDE_KEY but child sees ANTHROPIC_AUTH_TOKEN."""
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"ANDYFENG_CLAUDE_KEY": "sk-ant-test-xyz"})

        with mock.patch("os.execvpe") as exec_mock:
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_run(keys=[], backend="claude", variant=None, cmd=["printenv"])
        args, kwargs = exec_mock.call_args
        passed_env = args[2]
        # env_alias mapping
        self.assertEqual(passed_env["ANTHROPIC_AUTH_TOKEN"], "sk-ant-test-xyz")
        # Original bundle key NOT exposed (we only map via env_alias)
        self.assertNotIn("ANDYFENG_CLAUDE_KEY", passed_env)
        # base_url resolver
        self.assertEqual(passed_env["ANTHROPIC_BASE_URL"], "https://api.example.invalid")
        # extra_env passthrough
        self.assertEqual(passed_env["TEST_EXTRA"], "yes")
        # model bubbled up
        self.assertEqual(passed_env["DOTPANEL_MODEL"], "claude-fake-test")

    def test_run_backend_unknown_variant_exits_2(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"ANDYFENG_CLAUDE_KEY": "x"})
        with self.assertRaises(SecretsError) as ctx:
            cmd_run(keys=[], backend="claude", variant="ghost",
                    cmd=["printenv"])
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_run_backend_variant_missing_bundle_key_exits_2(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        # Variant claude.andy references ANDYFENG_CLAUDE_KEY; don't seed it.
        self._seed_bundle({"OTHER": "x"})
        with self.assertRaises(SecretsError) as ctx:
            cmd_run(keys=[], backend="claude", variant="andy",
                    cmd=["printenv"])
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_export_scope_llm_only_emits_matches(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({
            "ANDYFENG_CLAUDE_KEY": "secret-andy",
            "OPENAI_API_KEY": "secret-openai",
            "GH_TOKEN": "should-not-export",
            "DEEPSEEK_API_KEY": "secret-deepseek",
        })
        buf = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = cmd_export(scope="llm", shell="bash")
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("ANDYFENG_CLAUDE_KEY", out)
        self.assertIn("OPENAI_API_KEY", out)
        self.assertIn("DEEPSEEK_API_KEY", out)
        # GH_TOKEN is explicitly NOT in llm_scope
        self.assertNotIn("GH_TOKEN", out)

    def test_export_backend_emits_only_resolved_variant_env(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({
            "ANDYFENG_CLAUDE_KEY": "secret-andy",
            "OPENAI_API_KEY": "secret-openai",
        })
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_export(scope=None, shell="bash", backend="claude", variant="andy")
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("export ANTHROPIC_AUTH_TOKEN=secret-andy", out)
        self.assertIn("export ANTHROPIC_BASE_URL=https://api.example.invalid", out)
        self.assertIn("export DOTPANEL_MODEL=claude-fake-test", out)
        self.assertIn("export TEST_EXTRA=yes", out)
        self.assertNotIn("OPENAI_API_KEY", out)
        self.assertNotIn("ANDYFENG_CLAUDE_KEY", out)

    def test_export_requires_exactly_one_selector(self) -> None:
        with self.assertRaises(SecretsError) as ctx:
            cmd_export(scope=None, shell="bash", backend=None, variant=None)
        self.assertEqual(ctx.exception.exit_code, 2)

        with self.assertRaises(SecretsError) as ctx:
            cmd_export(scope="llm", shell="bash", backend="claude", variant=None)
        self.assertEqual(ctx.exception.exit_code, 2)

        with self.assertRaises(SecretsError) as ctx:
            cmd_export(scope=None, shell="bash", backend=None, variant="andy")
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("--variant requires --backend", str(ctx.exception))

    def test_export_without_scope_llm_refuses(self) -> None:
        # cmd_export only runs when --scope llm is parsed. Manually pass other:
        with self.assertRaises(SecretsError) as ctx:
            cmd_export(scope="cos", shell="bash")
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_list_scope_filters(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"ANDYFENG_CLAUDE_KEY": "a", "GH_TOKEN": "b"})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_list(scope="llm", names_only=True)
        self.assertEqual(rc, 0)
        names = buf.getvalue().splitlines()
        self.assertIn("ANDYFENG_CLAUDE_KEY", names)
        self.assertNotIn("GH_TOKEN", names)

    def test_rotate_key_re_encrypts(self) -> None:
        self._silent_run(cmd_init, True, None, False)
        self._seed_bundle({"ROTATE_TEST": "v1"})
        # Capture bundle bytes before rotate
        bundle = self.root / "secret" / ".secrets.age"
        before = bundle.read_bytes()
        from dotpanel.secrets import cmd_rotate_key
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cmd_rotate_key(add_recipient=None)
        self.assertEqual(rc, 0)
        after = bundle.read_bytes()
        # Different ciphertext because age randomizes header.
        self.assertNotEqual(before, after)

    # --- helpers -----------------------------------------------------

    def _seed_bundle(self, kv: dict[str, str]) -> None:
        """Write KEY=VALUE pairs into the existing bundle by unpack/repack."""
        # We use the public surface: unpack scratch dir, edit env, repack.
        ctx = self._ctx()
        from dotpanel.secrets import _resolve_age_key, _unpack_to_dir, _pack_and_encrypt
        age_key = _resolve_age_key()
        scratch = _unpack_to_dir(ctx.bundle_path, age_key)
        try:
            env_path = scratch / "env"
            lines = env_path.read_text(encoding="utf-8").splitlines()
            existing = {l.split("=", 1)[0]: l for l in lines if "=" in l}
            for k, v in kv.items():
                existing[k] = f"{k}={v}"
            env_path.write_text("\n".join(existing.values()) + "\n", encoding="utf-8")
            _pack_and_encrypt(scratch, ctx.pubkey_path, ctx.bundle_path)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def _ctx(self) -> SecretsContext:
        from dotpanel.secrets import _load_context
        return _load_context(require_bundle=False)


class PureHelpersTests(unittest.TestCase):
    """Pure-Python helpers that don't need a bundle."""

    def test_parse_run_args_splits_at_dash(self) -> None:
        keys, backend, variant, cmd = _parse_run_args(
            ["--key", "A", "--key", "B", "--", "cmd", "arg1"]
        )
        self.assertEqual(keys, ["A", "B"])
        self.assertIsNone(backend)
        self.assertIsNone(variant)
        self.assertEqual(cmd, ["cmd", "arg1"])

    def test_parse_run_args_backend_variant(self) -> None:
        keys, backend, variant, cmd = _parse_run_args(
            ["--backend", "claude", "--variant", "kimi", "--", "claude", "-h"]
        )
        self.assertEqual(keys, [])
        self.assertEqual(backend, "claude")
        self.assertEqual(variant, "kimi")
        self.assertEqual(cmd, ["claude", "-h"])

    def test_parse_run_args_missing_arg_raises(self) -> None:
        with self.assertRaises(SecretsError):
            _parse_run_args(["--key"])
        with self.assertRaises(SecretsError):
            _parse_run_args(["--backend"])
        with self.assertRaises(SecretsError):
            _parse_run_args(["--unknown"])

    def test_parse_run_args_no_dash_separator(self) -> None:
        with self.assertRaises(SecretsError):
            _parse_run_args(["--key", "A", "cmd"])

    def test_render_export_bash_quotes_value(self) -> None:
        line = _render_export_line("X", "needs quoting", "bash")
        self.assertEqual(line, "export X='needs quoting'")

    def test_render_export_fish_uses_set_gx(self) -> None:
        line = _render_export_line("X", "v", "fish")
        self.assertEqual(line, "set -gx X v")

    def test_provider_resolver_table(self) -> None:
        # IC-SG-3: claude → ANTHROPIC_BASE_URL, codex → OPENAI_BASE_URL
        self.assertEqual(PROVIDER_BASE_URL_ENV["claude"], "ANTHROPIC_BASE_URL")
        self.assertEqual(PROVIDER_BASE_URL_ENV["codex"], "OPENAI_BASE_URL")
        self.assertEqual(PROVIDER_BASE_URL_ENV["kimi"], "ANTHROPIC_BASE_URL")

    def test_matches_any_fnmatch(self) -> None:
        self.assertTrue(_matches_any("ANDYFENG_CLAUDE_KEY", ["ANDYFENG_*"]))
        self.assertFalse(_matches_any("GH_TOKEN", ["ANDYFENG_*", "OPENAI_*"]))

    def test_parse_env_file_skips_comments_and_blanks(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("# comment\n\nKEY1=v1\nKEY2=v2 with spaces\nbroken line\n")
            tmp = Path(fh.name)
        try:
            entries = _parse_env_file(tmp)
            self.assertEqual(entries, [("KEY1", "v1"), ("KEY2", "v2 with spaces")])
        finally:
            tmp.unlink()


class BackendEnvComposeTests(unittest.TestCase):
    """Exercise _backend_env with no bundle access needed (pure data)."""

    def test_env_alias_default_to_key(self) -> None:
        # Construct a minimal ctx + variant manually
        from dotpanel.config import (
            BackendProvider, BackendsSection, HarnessSection, PathsSection,
            SecretsSection, SubstrateConfig, SyncSection, SkillsSection,
        )
        cfg = SubstrateConfig(root=Path("/tmp"))
        ctx = SecretsContext(
            config=cfg,
            bundle_path=Path("/tmp/bundle"),
            pubkey_path=Path("/tmp/pub"),
        )
        variant = BackendVariant(key="MY_KEY", env_alias="MY_KEY")
        env = _backend_env(ctx, "myprov", "v", variant, "value")
        self.assertEqual(env, {"MY_KEY": "value"})

    def test_unknown_provider_uses_uppercase_base_url_var(self) -> None:
        from dotpanel.config import SubstrateConfig
        cfg = SubstrateConfig(root=Path("/tmp"))
        ctx = SecretsContext(
            config=cfg,
            bundle_path=Path("/tmp/bundle"),
            pubkey_path=Path("/tmp/pub"),
        )
        variant = BackendVariant(
            key="K", env_alias="K", base_url="https://x.invalid"
        )
        env = _backend_env(ctx, "newprov", "v", variant, "val")
        self.assertEqual(env["NEWPROV_BASE_URL"], "https://x.invalid")


class BulkExportRefusedTests(unittest.TestCase):
    """Threat-model invariant: there is no bulk-decrypt path. EC-3."""

    def test_dispatch_with_no_export_selector_rejects(self) -> None:
        from dotpanel.secrets import main
        with contextlib.redirect_stderr(io.StringIO()):
            rc = main(["export"])
        self.assertEqual(rc, 2)

    def test_dispatch_with_scope_all_rejected_by_argparse(self) -> None:
        from dotpanel.secrets import main
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["export", "--scope", "all"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
