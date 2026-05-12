"""Phase C step 4: dotpanel.install pin-parser + verification coverage.

Tests focus on the pure, deterministic surface (pin parsing + SHA-256
verification + unknown-tool refusal). We don't reach out to the real
network: `_download` is monkeypatched to write a fixed payload from a
fixture path.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from dotpanel.install import (
    InstallError,
    Pin,
    _install_one,
    cmd_install,
    cmd_install_list,
    parse_pins_file,
)


PINS_SAMPLE = """#!/usr/bin/env bash
# install-pins.sh — sample
PIN_cloudflared_url="https://example.invalid/cloudflared"
PIN_cloudflared_sha256="0000000000000000000000000000000000000000000000000000000000000000"

# vscode CLI unpinned
PIN_code_url=""
PIN_code_sha256=""
"""


class ParsePinsTests(unittest.TestCase):
    def test_parses_quoted_assignments(self) -> None:
        pins = parse_pins_file(PINS_SAMPLE)
        self.assertIn("cloudflared", pins)
        self.assertIn("code", pins)
        cf = pins["cloudflared"]
        self.assertEqual(cf.url, "https://example.invalid/cloudflared")
        self.assertEqual(cf.sha256, "0" * 64)
        self.assertTrue(cf.is_pinned)
        self.assertFalse(pins["code"].is_pinned)

    def test_ignores_unrelated_lines(self) -> None:
        text = """
        # comment
        SOMETHING_ELSE=42
        export FOO=bar
        PIN_x_url='https://x'
        PIN_x_sha256='abc'
        """
        pins = parse_pins_file(text)
        self.assertEqual(set(pins), {"x"})
        self.assertEqual(pins["x"].url, "https://x")
        self.assertEqual(pins["x"].sha256, "abc")

    def test_bare_token_value(self) -> None:
        # v4 install-pins occasionally used unquoted values.
        pins = parse_pins_file("PIN_y_url=https://example.invalid/y\nPIN_y_sha256=deadbeef\n")
        self.assertEqual(pins["y"].url, "https://example.invalid/y")
        self.assertEqual(pins["y"].sha256, "deadbeef")


class InstallOneTests(unittest.TestCase):
    """Exercise `_install_one` with a stubbed `_download`."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.local_bin = Path(self._tmp.name) / "bin"

    def _patch_download(self, payload: bytes):
        def fake_download(url: str, dest: Path, *, timeout: int = 180) -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
        return mock.patch("dotpanel.install._download", side_effect=fake_download)

    def test_pinned_download_verifies_and_installs(self) -> None:
        payload = b"#!/bin/sh\necho ok\n"
        sha = hashlib.sha256(payload).hexdigest()
        pin = Pin(name="hello", url="https://example.invalid/hello", sha256=sha)
        with self._patch_download(payload):
            target = _install_one(pin, self.local_bin)
        self.assertTrue(target.is_file())
        self.assertTrue(os.access(target, os.X_OK))
        self.assertEqual(target.read_bytes(), payload)

    def test_sha_mismatch_raises_and_cleans(self) -> None:
        payload = b"corrupt\n"
        pin = Pin(name="hello", url="https://example.invalid/hello", sha256="0" * 64)
        with self._patch_download(payload):
            with self.assertRaises(InstallError) as ctx:
                _install_one(pin, self.local_bin)
        self.assertEqual(ctx.exception.exit_code, 2)
        # No leftover binary at the canonical name.
        self.assertFalse((self.local_bin / "hello").exists())
        # No leftover temp file matching the prefix either.
        leftovers = list(self.local_bin.glob("dotpanel-install-hello-*"))
        self.assertEqual(leftovers, [])

    def test_unpinned_without_opt_in_refuses(self) -> None:
        pin = Pin(name="nopin", url="", sha256="")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DOTPANEL_INSTALL_ALLOW_UNPINNED", None)
            os.environ.pop("INSTALL_TOOLS_ALLOW_UNPINNED", None)
            with self.assertRaises(InstallError) as ctx:
                _install_one(pin, self.local_bin)
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_unpinned_opt_in_still_needs_url(self) -> None:
        pin = Pin(name="nopin", url="", sha256="")
        with mock.patch.dict(os.environ, {"DOTPANEL_INSTALL_ALLOW_UNPINNED": "1"}, clear=False):
            with self.assertRaises(InstallError) as ctx:
                _install_one(pin, self.local_bin)
        # Should still raise because no fallback URL is registered (single-arch
        # design; per-tool fallback URLs are in v4 cmd_<tool> handlers which
        # v5 does NOT carry forward into install.py — operators bootstrap by
        # downloading manually and capturing the SHA themselves).
        self.assertEqual(ctx.exception.exit_code, 2)


class CmdInstallDispatchTests(unittest.TestCase):
    """Exercise `cmd_install` end-to-end against a stub substrate config."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.root = root
        (root / "tools").mkdir()
        (root / "tools" / "install-pins.sh").write_text(PINS_SAMPLE)
        (root / "persona").mkdir()
        (root / "persona" / "voice.md").write_text("# voice\n")
        (root / "persona" / "identity.yaml").write_text("name:\n  chinese: T\n")
        (root / ".dotpanel.toml").write_text(
            '[dotpanel]\nschema_version = "1.0"\n'
            '[paths]\npersona = "persona"\n'
            'install_pins = "tools/install-pins.sh"\n'
        )
        self.env_patch = mock.patch.dict(
            os.environ, {"DOTPANEL_SUBSTRATE": str(root)}, clear=False
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_list_dumps_known_pins(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cmd_install_list()
        self.assertEqual(rc, 0)

    def test_unknown_tool_exits_2(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cmd_install("doesnt-exist")
        self.assertEqual(rc, 2)

    def test_install_all_when_no_pins_completes(self) -> None:
        # `cloudflared` is pinned but points at example.invalid; calling `all`
        # would try to download. Replace _install_one with a stub.
        with mock.patch(
            "dotpanel.install._install_one",
            side_effect=lambda pin, local_bin: local_bin / pin.name,
        ), contextlib.redirect_stdout(io.StringIO()):
            rc = cmd_install("all")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
