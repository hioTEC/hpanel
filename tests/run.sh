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
"$HOME/.agents/.dotpanel/bin/dot" doctor
"$HOME/.agents/.dotpanel/bin/dot" set -a

grep -qxF '/.dotpanel/' "$HOME/.agents/.gitignore"
test -L "$HOME/.local/bin/dot"
test -L "$HOME/.local/bin/dkey"
test -f "$HOME/.claude/CLAUDE.md"
test -f "$HOME/.codex/AGENTS.md"
test -f "$HOME/.kimi/AGENTS.md"
grep -q '`~/.agents/` is your memspace' "$HOME/.claude/CLAUDE.md"

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
fi

echo "OK"
