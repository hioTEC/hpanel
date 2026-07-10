# Changelog

## Unreleased

### Changed
- **Breaking:** persistent backend switching via `dkey use` has been removed.
  Use per-invocation wrappers (`claw`/`clawb`, `codx`/`codxb`, `gem`/`gemb`)
  instead; they read `dkey.providers.json` and load secrets through grants
  without rewriting global harness config or Codex auth state.
- **Breaking:** unscoped `dkey on` activation is disabled. Current-shell
  activation now requires one or more `--with GRANT` scopes.

### Added
- Optional Codex skill alias rendering from `~/.agents/skills/sources.json`.
  Generated adapters link to safely resolved canonical skills, carry an
  ownership banner, preserve alias-specific discovery/guidance metadata, and
  are checked by `dot doctor`. Rendering and unset refuse to overwrite or
  delete unmanaged Codex skills.
- `dkey grants` surfaced in `dkey help`/README, and now prints the env vars each
  grant injects (never secret values); `grant not found` errors list available grants.
- `dkey identity import PATH [--force]` and `dkey identity import --stdin [--force]`
  for importing an existing age identity.
- `dot init`/`dot set path` add `~/.agents/tools/bin` to PATH via `env.sh`, so the
  `claw`/`clawb` (claude) and `codx`/`codxb` (codex) multi-call scripts resolve
  there — per-invocation backend switch from `dkey.providers.json`, no shell aliases.

### Removed
- Public apt/brew packaging (`debian/`, `homebrew/`) and their README install
  sections — install from source.

### Fixed
- `dot sync push` no longer stages or commits memspace changes. It now refuses
  dirty worktrees and pushes existing commits only.
- `dot sync pull` now reports status, fetches, enforces clean-worktree and
  fast-forward-only gates, recursively initializes/updates submodules, and
  renders harness outputs only after success.
- Multi-harness rendering prepares Claude plugins and Codex aliases, including
  ownership collision checks, before changing generated state. A missing alias
  manifest now reconciles the dot-managed alias set to empty.
- Claude plugin rendering now validates source containment/frontmatter, rejects
  symlinked trees, and uses `.dotpanel-owner` for safe migration, reconciliation,
  doctor, and unset behavior.
- `dkey reset` removes only registry-owned backend state, preserves unrelated
  provider/OAuth configuration, requires target paths below `HOME` with no
  symlinked component, uses random sibling temp files, and validates all
  replacement inputs before target files are changed.
- Grant-scoped shell activation now uses exact grant lookup and validates every
  emitted env/secret name before generated shell code can be evaluated. Current
  shell activation/removal is preflighted and refuses repeated activation or
  reserved shell-control variables.
- `dot self update` now refuses dirty managed checkouts before pulling.
- Render/reset signal handlers now clean staging and terminate with the signal
  status instead of resuming a cancelled mutation.
- `dkey set`, `dkey edit`, and identity import now use distinct random `0600`
  temporary files, preserve the encrypted target on failure, and remove
  plaintext/private-key material on normal exit or HUP/INT/TERM.
- Shell rc injection/removal now refuses symlinks and non-regular files,
  revalidates the mutation boundary, preserves an existing rc file's mode, and
  cleans same-directory rewrite files on failure or signal.
- Codex alias apply rechecks ownership after preflight; a concurrent unmanaged
  replacement is preserved and fails closed.
- Generated harness roots are revalidated after directory creation and before
  replacement. Wrapper unset requires the exact generated first-line marker,
  and skill frontmatter is now parsed with duplicate-key-safe PyYAML. Block
  scalar names, malformed documents, non-string scalars, and non-UTF-8 values
  are rejected consistently with the memspace checker; deprecated ad-hoc
  `type`/`supported_harnesses` text filters were removed.
- `dkey reset codex` fails closed on dotted `model_providers.*` keys and
  array-of-table syntax, including whitespace and quoted-key variants, instead
  of partially removing managed provider state.
- Sensitive identity/encrypted-key targets must be absolute, lexically
  normalized regular files below non-symlinked mutation boundaries. Directory,
  symlink, and initially-absent targets that appear during work are refused;
  `--force` does not authorize replacing a target that appeared mid-operation.
- `dot doctor` now exits non-zero for a missing memspace entry, wrapper or
  `env.sh` drift, unsafe generated-file types, or generated Claude plugins that
  differ from their source render. `dkey doctor` uses the same versioned schema
  as reset, validates the age identity and encrypted-key decryptability, and
  treats missing, empty, symlinked, non-regular, or group/other-accessible
  identity inputs as failures.
- jq 1.8.1 compatibility in `write_claude_use`.

## 0.0.1 — 2026-05-14

### Added
- `dot` command: memspace sync, harness entry rendering, PATH wiring.
- `dkey` command: age-encrypted secret storage, grant-based injection,
  `dkey on` / `dkey off` shell integration.
- Bilingual README (English, 中文).
- Test suite (`tests/run.sh`).
- Harness entry rendering for Claude, Codex, and Kimi.
- `dot init` bootstrap with template/blank/from/none entry modes.
- `dot sync` for memspace repo push/pull.
- `dot self update` for dotpanel self-update.
- Template files for `dkey.conf`, `keys.env.template`, and `AGENTS.md`.
