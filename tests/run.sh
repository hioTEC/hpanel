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
mkdir -p "$HOME/.agents/skills/hio/minimal"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: Minimal Matt-style skill without deprecated type metadata.
---

# Minimal
SKILL
mkdir -p "$HOME/.agents/skills/matt/.claude-plugin" "$HOME/.agents/skills/matt/skills/engineering/diagnose"
cat > "$HOME/.agents/skills/matt/.claude-plugin/plugin.json" <<'JSON'
{"skills":["skills/engineering/diagnose"]}
JSON
cat > "$HOME/.agents/skills/matt/skills/engineering/diagnose/SKILL.md" <<'SKILL'
---
name: diagnose
description: Minimal matt fixture.
---

# Diagnose
SKILL
mkdir -p "$HOME/.agents/skills/impeccable/plugin/skills/impeccable"
cat > "$HOME/.agents/skills/impeccable/plugin/skills/impeccable/SKILL.md" <<'SKILL'
---
name: impeccable
description: Minimal impeccable fixture.
---

# Impeccable
SKILL
"$HOME/.agents/.dotpanel/bin/dot" set claude
. "$HOME/.agents/.dotpanel/env.sh"
"$HOME/.agents/.dotpanel/bin/dot" doctor

mv "$HOME/.agents/AGENTS.md" "$HOME/.agents/AGENTS.md.saved"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-missing-entry.out" 2>&1; then
  echo "FAIL: dot doctor accepted a missing memspace entry" >&2
  exit 1
fi
grep -q "entry missing: $HOME/.agents/AGENTS.md" "$TMP/dot-doctor-missing-entry.out"
mv "$HOME/.agents/AGENTS.md.saved" "$HOME/.agents/AGENTS.md"

printf '\nlocal wrapper drift\n' >> "$HOME/.claude/CLAUDE.md"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-wrapper-drift.out" 2>&1; then
  echo "FAIL: dot doctor accepted a stale generated wrapper" >&2
  exit 1
fi
grep -q "wrapper differs from generated content: $HOME/.claude/CLAUDE.md" "$TMP/dot-doctor-wrapper-drift.out"
"$HOME/.agents/.dotpanel/bin/dot" set claude

printf '\ngenerated drift\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-plugin-drift.out" 2>&1; then
  echo "FAIL: dot doctor accepted stale generated skills" >&2
  exit 1
fi
grep -q "hio plugin differs from source render" "$TMP/dot-doctor-plugin-drift.out"
"$HOME/.agents/.dotpanel/bin/dot" set claude

"$HOME/.agents/.dotpanel/bin/dot" set -a

grep -qxF '/.dotpanel/' "$HOME/.agents/.gitignore"
test "$(command -v dot)" = "$HOME/.agents/.dotpanel/bin/dot"
type dkey | grep -q 'dkey is a function'
test -x "$HOME/.agents/.dotpanel/bin/dkey"
test -f "$HOME/.claude/CLAUDE.md"
test -f "$HOME/.codex/AGENTS.md"
test -f "$HOME/.kimi/AGENTS.md"
grep -q '`~/.agents/` is your memspace' "$HOME/.claude/CLAUDE.md"
# claw/clawb and codx/codxb are memspace PATH scripts (~/.agents/tools/bin/),
# per-invocation backend switch — not env.sh aliases. dotpanel emits neither,
# but env.sh DOES put ~/.agents/tools/bin on PATH so the scripts resolve.
! grep -q "alias claw=" "$HOME/.agents/.dotpanel/env.sh"
! grep -q "alias codx=" "$HOME/.agents/.dotpanel/env.sh"
case ":$PATH:" in *":$HOME/.agents/tools/bin:"*) ;; *) echo "FAIL: tools/bin not on PATH after sourcing env.sh"; exit 1 ;; esac

test -f "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
test -f "$HOME/.claude/skills/matt/skills/diagnose/SKILL.md"
test -f "$HOME/.claude/skills/impeccable/skills/impeccable/SKILL.md"

git -C "$HOME/.agents" init -q -b main
git -C "$HOME/.agents" config user.name "Dotpanel Tests"
git -C "$HOME/.agents" config user.email "dotpanel-tests@example.invalid"
git -C "$HOME/.agents" add .gitignore AGENTS.md skills
git -C "$HOME/.agents" commit -q -m "test: initial memspace"
"$HOME/.agents/.dotpanel/bin/dot" sync status >/dev/null
git -C "$HOME/.agents" status --short --ignored | grep -q '!! .dotpanel/'

git init -q --bare "$TMP/memspace-origin.git"
git -C "$HOME/.agents" remote add origin "$TMP/memspace-origin.git"
git -C "$HOME/.agents" push -q -u origin main
git --git-dir="$TMP/memspace-origin.git" symbolic-ref HEAD refs/heads/main
printf 'committed\n' > "$HOME/.agents/existing-commit.md"
git -C "$HOME/.agents" add existing-commit.md
git -C "$HOME/.agents" commit -q -m "test: existing commit"

printf 'staged\n' > "$HOME/.agents/staged.md"
git -C "$HOME/.agents" add staged.md
printf '\nunstaged\n' >> "$HOME/.agents/AGENTS.md"
printf 'untracked\n' > "$HOME/.agents/untracked.md"
push_head_before="$(git -C "$HOME/.agents" rev-parse HEAD)"
push_index_before="$(git -C "$HOME/.agents" ls-files --stage)"
push_status_before="$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)"
remote_head_before="$(git --git-dir="$TMP/memspace-origin.git" rev-parse refs/heads/main)"
if "$HOME/.agents/.dotpanel/bin/dot" sync push > "$TMP/dot-sync-push-dirty.out" 2>&1; then
  echo "FAIL: dot sync push accepted a dirty memspace" >&2
  exit 1
fi
grep -q 'memspace has uncommitted changes; commit or stash them before pushing' "$TMP/dot-sync-push-dirty.out"
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$push_head_before"
test "$(git -C "$HOME/.agents" ls-files --stage)" = "$push_index_before"
test "$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)" = "$push_status_before"
test "$(git --git-dir="$TMP/memspace-origin.git" rev-parse refs/heads/main)" = "$remote_head_before"

git -C "$HOME/.agents" restore --staged staged.md
rm "$HOME/.agents/staged.md" "$HOME/.agents/untracked.md"
git -C "$HOME/.agents" restore AGENTS.md
clean_push_head_before="$(git -C "$HOME/.agents" rev-parse HEAD)"
clean_push_index_before="$(git -C "$HOME/.agents" ls-files --stage)"
"$HOME/.agents/.dotpanel/bin/dot" sync push > "$TMP/dot-sync-push-clean.out" 2>&1
test "$(git --git-dir="$TMP/memspace-origin.git" rev-parse refs/heads/main)" = "$clean_push_head_before"
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$clean_push_head_before"
test "$(git -C "$HOME/.agents" ls-files --stage)" = "$clean_push_index_before"
test -z "$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)"

git clone -q "$TMP/memspace-origin.git" "$TMP/memspace-upstream"
git -C "$TMP/memspace-upstream" config user.name "Dotpanel Tests"
git -C "$TMP/memspace-upstream" config user.email "dotpanel-tests@example.invalid"
printf 'from remote\n' > "$TMP/memspace-upstream/pulled.md"
git -C "$TMP/memspace-upstream" add pulled.md
git -C "$TMP/memspace-upstream" commit -q -m "test: remote update"
git -C "$TMP/memspace-upstream" push -q origin main
pull_target="$(git -C "$TMP/memspace-upstream" rev-parse HEAD)"

printf 'untracked pull blocker\n' > "$HOME/.agents/pull-dirty.md"
printf '\nwrapper must not render on refused pull\n' >> "$HOME/.codex/AGENTS.md"
pull_head_before="$(git -C "$HOME/.agents" rev-parse HEAD)"
pull_index_before="$(git -C "$HOME/.agents" ls-files --stage)"
pull_status_before="$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)"
if "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-dirty.out" 2>&1; then
  echo "FAIL: dot sync pull accepted a dirty memspace" >&2
  exit 1
fi
grep -q '^## main' "$TMP/dot-sync-pull-dirty.out"
grep -q 'memspace has uncommitted changes; commit or stash them before pulling' "$TMP/dot-sync-pull-dirty.out"
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$pull_head_before"
test "$(git -C "$HOME/.agents" ls-files --stage)" = "$pull_index_before"
test "$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)" = "$pull_status_before"
test "$(git -C "$HOME/.agents" rev-parse refs/remotes/origin/main)" = "$pull_target"
grep -q 'wrapper must not render on refused pull' "$HOME/.codex/AGENTS.md"

rm "$HOME/.agents/pull-dirty.md"
"$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-clean.out" 2>&1
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$pull_target"
test -f "$HOME/.agents/pulled.md"
cmp -s "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md"
"$HOME/.agents/.dotpanel/bin/dot" doctor >/dev/null

printf 'local only\n' > "$HOME/.agents/local-only.md"
git -C "$HOME/.agents" add local-only.md
git -C "$HOME/.agents" commit -q -m "test: local divergence"
printf 'remote only\n' > "$TMP/memspace-upstream/remote-only.md"
git -C "$TMP/memspace-upstream" add remote-only.md
git -C "$TMP/memspace-upstream" commit -q -m "test: remote divergence"
git -C "$TMP/memspace-upstream" push -q origin main
diverged_remote_head="$(git -C "$TMP/memspace-upstream" rev-parse HEAD)"
printf '\nwrapper must not render on non-fast-forward pull\n' >> "$HOME/.kimi/AGENTS.md"
diverged_local_head="$(git -C "$HOME/.agents" rev-parse HEAD)"
diverged_local_index="$(git -C "$HOME/.agents" ls-files --stage)"
if "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-diverged.out" 2>&1; then
  echo "FAIL: dot sync pull merged diverged branches" >&2
  exit 1
fi
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$diverged_local_head"
test "$(git -C "$HOME/.agents" ls-files --stage)" = "$diverged_local_index"
test -z "$(git -C "$HOME/.agents" status --porcelain=v1 --untracked-files=all)"
test "$(git -C "$HOME/.agents" rev-parse refs/remotes/origin/main)" = "$diverged_remote_head"
grep -q 'wrapper must not render on non-fast-forward pull' "$HOME/.kimi/AGENTS.md"
"$HOME/.agents/.dotpanel/bin/dot" set kimi >/dev/null

cat > "$HOME/.agents/.dotpanel/.gitignore" <<'EOF'
/env.sh
/var/
EOF
git -C "$HOME/.agents/.dotpanel" init -q -b main
git -C "$HOME/.agents/.dotpanel" config user.name "Dotpanel Tests"
git -C "$HOME/.agents/.dotpanel" config user.email "dotpanel-tests@example.invalid"
git -C "$HOME/.agents/.dotpanel" add .gitignore bin
git -C "$HOME/.agents/.dotpanel" commit -q -m "test: installed dotpanel"
git init -q --bare "$TMP/dotpanel-origin.git"
git -C "$HOME/.agents/.dotpanel" remote add origin "$TMP/dotpanel-origin.git"
git -C "$HOME/.agents/.dotpanel" push -q -u origin main
git --git-dir="$TMP/dotpanel-origin.git" symbolic-ref HEAD refs/heads/main
git clone -q "$TMP/dotpanel-origin.git" "$TMP/dotpanel-upstream"
git -C "$TMP/dotpanel-upstream" config user.name "Dotpanel Tests"
git -C "$TMP/dotpanel-upstream" config user.email "dotpanel-tests@example.invalid"
printf 'remote dotpanel update\n' > "$TMP/dotpanel-upstream/remote-update.md"
git -C "$TMP/dotpanel-upstream" add remote-update.md
git -C "$TMP/dotpanel-upstream" commit -q -m "test: remote dotpanel update"
git -C "$TMP/dotpanel-upstream" push -q origin main
self_update_target="$(git -C "$TMP/dotpanel-upstream" rev-parse HEAD)"

printf 'staged self change\n' > "$HOME/.agents/.dotpanel/staged-self.md"
git -C "$HOME/.agents/.dotpanel" add staged-self.md
printf '\n# unstaged self change\n' >> "$HOME/.agents/.dotpanel/bin/dot"
printf 'untracked self change\n' > "$HOME/.agents/.dotpanel/untracked-self.md"
self_head_before="$(git -C "$HOME/.agents/.dotpanel" rev-parse HEAD)"
self_index_before="$(git -C "$HOME/.agents/.dotpanel" ls-files --stage)"
self_status_before="$(git -C "$HOME/.agents/.dotpanel" status --porcelain=v1 --untracked-files=all)"
self_tracking_before="$(git -C "$HOME/.agents/.dotpanel" rev-parse refs/remotes/origin/main)"
if "$HOME/.agents/.dotpanel/bin/dot" self update > "$TMP/dot-self-update-dirty.out" 2>&1; then
  echo "FAIL: dot self update accepted a dirty managed checkout" >&2
  exit 1
fi
grep -q 'dotpanel checkout has uncommitted changes; commit or stash them before updating' "$TMP/dot-self-update-dirty.out"
test "$(git -C "$HOME/.agents/.dotpanel" rev-parse HEAD)" = "$self_head_before"
test "$(git -C "$HOME/.agents/.dotpanel" ls-files --stage)" = "$self_index_before"
test "$(git -C "$HOME/.agents/.dotpanel" status --porcelain=v1 --untracked-files=all)" = "$self_status_before"
test "$(git -C "$HOME/.agents/.dotpanel" rev-parse refs/remotes/origin/main)" = "$self_tracking_before"

git -C "$HOME/.agents/.dotpanel" restore --staged staged-self.md
rm "$HOME/.agents/.dotpanel/staged-self.md" "$HOME/.agents/.dotpanel/untracked-self.md"
git -C "$HOME/.agents/.dotpanel" restore bin/dot
"$HOME/.agents/.dotpanel/bin/dot" self update > "$TMP/dot-self-update-clean.out" 2>&1
test "$(git -C "$HOME/.agents/.dotpanel" rev-parse HEAD)" = "$self_update_target"
test -f "$HOME/.agents/.dotpanel/remote-update.md"
test -z "$(git -C "$HOME/.agents/.dotpanel" status --porcelain=v1 --untracked-files=all)"

if [ "${DOT_ONLY:-0}" = "1" ]; then
  echo "OK (dot only)"
  exit 0
fi

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
  if "$HOME/.agents/.dotpanel/bin/dkey" use codex:ok 2> "$TMP/dkey-use-removed.err"; then
    exit 1
  fi
  grep -q 'dkey use has been removed' "$TMP/dkey-use-removed.err"
  test ! -f "$HOME/.codex/auth.json"
  test ! -f "$HOME/.codex/config.toml"
  test ! -f "$HOME/.claude/settings.json"
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
