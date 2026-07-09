# dkey providers registry

`~/.agents/secrets/dkey.providers.json` is the single backend-definition source
for per-invocation wrappers:

- `claw` / `clawb` for Claude-compatible backends
- `codx` / `codxb` for Codex-compatible backends
- `gem` / `gemb` for Gemini-compatible backends

The wrappers read this registry, load required secrets through
`dkey run --with llm-backends`, and apply backend settings only to the process
they launch. Persistent backend switching via `dkey use` has been removed
because it wrote global harness config and could overwrite Codex ChatGPT/OAuth
auth state with API-key mode.

A template is available at `templates/secrets/dkey.providers.example.json`.

## Quick start

```bash
# Create your providers registry from the template
cp ~/.agents/.dotpanel/templates/secrets/dkey.providers.example.json \
   ~/.agents/secrets/dkey.providers.json
# Edit it with real provider values, then store its secret and run per invocation:
dkey set MY_KEY my-api-key-value
claw example
codx example "prompt"
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
| `defaults.claude.managed_env_keys` | []string | no | Legacy field kept for old registries; wrappers do not write global settings. |
| `defaults.codex.config_path` | string | no | Path to Codex config TOML (default `~/.codex/config.toml`). |

### `providers.<name>`

| Key | Type | Required | Description |
|---|---|---|---|
| `default_profile` | string | yes | Profile to use when a wrapper is called with only the provider name. |
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
| `settings.env` | object | no | Env vars exported for the launched Claude process. Values can be literal strings or `{"secret": "KEY_NAME"}` to resolve from the encrypted keys file. |
| `home` | object | no | Legacy field kept for old registries; wrappers do not write `~/.claude.json`. |

### `profiles.<name>.codex`

| Key | Type | Required | Description |
|---|---|---|---|
| `model` | string | yes | Model identifier passed to Codex for this invocation. |
| `model_provider` | string | yes | Provider ID passed as `model_provider` for this invocation. |
| `model_provider_config` | object | yes | Key-value pairs passed as `model_providers.<id>.*` overrides for this invocation. |
| `status` | string | no | `supported` (default) or other value to block application. |
| `status_message` | string | no | Human explanation shown when status is not `supported`. |

The `model_provider_config` object must include at minimum:

| Key | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Display name for the provider. |
| `base_url` | string | yes | API base URL (e.g. `https://api.openai.com/v1`). |
| `wire_api` | string | yes | Must be `responses` for Codex 0.130+. |
| `requires_openai_auth` | bool | no | Whether Codex should use its OpenAI/Codex auth path for the provider. Wrappers pass this as a process-local config override and do not write `auth.json`. |

## Secret resolution

When a value in settings is `{"secret": "KEY_NAME"}`, `dkey` looks up `KEY_NAME`
in the encrypted keys file (`~/.agents/secrets/keys.env.age`) and writes the
decrypted value.

## Example usage

```bash
# Run Claude Code against the deepseek backend using its default profile
claw deepseek

# Run Codex against qwen for this invocation only
codx qwen "prompt"

# Headless workers
clawb kimi "prompt"
codxb qwen "prompt"
```
