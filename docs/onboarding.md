---
name: Collaborator onboarding
description: First-session guide for new collaborators using dotpanel — AI reads this to interactively bootstrap a fresh operator
type: reference
tags: [onboarding, setup, workflow]
---

# Collaborator Onboarding

This doc is the first-session script for a new collaborator. The agent should
read it during the first `claude` / `codex` / `kimi` session and walk the
operator through one phase at a time — confirm each step before moving on; do
not dump the whole document at once.

> **Scope.** dotpanel is the public, fork-able half of a 3-layer model
> (protocol / persona / project). Cloning dotpanel is enough to get started.
> You do **not** need access to any operator's private dotfiles, secrets, or
> infrastructure repos to use dotpanel. Anything you read here that mentions
> "operator-private" infra refers to *your own* setup, not someone else's.

---

## Phase 0: Prerequisites

Before starting, confirm:

1. A Linux box (incl. WSL) or macOS.
2. `git`, `curl`, Python ≥ 3.12, and `uv` installed.
   On a clean Ubuntu/WSL box:

   ```bash
   sudo apt-get update
   sudo apt-get install -y git curl python3 python3-venv python3-pip gh
   gh auth login --web
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   ```

   `uv` is the preferred install path because modern Debian/Ubuntu systems
   mark system Python as externally managed (PEP 668). If `uv` is unavailable,
   use a dedicated venv; do not install dotpanel into system Python.

3. Unix-style workspace directories exist:

   ```bash
   mkdir -p ~/src ~/vendor ~/tmp
   ```

   Owned repos go under `~/src/`; third-party trials under `~/vendor/`;
   one-off scripts and reports under `~/tmp/`.

4. At least one AI harness CLI installed and reachable:
   - `claude --version` — Claude Code (`npm i -g @anthropic-ai/claude-code`)
   - `codex --version` — Codex CLI
   - `kimi --version` — Kimi CLI

   Pick whichever you'll use; you can add the others later.

5. dotpanel cloned and installed:

   ```bash
   git clone <dotpanel-repo-url> ~/src/dotpanel
   uv tool install --editable ~/src/dotpanel
   dotpanel --version    # confirm install
   ```

   venv fallback:

   ```bash
   python3 -m venv ~/.local/share/venvs/dotpanel
   ~/.local/share/venvs/dotpanel/bin/pip install -e ~/src/dotpanel
   ~/.local/share/venvs/dotpanel/bin/dotpanel --version
   ```

If anything is missing, fix it before continuing. Once `dotpanel --version`
prints, Phase 0 is done.

---

## Phase 1: Persona — Tell dotpanel Who You Are

A **persona** is a small directory containing your operator data: how you
want the agent to address you, your git identity, voice/tone preferences,
and any private routing rules. dotpanel reads it through a gitignored symlink
so your persona never enters this public repo.

You choose where the persona lives. Recommended locations:

- `~/.persona/` — simple, lives in your home directory.
- A path inside your own private dotfiles repo, if you have one.

Create the directory and the two required files:

```bash
mkdir -p ~/.persona

cat > ~/.persona/voice.md <<'EOF'
# <your handle> — Persona

> Operator-private voice. Read by the harness wrapper before the public protocol.

## §0 — Identity
(Describe how you want the agent to address you; communication style; values.)

## §1 — Voice
(Language preferences, tone, hedging style.)
EOF

cat > ~/.persona/identity.yaml <<'EOF'
name:
  chinese: "your handle"     # or just your preferred display name
handle: yourhandle
email: "you@example.com"
languages: [en]
git:
  name: yourhandle
  email: "you@example.com"
EOF
```

Edit both files to match how you want the agent to interact with you. Keep
voice.md focused on identity/voice/tone — no methodology, no runtime state.

Then bind the persona to dotpanel:

```bash
dotpanel init --persona-root ~/.persona
```

This creates a gitignored symlink at `~/src/dotpanel/persona ->` your persona
directory and runs `dotpanel doctor` to verify the bridge.

---

## Phase 2: Render Harness Adapters

`dotpanel configure` generates the wrapper files the AI harness reads at
session start (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
`~/.kimi/AGENTS.md`, plus skill wrappers and settings). Each generated file
carries a banner so `dotpanel uninstall` can clean up safely.

Render for whichever harness(es) you installed:

```bash
dotpanel configure --harness claude    # or codex, kimi, or "all"
dotpanel configure --check             # dry-run validator
dotpanel doctor                         # final sanity check
```

After this, launching `claude` (or `codex`, `kimi`) auto-loads:

1. `<dotpanel-root>/persona/voice.md` — your private voice.
2. `<dotpanel-root>/protocol/workspace.md` — universal methodology.

Edits to either file take effect on the next agent session — no reconfigure
needed. Reconfigure only after **structural** changes (new skill, changed
harness path, dotpanel upgrade).

> **Do not hand-edit** files in `~/.claude/`, `~/.codex/`, or `~/.kimi/`.
> They are rendered output; dotpanel will overwrite them on the next configure.
> Edit the source under `~/src/dotpanel/` (or your persona) instead.

Phase 2 done when the harness CLI starts and the agent greets you using
your `voice.md` identity.

---

## Phase 3: Understand the Architecture

### Three Layers

```
PROTOCOL (universal methodology, public)
    ~/src/dotpanel/protocol/workspace.md     working style, stop rules, principles
    ~/src/dotpanel/protocol/rules/           engineering / interaction / collaboration rules
    ~/src/dotpanel/protocol/skills/          reusable procedures (plan / review / ship / wrap / sync / tool)
    ~/src/dotpanel/protocol/reference/       cross-project knowledge

PERSONA (operator data, private — yours, on your machine)
    <your persona>/voice.md                voice / identity prose
    <your persona>/identity.yaml           handle / email / git config
    <your persona>/rules/                  optional: private routing rules
    <your persona>/reference/              optional: machine / infra notes
    Persona is data only. No methodology, no runtime state, no program logic.

PROJECT (per project, travels with the code)
    {project}/.agents/runs/active.yaml     active-run truth source
    {project}/.agents/runs/<id>/handoff.md per-run state
    {project}/.agents/journal/diaries/     project-level diary
    {project}/.agents/memory/              project-scoped facts
```

### Directory Layout

```
~/src/dotpanel/
├── protocol/                           ← universal methodology
├── harness/{claude,codex,kimi}/templates/  ← wrapper templates
├── dotpanel/                             ← Python CLI source
└── persona                             ← gitignored symlink → your persona dir

<your persona dir>/                     ← e.g. ~/.persona or your own private repo
├── voice.md                            ← required
├── identity.yaml                       ← required
├── rules/                              ← optional
└── reference/                          ← optional
```

Generated harness homes (`~/.claude/`, `~/.codex/`, `~/.kimi/`) and Codex's
user skill surface (`~/.agents/skills/`) are **rendered output**, not source.
They're reproducible from dotpanel + persona at any time.

### File Classes

Every file under dotpanel + persona is exactly one of:

| Class | Definition | Owner |
|---|---|---|
| **Rendered** | Generated by `dotpanel configure`; carries a banner or is listed in `DOTPANEL_MANAGED_JSON`. | dotpanel writes; do not hand-edit |
| **Symlink** | OS bridge between layers (e.g. `~/src/dotpanel/persona`). | dotpanel creates via `init` |
| **Source** | Canonical authored content. | The layer's owner edits directly |

### Secrets and Independence

dotpanel itself does **not** ship a secret manager. For LLM API keys and any
other secrets, dotpanel reads `os.environ` and assumes you've already
populated the required environment variables. Your secret-management
mechanism (1Password CLI, age, direnv, GitHub Secrets in CI, …) is your
choice — document it in your own `voice.md` so the agent knows how to ask
you about it.

> If you collaborate with someone else's dotpanel-based workspace, you are
> not expected to have access to *their* secrets, dotfiles, or
> infrastructure. Bring your own.

---

## Phase 4: Workflow Basics

### Active Run Protocol

Small tasks: just do them. Only create an active run when you need
multi-agent concurrency, an independent worktree, or cross-session handoff.

Active runs are **repo-local**: `{project}/.agents/runs/active.yaml` is the
truth source, `{project}/.agents/runs/<run-id>/handoff.md` is the per-run
state. There is no global active-run index — to resume in another project,
go to that project's `.agents/runs/`.

Concurrent updates use an optimistic guard: each run in the manifest has a
`revision`, the handoff frontmatter has a matching `manifest_revision`.
Editing status / owner / scope / blocker / evidence / "Resume here" requires
reading both first; on write, increment both. Mismatches mean re-read and
merge — do not blind-overwrite.

Product sequencing lives in `{project}/docs/roadmap.md`; architecture truth
lives in ADRs / specs / rules / `CONTEXT.md`.

### Slash Commands

| Command | Purpose | When |
|---|---|---|
| `/plan` | Structured planning / discussion | New idea, design needed |
| `/review` | Dual-model code or design review | Before commit/merge |
| `/ship` | Delivery pipeline (review → test → commit → push → verify) | Review passed |
| `/wrap` | Session close, write durable handoff state | State changed and you're stopping |
| `/sync` | Config sync (push/pull dotfiles + dotpanel) | Configuration changes |
| `/tool` | Tool lifecycle (try / archive / drop) | Trying or retiring a tool |
| `/curriculum-bridge` | Curriculum comparison / bridging | Course-mapping work |
| `/teamleader` | Multi-stream orchestration with background teammates | Wide parallel work |

All slash commands are thin wrappers that delegate to skills under
`~/src/dotpanel/protocol/skills/`. Read the source if you want to know
exactly what each one does.

### Multi-Operator Collaboration

See `~/src/dotpanel/protocol/rules/collaboration.md` (short, universal). Each
operator owns their own persona — never edit anyone else's. Run
owner/scope/status come from the project-local manifest. Cross-operator
coordination goes through the project's `.agents/`, never through writes
into another person's persona.

---

## Phase 5: First Real Task

A reasonable first session:

1. Pick a project under `~/src/`, `cd` into it.
2. If it has `.agents/runs/active.yaml`, read it and pick an in-flight run.
3. Read the corresponding `handoff.md` plus any ADR/spec/design docs it
   names.
4. Make a small forward step (single-file change, small refactor,
   documentation fix).
5. When state has materially changed, run `/wrap` to write a durable
   handoff so the next session can resume cleanly.

If the project has no `.agents/` yet, that's fine — start by adding
`.agents/runs/active.yaml` only when you actually need an active run.

---

## Appendix A: Windows + WSL Notes

### Multiple Shells

| Shell | Where | Use |
|---|---|---|
| **WSL bash/zsh** | Windows Terminal → Ubuntu | **Primary dev environment; all dotpanel/AI commands run here** |
| PowerShell | Windows Terminal → PowerShell | Windows admin only — not for development |
| Git Bash | Git for Windows | PATH/env incompatible — not recommended |
| CMD | Legacy | Not used |

**Rule:** all development happens inside WSL. PowerShell / Git Bash / CMD do
not load your shell config and will not have dotpanel on PATH.

Confirm you're inside WSL:

```bash
uname -r              # should contain "microsoft" or "WSL"
echo $WSL_DISTRO_NAME # should print "Ubuntu" (or similar)
```

### Clock Drift

WSL2 can lag behind real time after sleep, breaking TLS (git, curl) and any
crypto with timestamp checks:

```bash
sudo hwclock -s                  # quick resync
# or
sudo ntpdate pool.ntp.org        # via NTP
```

For a long-term fix, schedule it with a systemd timer.

### Proxy

WSL traffic does **not** automatically use Windows-side proxies (Clash,
Mihomo, etc.). If you need one:

```bash
export HTTP_PROXY=http://127.0.0.1:7890     # whatever port your proxy uses
export HTTPS_PROXY=$HTTP_PROXY
export NO_PROXY=localhost,127.0.0.1         # plus any internal/Tailscale ranges
```

### Windows PATH Leakage

WSL inherits Windows PATH by default (`/mnt/c/Windows/...`). Usually fine,
but if `which node` ever points at `/mnt/c/.../node.exe`, disable in
`/etc/wsl.conf`:

```ini
[interop]
appendWindowsPath = false
```

### File Permissions

`/mnt/c/` files are reported as 777 and `chmod` is a no-op there. Keep
sensitive files (SSH keys, API tokens, your persona) on the WSL filesystem
(`~/...`), never under `/mnt/c/`.

### systemd

If you use anything that needs systemd user units, enable it in
`/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

Then `wsl --shutdown` from PowerShell and reopen.

---

## Appendix B: macOS Notes

- Homebrew: ensure `/opt/homebrew/bin` is in PATH (Apple Silicon default).
- Tailscale: install via App Store, not CLI.
- iCloud-synced source paths can have unusual filename rules; prefer
  `~/src/` outside `~/Library/Mobile Documents/` for git work.
- For secret storage you can use macOS Keychain via `security
  add-generic-password`; bridge it to env vars in your shell rc.

---

## Appendix C: Compatibility Checklist

| Check | Healthy | Fix |
|---|---|---|
| `python3 --version` | ≥ 3.12 | install via pyenv / brew / apt |
| `dotpanel --version` | prints semver | `uv tool install --editable ~/src/dotpanel` |
| `dotpanel doctor` | OK | follow the FAIL message; usually `dotpanel init` |
| `claude --version` (or codex/kimi) | prints version | install the harness CLI |
| `git config user.email` | set | `git config --global user.email "..."` |
| `locale` | UTF-8 | `export LANG=en_US.UTF-8` |
| `date` | accurate | WSL: `sudo ntpdate pool.ntp.org` |
| `ls -l ~/src/dotpanel/persona` | symlink → your persona dir | `dotpanel init --persona-root <path>` |
