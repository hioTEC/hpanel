# Changelog

## Unreleased

### Changed
- **Breaking:** `dot use` moved to `dkey use`. Backend switching now lives on `dkey`
  because it reads encrypted secrets. Use `dkey use claude:deepseek`,
  `dkey use codex:qwen`, or `dkey use all:backend` instead of the old `dot use`
  syntax.

### Added
- `dkey grants` surfaced in `dkey help`/README, and now prints the env vars each
  grant injects (never secret values); `grant not found` errors list available grants.
- `dkey use` command: writes backend settings for Claude Code (`~/.claude/settings.json`,
  `~/.claude.json`) and Codex (`~/.codex/config.toml`, `~/.codex/auth.json`)
  from a provider registry at `~/.agents/secrets/dkey.providers.json`.
- `dkey identity import PATH [--force]` and `dkey identity import --stdin [--force]`
  for importing an existing age identity.
- Shell aliases `claw` and `codx` for permission-free harness invocation
  (installed by `dot init` via `env.sh`).

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
