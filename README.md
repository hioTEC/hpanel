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

`dot init` adds `~/.agents/.dotpanel/bin` (dot, dkey) and `~/.agents/tools/bin`
(claw/codx) to PATH through shell integration and renders the harness entry
files. For an already-open shell:

```bash
. ~/.agents/.dotpanel/env.sh
```

The shell integration no longer defines `claw`/`codx` aliases — both are memspace
multi-call PATH scripts in `~/.agents/tools/bin/`, each switching backend
per-invocation from `dkey.providers.json`:

```text
claw / clawb   — claude front-end / headless worker
codx / codxb   — codex  front-end / headless worker
```

After updating dotpanel (`dot self update` or `dot set path`), source again:

```bash
. ~/.agents/.dotpanel/env.sh
```

If `codx` is still missing (`codx: command not found`), regenerate the env
file first:

```bash
dot set path && . ~/.agents/.dotpanel/env.sh
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
dot sync push
```

`dot sync push` pushes existing commits only. It refuses staged, unstaged, or
untracked files and never stages or commits them. Commit the exact paths you
intend to share before running it. `dot sync pull` prints status, fetches, then
requires a clean worktree and a fast-forward path before updating and
re-rendering harness files.

Switch AI backends per invocation (reads `~/.agents/secrets/dkey.providers.json`
and injects keys with the `llm-backends` grant when needed):

```bash
claw deepseek
clawb deepseek "review this change"
codx qwen
codxb qwen "review this change"
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
- `dot doctor` checks that the entry exists and generated wrappers and Claude
  plugins exactly match their source render. These coherence failures return a
  non-zero status.

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

AI backend definitions live in `~/.agents/secrets/dkey.providers.json`.
`claw`/`clawb`, `codx`/`codxb`, and `gem`/`gemb` read that registry and apply
backend settings only to the process they launch. Secrets are loaded through the
`llm-backends` grant.

```bash
codx qwen "prompt"
clawb kimi "prompt"
```

`dkey use` has been removed because it persisted global harness settings and
could overwrite Codex ChatGPT/OAuth login state with API-key mode. Use
`dkey reset codex|claude|all` only to clear old persisted backend settings.
See [PROVIDERS.md](PROVIDERS.md) for the provider schema and a template at
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
- `dot sync push` refuses a dirty memspace and pushes existing commits only; it
  never stages or commits files.
- `dot sync pull` fetches before its clean-worktree and fast-forward-only gates;
  harness files are rendered only after a successful update.
- `dot self update` refuses a dirty managed checkout.
- `dkey` is privileged; do not use it from subagents or scripts that should not
  see secrets.

## See Also

- [CHANGELOG.md](CHANGELOG.md)
- [PROVIDERS.md](PROVIDERS.md) — provider registry schema
- [LICENSE](LICENSE)
