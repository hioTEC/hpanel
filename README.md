# dotpanel

[中文版](README.zh-CN.md)

Personal Agent Workspace control plane. Public protocol library + Python CLI + harness adapter generator for AI coding agents (Claude Code, Codex, Kimi).

dotpanel solves the "agent setup is scattered across hidden home directories"
problem. It keeps universal operating rules in a public repo, keeps operator
persona data outside the public repo, and renders the exact startup files each
AI harness expects. After setup, a fresh `claude`, `codex`, or `kimi` session
loads the same protocol plus your persona without hand-editing `~/.claude/`,
`~/.codex/`, or `~/.kimi/`.

## What You Get

- `~/src/dotpanel/` as the public protocol + CLI source.
- A persona directory such as `~/.persona/` with `voice.md` and `identity.yaml`.
- A gitignored `~/src/dotpanel/persona` symlink pointing at that persona.
- Rendered harness adapters in `~/.claude/`, `~/.codex/`, and `~/.kimi/`.
- Optional launchers (`claw`, `codx`, `dot`) on PATH via `~/.config/dotpanel/path.sh`.

## Three-Layer Model

| Layer | Location | Scope |
|---|---|---|
| **Protocol** | this repo (public) | Universal methodology, skills, rules, reference |
| **Persona** | operator-private repo | Voice, identity, keyword routing, private reference |
| **Project** | `{project}/.agents/` | Run handoffs, decisions, project memory |

Persona content stays out of this repo. dotpanel ships only the universal protocol + the CLI that renders harness adapters from it.

## Skill Map

### User-invoked (8)

| Situation | Skill | What it does |
|---|---|---|
| Design a feature or approach | `/plan` | Multi-agent discussion → design artifact + Decision Registry |
| Deliver after plan sign-off | `/ship` | ADR → implement → cross-harness review → push → deploy → smoke |
| Parallel multi-stream feature | `/teamleader` | Spawn teammates per stream, coordinate cherry-picks |
| End a session | `/wrap` | Update run manifests, graduate learnings, journal |
| Push/pull dotpanel + persona | `/sync` | Thin wrapper around `dotpanel sync` |
| Code or design review | `/review` | Cross-harness dual review (sub-agent + external) |
| Evaluate or retire a tool | `/tool` | Try / drop / delete lifecycle |
| Curriculum gap analysis | `/curriculum-bridge` | Cross-reference two education systems, generate bridging course |

### Auto-triggered by other skills (5)

| Skill | Called by | Purpose |
|---|---|---|
| `grill-me` | `/plan`, `/ship` | One question at a time until all design branches resolved |
| `decision-gate` | `grill-me` output | Classify each choice: Convention / Decision / Discretion |
| `delegate-spec` | `implement-pipeline`, `/ship` | Decide self-do vs spawn sub-agent (100 LOC threshold) |
| `implement-pipeline` | large multi-session runs | State machine: code → review → verify → ship → wrap |
| `session-guardrails` | `implement-pipeline`, `/plan` | Auto-checkpoint at 30/50/100 turns, scope drift, ping-pong |

### Internal reference (1)

| Skill | Purpose |
|---|---|
| `investigate` | Root-cause analysis; 3 failed hypotheses → escalate to human |

### Main workflow

```
/plan ──→ /ship ──→ /wrap
  │         │
  └── grill-me, decision-gate,    └── delegate-spec, investigate,
      session-guardrails               code-review, session-guardrails

Large projects:  /plan → /teamleader → /wrap
```

## Quick Start

```bash
# 0. Clean Linux/WSL prerequisites
sudo apt-get update
sudo apt-get install -y git curl python3 python3-venv python3-pip gh
gh auth login --web

# 1. Clone
mkdir -p ~/src ~/vendor ~/tmp
git clone https://github.com/hioTEC/dotpanel.git ~/src/dotpanel

# 2. Install (Python >= 3.12)
# uv avoids PEP 668 system-python restrictions on modern Debian/Ubuntu.
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv tool install --editable ~/src/dotpanel

# 3. Create a persona directory
mkdir -p ~/.persona
# Write voice.md and identity.yaml (see docs/onboarding.md)

# 4. Wire the persona symlink
dotpanel init --persona-root ~/.persona

# 5. Render harness adapters
dotpanel configure --harness all

# 6. Open a new shell (or `source ~/.config/dotpanel/path.sh`)
#    so `claw` / `codx` / `dot` land on PATH

# 7. Verify
dotpanel doctor && dotpanel audit
```

If you cannot use `uv`, use an isolated virtual environment instead of writing
into the system Python:

```bash
python3 -m venv ~/.local/share/venvs/dotpanel
~/.local/share/venvs/dotpanel/bin/pip install -e ~/src/dotpanel
~/.local/share/venvs/dotpanel/bin/dotpanel --version
```

After step 4, `claude` / `codex` / `kimi` auto-load the generated adapters which reference your persona + the universal protocol. Direct `claude`, `codex`, `claw`, and `codx` use the official provider/auth path. Relay backends are explicit: `claw --variant NAME` runs Claude through `dotpanel secrets run --backend claude --variant NAME`, and `codx --variant PROFILE` or shortcuts such as `codx --let` run Codex through `dotpanel secrets run --backend codex --variant PROFILE -- codex -p PROFILE`.

VS Code extensions start their own agent servers directly, so switch them with launcher injection mode. For Codex, `codx --vscode --variant PROFILE` writes a managed block in Remote `server-env-setup` and an isolated `CODEX_HOME=~/.codex-vscode/PROFILE`; use `codx --vscode --openai` to switch back to the official OpenAI config at `~/.codex`. For Claude Code, `claw --vscode --variant NAME` injects the Claude relay env, and `claw --vscode --official` restores the official Claude path. Restart VS Code Remote / vscode-server after changing either one.

Codex user skills render to `~/.agents/skills/`, while Codex config and runtime stay in `~/.codex/`. `configure` also renders `~/.codex/rules/default.rules`, the regular-mode command prefix allowlist for narrow trusted commands such as `git` and common test/build invocations. For day-to-day updates across machines, run `dotpanel sync pull` — it pulls configured repos, reinstalls dotpanel if its source changed, and re-runs `configure --harness all`.

## CLI

| Command | Purpose |
|---|---|
| `dotpanel root` | Print install path |
| `dotpanel --version` | Print version |
| `dotpanel init` | Create persona symlink, run doctor |
| `dotpanel doctor` | Verify install, symlinks, paths, invariants |
| `dotpanel audit` | Structural checks (CI-safe) |
| `dotpanel configure --harness all` | Render `~/.claude/`, `~/.codex/`, `~/.kimi/` |
| `dotpanel configure --check` | Dry-run validation |
| `dotpanel sync pull` | Multi-phase: pull repos → reinstall dotpanel if updated → re-`configure --harness all` |
| `dotpanel sync push\|status\|diff` | Per-repo leak-checked push; read-only status/diff |
| `dotpanel secrets list\|run\|export\|edit` | Scoped secrets API (age-encrypted) |
| `dotpanel context` | Resolve identity + machine + path anchors |
| `dotpanel ssh render` | Generate SSH config from machines.yaml |
| `dotpanel install <tool>` | SHA-256-verified binary installer |
| `dotpanel uninstall --harness all` | Remove banner-marked files |

## Architecture

```
protocol/
  workspace.md          Operating principles (always loaded)
  skills/               Multi-step procedures (14 skills)
  rules/                Decision frameworks (14 rules)
  reference/            Cross-project knowledge
harness/
  claude/templates/     CLAUDE.md, settings.json, statusline.py
  codex/templates/      AGENTS.md, config.toml, rules/default.rules
  kimi/templates/       AGENTS.md
dotpanel/               Python CLI source
tools/bin/              Bundled launchers (claw, codx, dot)
docs/                   ADRs, design docs, onboarding
```

## Documentation

- [Onboarding](docs/onboarding.md) — first-session walkthrough
- [Architecture](docs/architecture.md) — 3-layer model, file taxonomy, configure protocol
- [ADR-0001](docs/adr/0001-repo-split.md) — public/private boundary
- [ADR-0002](docs/adr/0002-paths-and-layout.md) — path resolution + persona bridge
- [ADR-0003](docs/adr/0003-configure-protocol.md) — banner protocol, dry-run gate

## License

Apache-2.0
