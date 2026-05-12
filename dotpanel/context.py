"""dotpanel.context — identity + machine + path resolver.

Reads identity from the substrate's `persona/identity.yaml` and machine OS
from `infra/machines.yaml`. Paths are discovered through `.dotpanel.toml`.

Output modes:

    dotpanel context               markdown prompt block (default)
    dotpanel context --name        chinese name only (for shell scripting)
    dotpanel context --env         eval-able shell exports
    dotpanel context --json        structured dump

D3: Python cold-start adds ~200ms vs v4 awk. Accepted trade-off for
correct yaml parsing.
"""
from __future__ import annotations

import argparse
import json as _json
import os
import sys
from pathlib import Path
from typing import Any

from .config import find_substrate, SubstrateNotFound


def _read_machine_id() -> str:
    home = Path.home()
    path = home / ".machine-id"
    if not path.exists():
        return "unknown"
    try:
        return path.read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def _load_yaml(path: Path) -> Any:
    """Lazy YAML loader. Tries PyYAML; falls back to a minimal indent-aware
    parser sufficient for identity.yaml / machines.yaml schemas. The fallback
    is deliberately conservative — if PyYAML is available, we use it."""
    try:
        import yaml  # type: ignore[import-not-found]
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        return _fallback_yaml(path.read_text(encoding="utf-8"))


def _fallback_yaml(text: str) -> Any:
    """Tiny YAML subset: top-level scalars, one level of nested mapping,
    flow-style `[a, b]` lists, and lists of mappings indented by 2 spaces
    with `- key: value` entries.

    Sufficient for identity.yaml (small, flat-with-one-nested-mapping)
    and machines.yaml (list-of-mappings). Not a replacement for PyYAML.
    """
    out: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(0, out)]
    list_item: dict[str, Any] | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        # Pop stack to current indent level.
        while stack and indent < stack[-1][0]:
            stack.pop()
        cur = stack[-1][1]
        if line.startswith("- "):
            entry = line[2:]
            if isinstance(cur, list):
                if ":" in entry:
                    key, _, val = entry.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    item: dict[str, Any] = {key: val}
                    cur.append(item)
                    list_item = item
                    stack.append((indent + 2, item))
                else:
                    cur.append(entry.strip().strip('"').strip("'"))
                    list_item = None
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # mapping or list starts on next line; default to mapping
                nested: dict[str, Any] = {}
                if isinstance(cur, dict):
                    cur[key] = nested
                stack.append((indent + 2, nested))
            elif val.startswith("[") and val.endswith("]"):
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                if isinstance(cur, dict):
                    cur[key] = items
            else:
                cleaned = val.strip('"').strip("'")
                if isinstance(cur, dict):
                    cur[key] = cleaned
    return out


def resolve_identity(persona_dir: Path) -> dict[str, Any]:
    """Read persona/identity.yaml and return a flat dict."""
    identity_file = persona_dir / "identity.yaml"
    if not identity_file.exists():
        raise FileNotFoundError(f"{identity_file} not found")
    data = _load_yaml(identity_file)
    if not isinstance(data, dict):
        raise ValueError(f"identity.yaml is not a mapping: {identity_file}")
    name_field = data.get("name")
    chinese = ""
    if isinstance(name_field, dict):
        chinese = str(name_field.get("chinese", "")).strip()
    elif isinstance(name_field, str):
        chinese = name_field
    if not chinese:
        raise ValueError(f"could not parse 'name.chinese' from {identity_file}")
    git_info = data.get("git", {}) if isinstance(data.get("git"), dict) else {}
    return {
        "chinese": chinese,
        "handle": data.get("handle", ""),
        "email": data.get("email", ""),
        "languages": data.get("languages", []),
        "git_name": git_info.get("name", "") if isinstance(git_info, dict) else "",
        "git_email": git_info.get("email", "") if isinstance(git_info, dict) else "",
        "focus": data.get("focus", ""),
    }


def resolve_machine_os(machines_yaml: Path, machine_id: str) -> str:
    """Look up the OS for a machine id in machines.yaml.

    machines.yaml convention: top-level mapping with one or more lists of
    machine entries (e.g. `dev_machines:`, `servers:`). We flatten all
    lists and search by `name`.
    """
    if not machines_yaml.exists() or machine_id == "unknown":
        return "unknown"
    data = _load_yaml(machines_yaml)
    machines: list[Any] = []
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                machines.extend(v)
    elif isinstance(data, list):
        machines = data
    for m in machines:
        if isinstance(m, dict) and m.get("name") == machine_id:
            return str(m.get("os", "unknown"))
    return "unknown"


def gather_context(substrate_root: Path, persona_dir: Path, infra_dir: Path | None) -> dict[str, Any]:
    identity = resolve_identity(persona_dir)
    machine_id = _read_machine_id()
    machine_os = "unknown"
    if infra_dir is not None:
        machine_os = resolve_machine_os(infra_dir / "machines.yaml", machine_id)
    return {
        "identity": identity,
        "machine": {"id": machine_id, "os": machine_os},
        "paths": {
            "substrate": str(substrate_root),
            "persona": str(persona_dir),
            "infra": str(infra_dir) if infra_dir else "",
        },
    }


def render_markdown(ctx: dict[str, Any]) -> str:
    identity = ctx["identity"]
    machine = ctx["machine"]
    paths = ctx["paths"]
    langs = identity["languages"]
    if isinstance(langs, list):
        langs_str = ", ".join(str(x) for x in langs)
    else:
        langs_str = str(langs)
    focus_line = f"\nFocus: {identity['focus']}" if identity.get("focus") else ""
    return (
        "## Who I Am\n\n"
        f"**{identity['chinese']}** · {identity['handle']} · <{identity['email']}>\n"
        f"Git: {identity['git_name']} <{identity['git_email']}> · Languages: {langs_str}{focus_line}\n"
        f"Machine: {machine['id']} ({machine['os']})\n\n"
        "### Paths\n\n"
        "| Resource | Path |\n"
        "|----------|------|\n"
        f"| Identity | {paths['persona']}/identity.yaml |\n"
        f"| Voice | {paths['persona']}/voice.md |\n\n"
        "Persona is data only — no runtime, no active-run index.\n"
        "Active runs are repo-local: each project's `.agents/runs/` is authoritative.\n"
        "Cross-project journal goes to the operator's central-node repo (see voice.md).\n"
    )


def render_env(ctx: dict[str, Any]) -> str:
    identity = ctx["identity"]
    machine = ctx["machine"]
    paths = ctx["paths"]
    lines = [
        f'export AGENT_PERSON="{identity["chinese"]}"',
        f'export AGENT_MACHINE="{machine["id"]}"',
        f'export AGENT_MACHINE_OS="{machine["os"]}"',
        f'export AGENT_HANDLE="{identity["handle"]}"',
        f'export AGENT_EMAIL="{identity["email"]}"',
        f'export DOTPANEL_SUBSTRATE="{paths["substrate"]}"',
    ]
    return "\n".join(lines) + "\n"


def cmd_context(mode: str) -> int:
    """Entry point invoked from cli.main."""
    try:
        substrate = find_substrate()
    except SubstrateNotFound as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 2

    persona_dir = substrate.path_for("persona")
    if not persona_dir.is_dir():
        print(f"FAIL  persona directory not found: {persona_dir}", file=sys.stderr)
        return 2

    infra_dir: Path | None = None
    if substrate.has_path("infra"):
        candidate = substrate.path_for("infra")
        if candidate.is_dir():
            infra_dir = candidate

    try:
        ctx = gather_context(substrate.root, persona_dir, infra_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 2

    needs_machine = mode in ("name", "markdown")
    if needs_machine and ctx["machine"]["id"] == "unknown":
        # Per spec: --name and default markdown require machine-id resolution.
        print(
            "FAIL  $HOME/.machine-id is missing; required for context --name and default markdown.",
            file=sys.stderr,
        )
        return 3

    if mode == "name":
        sys.stdout.write(ctx["identity"]["chinese"])
        return 0
    if mode == "env":
        sys.stdout.write(render_env(ctx))
        return 0
    if mode == "json":
        sys.stdout.write(_json.dumps(ctx, indent=2) + "\n")
        return 0
    # default markdown
    sys.stdout.write(render_markdown(ctx))
    return 0


def build_context_parser(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--name", dest="mode_name", action="store_const",
                       const="name", help="print operator's chinese name only")
    group.add_argument("--env", dest="mode_env", action="store_const",
                       const="env", help="print eval-able shell exports")
    group.add_argument("--json", dest="mode_json", action="store_const",
                       const="json", help="print structured JSON")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotpanel context")
    build_context_parser(parser)
    args = parser.parse_args(argv)
    mode = args.mode_name or args.mode_env or args.mode_json or "markdown"
    return cmd_context(mode)


if __name__ == "__main__":
    raise SystemExit(main())
