# dotpanel

[中文版](README.zh-CN.md)

`dotpanel` is a tiny shell toolkit for an agent memspace.

Core invariant:

```text
~/.agents/ is your memspace.
~/.agents/AGENTS.md is the entry.
~/.agents/.dotpanel/ is managed tooling and must be gitignored.
```

The repo provides a minimal `AGENTS.md` template and the small tools needed to
install/sync a memspace. It does not proactively create the optional memspace
folders; agents and users can grow them naturally when they have memory to
store.

- `dot` — sync and render helper for the memspace.
- `dkey` — age-backed capability grants for short-lived CLI secret injection.

## Install

Fresh machine:

```bash
mkdir -p ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

Existing memspace repo:

```bash
git clone <your-agents-repo> ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

`dot init` creates `AGENTS.md` only when requested/accepted, configures harness
entry files, and installs `dot` / `dkey` into `~/.local/bin`. The current
already-open shell may need:

```bash
. ~/.agents/.dotpanel/env.sh
```

## Commands

```text
dot init [--template|--blank|--from PATH|--no-entry] [--yes] [--no-path]
dot set -a|--all
dot set claude|codex|kimi
dot configure [--harness all|claude|codex|kimi]
dot doctor
dot path
dot sync status|diff|pull|push
dot self status|update
```

`dot configure` is the long internal form. Humans usually use `dot set`.

### Daily workflow

Use `dot set` after editing `~/.agents/AGENTS.md` or after pulling memspace
changes:

```bash
dot set -a        # render Claude, Codex, and Kimi entries
dot set claude    # render only ~/.claude/CLAUDE.md
dot set codex     # render only ~/.codex/AGENTS.md
dot set kimi      # render only ~/.kimi/AGENTS.md
```

The rendered harness entry is intentionally minimal:

```text
`~/.agents/` is your memspace. `~/.agents/AGENTS.md` is the entry.
```

No recursive scan, no hidden overlay, no private bridge.

Use `dot sync` to move the memspace itself across machines:

```bash
dot sync status
dot sync diff
dot sync pull
dot sync push "sync memspace"
```

`dot sync pull` runs `git pull --ff-only` in `~/.agents`, then runs
`dot set -a`. `dot sync push` stages all `~/.agents` changes, creates a commit
when needed, and pushes.

### Script assumptions

- `dot init` is a bootstrap command. The install script normally runs it once;
  people should not need it day to day.
- `~/.agents` is the user-owned memspace repo. `~/.agents/.dotpanel` is the
  managed dotpanel checkout and is ignored by the memspace repo.
- `dot` and `dkey` are symlinked into `~/.local/bin`.
- The shell loads `~/.agents/.dotpanel/env.sh`; already-open shells may need
  `. ~/.agents/.dotpanel/env.sh`.
- `dot sync` assumes `~/.agents` is a git repo with a configured remote.
- `dot sync pull` only accepts fast-forward pulls.
- `dot sync push` intentionally commits every tracked/untracked memspace change
  under `~/.agents`, except ignored files such as `.dotpanel/`.

## Templates

Tracked templates live in `templates/`:

- `templates/AGENTS.md` — minimal memspace entry scaffold.
- `templates/secrets/dkey.conf` — starter grant map.
- `templates/secrets/keys.env.template` — starter plaintext env template.

`dot init --template` copies only the entry scaffold. `dkey init` creates only
`secrets/` files needed for dkey; it does not create the rest of the memspace
layout.

## dkey

```text
dkey init
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey edit
dkey list
dkey status
dkey doctor
dkey run --with GRANT -- COMMAND
dkey on [--with GRANT]
dkey off
```

`dkey` is for privileged CLI capability grants, not routine LLM backend setup.
It decrypts only when a grant is used and injects only the selected environment
variables into the target process or current shell.

First-time secret setup:

```bash
dkey keygen
dkey set OPENAI_API_KEY sk-...
dkey set ANTHROPIC_API_KEY sk-ant-...
dkey list
```

`dkey keygen` creates the local age identity at `~/.config/age/key.txt` when it
does not already exist. `dkey set` creates or overwrites a named encrypted key
inside `~/.agents/secrets/keys.env.age`; setting the same name again replaces
the old value.

Current-shell env workflow:

```bash
dkey on
dkey status
dkey off
```

`dkey on` exports all encrypted keys into the current shell. `dkey off` unsets
every variable that `dkey on` set. These commands affect the current shell only
after `dot init` has installed the shell function from
`~/.agents/.dotpanel/env.sh`; direct `dkey on` refuses to print secret-bearing
shell code.

Grant workflow remains available for narrower command execution:

```bash
dkey run --with GRANT -- COMMAND
dkey on --with GRANT
dkey off
```

Subagents must not invoke `dkey` or wrappers known to use it. Resource-affecting
credential use stays with the main agent.
