"""dotpanel.config — `.dotpanel.toml` loader + substrate discovery.

Schema is documented fully in
`docs/design/2026-05-11-dotpanel-control-plane.md`. The first-pass loader
(this module) supports:

- `[dotpanel]` envelope (`schema_version`)
- `[paths]` (persona, secret_bundle, secret_pubkey, secret_keys, infra,
  journal, install_pins, network_nodes, skills)
- `[configure]` (substrate_bin)
- `[sync]` (repos, leak_mode_default, leak_mode_overrides)
- `[backends.*]` (default + variants)
- `[secrets]` (llm_scope)
- `[harness]` (enabled, sync_command)
- `[skills]` (disabled, per-skill table)

Path-traversal validation (H9): every `[paths.*]` field is resolved relative
to the substrate root; any `..` escape rejected. `secret_bundle` /
`secret_pubkey` may also be absolute paths beginning with `~/.config/age/`
(narrow allowlist).

Pydantic v2 is the long-term target. For Phase B / C-step-1 the loader uses
dataclasses + manual validation so the kernel works on a stock Python install
without adding a hard dependency mid-rename. Pydantic migration ships in a
follow-up commit per the Test Strategy section of the design doc.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib as _tomllib
else:  # pragma: no cover - we already require >=3.12 in pyproject
    import tomli as _tomllib  # type: ignore[import-not-found]


class SubstrateNotFound(Exception):
    """Raised when no `.dotpanel.toml` can be located."""


class SchemaError(Exception):
    """Raised on invalid `.dotpanel.toml` content."""


_PATH_FIELD_ABS_ALLOWLIST_PREFIX = "~/.config/age/"


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path))


def _validate_under(root: Path, candidate: Path, field_name: str,
                    *, allow_age: bool = False) -> Path:
    """Resolve candidate relative to root and assert it stays under root.

    Allows absolute paths only when `allow_age` is True and the path lies
    under `~/.config/age/`. H9 enforcement.
    """
    if candidate.is_absolute():
        if allow_age and str(candidate).startswith(str(_expand(_PATH_FIELD_ABS_ALLOWLIST_PREFIX))):
            return candidate.resolve()
        raise SchemaError(
            f"[paths] {field_name}: absolute path not allowed: {candidate}"
        )
    resolved = (root / candidate).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SchemaError(
            f"[paths] {field_name}: path escapes substrate root: {candidate}"
        ) from exc
    return resolved


@dataclass
class PathsSection:
    persona: Path
    skills: Path
    secret_bundle: Path
    secret_pubkey: Path
    secret_keys: Path
    infra: Path
    journal: Path
    install_pins: Path
    network_nodes: Path


@dataclass
class ConfigureSection:
    substrate_bin: Path


@dataclass
class SyncRepo:
    path: str
    label: str


@dataclass
class SyncSection:
    repos: list[SyncRepo] = field(default_factory=list)
    leak_mode_default: str = "generic"
    leak_mode_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class BackendVariant:
    key: str
    env_alias: str
    base_url: str = ""
    model: str = ""
    extra_env: dict[str, str] = field(default_factory=dict)
    prompt_overlay: str = ""


@dataclass
class BackendProvider:
    default: str
    variants: dict[str, BackendVariant] = field(default_factory=dict)


@dataclass
class BackendsSection:
    default_provider: str = "claude"
    providers: dict[str, BackendProvider] = field(default_factory=dict)


@dataclass
class SecretsSection:
    llm_scope: list[str] = field(default_factory=list)


@dataclass
class HarnessSection:
    enabled: list[str] = field(default_factory=lambda: ["claude", "codex", "kimi"])
    sync_command: str = "dotpanel sync"


@dataclass
class SkillsSection:
    disabled: list[str] = field(default_factory=list)
    # name -> {"harnesses": [...]}
    per_skill: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SubstrateConfig:
    root: Path
    schema_version: str = "1.0"
    paths: PathsSection | None = None
    configure: ConfigureSection | None = None
    sync: SyncSection = field(default_factory=SyncSection)
    backends: BackendsSection = field(default_factory=BackendsSection)
    secrets: SecretsSection = field(default_factory=SecretsSection)
    harness: HarnessSection = field(default_factory=HarnessSection)
    skills: SkillsSection = field(default_factory=SkillsSection)

    @classmethod
    def empty(cls, root: Path | None = None) -> "SubstrateConfig":
        return cls(root=root or Path.cwd())

    def has_path(self, name: str) -> bool:
        return self.paths is not None and getattr(self.paths, name, None) is not None

    def path_for(self, name: str) -> Path:
        if self.paths is None:
            raise SchemaError(
                f"[paths] section missing; cannot resolve {name!r}. "
                f"Add `[paths] {name} = ...` to {self.root}/.dotpanel.toml"
            )
        value = getattr(self.paths, name, None)
        if value is None:
            raise SchemaError(
                f"[paths] {name!r} not set in {self.root}/.dotpanel.toml"
            )
        return value


def _load_paths(root: Path, raw: dict[str, Any]) -> PathsSection | None:
    if not raw:
        return None
    defaults = {
        "persona": "persona",
        "skills": "skills",
        "secret_bundle": "secret/.secrets.age",
        "secret_pubkey": "secret/.secrets.pub",
        "secret_keys": "secret/keys",
        "infra": "infra",
        "journal": ".agents/journal",
        "install_pins": "install-pins.sh",
        "network_nodes": "network/nodes.yaml",
    }
    allow_age_fields = {"secret_bundle", "secret_pubkey"}
    resolved: dict[str, Path] = {}
    for fname, default in defaults.items():
        raw_value = raw.get(fname, default)
        if not isinstance(raw_value, str):
            raise SchemaError(f"[paths] {fname}: expected string, got {type(raw_value).__name__}")
        candidate = _expand(raw_value)
        resolved[fname] = _validate_under(
            root,
            candidate,
            fname,
            allow_age=fname in allow_age_fields,
        )
    return PathsSection(**resolved)


def _load_configure(root: Path, raw: dict[str, Any]) -> ConfigureSection | None:
    if not raw:
        return None
    substrate_bin = raw.get("substrate_bin", "tools/bin")
    if not isinstance(substrate_bin, str):
        raise SchemaError("[configure] substrate_bin: expected string")
    resolved = _validate_under(root, _expand(substrate_bin), "substrate_bin")
    return ConfigureSection(substrate_bin=resolved)


def _load_sync(raw: dict[str, Any]) -> SyncSection:
    if not raw:
        return SyncSection()
    repos: list[SyncRepo] = []
    for entry in raw.get("repos", []) or []:
        if not isinstance(entry, dict):
            raise SchemaError(f"[sync] repos: each entry must be a table, got {entry!r}")
        repos.append(SyncRepo(path=str(entry.get("path", "")), label=str(entry.get("label", ""))))
    default_mode = str(raw.get("leak_mode_default", "generic"))
    if default_mode not in ("generic", "synced"):
        raise SchemaError(f"[sync] leak_mode_default: must be generic|synced, got {default_mode!r}")
    overrides = raw.get("leak_mode_overrides", {}) or {}
    if not isinstance(overrides, dict):
        raise SchemaError("[sync] leak_mode_overrides: must be a table")
    for k, v in overrides.items():
        if v not in ("generic", "synced"):
            raise SchemaError(f"[sync] leak_mode_overrides[{k!r}]: must be generic|synced")
    return SyncSection(repos=repos, leak_mode_default=default_mode, leak_mode_overrides=overrides)


def _load_backends(raw: dict[str, Any]) -> BackendsSection:
    if not raw:
        return BackendsSection()
    default_provider = raw.get("default_provider", "claude")
    if not isinstance(default_provider, str):
        raise SchemaError("[backends] default_provider: expected string")
    providers: dict[str, BackendProvider] = {}
    for provider_name, provider_raw in raw.items():
        if provider_name == "default_provider":
            continue
        if not isinstance(provider_raw, dict):
            continue
        prov_default = provider_raw.get("default")
        if not isinstance(prov_default, str):
            raise SchemaError(f"[backends.{provider_name}] default: required string")
        variants_raw = provider_raw.get("variants", {}) or {}
        variants: dict[str, BackendVariant] = {}
        for vname, v in variants_raw.items():
            if not isinstance(v, dict):
                continue
            if "key" not in v:
                raise SchemaError(f"[backends.{provider_name}.variants.{vname}] missing required 'key'")
            variants[vname] = BackendVariant(
                key=str(v["key"]),
                env_alias=str(v.get("env_alias", v["key"])),
                base_url=str(v.get("base_url", "")),
                model=str(v.get("model", "")),
                extra_env=dict(v.get("extra_env", {}) or {}),
                prompt_overlay=str(v.get("prompt_overlay", "")),
            )
        providers[provider_name] = BackendProvider(default=prov_default, variants=variants)
    return BackendsSection(default_provider=default_provider, providers=providers)


def _load_secrets(raw: dict[str, Any]) -> SecretsSection:
    if not raw:
        return SecretsSection()
    llm_scope = raw.get("llm_scope", []) or []
    if not isinstance(llm_scope, list):
        raise SchemaError("[secrets] llm_scope: must be a list")
    return SecretsSection(llm_scope=[str(x) for x in llm_scope])


def _load_harness(raw: dict[str, Any]) -> HarnessSection:
    if not raw:
        return HarnessSection()
    enabled = raw.get("enabled", ["claude", "codex", "kimi"]) or []
    if not isinstance(enabled, list):
        raise SchemaError("[harness] enabled: must be a list")
    sync_command = raw.get("sync_command", "dotpanel sync")
    if not isinstance(sync_command, str) or not sync_command:
        raise SchemaError("[harness] sync_command: must be a non-empty string")
    return HarnessSection(enabled=[str(x) for x in enabled], sync_command=sync_command)


def _load_skills(raw: dict[str, Any]) -> SkillsSection:
    if not raw:
        return SkillsSection()
    disabled = raw.get("disabled", []) or []
    if not isinstance(disabled, list):
        raise SchemaError("[skills] disabled: must be a list")
    per_skill: dict[str, dict[str, Any]] = {}
    for key, val in raw.items():
        if key == "disabled":
            continue
        if isinstance(val, dict):
            per_skill[key] = dict(val)
    return SkillsSection(disabled=[str(x) for x in disabled], per_skill=per_skill)


def load_toml(path: Path) -> SubstrateConfig:
    """Parse `.dotpanel.toml` at `path` and return a populated SubstrateConfig."""
    root = path.parent.resolve()
    data = _tomllib.loads(path.read_text(encoding="utf-8"))
    dot = data.get("dotpanel", {}) or {}
    schema_version = str(dot.get("schema_version", "1.0"))
    if not _is_version_compatible(schema_version):
        raise SchemaError(
            f"[dotpanel] schema_version={schema_version!r}: kernel supports 1.x only. "
            "Upgrade the kernel or downgrade the substrate config."
        )
    cfg = SubstrateConfig(
        root=root,
        schema_version=schema_version,
        paths=_load_paths(root, data.get("paths", {}) or {}),
        configure=_load_configure(root, data.get("configure", {}) or {}),
        sync=_load_sync(data.get("sync", {}) or {}),
        backends=_load_backends(data.get("backends", {}) or {}),
        secrets=_load_secrets(data.get("secrets", {}) or {}),
        harness=_load_harness(data.get("harness", {}) or {}),
        skills=_load_skills(data.get("skills", {}) or {}),
    )
    return cfg


def _is_version_compatible(version: str) -> bool:
    try:
        major, _ = version.split(".", 1)
    except ValueError:
        return False
    return major == "1"


def find_substrate(start: Path | None = None) -> SubstrateConfig:
    """Discover and load the active substrate config.

    Order:
      1. $DOTPANEL_SUBSTRATE env override
      2. ~/.dotfiles/.dotpanel.toml default
      3. Walk up from `start` (defaults to $PWD)
      4. Empty config (caller subcommands fail at use time if they need a value)

    Raises SubstrateNotFound only when DOTPANEL_SUBSTRATE points at a path
    without a `.dotpanel.toml`. Missing configs in defaults / walk-up fall
    through to the empty config.
    """
    env = os.environ.get("DOTPANEL_SUBSTRATE")
    if env:
        candidate = Path(env).expanduser().resolve() / ".dotpanel.toml"
        if candidate.is_file():
            return load_toml(candidate)
        raise SubstrateNotFound(
            f"DOTPANEL_SUBSTRATE={env} but no .dotpanel.toml inside"
        )

    home_default = Path.home() / ".dotfiles" / ".dotpanel.toml"
    if home_default.is_file():
        return load_toml(home_default)

    cur = (start or Path.cwd()).resolve()
    while cur != cur.parent:
        candidate = cur / ".dotpanel.toml"
        if candidate.is_file():
            return load_toml(candidate)
        cur = cur.parent

    return SubstrateConfig.empty()
