"""Phase C step 3: dotpanel.ssh happy-path coverage.

Tests are pure render-from-yaml; no actual filesystem write to ~/.ssh/.
"""
from __future__ import annotations

import unittest

from dotpanel.ssh import render_config


_MACHINES = {
    "version": "1.0",
    "dev_machines": [],
    "servers": [
        {
            "name": "uisz",
            "alias": ["OpenClaw"],
            "ip": "1.2.3.4",
            "user": "ubuntu",
            "magicdns": "uisz.example.ts.net",
            "ssh_key": "uisz-key",
            "proxy_jump": "aliyun-gz",
        },
        {
            "name": "tcsg",
            "ip": "5.6.7.8",
            "user": "ubuntu",
            "lan_ip": "192.168.1.10",
            "cloudflare": {"hostname": "tcsg.example.com", "port": 2222},
        },
    ],
}


class RenderConfigTests(unittest.TestCase):
    def test_default_block_uses_magicdns(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host uisz", out)
        self.assertIn("HostName uisz.example.ts.net", out)

    def test_alias_block_lowercased(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host openclaw", out)

    def test_pub_block_uses_ip(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host uisz-pub", out)
        self.assertIn("HostName 1.2.3.4", out)
        self.assertIn("IdentityFile ~/.ssh/vps-keys/uisz-key", out)

    def test_proxy_jump_emits_jp_variant(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host uisz-jp", out)
        self.assertIn("ProxyJump aliyun-gz", out)

    def test_cloudflare_emits_cf_variant_with_port(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host tcsg-cf", out)
        self.assertIn("HostName tcsg.example.com", out)
        self.assertIn("Port 2222", out)

    def test_lan_ip_emits_local_variant(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("Host tcsg-local", out)
        self.assertIn("HostName 192.168.1.10", out)

    def test_header_contains_global_options(self) -> None:
        out = render_config(_MACHINES)
        self.assertIn("ConnectTimeout 10", out)
        self.assertIn("ServerAliveInterval 30", out)
        self.assertIn("StrictHostKeyChecking accept-new", out)


if __name__ == "__main__":
    unittest.main()
