# dkey providers registry

> **`dkey use` is deprecated (2026-05).** Permanent backend switching (writing
> `~/.claude/settings.json` / `~/.codex/config.toml`) is superseded by
> **per-invocation** switching: `claw`/`clawb` (claude) and `codx`/`codxb` (codex)
> read this same registry and apply a backend per-process — so concurrent workers
> can target different backends, which a global settings file can't. The `dkey use`
> command is retained (not removed) but is no longer the recommended path.
> **This file remains the single backend-definition source** for both paths.

`dkey use` reads `~/.agents/secrets/dkey.providers.json` to configure AI
coding harnesses for a specific backend and profile.

A template is available at `templates/secrets/dkey.providers.example.json`.

## Quick start

```bash
# Create your providers registry from the template
cp ~/.agents/.dotpanel/templates/secrets/dkey.providers.example.json \
   ~/.agents/secrets/dkey.providers.json
# Edit it with real provider values, then:
dkey set MY_KEY my-api-key-value
dkey use claude:example
```

## Schema

### Top level

| Key | Type | Required | Description |
|---|---|---|---|
| `version` | integer | yes | Schema version. Currently `1`. |
| `defaults` | object | yes | Harness-level defaults. |
| `providers` | object | yes | Per-provider profiles keyed by provider name. |

### `defaults`

| Key | Type | Required | Description |
|---|---|---|---|
| `defaults.claude.settings_path` | string | no | Path to Claude settings JSON (default `~/.claude/settings.json`). |
| `defaults.claude.home_path` | string | no | Path to Claude home JSON (default `~/.claude.json`). |
| `defaults.claude.home` | object | no | Default values merged into `~/.claude.json`. |
| `defaults.claude.settings.env` | object | no | Default env vars merged into settings. |
| `defaults.claude.managed_env_keys` | []string | no | Env keys that `dkey use` will purge from settings before writing new ones. |
| `defaults.codex.config_path` | string | no | Path to Codex config TOML (default `~/.codex/config.toml`). |

### `providers.<name>`

| Key | Type | Required | Description |
|---|---|---|---|
| `default_profile` | string | yes | Profile to use when none is given in `dkey use`. |
| `secret` | string | no | Default secret name for provider-wide API key. |
| `profiles` | object | yes | Named profiles under this provider. |

### `profiles.<name>`

Each profile may contain `claude` and/or `codex` sections. At minimum one harness
section must be present.

| Key | Type | Required | Description |
|---|---|---|---|
| `claude` | object | no | Claude Code settings for this profile. |
| `codex` | object | no | Codex settings for this profile. |
| `env` | object | no | Profile-level env secret mappings. |

### `profiles.<name>.claude`

| Key | Type | Required | Description |
|---|---|---|---|
| `settings.env` | object | no | Env vars to write into `~/.claude/settings.json`. Values can be literal strings or `{"secret": "KEY_NAME"}` to resolve from the encrypted keys file. |
| `home` | object | no | Values merged into `~/.claude.json`. |

### `profiles.<name>.codex`

| Key | Type | Required | Description |
|---|---|---|---|
| `model` | string | yes | Model identifier written to `config.toml`. |
| `model_provider` | string | yes | Provider ID used as `[model_providers.<id>]` in TOML. |
| `model_provider_config` | object | yes | Key-value pairs written under the provider TOML section. |
| `status` | string | no | `supported` (default) or other value to block application. |
| `status_message` | string | no | Human explanation shown when status is not `supported`. |

The `model_provider_config` object must include at minimum:

| Key | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Display name for the provider. |
| `base_url` | string | yes | API base URL (e.g. `https://api.openai.com/v1`). |
| `wire_api` | string | yes | Must be `responses` for Codex 0.130+. |
| `requires_openai_auth` | bool | no | Whether to write an `auth.json` with the API key. |

## Secret resolution

When a value in settings is `{"secret": "KEY_NAME"}`, `dkey` looks up `KEY_NAME`
in the encrypted keys file (`~/.agents/secrets/keys.env.age`) and writes the
decrypted value.

## Example usage

```bash
# Switch Claude Code to the deepseek backend using its default profile
dkey use claude:deepseek

# Switch Codex to a specific qwen profile
dkey use codex:qwen:payg-global

# Switch both harnesses
dkey use all:deepseek
```
