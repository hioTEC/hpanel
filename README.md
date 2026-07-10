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
- Python 3 with `PyYAML` (for exact skill-frontmatter validation)

Debian/Ubuntu:

```bash
sudo apt-get install -y git age jq python3 python3-yaml
```

macOS:

```bash
brew install git age jq
python3 -m pip install PyYAML
```

Fresh machine without an existing memspace:

```bash
mkdir -p ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

Machine with an existing memspace repo:

```bash
git clone --recurse-submodules <your-agents-repo> ~/.agents
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
requires a clean worktree and a fast-forward path. After the fast-forward it
recursively initializes/updates submodules. Harness files are rendered only
after those steps succeed. Requested Claude/Codex skill renders and ownership
collisions are prepared before any generated harness state is changed.

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
- `dot doctor` checks that the entry exists and generated wrappers, shell
  integration, Claude plugins, and declared Codex aliases exactly match their
  source render. Symlinked/non-regular generated files and coherence failures
  return a non-zero status.

Rendered harness entries are deliberately tiny. They tell the harness to read
`~/.agents/AGENTS.md`; they do not duplicate your private rules.

Shell rc mutation is fail-closed: `dot set path` and `dot unset path` refuse a
symlinked or non-regular rc file, recheck its mutation boundary, preserve the
mode of an existing file, and clean same-directory rewrite files after failure
or signal. `DOT_SHELL_RC` and `ZDOTDIR` may still select an rc outside `HOME`.

Claude plugin rendering accepts only path-safe skill IDs, closed frontmatter
with one `name` and `description`, and source trees without symlinks. Generated
plugins carry a regular `.dotpanel-owner` marker. Reconciliation, doctor, and
unset use that marker; an exact legacy dot render without the marker is migrated
once, while unmanaged destinations are never overwritten or deleted.

### Optional Codex skill aliases

`dot set codex` and `dot configure --harness codex` also reconcile short Codex
skill aliases when `~/.agents/skills/sources.json` exists. A minimal version 1
manifest looks like this:

```json
{
  "version": 1,
  "alias_adapter": {
    "owner": "dotpanel",
    "destination": "~/.codex/skills",
    "renderer": "dot set codex",
    "retired_aliases": ["old-name"]
  },
  "aliases": [
    {
      "id": "plan",
      "source": "local",
      "skill": "plan-discussion",
      "target": "plan-discussion/SKILL.md",
      "description": "Use for structured planning and architecture choices.",
      "guidance": "Keep the resulting design proposed until operator sign-off."
    }
  ],
  "sources": [
    {"id": "local", "paths": ["skills/local"]}
  ]
}
```

The adapter is enabled only when the manifest is a regular, non-symlinked file
and `owner`, `destination`, and `renderer` exactly match the values above.

Each referenced alias source must resolve to exactly one relative directory
below the memspace's `skills/` root, and neither that root nor the declared
source directory itself may be a symlink. Its target must be a regular,
non-symlinked file inside that source; aliases can never route into `secrets/`.
Every alias supplies its own one-line `description` and may add one-line
alias-specific `guidance`; each is capped at 500 characters. Control characters
and multiline values are rejected. The generated
`~/.codex/skills/<id>/SKILL.md` uses that discovery metadata and links to the
canonical file instead of copying its instructions or bundled resources.

Generated aliases carry a dot ownership banner. Reconciliation refuses to
overwrite a matching directory without that banner, removes stale or retired
directories only when they carry the banner, and leaves all unrelated Codex
skills untouched. `dot unset codex` follows the same ownership rule.
`dot doctor` reports missing aliases, content drift, and stale dot-managed
aliases.
An absent manifest means the desired alias set is empty. The next
`dot set codex` removes stale aliases carrying dotpanel's ownership banner and
leaves unmanaged Codex skills untouched; normal Codex entry rendering still
continues.

## What `dkey` Does

`dkey` stores secret values encrypted with age:

```bash
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey list
```

`dkey set`, `dkey edit`, and identity import keep sensitive intermediates in
random `0600` files and remove them on success, failure, or HUP/INT/TERM. The
encrypted keys or identity target is replaced only after validation succeeds.
Sensitive target overrides must be absolute and lexically normalized;
directories, symlinks, and symlinked mutation boundaries are refused. `dkey
doctor` applies the same path checks and rejects age identities exposed to
group or other users.

The implementation is portable POSIX shell: it revalidates immediately before
the final rename, but cannot make validation plus rename descriptor-relative.
Do not let another same-user process concurrently replace the validated parent
directories while a mutation is running.

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

`dkey on --with GRANT` changes only the current shell. Unscoped activation is
disabled, and an active grant must be removed with `dkey off` before another is
activated. Activation and removal are preflighted in a subshell so readonly or
tampered control variables do not leave untracked partial state. Direct
`command dkey on` refuses to print secret-bearing shell code; use the shell
function installed by `dot init`.

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
Reset is ownership-aware and conservative: Claude reset removes only
registry-declared managed env keys; Codex reset removes registry-managed
provider sections and clears the legacy API-key auth override only when the
active top-level provider is registry-managed. User-owned providers, unrelated
settings, and OAuth token fields are preserved. Inputs are validated and
prepared before any target is replaced; this is not a cross-file transaction
against filesystem failures. Reset refuses multiline TOML and provider-table
forms outside the conservative legacy subset instead of partially rewriting
them. Reset target paths must stay below `HOME`, and every path component from
the home boundary to the target must be non-symlinked.
See [PROVIDERS.md](PROVIDERS.md) for the provider schema and a template at
`templates/secrets/dkey.providers.example.json`.

## Files Created

`dot init` may create or update:

- `~/.agents/.dotpanel/env.sh`
- `~/.claude/CLAUDE.md`
- `~/.codex/AGENTS.md`
- `~/.kimi/AGENTS.md`
- `~/.claude/skills/{hio,matt,impeccable}/` with a `.dotpanel-owner` marker
- `~/.codex/skills/<alias>/SKILL.md` when declared by
  `~/.agents/skills/sources.json`

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
- `dot sync pull` fetches before its clean-worktree and fast-forward-only gates,
  then recursively initializes/updates submodules. If render preparation fails
  after a successful fast-forward, Git stays at the pulled commit while the
  prior generated snapshot remains; fix the source, rerun `dot set -a`, and
  verify with `dot doctor`.
- `dot self update` refuses a dirty managed checkout.
- `dkey` is privileged; do not use it from subagents or scripts that should not
  see secrets.

## See Also

- [CHANGELOG.md](CHANGELOG.md)
- [PROVIDERS.md](PROVIDERS.md) — provider registry schema
- [LICENSE](LICENSE)
