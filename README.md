# dotpanel

[中文版](README.zh-CN.md)

`dotpanel` is the small public toolkit that makes an agent memspace usable on a
machine. It installs two commands:

- `dot` keeps `~/.agents` wired into Claude, Codex, and Kimi harnesses.
- `dkey` stores encrypted environment secrets and injects them only when asked.

It does not define your private rules, projects, memories, or infrastructure.
Those live in your own memspace repo at `~/.agents`.

## Mental Model

```text
~/.agents/            your private memspace repo
~/.agents/AGENTS.md   the entry file agents read first
~/.agents/.dotpanel/  this public toolkit checkout, ignored by git
```

`dotpanel` is intentionally small. It provides bootstrap, rendering, sync
helpers, and secret injection. Your memspace decides what the agent should know.

## Install

### Homebrew (macOS / Linux)

```bash
brew tap hioTEC/dotpanel
brew install dotpanel
dot init
```

### dpkg (Debian / Ubuntu)

```bash
curl -LO https://github.com/hioTEC/dotpanel/releases/latest/download/dotpanel_latest_all.deb
sudo dpkg -i dotpanel_latest_all.deb
dot init
```

### From source (any platform)

Dependencies:

- `git`
- `age` and `age-keygen` (from the `age` package)
- `jq`

Debian/Ubuntu:

```bash
sudo apt-get install -y git age jq
```

macOS:

```bash
brew install git age jq
```

Fresh machine without an existing memspace:

```bash
mkdir -p ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

Machine with an existing memspace repo:

```bash
git clone <your-agents-repo> ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init --no-entry
```

`dot init` adds `~/.agents/.dotpanel/bin` to PATH through shell integration and
renders the harness entry files. For an already-open shell:

```bash
. ~/.agents/.dotpanel/env.sh
```

The shell integration also defines two convenience aliases:

```bash
claw='claude --dangerously-skip-permissions'
codx='codex --dangerously-bypass-approvals-and-sandbox'
```

After updating dotpanel (`dot self update` or `dot path`), source again:

```bash
. ~/.agents/.dotpanel/env.sh
```

If the aliases are still missing (`claw: command not found`), regenerate the env
file first:

```bash
dot path && . ~/.agents/.dotpanel/env.sh
```

## Everyday Commands

Render harness entry files after editing `~/.agents/AGENTS.md`:

```bash
dot set -a
dot set claude
dot set codex
dot set kimi
```

Check local wiring:

```bash
dot doctor
dkey doctor
```

Sync the private memspace repo:

```bash
dot sync status
dot sync diff
dot sync pull
dot sync push "sync memspace"
```

Switch harness backends (reads `~/.agents/secrets/dkey.providers.json`):

```bash
dkey use claude:deepseek
dkey use codex:qwen:payg-global
dkey use all:deepseek
```

Update this public toolkit checkout:

```bash
dot self status
dot self update
```

## What `dot` Does

`dot` manages machine wiring around the memspace:

- `dot init` bootstraps shell integration and adds dotpanel commands to PATH.
- `dot set` renders minimal harness entry files from `~/.agents/AGENTS.md`.
- `dot sync` runs git operations in `~/.agents`.
- `dot self` runs git operations in `~/.agents/.dotpanel`.
- `dot doctor` checks that the local setup is coherent.

Rendered harness entries are deliberately tiny. They tell the harness to read
`~/.agents/AGENTS.md`; they do not duplicate your private rules.

## What `dkey` Does

`dkey` stores secret values encrypted with age:

```bash
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey list
```

It can inject those secrets into one command:

```bash
dkey run --with GRANT -- command arg1 arg2
```

Or into the current shell when shell integration is loaded:

```bash
dkey on --with GRANT
dkey status
dkey off
```

`dkey on` changes only the current shell. Direct `command dkey on` refuses to
print secret-bearing shell code; use the shell function installed by `dot init`.

`dkey use` writes harness backend settings from a provider registry:

```bash
dkey use claude:deepseek       # switch Claude Code to a backend
dkey use codex:qwen:payg-global # switch Codex to a backend
dkey use all:deepseek           # switch both
```

The provider registry lives at `~/.agents/secrets/dkey.providers.json`.
See [PROVIDERS.md](PROVIDERS.md) for the full schema and a template at
`templates/secrets/dkey.providers.example.json`.

## Files Created

`dot init` may create or update:

- `~/.agents/.dotpanel/env.sh`
- `~/.claude/CLAUDE.md`
- `~/.codex/AGENTS.md`
- `~/.kimi/AGENTS.md`

`dkey init` may create:

- `~/.agents/secrets/dkey.conf`
- `~/.agents/secrets/keys.env.template`
- `~/.agents/secrets/keys.env.age`
- `~/.agents/secrets/dkey.providers.json`

## Boundaries

- `~/.agents` is user-owned and private.
- `~/.agents/.dotpanel` is the managed public checkout and should be ignored by
  the memspace repo.
- `dot sync push` stages all non-ignored changes under `~/.agents`.
- `dkey` is privileged; do not use it from subagents or scripts that should not
  see secrets.

## See Also

- [CHANGELOG.md](CHANGELOG.md)
- [PROVIDERS.md](PROVIDERS.md) — provider registry schema
- [LICENSE](LICENSE)
