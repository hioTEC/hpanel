# dotpanel

`dotpanel` is a tiny shell toolkit for an agent memspace.

Core invariant:

```text
~/.agents/ is your memspace.
~/.agents/AGENTS.md is the entry.
~/.agents/.dotpanel/ is managed tooling and must be gitignored.
```

The repo intentionally does not define what your `~/.agents/` tree looks like.
It only provides:

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

`dot init` configures harness entry files and installs `dot` / `dkey` into
`~/.local/bin`. The current already-open shell may need:

```bash
. ~/.agents/.dotpanel/env.sh
```

## Commands

```text
dot init [--template|--blank|--from PATH|--no-entry] [--yes] [--no-path]
dot configure [--harness all|claude|codex|kimi]
dot doctor
dot path
dot sync status|diff|pull|push
dot self status|update
```

`dot configure` renders a minimal wrapper into each harness:

```text
`~/.agents/` is your memspace. `~/.agents/AGENTS.md` is the entry.
```

No recursive scan, no hidden overlay, no private bridge.

## dkey

```text
dkey init
dkey keygen
dkey edit
dkey list
dkey status
dkey doctor
dkey run --with GRANT -- COMMAND
dkey on --with GRANT
dkey off
```

`dkey` is for privileged CLI capability grants, not routine LLM backend setup.
It decrypts only when a grant is used and injects only the selected environment
variables into the target process or current shell.

`dkey on/off` affect the current shell after `dot init` has sourced
`~/.agents/.dotpanel/env.sh`. Direct `dkey on` refuses to print secret-bearing
shell code.

Subagents must not invoke `dkey` or wrappers known to use it. Resource-affecting
credential use stays with the main agent.
