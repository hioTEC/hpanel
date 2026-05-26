#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export HOME="$TMP/home"
mkdir -p "$HOME/.agents/.dotpanel"
cp -R "$ROOT/bin" "$HOME/.agents/.dotpanel/bin"

sh -n "$ROOT/bin/dot"
sh -n "$ROOT/bin/dkey"
bash -n "$ROOT/bin/dot"
bash -n "$ROOT/bin/dkey"
command -v jq >/dev/null 2>&1

sh "$HOME/.agents/.dotpanel/bin/dot" init --yes
printf '# Test memspace\n' > "$HOME/.agents/AGENTS.md"
mkdir -p "$HOME/.agents/skills/minimal"
cat > "$HOME/.agents/skills/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: Minimal Matt-style skill without deprecated type metadata.
---

# Minimal
SKILL
"$HOME/.agents/.dotpanel/bin/dot" set claude
"$HOME/.agents/.dotpanel/bin/dot" doctor
"$HOME/.agents/.dotpanel/bin/dot" set -a

grep -qxF '/.dotpanel/' "$HOME/.agents/.gitignore"
. "$HOME/.agents/.dotpanel/env.sh"
test "$(command -v dot)" = "$HOME/.agents/.dotpanel/bin/dot"
type dkey | grep -q 'dkey is a function'
test -x "$HOME/.agents/.dotpanel/bin/dkey"
test -f "$HOME/.claude/CLAUDE.md"
test -f "$HOME/.codex/AGENTS.md"
test -f "$HOME/.kimi/AGENTS.md"
grep -q '`~/.agents/` is your memspace' "$HOME/.claude/CLAUDE.md"
# claw/clawb and codx/codxb are memspace PATH scripts (~/.agents/tools/bin/),
# per-invocation backend switch — not env.sh aliases. dotpanel emits neither.
! grep -q "alias claw=" "$HOME/.agents/.dotpanel/env.sh"
! grep -q "alias codx=" "$HOME/.agents/.dotpanel/env.sh"

test -f "$HOME/.agents/.dotpanel/plugins/memspace/skills/minimal/SKILL.md"

git -C "$HOME/.agents" init >/dev/null
"$HOME/.agents/.dotpanel/bin/dot" sync status >/dev/null
git -C "$HOME/.agents" status --short --ignored | grep -q '!! .dotpanel/'

"$HOME/.agents/.dotpanel/bin/dkey" init
"$HOME/.agents/.dotpanel/bin/dkey" status | grep -q 'active grant: none'
"$HOME/.agents/.dotpanel/bin/dkey" off | grep -q 'DKEY_ACTIVE_GRANT'

if command -v age >/dev/null 2>&1 && command -v age-keygen >/dev/null 2>&1; then
  "$HOME/.agents/.dotpanel/bin/dkey" keygen >/dev/null
  "$HOME/.agents/.dotpanel/bin/dkey" set TEST_SECRET ok
  "$HOME/.agents/.dotpanel/bin/dkey" list | grep -qx 'TEST_SECRET'
  # shellcheck disable=SC1090
  . "$HOME/.agents/.dotpanel/env.sh"
  dkey on
  test "${TEST_SECRET:-}" = "ok"
  dkey off
  test -z "${TEST_SECRET:-}"

  printf 'TEST_SECRET=ok\n' > "$HOME/.agents/secrets/keys.env"
  recipient="$(age-keygen -y "$HOME/.config/age/key.txt")"
  age -r "$recipient" -o "$HOME/.agents/secrets/keys.env.age" "$HOME/.agents/secrets/keys.env"
  "$HOME/.agents/.dotpanel/bin/dkey" set OTHER_SECRET fine
  printf 'grant:test:TEST_VALUE=TEST_SECRET\ngrant:other:OTHER_VALUE=OTHER_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"
  dkey on --with test
  test "${TEST_VALUE:-}" = "ok"
  dkey off
  test -z "${TEST_VALUE:-}"
  dkey on --with test --with other
  test "${TEST_VALUE:-}" = "ok"
  test "${OTHER_VALUE:-}" = "fine"
  case "${DKEY_ACTIVE_GRANT:-}" in
    test,other) ;;
    *) exit 1 ;;
  esac
  dkey off
  test -z "${TEST_VALUE:-}"
  test -z "${OTHER_VALUE:-}"
  run_out="$("$HOME/.agents/.dotpanel/bin/dkey" run --with test --with other -- sh -c 'printf "%s:%s:%s" "$TEST_VALUE" "$OTHER_VALUE" "$DKEY_ACTIVE_GRANT"')"
  test "$run_out" = "ok:fine:test,other"

  cat > "$HOME/.agents/secrets/dkey.providers.json" <<'JSON'
{
  "version": 1,
  "defaults": {
    "claude": {
      "settings_path": "~/.claude/settings.json",
      "home_path": "~/.claude.json",
      "home": {"hasCompletedOnboarding": true},
      "settings": {"env": {"API_TIMEOUT_MS": "3000000"}},
      "managed_env_keys": [
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "API_TIMEOUT_MS"
      ]
    },
    "codex": {"config_path": "~/.codex/config.toml"}
  },
  "providers": {
    "ok": {
      "default_profile": "default",
      "secret": "TEST_SECRET",
      "profiles": {
        "default": {
          "claude": {
            "settings": {
              "env": {
                "ANTHROPIC_BASE_URL": "https://example.test/anthropic",
                "ANTHROPIC_AUTH_TOKEN": {"secret": "TEST_SECRET"},
                "ANTHROPIC_MODEL": "model-pro",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "model-flash"
              }
            }
          },
          "codex": {
            "model": "model-pro",
            "model_provider": "ok",
            "model_provider_config": {
              "name": "OK",
              "base_url": "https://example.test/v1",
              "wire_api": "responses",
              "requires_openai_auth": true
            },
            "status": "supported"
          },
          "env": {"TEST_SECRET": {"secret": "TEST_SECRET"}}
        }
      }
    },
    "blocked": {
      "default_profile": "default",
      "secret": "TEST_SECRET",
      "profiles": {
        "default": {
          "claude": {
            "settings": {
              "env": {
                "ANTHROPIC_BASE_URL": "https://blocked.test/anthropic",
                "ANTHROPIC_AUTH_TOKEN": {"secret": "TEST_SECRET"}
              }
            }
          },
          "codex": {
            "model": "blocked-model",
            "model_provider": "blocked",
            "model_provider_config": {
              "name": "Blocked",
              "base_url": "https://blocked.test/v1",
              "wire_api": "chat"
            },
            "status": "unsupported",
            "status_message": "blocked for test"
          },
          "env": {"TEST_SECRET": {"secret": "TEST_SECRET"}}
        }
      }
    }
  }
}
JSON
  "$HOME/.agents/.dotpanel/bin/dkey" use codex:ok
  grep -q 'model_provider = "ok"' "$HOME/.codex/config.toml"
  grep -q 'wire_api = "responses"' "$HOME/.codex/config.toml"
  jq -e '.auth_mode == "apikey" and .OPENAI_API_KEY == "ok"' "$HOME/.codex/auth.json" >/dev/null
  "$HOME/.agents/.dotpanel/bin/dkey" use all:blocked 2> "$TMP/dkey-use-blocked.err"
  grep -q 'blocked for test' "$TMP/dkey-use-blocked.err"
  jq -e '.env.ANTHROPIC_BASE_URL == "https://blocked.test/anthropic"' "$HOME/.claude/settings.json" >/dev/null
  if "$HOME/.agents/.dotpanel/bin/dkey" use codex:blocked 2> "$TMP/dkey-use-blocked-strict.err"; then
    exit 1
  fi
  grep -q 'blocked for test' "$TMP/dkey-use-blocked-strict.err"
  if "$HOME/.agents/.dotpanel/bin/dot" use codex:ok 2> "$TMP/dot-use-removed.err"; then
    exit 1
  fi
  grep -q 'unknown command: use' "$TMP/dot-use-removed.err"
  "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor.out" 2>&1
  grep -q 'providers registry valid' "$TMP/dkey-doctor.out"
  echo '{"bad": "json"}' > "$HOME/.agents/secrets/dkey.providers.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-invalid.out" 2>&1; then
    exit 1
  fi
  grep -q 'providers registry invalid' "$TMP/dkey-doctor-invalid.out"
fi

echo "OK"
