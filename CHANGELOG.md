# Changelog

## Unreleased

### Changed
- **Breaking:** persistent backend switching via `dkey use` has been removed.
  Use per-invocation wrappers (`claw`/`clawb`, `codx`/`codxb`, `gem`/`gemb`)
  instead; they read `dkey.providers.json` and load secrets through grants
  without rewriting global harness config or Codex auth state.

### Added
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
