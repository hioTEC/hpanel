#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT

YAML_SITE_PACKAGES="$(python3 -c 'from pathlib import Path; import yaml; print(Path(yaml.__file__).resolve().parents[1])')"
export PYTHONPATH="$YAML_SITE_PACKAGES${PYTHONPATH:+:$PYTHONPATH}"

export HOME="$TMP/home"
mkdir -p "$HOME/.agents/.dotpanel"
cp -R "$ROOT/bin" "$HOME/.agents/.dotpanel/bin"

sh -n "$ROOT/bin/dot"
sh -n "$ROOT/bin/dkey"
bash -n "$ROOT/bin/dot"
bash -n "$ROOT/bin/dkey"
command -v jq >/dev/null 2>&1

template_home="$TMP/template-home"
fallback_home="$TMP/fallback-home"
mkdir -p "$template_home/.agents/.dotpanel" "$fallback_home/.agents/.dotpanel"
cp -R "$ROOT/bin" "$template_home/.agents/.dotpanel/bin"
cp -R "$ROOT/templates" "$template_home/.agents/.dotpanel/templates"
cp -R "$ROOT/bin" "$fallback_home/.agents/.dotpanel/bin"
HOME="$template_home" sh "$template_home/.agents/.dotpanel/bin/dot" init --template --no-path >/dev/null
HOME="$fallback_home" sh "$fallback_home/.agents/.dotpanel/bin/dot" init --template --no-path >/dev/null
cmp -s "$template_home/.agents/AGENTS.md" "$fallback_home/.agents/AGENTS.md"
! grep -Eq 'flow-resource-ops|flow-improve-protocol' "$template_home/.agents/AGENTS.md"
! grep -q 'stages all non-ignored' "$template_home/.agents/AGENTS.md"
grep -q 'Add a route only after its target' "$template_home/.agents/AGENTS.md"

sh "$HOME/.agents/.dotpanel/bin/dot" init --yes

printf 'outside wrapper scratch sentinel\n' > "$TMP/outside-wrapper-scratch"
printf 'outside env scratch sentinel\n' > "$TMP/outside-env-scratch"
cp "$TMP/outside-wrapper-scratch" "$TMP/outside-wrapper-scratch-before"
cp "$TMP/outside-env-scratch" "$TMP/outside-env-scratch-before"
mkdir -p "$TMP/dot-scratch-preplant-bin"
cat > "$TMP/dot-scratch-preplant-bin/mkdir" <<'SH'
#!/bin/sh
if [ ! -e "$DOT_TEST_SCRATCH_MARKER" ]; then
  /bin/mkdir -p "$DOT_TEST_SCRATCH_VAR" || exit 1
  wrapper_path="$DOT_TEST_SCRATCH_VAR/wrapper.kimi.$PPID"
  env_path="$DOT_TEST_SCRATCH_VAR/env.$PPID"
  /bin/ln -s "$DOT_TEST_SCRATCH_WRAPPER_OUTSIDE" "$wrapper_path" || exit 1
  /bin/ln -s "$DOT_TEST_SCRATCH_ENV_OUTSIDE" "$env_path" || exit 1
  printf '%s\n%s\n' "$wrapper_path" "$env_path" > "$DOT_TEST_SCRATCH_PATHS"
  : > "$DOT_TEST_SCRATCH_MARKER"
fi
exec /bin/mkdir "$@"
SH
chmod +x "$TMP/dot-scratch-preplant-bin/mkdir"
DOT_TEST_SCRATCH_MARKER="$TMP/dot-scratch-preplant-triggered" \
DOT_TEST_SCRATCH_PATHS="$TMP/dot-scratch-preplant-paths" \
DOT_TEST_SCRATCH_VAR="$HOME/.agents/.dotpanel/var" \
DOT_TEST_SCRATCH_WRAPPER_OUTSIDE="$TMP/outside-wrapper-scratch" \
DOT_TEST_SCRATCH_ENV_OUTSIDE="$TMP/outside-env-scratch" \
PATH="$TMP/dot-scratch-preplant-bin:$PATH" \
  "$HOME/.agents/.dotpanel/bin/dot" set kimi >/dev/null
cmp -s "$TMP/outside-wrapper-scratch-before" "$TMP/outside-wrapper-scratch"
cmp -s "$TMP/outside-env-scratch-before" "$TMP/outside-env-scratch"
while IFS= read -r scratch_path; do
  test -L "$scratch_path"
  rm "$scratch_path"
done < "$TMP/dot-scratch-preplant-paths"
rm -rf "$TMP/dot-scratch-preplant-bin"

dot_env_line="[ -f \"$HOME/.agents/.dotpanel/env.sh\" ] && . \"$HOME/.agents/.dotpanel/env.sh\""
printf 'outside shell rc target\n%s\n' "$dot_env_line" > "$TMP/outside-shell-rc"
cp "$TMP/outside-shell-rc" "$TMP/outside-shell-rc-before"
ln -s "$TMP/outside-shell-rc" "$TMP/symlink-shell-rc"
if DOT_SHELL_RC="$TMP/symlink-shell-rc" "$HOME/.agents/.dotpanel/bin/dot" set path \
    > "$TMP/dot-set-symlink-rc.out" 2>&1; then
  echo "FAIL: dot set path followed a symlinked shell rc" >&2
  exit 1
fi
grep -q 'shell rc must not be symlinked' "$TMP/dot-set-symlink-rc.out"
test -L "$TMP/symlink-shell-rc"
cmp -s "$TMP/outside-shell-rc-before" "$TMP/outside-shell-rc"
if DOT_SHELL_RC="$TMP/symlink-shell-rc" "$HOME/.agents/.dotpanel/bin/dot" unset path \
    > "$TMP/dot-unset-symlink-rc.out" 2>&1; then
  echo "FAIL: dot unset path replaced a symlinked shell rc" >&2
  exit 1
fi
grep -q 'shell rc must not be symlinked' "$TMP/dot-unset-symlink-rc.out"
test -L "$TMP/symlink-shell-rc"
cmp -s "$TMP/outside-shell-rc-before" "$TMP/outside-shell-rc"
rm "$TMP/symlink-shell-rc"

printf 'private shell rc marker\n' > "$TMP/private-shell-rc"
chmod 600 "$TMP/private-shell-rc"
DOT_SHELL_RC="$TMP/private-shell-rc" "$HOME/.agents/.dotpanel/bin/dot" set path >/dev/null
private_rc_mode="$(stat -f '%Lp' "$TMP/private-shell-rc" 2>/dev/null || stat -c '%a' "$TMP/private-shell-rc")"
test "$private_rc_mode" = '600'
DOT_SHELL_RC="$TMP/private-shell-rc" "$HOME/.agents/.dotpanel/bin/dot" unset path >/dev/null
private_rc_mode="$(stat -f '%Lp' "$TMP/private-shell-rc" 2>/dev/null || stat -c '%a' "$TMP/private-shell-rc")"
test "$private_rc_mode" = '600'
grep -qxF 'private shell rc marker' "$TMP/private-shell-rc"
! grep -qxF "$dot_env_line" "$TMP/private-shell-rc"
"$HOME/.agents/.dotpanel/bin/dot" set path >/dev/null

mkfifo "$TMP/fifo-shell-rc"
if DOT_SHELL_RC="$TMP/fifo-shell-rc" "$HOME/.agents/.dotpanel/bin/dot" set path \
    > "$TMP/dot-set-fifo-rc.out" 2>&1; then
  echo "FAIL: dot set path accepted a FIFO shell rc" >&2
  exit 1
fi
grep -q 'shell rc is not a regular file' "$TMP/dot-set-fifo-rc.out"
rm "$TMP/fifo-shell-rc"

printf 'signal shell rc marker\n%s\n' "$dot_env_line" > "$TMP/signal-shell-rc"
cp "$TMP/signal-shell-rc" "$TMP/signal-shell-rc-before"
mkdir -p "$TMP/dot-rc-signal-bin"
cat > "$TMP/dot-rc-signal-bin/mv" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$DOT_TEST_SIGNAL_RC" ]; then
  kill -TERM "$PPID"
  exit 0
fi
exec /bin/mv "$@"
SH
chmod +x "$TMP/dot-rc-signal-bin/mv"
if DOT_TEST_SIGNAL_RC="$TMP/signal-shell-rc" DOT_SHELL_RC="$TMP/signal-shell-rc" \
    PATH="$TMP/dot-rc-signal-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dot" unset path \
    > "$TMP/dot-unset-rc-signal.out" 2>&1; then
  echo "FAIL: dot unset path continued after TERM" >&2
  exit 1
else
  dot_unset_rc_signal_status=$?
fi
test "$dot_unset_rc_signal_status" -eq 143
cmp -s "$TMP/signal-shell-rc-before" "$TMP/signal-shell-rc"
test -z "$(find "$TMP" -maxdepth 1 -type f -name '.dotpanel-rc*' -print -quit)"
rm -rf "$TMP/dot-rc-signal-bin"

mkdir -p "$TMP/dot-rc-root-race-bin"
cat > "$TMP/dot-rc-root-race-bin/mkdir" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$DOT_TEST_RC_PARENT" ] && [ ! -e "$DOT_TEST_RC_SWAP_MARKER" ]; then
  /bin/mkdir "$@" || exit 1
  /bin/mv "$DOT_TEST_RC_PARENT" "$DOT_TEST_RC_SAVED"
  /bin/mkdir -p "$DOT_TEST_RC_OUTSIDE"
  /bin/ln -s "$DOT_TEST_RC_OUTSIDE" "$DOT_TEST_RC_PARENT"
  : > "$DOT_TEST_RC_SWAP_MARKER"
  exit 0
fi
exec /bin/mkdir "$@"
SH
chmod +x "$TMP/dot-rc-root-race-bin/mkdir"
export DOT_TEST_RC_PARENT="$TMP/rc-root-race/config"
export DOT_TEST_RC_SAVED="$TMP/rc-root-race-saved"
export DOT_TEST_RC_OUTSIDE="$TMP/rc-root-race-outside"
export DOT_TEST_RC_SWAP_MARKER="$TMP/rc-root-race-triggered"
if DOT_SHELL_RC="$DOT_TEST_RC_PARENT/.zshrc" PATH="$TMP/dot-rc-root-race-bin:$PATH" \
    "$HOME/.agents/.dotpanel/bin/dot" set path > "$TMP/dot-set-rc-root-race.out" 2>&1; then
  echo "FAIL: dot set path wrote through a swapped shell rc parent" >&2
  exit 1
fi
grep -q 'shell rc path contains a symlink' "$TMP/dot-set-rc-root-race.out"
test -L "$DOT_TEST_RC_PARENT"
test ! -e "$DOT_TEST_RC_OUTSIDE/.zshrc"
rm "$DOT_TEST_RC_PARENT"
/bin/mv "$DOT_TEST_RC_SAVED" "$DOT_TEST_RC_PARENT"
rm -rf "$TMP/dot-rc-root-race-bin" "$DOT_TEST_RC_OUTSIDE"
unset DOT_TEST_RC_PARENT DOT_TEST_RC_SAVED DOT_TEST_RC_OUTSIDE DOT_TEST_RC_SWAP_MARKER

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
cat > "$HOME/.agents/skills/sources.json" <<'JSON'
{
  "version": 1,
  "alias_adapter": {
    "owner": "dotpanel",
    "destination": "~/.codex/skills",
    "renderer": "dot set codex",
    "retired_aliases": ["tool"]
  },
  "aliases": [
    {
      "id": "plan",
      "source": "hio",
      "skill": "minimal",
      "target": "minimal/SKILL.md",
      "description": "Alias-specific planning trigger."
    }
  ],
  "sources": [
    {
      "id": "hio",
      "paths": ["skills/hio"]
    },
    {
      "id": "arkcli",
      "paths": ["skills/arkcli-*"]
    }
  ]
}
JSON
"$HOME/.agents/.dotpanel/bin/dot" set claude
rm "$HOME/.claude/skills/hio/.dotpanel-owner"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
grep -qxF 'Generated by dotpanel; safe to reconcile.' "$HOME/.claude/skills/hio/.dotpanel-owner"
printf '\nplugin prepare failures must preserve live output\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"

mkdir -p "$HOME/.agents/secrets/plugin-trap"
cat > "$HOME/.agents/secrets/plugin-trap/SKILL.md" <<'SKILL'
---
name: plugin-trap
description: Boundary-only fixture with no secret value.
---
SKILL
ln -s "$HOME/.agents/secrets/plugin-trap" "$HOME/.agents/skills/hio/linked-secret"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-linked-secret.out" 2>&1; then
  echo "FAIL: Claude renderer followed a symlinked skill directory" >&2
  exit 1
fi
grep -q 'skill directory is symlinked' "$TMP/dot-claude-linked-secret.out"
grep -q 'plugin prepare failures must preserve live output' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
rm "$HOME/.agents/skills/hio/linked-secret"

mv "$HOME/.agents/skills" "$TMP/skills-root-real"
ln -s "$TMP/missing-skills-root" "$HOME/.agents/skills"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-broken-skills-root.out" 2>&1; then
  echo "FAIL: Claude renderer treated a broken symlinked skills root as an empty source" >&2
  exit 1
fi
grep -q 'Claude plugin skills root must not be symlinked' "$TMP/dot-claude-broken-skills-root.out"
grep -q 'plugin prepare failures must preserve live output' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
rm "$HOME/.agents/skills"
mv "$TMP/skills-root-real" "$HOME/.agents/skills"

mkdir -p "$HOME/.agents/skills/hio/unsafe-name"
cat > "$HOME/.agents/skills/hio/unsafe-name/SKILL.md" <<'SKILL'
---
name: ../escape
description: Unsafe-name fixture.
---
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-unsafe-name.out" 2>&1; then
  echo "FAIL: Claude renderer accepted a path-escaping skill name" >&2
  exit 1
fi
grep -q 'unsafe skill name' "$TMP/dot-claude-unsafe-name.out"
grep -q 'plugin prepare failures must preserve live output' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
rm -rf "$HOME/.agents/skills/hio/unsafe-name"

cp "$HOME/.agents/skills/hio/minimal/SKILL.md" "$TMP/minimal-skill-valid.md"
for invalid_description in '# TODO' 'null' '[]' '>'; do
  cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<SKILL
---
name: minimal
description: $invalid_description
---

# Minimal
SKILL
  if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-invalid-description.out" 2>&1; then
    echo "FAIL: Claude renderer accepted a semantically empty/non-string description: $invalid_description" >&2
    exit 1
  fi
  grep -q 'has no description' "$TMP/dot-claude-invalid-description.out"
done
for invalid_description in 'foo: bar' '0x10' '00' $'foo:\tbar'; do
  cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<SKILL
---
name: minimal
description: $invalid_description
---

# Minimal
SKILL
  if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-non-string-description.out" 2>&1; then
    echo "FAIL: Claude renderer accepted a non-string YAML description: $invalid_description" >&2
    exit 1
  fi
  grep -q 'has no description' "$TMP/dot-claude-non-string-description.out"
done
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: >++
  Invalid block scalar header.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-invalid-block-header.out" 2>&1; then
  echo "FAIL: Claude renderer accepted an invalid block scalar header" >&2
  exit 1
fi
grep -q 'has no description' "$TMP/dot-claude-invalid-block-header.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: >2
 text
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-invalid-block-indent.out" 2>&1; then
  echo "FAIL: Claude renderer accepted invalid YAML block indentation" >&2
  exit 1
fi
grep -q 'has no description' "$TMP/dot-claude-invalid-block-indent.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: Valid description.
stray: [unterminated
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-malformed-extra-field.out" 2>&1; then
  echo "FAIL: Claude renderer accepted malformed extra frontmatter" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-malformed-extra-field.out"
for quoted_description in '"0x10"' '"foo: bar"'; do
  cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<SKILL
---
name: minimal
description: $quoted_description
---

# Minimal
SKILL
  "$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
done
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: true
description: Valid description.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-non-string-name.out" 2>&1; then
  echo "FAIL: Claude renderer accepted a non-string YAML name" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-non-string-name.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: "foo # bar"
description: Valid description.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-quoted-unsafe-name.out" 2>&1; then
  echo "FAIL: Claude renderer truncated a quoted unsafe name" >&2
  exit 1
fi
grep -q 'unsafe skill name: foo # bar' "$TMP/dot-claude-quoted-unsafe-name.out"
for block_name_header in 'name : >-' '"name": >-' 'name: &canonical >-' 'name: !!str >-'; do
  cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<SKILL
---
$block_name_header
  minimal
description: Valid description.
---

# Minimal
SKILL
  if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-block-name.out" 2>&1; then
    echo "FAIL: Claude renderer accepted a block-scalar skill name: $block_name_header" >&2
    exit 1
  fi
  grep -q 'invalid frontmatter' "$TMP/dot-claude-block-name.out"
done
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
? name
: >-
  minimal
description: Valid description.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-explicit-block-name.out" 2>&1; then
  echo "FAIL: Claude renderer accepted an explicit-key block-scalar skill name" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-explicit-block-name.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
 name: >-
   minimal
 description: Valid description.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-indented-block-name.out" 2>&1; then
  echo "FAIL: Claude renderer accepted an indented block-scalar skill name" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-indented-block-name.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: "\uD800"
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-surrogate-description.out" 2>&1; then
  echo "FAIL: Claude renderer accepted a non-UTF-8 YAML description" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-surrogate-description.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal
description: First description.
description: Second description.
---

# Minimal
SKILL
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-duplicate-description.out" 2>&1; then
  echo "FAIL: Claude renderer accepted duplicate frontmatter descriptions" >&2
  exit 1
fi
grep -q 'invalid frontmatter' "$TMP/dot-claude-duplicate-description.out"
cat > "$HOME/.agents/skills/hio/minimal/SKILL.md" <<'SKILL'
---
name: minimal # canonical
description: >
  Folded descriptions remain valid when they contain text.
---

# Minimal
SKILL
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
"$HOME/.agents/.dotpanel/bin/dot" set codex >/dev/null
test -f "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
test -f "$HOME/.codex/skills/plan/SKILL.md"
cp "$TMP/minimal-skill-valid.md" "$HOME/.agents/skills/hio/minimal/SKILL.md"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
"$HOME/.agents/.dotpanel/bin/dot" set codex >/dev/null
printf '\nplugin prepare failures must preserve live output\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"

cp "$HOME/.agents/skills/matt/.claude-plugin/plugin.json" "$TMP/matt-plugin-valid.json"
printf '{invalid json\n' > "$HOME/.agents/skills/matt/.claude-plugin/plugin.json"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-invalid-matt-json.out" 2>&1; then
  echo "FAIL: Claude renderer accepted malformed matt plugin JSON" >&2
  exit 1
fi
grep -q 'invalid matt plugin skill manifest' "$TMP/dot-claude-invalid-matt-json.out"
grep -q 'plugin prepare failures must preserve live output' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
printf '{"skills":["../secrets/plugin-trap"]}\n' > "$HOME/.agents/skills/matt/.claude-plugin/plugin.json"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-escaping-matt-path.out" 2>&1; then
  echo "FAIL: Claude renderer accepted an escaping matt skill path" >&2
  exit 1
fi
grep -q 'unsafe matt skill path' "$TMP/dot-claude-escaping-matt-path.out"
cp "$TMP/matt-plugin-valid.json" "$HOME/.agents/skills/matt/.claude-plugin/plugin.json"
test -z "$(find "$HOME/.agents/.dotpanel/var" \( -name 'plugin.*' -o -name '*-prepared.*' \) -print -quit)"
rm -rf "$HOME/.agents/secrets/plugin-trap"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
! grep -q 'plugin prepare failures must preserve live output' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
mv "$HOME/.agents/skills/hio" "$TMP/hio-source-absent"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
test ! -e "$HOME/.claude/skills/hio"
mv "$TMP/hio-source-absent" "$HOME/.agents/skills/hio"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
test -f "$HOME/.claude/skills/hio/.dotpanel-owner"
rm -rf "$HOME/.claude/skills/hio"
mkdir -p "$HOME/.claude/skills/hio"
printf 'user-owned Claude plugin\n' > "$HOME/.claude/skills/hio/README"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-unmanaged-collision.out" 2>&1; then
  echo "FAIL: Claude renderer overwrote an unmanaged plugin" >&2
  exit 1
fi
grep -q 'Claude plugin destination is unmanaged; refusing to overwrite' "$TMP/dot-claude-unmanaged-collision.out"
grep -qxF 'user-owned Claude plugin' "$HOME/.claude/skills/hio/README"
rm -rf "$HOME/.claude/skills/hio"
"$HOME/.agents/.dotpanel/bin/dot" set claude >/dev/null
mv "$HOME/.claude" "$TMP/claude-config-real"
ln -s "$TMP/claude-config-real" "$HOME/.claude"
if "$HOME/.agents/.dotpanel/bin/dot" unset claude > "$TMP/dot-unset-claude-parent-symlink.out" 2>&1; then
  echo "FAIL: Claude unset followed a symlinked config root" >&2
  exit 1
fi
test -f "$TMP/claude-config-real/CLAUDE.md"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-claude-parent-symlink.out" 2>&1; then
  echo "FAIL: Claude renderer followed a symlinked config root" >&2
  exit 1
fi
grep -q 'path contains a symlink\|root must not be symlinked' "$TMP/dot-claude-parent-symlink.out"
test -L "$HOME/.claude"
rm "$HOME/.claude"
mv "$TMP/claude-config-real" "$HOME/.claude"

mkdir -p "$HOME/.codex/skills/plan"
printf 'preexisting plan skill\n' > "$HOME/.codex/skills/plan/SKILL.md"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-first-migration.out" 2>&1; then
  echo "FAIL: first Codex alias migration overwrote an unmanaged target" >&2
  exit 1
fi
grep -q 'Codex alias destination is unmanaged; refusing to overwrite' "$TMP/dot-codex-first-migration.out"
grep -qxF 'preexisting plan skill' "$HOME/.codex/skills/plan/SKILL.md"
rm -rf "$HOME/.codex/skills/plan"
"$HOME/.agents/.dotpanel/bin/dot" set codex
test -f "$HOME/.codex/skills/plan/SKILL.md"
grep -qxF '<!-- Generated by dot configure from ~/.agents/skills/sources.json; do not edit directly. -->' "$HOME/.codex/skills/plan/SKILL.md"
grep -q '^name: plan$' "$HOME/.codex/skills/plan/SKILL.md"
grep -qxF 'description: "Alias-specific planning trigger."' "$HOME/.codex/skills/plan/SKILL.md"
grep -q '^# plan — Codex alias$' "$HOME/.codex/skills/plan/SKILL.md"
canonical_fixture="$(cd "$HOME/.agents/skills/hio/minimal" && pwd -P)/SKILL.md"
grep -qxF "\`$canonical_fixture\`" "$HOME/.codex/skills/plan/SKILL.md"
grep -q 'Resolve relative references from the canonical skill directory' "$HOME/.codex/skills/plan/SKILL.md"
! grep -q '^# Minimal$' "$HOME/.codex/skills/plan/SKILL.md"
mv "$HOME/.codex" "$TMP/codex-config-real"
ln -s "$TMP/codex-config-real" "$HOME/.codex"
if "$HOME/.agents/.dotpanel/bin/dot" unset codex > "$TMP/dot-unset-codex-parent-symlink.out" 2>&1; then
  echo "FAIL: Codex unset followed a symlinked config root" >&2
  exit 1
fi
test -f "$TMP/codex-config-real/AGENTS.md"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-parent-symlink.out" 2>&1; then
  echo "FAIL: Codex renderer followed a symlinked config root" >&2
  exit 1
fi
grep -q 'path contains a symlink\|root must not be symlinked' "$TMP/dot-codex-parent-symlink.out"
test -L "$HOME/.codex"
rm "$HOME/.codex"
mv "$TMP/codex-config-real" "$HOME/.codex"

mv "$HOME/.kimi" "$TMP/kimi-config-real"
ln -s "$TMP/kimi-config-real" "$HOME/.kimi"
if "$HOME/.agents/.dotpanel/bin/dot" unset kimi > "$TMP/dot-unset-kimi-parent-symlink.out" 2>&1; then
  echo "FAIL: Kimi unset followed a symlinked config root" >&2
  exit 1
fi
test -f "$TMP/kimi-config-real/AGENTS.md"
if "$HOME/.agents/.dotpanel/bin/dot" set kimi > "$TMP/dot-kimi-parent-symlink.out" 2>&1; then
  echo "FAIL: Kimi renderer followed a symlinked config root" >&2
  exit 1
fi
grep -q 'path contains a symlink\|root must not be symlinked' "$TMP/dot-kimi-parent-symlink.out"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-kimi-parent-symlink.out" 2>&1; then
  echo "FAIL: dot doctor followed a symlinked Kimi config root" >&2
  exit 1
fi
grep -q 'path contains a symlink\|root must not be symlinked' "$TMP/dot-doctor-kimi-parent-symlink.out"
rm "$HOME/.kimi"
mv "$TMP/kimi-config-real" "$HOME/.kimi"

mkdir -p "$TMP/dot-root-race-bin"
cat > "$TMP/dot-root-race-bin/mkdir" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$DOT_TEST_SWAP_TRIGGER" ] && [ ! -e "$DOT_TEST_SWAP_MARKER" ]; then
  /bin/mv "$DOT_TEST_SWAP_ROOT" "$DOT_TEST_SWAP_SAVED"
  /bin/mkdir -p "$DOT_TEST_SWAP_OUTSIDE"
  /bin/ln -s "$DOT_TEST_SWAP_OUTSIDE" "$DOT_TEST_SWAP_ROOT"
  : > "$DOT_TEST_SWAP_MARKER"
fi
exec /bin/mkdir "$@"
SH
chmod +x "$TMP/dot-root-race-bin/mkdir"
for harness in claude codex kimi; do
  case "$harness" in
    claude) root="$HOME/.claude"; trigger="$HOME/.claude/skills" ;;
    codex) root="$HOME/.codex"; trigger="$HOME/.codex/skills" ;;
    kimi) root="$HOME/.kimi"; trigger="$HOME/.kimi" ;;
  esac
  export DOT_TEST_SWAP_ROOT="$root"
  export DOT_TEST_SWAP_TRIGGER="$trigger"
  export DOT_TEST_SWAP_SAVED="$TMP/$harness-root-race-saved"
  export DOT_TEST_SWAP_OUTSIDE="$TMP/$harness-root-race-outside"
  export DOT_TEST_SWAP_MARKER="$TMP/$harness-root-race-triggered"
  if PATH="$TMP/dot-root-race-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dot" set "$harness" > "$TMP/dot-$harness-root-race.out" 2>&1; then
    echo "FAIL: dot set $harness wrote through a root swapped after validation" >&2
    exit 1
  fi
  grep -q 'path contains a symlink\|root must not be symlinked' "$TMP/dot-$harness-root-race.out"
  test -L "$root"
  rm "$root"
  /bin/mv "$DOT_TEST_SWAP_SAVED" "$root"
  rm -rf "$DOT_TEST_SWAP_OUTSIDE"
done
unset DOT_TEST_SWAP_ROOT DOT_TEST_SWAP_TRIGGER DOT_TEST_SWAP_SAVED DOT_TEST_SWAP_OUTSIDE DOT_TEST_SWAP_MARKER
rm -rf "$TMP/dot-root-race-bin"

mv "$HOME/.kimi/AGENTS.md" "$TMP/kimi-generated-wrapper.md"
cat > "$HOME/.kimi/AGENTS.md" <<'EOF'
# Personal Kimi notes

This prose mentions Generated by dot configure but is not owned by dotpanel.
EOF
"$HOME/.agents/.dotpanel/bin/dot" unset kimi > "$TMP/dot-unset-personal-wrapper.out" 2>&1
grep -q 'not generated by dot; leaving untouched' "$TMP/dot-unset-personal-wrapper.out"
test -f "$HOME/.kimi/AGENTS.md"
rm "$HOME/.kimi/AGENTS.md"
mv "$TMP/kimi-generated-wrapper.md" "$HOME/.kimi/AGENTS.md"

mkdir -p "$HOME/.codex/skills/manifest-user-owned"
printf 'manifest transition user skill\n' > "$HOME/.codex/skills/manifest-user-owned/SKILL.md"
mv "$HOME/.agents/skills/sources.json" "$TMP/sources-manifest-removed.json"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-manifest-removed.out" 2>&1; then
  echo "FAIL: dot doctor accepted a stale managed alias after manifest removal" >&2
  exit 1
fi
grep -q "stale dot-managed Codex alias: $HOME/.codex/skills/plan" "$TMP/dot-doctor-manifest-removed.out"
"$HOME/.agents/.dotpanel/bin/dot" set codex
test ! -e "$HOME/.codex/skills/plan"
grep -qxF 'manifest transition user skill' "$HOME/.codex/skills/manifest-user-owned/SKILL.md"
mv "$TMP/sources-manifest-removed.json" "$HOME/.agents/skills/sources.json"
"$HOME/.agents/.dotpanel/bin/dot" set codex
test -f "$HOME/.codex/skills/plan/SKILL.md"

jq '.alias_adapter.renderer = "other renderer"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-wrong-renderer.json"
mv "$TMP/sources-wrong-renderer.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-wrong-renderer.out" 2>&1; then
  echo "FAIL: dot set codex accepted a manifest assigned to another renderer" >&2
  exit 1
fi
grep -q 'invalid Codex alias manifest' "$TMP/dot-codex-wrong-renderer.out"
jq '.alias_adapter.renderer = "dot set codex"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-right-renderer.json"
mv "$TMP/sources-right-renderer.json" "$HOME/.agents/skills/sources.json"

mv "$HOME/.agents/skills/sources.json" "$TMP/sources-real.json"
ln -s "$TMP/sources-real.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-manifest-symlink.out" 2>&1; then
  echo "FAIL: dot set codex accepted a symlinked manifest" >&2
  exit 1
fi
grep -q 'Codex alias manifest must be a regular non-symlinked file' "$TMP/dot-codex-manifest-symlink.out"
rm "$HOME/.agents/skills/sources.json"
mv "$TMP/sources-real.json" "$HOME/.agents/skills/sources.json"

ln -s "$HOME/.agents/skills/hio" "$HOME/.agents/skills/linked-source"
jq '.sources += [{"id":"linked","paths":["skills/linked-source"]}] |
    .aliases[0].source = "linked"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-linked-source.json"
mv "$TMP/sources-linked-source.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-source-symlink.out" 2>&1; then
  echo "FAIL: dot set codex accepted a symlinked alias source" >&2
  exit 1
fi
grep -q 'Codex alias source path must not be symlinked' "$TMP/dot-codex-source-symlink.out"
jq '.sources = [.sources[] | select(.id != "linked")] | .aliases[0].source = "hio"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-linked-source.json"
mv "$TMP/sources-no-linked-source.json" "$HOME/.agents/skills/sources.json"
rm "$HOME/.agents/skills/linked-source"

mkdir -p "$HOME/.agents/secrets/alias-trap"
cat > "$HOME/.agents/secrets/alias-trap/SKILL.md" <<'SKILL'
---
name: alias-trap
description: Boundary fixture; contains no secret value.
---
SKILL
jq '.sources += [{"id":"root","paths":["."]}] |
    .aliases[0].source = "root" |
    .aliases[0].skill = "alias-trap" |
    .aliases[0].target = "secrets/alias-trap/SKILL.md"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-secret-route.json"
mv "$TMP/sources-secret-route.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-secret-route.out" 2>&1; then
  echo "FAIL: dot set codex accepted an alias source outside skills/" >&2
  exit 1
fi
grep -q 'unsafe Codex alias source path: .' "$TMP/dot-codex-secret-route.out"

jq '.sources = [.sources[] | select(.id != "root")] |
    .aliases[0].source = "hio" |
    .aliases[0].skill = "minimal" |
    .aliases[0].target = "minimal/SKILL.md"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-secret-route.json"
mv "$TMP/sources-no-secret-route.json" "$HOME/.agents/skills/sources.json"

ln -s "$HOME/.agents/secrets" "$HOME/.agents/skills/linked-parent"
jq '.sources += [{"id":"nested-link","paths":["skills/linked-parent/alias-trap"]}] |
    .aliases[0].source = "nested-link" |
    .aliases[0].skill = "alias-trap"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-nested-secret-route.json"
mv "$TMP/sources-nested-secret-route.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-nested-secret-route.out" 2>&1; then
  echo "FAIL: dot set codex accepted a nested symlink outside skills/" >&2
  exit 1
fi
grep -q 'Codex alias source escapes the skills root' "$TMP/dot-codex-nested-secret-route.out"
jq '.sources = [.sources[] | select(.id != "nested-link")] |
    .aliases[0].source = "hio" |
    .aliases[0].skill = "minimal"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-nested-secret-route.json"
mv "$TMP/sources-no-nested-secret-route.json" "$HOME/.agents/skills/sources.json"
rm "$HOME/.agents/skills/linked-parent"
rm -rf "$HOME/.agents/secrets/alias-trap"

jq '.aliases[0].description = "bad\nmultiline" | .aliases[0].guidance = "bad\tguidance"' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-control-chars.json"
mv "$TMP/sources-control-chars.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-control-chars.out" 2>&1; then
  echo "FAIL: dot set codex accepted multiline/control alias metadata" >&2
  exit 1
fi
grep -q 'invalid Codex alias manifest' "$TMP/dot-codex-control-chars.out"
jq '.aliases[0].description = "Alias-specific planning trigger." | del(.aliases[0].guidance)' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-clean-metadata.json"
mv "$TMP/sources-clean-metadata.json" "$HOME/.agents/skills/sources.json"

cp -R "$HOME/.codex/skills/plan" "$HOME/.codex/skills/stale"
mkdir -p "$HOME/.codex/skills/user-owned"
printf 'user owned\n' > "$HOME/.codex/skills/user-owned/SKILL.md"
jq '.aliases[0].id = "review" |
    .aliases[0].description = "Use for code review or UI review." |
    .aliases[0].guidance = "When --ui is present, include UI/product-design focus." |
    .alias_adapter.retired_aliases = ["plan", "tool"]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-next.json"
mv "$TMP/sources-next.json" "$HOME/.agents/skills/sources.json"
"$HOME/.agents/.dotpanel/bin/dot" set codex
test ! -e "$HOME/.codex/skills/plan"
test ! -e "$HOME/.codex/skills/stale"
test -f "$HOME/.codex/skills/review/SKILL.md"
grep -q '^name: review$' "$HOME/.codex/skills/review/SKILL.md"
grep -qxF 'description: "Use for code review or UI review."' "$HOME/.codex/skills/review/SKILL.md"
grep -qxF 'When --ui is present, include UI/product-design focus.' "$HOME/.codex/skills/review/SKILL.md"
grep -qxF 'user owned' "$HOME/.codex/skills/user-owned/SKILL.md"

cp "$HOME/.codex/skills/review/SKILL.md" "$TMP/review-before-collision.md"
cp "$HOME/.agents/.dotpanel/env.sh" "$TMP/env-before-render-collision.sh"
printf '\nprepare collision must preserve Claude wrapper\n' >> "$HOME/.claude/CLAUDE.md"
printf '\nprepare collision must preserve Claude plugin\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
printf '\nprepare collision must preserve Kimi wrapper\n' >> "$HOME/.kimi/AGENTS.md"
jq '.aliases += [{"id":"user-owned","source":"hio","skill":"minimal","target":"minimal/SKILL.md","description":"Collision fixture."}]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-collision.json"
mv "$TMP/sources-collision.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" configure --harness all > "$TMP/dot-codex-unmanaged.out" 2>&1; then
  echo "FAIL: dot configure changed state after a Codex ownership collision" >&2
  exit 1
fi
grep -q 'Codex alias destination is unmanaged; refusing to overwrite' "$TMP/dot-codex-unmanaged.out"
grep -qxF 'user owned' "$HOME/.codex/skills/user-owned/SKILL.md"
cmp -s "$TMP/review-before-collision.md" "$HOME/.codex/skills/review/SKILL.md"
cmp -s "$TMP/env-before-render-collision.sh" "$HOME/.agents/.dotpanel/env.sh"
grep -q 'prepare collision must preserve Claude wrapper' "$HOME/.claude/CLAUDE.md"
grep -q 'prepare collision must preserve Claude plugin' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
grep -q 'prepare collision must preserve Kimi wrapper' "$HOME/.kimi/AGENTS.md"
jq '.aliases = [.aliases[] | select(.id != "user-owned")]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-collision.json"
mv "$TMP/sources-no-collision.json" "$HOME/.agents/skills/sources.json"
"$HOME/.agents/.dotpanel/bin/dot" configure --harness all >/dev/null
! grep -q 'prepare collision must preserve Claude wrapper' "$HOME/.claude/CLAUDE.md"
! grep -q 'prepare collision must preserve Claude plugin' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
! grep -q 'prepare collision must preserve Kimi wrapper' "$HOME/.kimi/AGENTS.md"

mkdir -p "$HOME/.codex/skills/symlink-owned"
printf '%s\n' '<!-- Generated by dot configure from ~/.agents/skills/sources.json; do not edit directly. -->' \
  > "$TMP/fake-managed-alias.md"
ln -s "$TMP/fake-managed-alias.md" "$HOME/.codex/skills/symlink-owned/SKILL.md"
jq '.aliases += [{"id":"symlink-owned","source":"hio","skill":"minimal","target":"minimal/SKILL.md","description":"Symlink ownership fixture."}]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-symlink-owned.json"
mv "$TMP/sources-symlink-owned.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-symlink-owned.out" 2>&1; then
  echo "FAIL: dot trusted a symlinked alias ownership file" >&2
  exit 1
fi
grep -q 'Codex alias destination is unmanaged; refusing to overwrite' "$TMP/dot-codex-symlink-owned.out"
test -L "$HOME/.codex/skills/symlink-owned/SKILL.md"
jq '.aliases = [.aliases[] | select(.id != "symlink-owned")]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-symlink-owned.json"
mv "$TMP/sources-no-symlink-owned.json" "$HOME/.agents/skills/sources.json"
rm -rf "$HOME/.codex/skills/symlink-owned"

mkdir -p "$HOME/.codex/skills/legacy"
printf 'legacy user skill\n' > "$HOME/.codex/skills/legacy/SKILL.md"
jq '.alias_adapter.retired_aliases += ["legacy"]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-retired-unmanaged.json"
mv "$TMP/sources-retired-unmanaged.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-retired-unmanaged.out" 2>&1; then
  echo "FAIL: dot set codex accepted an unmanaged retired alias" >&2
  exit 1
fi
grep -q 'retired Codex alias is unmanaged; remove it manually' "$TMP/dot-codex-retired-unmanaged.out"
grep -qxF 'legacy user skill' "$HOME/.codex/skills/legacy/SKILL.md"
jq '.alias_adapter.retired_aliases = [.alias_adapter.retired_aliases[] | select(. != "legacy")]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-legacy.json"
mv "$TMP/sources-no-legacy.json" "$HOME/.agents/skills/sources.json"
rm -rf "$HOME/.codex/skills/legacy"

jq '.aliases += [{"id":"escape","source":"hio","skill":"minimal","target":"../outside/SKILL.md","description":"Escape fixture."}]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-escape.json"
mv "$TMP/sources-escape.json" "$HOME/.agents/skills/sources.json"
if "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-escape.out" 2>&1; then
  echo "FAIL: dot set codex accepted a target outside its declared source" >&2
  exit 1
fi
grep -q 'unsafe Codex alias target: ../outside/SKILL.md' "$TMP/dot-codex-escape.out"
test ! -e "$HOME/.codex/skills/escape"
jq '.aliases = [.aliases[] | select(.id != "escape")]' \
  "$HOME/.agents/skills/sources.json" > "$TMP/sources-no-escape.json"
mv "$TMP/sources-no-escape.json" "$HOME/.agents/skills/sources.json"
. "$HOME/.agents/.dotpanel/env.sh"
"$HOME/.agents/.dotpanel/bin/dot" doctor

printf 'outside doctor wrapper sentinel\n' > "$TMP/outside-doctor-wrapper"
printf 'outside doctor env sentinel\n' > "$TMP/outside-doctor-env"
cp "$TMP/outside-doctor-wrapper" "$TMP/outside-doctor-wrapper-before"
cp "$TMP/outside-doctor-env" "$TMP/outside-doctor-env-before"
mkdir -p "$TMP/dot-doctor-scratch-bin"
cat > "$TMP/dot-doctor-scratch-bin/mkdir" <<'SH'
#!/bin/sh
if [ ! -e "$DOT_TEST_DOCTOR_SCRATCH_MARKER" ]; then
  /bin/mkdir -p "$DOT_TEST_DOCTOR_SCRATCH_VAR" || exit 1
  wrapper_path="$DOT_TEST_DOCTOR_SCRATCH_VAR/doctor-wrapper.$PPID"
  env_path="$DOT_TEST_DOCTOR_SCRATCH_VAR/doctor-env.$PPID"
  /bin/ln -s "$DOT_TEST_DOCTOR_WRAPPER_OUTSIDE" "$wrapper_path" || exit 1
  /bin/ln -s "$DOT_TEST_DOCTOR_ENV_OUTSIDE" "$env_path" || exit 1
  printf '%s\n%s\n' "$wrapper_path" "$env_path" > "$DOT_TEST_DOCTOR_SCRATCH_PATHS"
  : > "$DOT_TEST_DOCTOR_SCRATCH_MARKER"
fi
exec /bin/mkdir "$@"
SH
chmod +x "$TMP/dot-doctor-scratch-bin/mkdir"
DOT_TEST_DOCTOR_SCRATCH_MARKER="$TMP/dot-doctor-scratch-triggered" \
DOT_TEST_DOCTOR_SCRATCH_PATHS="$TMP/dot-doctor-scratch-paths" \
DOT_TEST_DOCTOR_SCRATCH_VAR="$HOME/.agents/.dotpanel/var" \
DOT_TEST_DOCTOR_WRAPPER_OUTSIDE="$TMP/outside-doctor-wrapper" \
DOT_TEST_DOCTOR_ENV_OUTSIDE="$TMP/outside-doctor-env" \
PATH="$TMP/dot-doctor-scratch-bin:$PATH" \
  "$HOME/.agents/.dotpanel/bin/dot" doctor >/dev/null
cmp -s "$TMP/outside-doctor-wrapper-before" "$TMP/outside-doctor-wrapper"
cmp -s "$TMP/outside-doctor-env-before" "$TMP/outside-doctor-env"
while IFS= read -r scratch_path; do
  test -L "$scratch_path"
  rm "$scratch_path"
done < "$TMP/dot-doctor-scratch-paths"
rm -rf "$TMP/dot-doctor-scratch-bin"

printf '\nCodex alias drift\n' >> "$HOME/.codex/skills/review/SKILL.md"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-codex-alias-drift.out" 2>&1; then
  echo "FAIL: dot doctor accepted stale generated Codex alias content" >&2
  exit 1
fi
grep -q "Codex alias differs from source render: $HOME/.codex/skills/review" "$TMP/dot-doctor-codex-alias-drift.out"
"$HOME/.agents/.dotpanel/bin/dot" set codex

rm -rf "$HOME/.codex/skills/review"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-codex-alias-missing.out" 2>&1; then
  echo "FAIL: dot doctor accepted a missing declared Codex alias" >&2
  exit 1
fi
grep -q "Codex alias missing: $HOME/.codex/skills/review" "$TMP/dot-doctor-codex-alias-missing.out"
"$HOME/.agents/.dotpanel/bin/dot" set codex

cp -R "$HOME/.codex/skills/review" "$HOME/.codex/skills/stale-doctor"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-codex-alias-stale.out" 2>&1; then
  echo "FAIL: dot doctor accepted a stale dot-managed Codex alias" >&2
  exit 1
fi
grep -q "stale dot-managed Codex alias: $HOME/.codex/skills/stale-doctor" "$TMP/dot-doctor-codex-alias-stale.out"
rm -rf "$HOME/.codex/skills/stale-doctor"

"$HOME/.agents/.dotpanel/bin/dot" unset codex
test ! -e "$HOME/.codex/AGENTS.md"
test ! -e "$HOME/.codex/skills/review"
grep -qxF 'user owned' "$HOME/.codex/skills/user-owned/SKILL.md"
"$HOME/.agents/.dotpanel/bin/dot" set codex
test -f "$HOME/.codex/AGENTS.md"
test -f "$HOME/.codex/skills/review/SKILL.md"

mkdir -p "$TMP/codex-race-bin"
cat > "$TMP/codex-race-bin/mkdir" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$HOME/.codex/skills" ] && [ ! -e "$DOT_TEST_RACE_MARKER" ]; then
  /bin/mkdir "$@" || exit 1
  /bin/rm -rf "$HOME/.codex/skills/review"
  /bin/mkdir -p "$HOME/.codex/skills/review"
  printf 'user-owned race fixture\n' > "$HOME/.codex/skills/review/SKILL.md"
  : > "$DOT_TEST_RACE_MARKER"
  exit 0
fi
exec /bin/mkdir "$@"
SH
chmod +x "$TMP/codex-race-bin/mkdir"
export DOT_TEST_RACE_MARKER="$TMP/codex-race-triggered"
if PATH="$TMP/codex-race-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dot" set codex > "$TMP/dot-codex-apply-race.out" 2>&1; then
  echo "FAIL: Codex alias apply overwrote a destination that became unmanaged after preflight" >&2
  exit 1
fi
grep -q 'Codex alias destination became unmanaged' "$TMP/dot-codex-apply-race.out"
grep -qxF 'user-owned race fixture' "$HOME/.codex/skills/review/SKILL.md"
rm -rf "$HOME/.codex/skills/review" "$TMP/codex-race-bin"
unset DOT_TEST_RACE_MARKER
"$HOME/.agents/.dotpanel/bin/dot" set codex

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

mv "$HOME/.claude/CLAUDE.md" "$TMP/claude-wrapper-real.md"
ln -s "$TMP/claude-wrapper-real.md" "$HOME/.claude/CLAUDE.md"
if "$HOME/.agents/.dotpanel/bin/dot" set claude > "$TMP/dot-set-wrapper-symlink.out" 2>&1; then
  echo "FAIL: dot set accepted a symlinked generated wrapper" >&2
  exit 1
fi
grep -q 'path contains a symlink\|must not be symlinked' "$TMP/dot-set-wrapper-symlink.out"
test -L "$HOME/.claude/CLAUDE.md"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-wrapper-symlink.out" 2>&1; then
  echo "FAIL: dot doctor accepted a symlinked generated wrapper" >&2
  exit 1
fi
grep -q 'path contains a symlink\|must not be symlinked' "$TMP/dot-doctor-wrapper-symlink.out"
rm "$HOME/.claude/CLAUDE.md"
mv "$TMP/claude-wrapper-real.md" "$HOME/.claude/CLAUDE.md"

printf '\ngenerated drift\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-plugin-drift.out" 2>&1; then
  echo "FAIL: dot doctor accepted stale generated skills" >&2
  exit 1
fi
grep -q "hio plugin differs from source render" "$TMP/dot-doctor-plugin-drift.out"
"$HOME/.agents/.dotpanel/bin/dot" set claude

printf 'outside generated plugin tree\n' > "$TMP/plugin-outside.md"
ln -s "$TMP/plugin-outside.md" "$HOME/.claude/skills/hio/external-link"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-plugin-symlink.out" 2>&1; then
  echo "FAIL: dot doctor accepted a symlink inside a live generated plugin" >&2
  exit 1
fi
grep -q 'hio live plugin contains symlinks' "$TMP/dot-doctor-plugin-symlink.out"
rm "$HOME/.claude/skills/hio/external-link"
"$HOME/.agents/.dotpanel/bin/dot" doctor >/dev/null

printf '\nunsafe env drift\n' >> "$HOME/.agents/.dotpanel/env.sh"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-env-drift.out" 2>&1; then
  echo "FAIL: dot doctor accepted stale shell integration" >&2
  exit 1
fi
grep -q 'env file differs from generated content' "$TMP/dot-doctor-env-drift.out"
"$HOME/.agents/.dotpanel/bin/dot" set path >/dev/null
mv "$HOME/.agents/.dotpanel/env.sh" "$TMP/env-real.sh"
ln -s "$TMP/env-real.sh" "$HOME/.agents/.dotpanel/env.sh"
if "$HOME/.agents/.dotpanel/bin/dot" doctor > "$TMP/dot-doctor-env-symlink.out" 2>&1; then
  echo "FAIL: dot doctor accepted a symlinked shell integration file" >&2
  exit 1
fi
grep -q 'path contains a symlink\|must not be symlinked' "$TMP/dot-doctor-env-symlink.out"
rm "$HOME/.agents/.dotpanel/env.sh"
mv "$TMP/env-real.sh" "$HOME/.agents/.dotpanel/env.sh"

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

git init -q -b main "$TMP/submodule-work"
git -C "$TMP/submodule-work" config user.name "Dotpanel Tests"
git -C "$TMP/submodule-work" config user.email "dotpanel-tests@example.invalid"
printf 'submodule payload\n' > "$TMP/submodule-work/payload.txt"
git -C "$TMP/submodule-work" add payload.txt
git -C "$TMP/submodule-work" commit -q -m "test: submodule payload"
git init -q --bare "$TMP/submodule-origin.git"
git -C "$TMP/submodule-work" remote add origin "$TMP/submodule-origin.git"
git -C "$TMP/submodule-work" push -q -u origin main
git --git-dir="$TMP/submodule-origin.git" symbolic-ref HEAD refs/heads/main
git -c protocol.file.allow=always -C "$TMP/memspace-upstream" submodule add -q \
  "$TMP/submodule-origin.git" modules/example

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
GIT_ALLOW_PROTOCOL=file "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-clean.out" 2>&1
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$pull_target"
test -f "$HOME/.agents/pulled.md"
test -f "$HOME/.agents/modules/example/payload.txt"
cmp -s "$HOME/.claude/CLAUDE.md" "$HOME/.codex/AGENTS.md"
"$HOME/.agents/.dotpanel/bin/dot" doctor >/dev/null

jq '.alias_adapter.renderer = "invalid after pull"' \
  "$TMP/memspace-upstream/skills/sources.json" > "$TMP/upstream-invalid-sources.json"
mv "$TMP/upstream-invalid-sources.json" "$TMP/memspace-upstream/skills/sources.json"
git -C "$TMP/memspace-upstream" add skills/sources.json
git -C "$TMP/memspace-upstream" commit -q -m "test: invalid alias manifest"
git -C "$TMP/memspace-upstream" push -q origin main
invalid_render_target="$(git -C "$TMP/memspace-upstream" rev-parse HEAD)"
printf '\npull render failure preserves Claude wrapper\n' >> "$HOME/.claude/CLAUDE.md"
printf '\npull render failure preserves Claude plugin\n' >> "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
printf '\npull render failure preserves Codex alias\n' >> "$HOME/.codex/skills/review/SKILL.md"
printf '\npull render failure preserves Kimi wrapper\n' >> "$HOME/.kimi/AGENTS.md"
printf '\n# pull render failure preserves env\n' >> "$HOME/.agents/.dotpanel/env.sh"
if GIT_ALLOW_PROTOCOL=file "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-render-failure.out" 2>&1; then
  echo "FAIL: dot sync pull accepted an invalid post-fast-forward render" >&2
  exit 1
fi
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$invalid_render_target"
grep -q 'render preparation failed; generated harness state was not changed' "$TMP/dot-sync-pull-render-failure.out"
grep -q 'pull render failure preserves Claude wrapper' "$HOME/.claude/CLAUDE.md"
grep -q 'pull render failure preserves Claude plugin' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
grep -q 'pull render failure preserves Codex alias' "$HOME/.codex/skills/review/SKILL.md"
grep -q 'pull render failure preserves Kimi wrapper' "$HOME/.kimi/AGENTS.md"
grep -q 'pull render failure preserves env' "$HOME/.agents/.dotpanel/env.sh"

jq '.alias_adapter.renderer = "dot set codex"' \
  "$TMP/memspace-upstream/skills/sources.json" > "$TMP/upstream-fixed-sources.json"
mv "$TMP/upstream-fixed-sources.json" "$TMP/memspace-upstream/skills/sources.json"
git -C "$TMP/memspace-upstream" add skills/sources.json
git -C "$TMP/memspace-upstream" commit -q -m "test: repair alias manifest"
git -C "$TMP/memspace-upstream" push -q origin main
fixed_render_target="$(git -C "$TMP/memspace-upstream" rev-parse HEAD)"
GIT_ALLOW_PROTOCOL=file "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-render-recovery.out" 2>&1
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$fixed_render_target"
! grep -q 'pull render failure preserves Claude wrapper' "$HOME/.claude/CLAUDE.md"
! grep -q 'pull render failure preserves Claude plugin' "$HOME/.claude/skills/hio/skills/minimal/SKILL.md"
! grep -q 'pull render failure preserves Codex alias' "$HOME/.codex/skills/review/SKILL.md"
! grep -q 'pull render failure preserves Kimi wrapper' "$HOME/.kimi/AGENTS.md"
! grep -q 'pull render failure preserves env' "$HOME/.agents/.dotpanel/env.sh"
"$HOME/.agents/.dotpanel/bin/dot" doctor >/dev/null

submodule_commit="$(git -C "$TMP/submodule-work" rev-parse HEAD)"
git -C "$TMP/memspace-upstream" config -f .gitmodules submodule.broken.path modules/broken
git -C "$TMP/memspace-upstream" config -f .gitmodules submodule.broken.url "$TMP/missing-submodule.git"
git -C "$TMP/memspace-upstream" add .gitmodules
git -C "$TMP/memspace-upstream" update-index --add \
  --cacheinfo "160000,$submodule_commit,modules/broken"
git -C "$TMP/memspace-upstream" commit -q -m "test: broken submodule update"
git -C "$TMP/memspace-upstream" push -q origin main
failed_submodule_target="$(git -C "$TMP/memspace-upstream" rev-parse HEAD)"
printf '\nwrapper must not render after submodule failure\n' >> "$HOME/.kimi/AGENTS.md"
if GIT_ALLOW_PROTOCOL=file "$HOME/.agents/.dotpanel/bin/dot" sync pull > "$TMP/dot-sync-pull-submodule-failure.out" 2>&1; then
  echo "FAIL: dot sync pull rendered after a submodule update failure" >&2
  exit 1
fi
test "$(git -C "$HOME/.agents" rev-parse HEAD)" = "$failed_submodule_target"
grep -q 'wrapper must not render after submodule failure' "$HOME/.kimi/AGENTS.md"
test ! -e "$HOME/.agents/modules/broken/.git"
"$HOME/.agents/.dotpanel/bin/dot" set kimi >/dev/null

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

mkdir -p "$TMP/dot-signal-bin"
cat > "$TMP/dot-signal-bin/mv" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$HOME/.kimi/AGENTS.md" ] && [ ! -e "$DOT_TEST_SIGNAL_MARKER" ]; then
  : > "$DOT_TEST_SIGNAL_MARKER"
  kill -TERM "$PPID"
  exit 0
fi
exec /bin/mv "$@"
SH
chmod +x "$TMP/dot-signal-bin/mv"
export DOT_TEST_SIGNAL_MARKER="$TMP/dot-signal-triggered"
printf '\nsignal replacement fixture\n' >> "$HOME/.kimi/AGENTS.md"
if PATH="$TMP/dot-signal-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dot" set kimi > "$TMP/dot-set-signal.out" 2>&1; then
  echo "FAIL: dot set continued successfully after TERM" >&2
  exit 1
fi
test -f "$DOT_TEST_SIGNAL_MARKER"
unset DOT_TEST_SIGNAL_MARKER
rm -rf "$TMP/dot-signal-bin"

if [ "${DOT_ONLY:-0}" = "1" ]; then
  echo "OK (dot only)"
  exit 0
fi

"$HOME/.agents/.dotpanel/bin/dkey" init
"$HOME/.agents/.dotpanel/bin/dkey" status | grep -q 'active grant: none'
"$HOME/.agents/.dotpanel/bin/dkey" off | grep -q 'DKEY_ACTIVE_GRANT'

if command -v age >/dev/null 2>&1 && command -v age-keygen >/dev/null 2>&1; then
  assert_no_sensitive_dkey_temps() {
    if find "$HOME/.agents/secrets" "$HOME/.config/age" -maxdepth 1 -type f \
        \( -name '.keys.env.*' -o -name 'keys.env.age.dkey-encrypt.*' -o -name '.dkey-identity.*' \) \
        -print -quit | grep -q .; then
      echo "FAIL: dkey left a sensitive temporary file" >&2
      exit 1
    fi
  }

  "$HOME/.agents/.dotpanel/bin/dkey" keygen >/dev/null

  mkdir -p "$TMP/dkey-symlink-home-real"
  ln -s "$TMP/dkey-symlink-home-real" "$TMP/dkey-symlink-home"
  if HOME="$TMP/dkey-symlink-home" \
      "$HOME/.agents/.dotpanel/bin/dkey" keygen > "$TMP/dkey-symlink-home.out" 2>&1; then
    echo "FAIL: dkey keygen accepted a symlinked HOME boundary" >&2
    exit 1
  fi
  grep -q 'HOME boundary must not be symlinked' "$TMP/dkey-symlink-home.out"
  test ! -e "$TMP/dkey-symlink-home-real/.config/age/key.txt"

  mkdir -p "$TMP/dkey-failing-keygen-bin"
  cat > "$TMP/dkey-failing-keygen-bin/age-keygen" <<'SH'
#!/bin/sh
printf 'synthetic partial private key\n'
exit 9
SH
  chmod +x "$TMP/dkey-failing-keygen-bin/age-keygen"
  if DKEY_AGE_IDENTITY_FILE="$TMP/failed-keygen-target" \
      PATH="$TMP/dkey-failing-keygen-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" keygen > "$TMP/dkey-failing-keygen.out" 2>&1; then
    echo "FAIL: dkey keygen accepted a failed age-keygen result" >&2
    exit 1
  fi
  test ! -e "$TMP/failed-keygen-target"
  test -z "$(find "$TMP" -maxdepth 1 -type f -name '.dkey-identity.*' -print -quit)"
  rm -rf "$TMP/dkey-failing-keygen-bin"

  mkdir -p "$TMP/dkey-relative-target-sandbox"
  for invalid_sensitive_target in \
      './relative-identity' \
      '../traversal-identity' \
      "$TMP//duplicate-separator-identity" \
      "$TMP/path/../parent-traversal-identity"; do
    if (cd "$TMP/dkey-relative-target-sandbox" && \
        DKEY_AGE_IDENTITY_FILE="$invalid_sensitive_target" \
        "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" --force) \
        > "$TMP/dkey-invalid-sensitive-target.out" 2>&1; then
      echo "FAIL: dkey accepted a non-normalized sensitive target: $invalid_sensitive_target" >&2
      exit 1
    fi
    grep -q 'path must be absolute and lexically normalized' "$TMP/dkey-invalid-sensitive-target.out"
  done

  mkdir -p "$TMP/identity-directory-target" "$TMP/identity-symlink-outside"
  if DKEY_AGE_IDENTITY_FILE="$TMP/identity-directory-target" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" --force \
      > "$TMP/dkey-identity-directory.out" 2>&1; then
    echo "FAIL: dkey identity import accepted a directory target" >&2
    exit 1
  fi
  grep -q 'age identity is not a regular file' "$TMP/dkey-identity-directory.out"
  test -z "$(find "$TMP/identity-directory-target" -mindepth 1 -print -quit)"
  ln -s "$TMP/identity-symlink-outside" "$TMP/identity-symlink-target"
  if DKEY_AGE_IDENTITY_FILE="$TMP/identity-symlink-target" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" --force \
      > "$TMP/dkey-identity-symlink-directory.out" 2>&1; then
    echo "FAIL: dkey identity import followed a symlink-to-directory target" >&2
    exit 1
  fi
  grep -q 'age identity must not be symlinked' "$TMP/dkey-identity-symlink-directory.out"
  test -z "$(find "$TMP/identity-symlink-outside" -mindepth 1 -print -quit)"

  mkdir -p "$TMP/sensitive-ancestor-real/nested"
  ln -s "$TMP/sensitive-ancestor-real" "$TMP/sensitive-ancestor-link"
  if DKEY_AGE_IDENTITY_FILE="$TMP/sensitive-ancestor-link/nested/identity.txt" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" --force \
      > "$TMP/dkey-identity-ancestor-symlink.out" 2>&1; then
    echo "FAIL: dkey identity import traversed an outside-HOME ancestor symlink" >&2
    exit 1
  fi
  grep -q 'age identity path contains a symlink' "$TMP/dkey-identity-ancestor-symlink.out"
  test ! -e "$TMP/sensitive-ancestor-real/nested/identity.txt"
  if DKEY_KEYS_FILE="$TMP/sensitive-ancestor-link/nested/keys.env.age" \
      "$HOME/.agents/.dotpanel/bin/dkey" set ANCESTOR_SECRET synthetic \
      > "$TMP/dkey-keys-ancestor-symlink.out" 2>&1; then
    echo "FAIL: dkey set traversed an outside-HOME ancestor symlink" >&2
    exit 1
  fi
  grep -q 'encrypted keys path contains a symlink' "$TMP/dkey-keys-ancestor-symlink.out"
  test ! -e "$TMP/sensitive-ancestor-real/nested/keys.env.age"
  if DKEY_AGE_IDENTITY_FILE="$TMP/sensitive-ancestor-link/nested/identity.txt" \
      "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-ancestor-symlink.out" 2>&1; then
    echo "FAIL: dkey doctor accepted an outside-HOME ancestor symlink" >&2
    exit 1
  fi
  grep -q 'age identity path contains a symlink' "$TMP/dkey-doctor-ancestor-symlink.out"

  mkdir -p "$TMP/keys-directory-target" "$TMP/keys-symlink-outside"
  if DKEY_KEYS_FILE="$TMP/keys-directory-target" \
      "$HOME/.agents/.dotpanel/bin/dkey" set DIRECTORY_SECRET synthetic \
      > "$TMP/dkey-set-directory-target.out" 2>&1; then
    echo "FAIL: dkey set accepted an encrypted-key directory target" >&2
    exit 1
  fi
  grep -q 'encrypted keys is not a regular file' "$TMP/dkey-set-directory-target.out"
  test -z "$(find "$TMP/keys-directory-target" -mindepth 1 -print -quit)"
  ln -s "$TMP/keys-symlink-outside" "$TMP/keys-symlink-target"
  if DKEY_KEYS_FILE="$TMP/keys-symlink-target" \
      "$HOME/.agents/.dotpanel/bin/dkey" set DIRECTORY_SECRET synthetic \
      > "$TMP/dkey-set-symlink-directory.out" 2>&1; then
    echo "FAIL: dkey set followed an encrypted-key symlink-to-directory" >&2
    exit 1
  fi
  grep -q 'encrypted keys must not be symlinked' "$TMP/dkey-set-symlink-directory.out"
  test -z "$(find "$TMP/keys-symlink-outside" -mindepth 1 -print -quit)"

  mkdir -p "$TMP/dkey-identity-race-bin"
  cat > "$TMP/dkey-identity-race-bin/age-keygen" <<'SH'
#!/bin/sh
if [ "${1:-}" = '-y' ]; then
  printf 'intruder identity target\n' > "$DKEY_TEST_IDENTITY_RACE_TARGET"
fi
exec "$DKEY_TEST_REAL_AGE_KEYGEN" "$@"
SH
  chmod +x "$TMP/dkey-identity-race-bin/age-keygen"
  if DKEY_AGE_IDENTITY_FILE="$TMP/raced-identity-target" \
      DKEY_TEST_IDENTITY_RACE_TARGET="$TMP/raced-identity-target" \
      DKEY_TEST_REAL_AGE_KEYGEN="$(command -v age-keygen)" \
      PATH="$TMP/dkey-identity-race-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" \
      > "$TMP/dkey-identity-race.out" 2>&1; then
    echo "FAIL: dkey identity import overwrote a target that appeared during validation" >&2
    exit 1
  fi
  grep -q 'age identity appeared during import' "$TMP/dkey-identity-race.out"
  grep -qxF 'intruder identity target' "$TMP/raced-identity-target"
  test -z "$(find "$TMP" -maxdepth 1 -type f -name '.dkey-identity.*' -print -quit)"
  rm "$TMP/raced-identity-target"
  if DKEY_AGE_IDENTITY_FILE="$TMP/raced-identity-target" \
      DKEY_TEST_IDENTITY_RACE_TARGET="$TMP/raced-identity-target" \
      DKEY_TEST_REAL_AGE_KEYGEN="$(command -v age-keygen)" \
      PATH="$TMP/dkey-identity-race-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$HOME/.config/age/key.txt" --force \
      > "$TMP/dkey-identity-force-race.out" 2>&1; then
    echo "FAIL: dkey --force overwrote an identity target that appeared during validation" >&2
    exit 1
  fi
  grep -q 'age identity appeared during import' "$TMP/dkey-identity-force-race.out"
  grep -qxF 'intruder identity target' "$TMP/raced-identity-target"
  test -z "$(find "$TMP" -maxdepth 1 -type f -name '.dkey-identity.*' -print -quit)"
  rm -rf "$TMP/dkey-identity-race-bin"

  mkdir -p "$TMP/dkey-encrypt-race-bin"
  cat > "$TMP/dkey-encrypt-race-bin/age" <<'SH'
#!/bin/sh
"$DKEY_TEST_REAL_AGE" "$@"
age_status=$?
printf 'intruder encrypted target\n' > "$DKEY_TEST_ENCRYPT_RACE_TARGET"
exit "$age_status"
SH
  chmod +x "$TMP/dkey-encrypt-race-bin/age"
  if DKEY_KEYS_FILE="$TMP/raced-keys-target.age" \
      DKEY_TEST_ENCRYPT_RACE_TARGET="$TMP/raced-keys-target.age" \
      DKEY_TEST_REAL_AGE="$(command -v age)" \
      PATH="$TMP/dkey-encrypt-race-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" set RACE_SECRET synthetic \
      > "$TMP/dkey-encrypt-race.out" 2>&1; then
    echo "FAIL: dkey set overwrote a target that appeared during encryption" >&2
    exit 1
  fi
  grep -q 'encrypted keys target appeared during encryption' "$TMP/dkey-encrypt-race.out"
  grep -qxF 'intruder encrypted target' "$TMP/raced-keys-target.age"
  test -z "$(find "$TMP" -maxdepth 1 -type f -name 'raced-keys-target.age.dkey-encrypt.*' -print -quit)"
  rm -rf "$TMP/dkey-encrypt-race-bin"

  "$HOME/.agents/.dotpanel/bin/dkey" set TEST_SECRET ok
  assert_no_sensitive_dkey_temps
  EDITOR=true "$HOME/.agents/.dotpanel/bin/dkey" edit >/dev/null
  assert_no_sensitive_dkey_temps
  cp "$HOME/.agents/secrets/keys.env.age" "$TMP/keys-before-edit-help.age"
  EDITOR=false "$HOME/.agents/.dotpanel/bin/dkey" edit --help \
      > "$TMP/dkey-edit-help.out"
  grep -qxF 'Usage: dkey edit' "$TMP/dkey-edit-help.out"
  cmp -s "$TMP/keys-before-edit-help.age" "$HOME/.agents/secrets/keys.env.age"
  assert_no_sensitive_dkey_temps
  if EDITOR=false "$HOME/.agents/.dotpanel/bin/dkey" edit unexpected \
      > "$TMP/dkey-edit-argument.out" 2>&1; then
    echo "FAIL: dkey edit accepted an unexpected argument" >&2
    exit 1
  fi
  grep -qxF 'FAIL  usage: dkey edit' "$TMP/dkey-edit-argument.out"
  cmp -s "$TMP/keys-before-edit-help.age" "$HOME/.agents/secrets/keys.env.age"
  assert_no_sensitive_dkey_temps

  ln -s "$HOME/.config/age/key.txt" "$TMP/doctor-identity-link"
  if DKEY_AGE_IDENTITY_FILE="$TMP/doctor-identity-link" \
      "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-identity-link.out" 2>&1; then
    echo "FAIL: dkey doctor accepted a symlinked identity" >&2
    exit 1
  fi
  grep -q 'age identity must not be symlinked' "$TMP/dkey-doctor-identity-link.out"
  rm "$TMP/doctor-identity-link"
  ln -s "$HOME/.agents/secrets/keys.env.age" "$TMP/doctor-keys-link.age"
  if DKEY_KEYS_FILE="$TMP/doctor-keys-link.age" \
      "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-keys-link.out" 2>&1; then
    echo "FAIL: dkey doctor accepted a symlinked encrypted-key file" >&2
    exit 1
  fi
  grep -q 'encrypted keys must not be symlinked' "$TMP/dkey-doctor-keys-link.out"
  rm "$TMP/doctor-keys-link.age"
  cp "$HOME/.config/age/key.txt" "$TMP/doctor-world-readable-identity"
  chmod 644 "$TMP/doctor-world-readable-identity"
  if DKEY_AGE_IDENTITY_FILE="$TMP/doctor-world-readable-identity" \
      "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-identity-mode.out" 2>&1; then
    echo "FAIL: dkey doctor accepted group/other-readable identity permissions" >&2
    exit 1
  fi
  grep -q 'age identity permissions expose group/other access' "$TMP/dkey-doctor-identity-mode.out"

  cp "$HOME/.agents/secrets/keys.env.age" "$TMP/keys-before-failed-encrypt.age"
  mkdir -p "$TMP/dkey-failing-age-bin"
  cat > "$TMP/dkey-failing-age-bin/age" <<'SH'
#!/bin/sh
if [ "${1:-}" = '-d' ]; then
  exec "$DKEY_TEST_REAL_AGE" "$@"
fi
printf 'synthetic partial ciphertext\n'
exit 9
SH
  chmod +x "$TMP/dkey-failing-age-bin/age"
  if DKEY_TEST_REAL_AGE="$(command -v age)" PATH="$TMP/dkey-failing-age-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" set FAILED_SECRET synthetic \
      > "$TMP/dkey-set-encrypt-failure.out" 2>&1; then
    echo "FAIL: dkey set accepted an encryption failure" >&2
    exit 1
  fi
  cmp -s "$TMP/keys-before-failed-encrypt.age" "$HOME/.agents/secrets/keys.env.age"
  assert_no_sensitive_dkey_temps
  rm -rf "$TMP/dkey-failing-age-bin"

  mkdir -p "$TMP/dkey-editor-bin"
  cat > "$TMP/dkey-editor-bin/fail" <<'SH'
#!/bin/sh
printf 'SYNTHETIC_EDITOR_VALUE=discarded\n' >> "$1"
exit 17
SH
  cat > "$TMP/dkey-editor-bin/term" <<'SH'
#!/bin/sh
printf 'SYNTHETIC_EDITOR_VALUE=discarded\n' >> "$1"
kill -TERM "$PPID"
exit 0
SH
  chmod +x "$TMP/dkey-editor-bin/fail" "$TMP/dkey-editor-bin/term"
  cp "$HOME/.agents/secrets/keys.env.age" "$TMP/keys-before-editor-failure.age"
  if EDITOR="$TMP/dkey-editor-bin/fail" "$HOME/.agents/.dotpanel/bin/dkey" edit \
      > "$TMP/dkey-edit-failure.out" 2>&1; then
    echo "FAIL: dkey edit accepted an editor failure" >&2
    exit 1
  fi
  cmp -s "$TMP/keys-before-editor-failure.age" "$HOME/.agents/secrets/keys.env.age"
  assert_no_sensitive_dkey_temps
  if EDITOR="$TMP/dkey-editor-bin/term" "$HOME/.agents/.dotpanel/bin/dkey" edit \
      > "$TMP/dkey-edit-term.out" 2>&1; then
    echo "FAIL: dkey edit continued after TERM" >&2
    exit 1
  else
    dkey_edit_term_status=$?
  fi
  test "$dkey_edit_term_status" -eq 143
  cmp -s "$TMP/keys-before-editor-failure.age" "$HOME/.agents/secrets/keys.env.age"
  assert_no_sensitive_dkey_temps
  rm -rf "$TMP/dkey-editor-bin"

  printf 'original synthetic identity target\n' > "$TMP/imported-age-key.txt"
  printf 'synthetic identity source\n' > "$TMP/import-source.txt"
  cp "$TMP/imported-age-key.txt" "$TMP/imported-age-key-before.txt"
  mkdir -p "$TMP/dkey-identity-bin"
  cat > "$TMP/dkey-identity-bin/age-keygen" <<'SH'
#!/bin/sh
mode="$(stat -f '%Lp' "$2" 2>/dev/null || stat -c '%a' "$2")"
[ "$mode" = '600' ] || exit 88
: > "$DKEY_TEST_IDENTITY_MODE_MARKER"
kill -TERM "$PPID"
exit 0
SH
  chmod +x "$TMP/dkey-identity-bin/age-keygen"
  if DKEY_AGE_IDENTITY_FILE="$TMP/imported-age-key.txt" \
      DKEY_TEST_IDENTITY_MODE_MARKER="$TMP/dkey-identity-mode-ok" \
      PATH="$TMP/dkey-identity-bin:$PATH" \
      "$HOME/.agents/.dotpanel/bin/dkey" identity import "$TMP/import-source.txt" --force \
      > "$TMP/dkey-identity-term.out" 2>&1; then
    echo "FAIL: dkey identity import continued after TERM" >&2
    exit 1
  else
    dkey_identity_term_status=$?
  fi
  test "$dkey_identity_term_status" -eq 143
  test -f "$TMP/dkey-identity-mode-ok"
  cmp -s "$TMP/imported-age-key-before.txt" "$TMP/imported-age-key.txt"
  test -z "$(find "$TMP" -maxdepth 1 -type f -name '.dkey-identity.*' -print -quit)"
  rm -rf "$TMP/dkey-identity-bin"

  "$HOME/.agents/.dotpanel/bin/dkey" list | grep -qx 'TEST_SECRET'
  # shellcheck disable=SC1090
  . "$HOME/.agents/.dotpanel/env.sh"
  _dkey_exports=sentinel
  if dkey on > "$TMP/dkey-on-unscoped.out" 2>&1; then
    echo "FAIL: unscoped dkey on succeeded" >&2
    exit 1
  fi
  grep -q 'unscoped activation is disabled' "$TMP/dkey-on-unscoped.out"
  test -z "${TEST_SECRET:-}"
  test "$_dkey_exports" = "sentinel"

  printf 'TEST_SECRET=ok\n' > "$HOME/.agents/secrets/keys.env"
  recipient="$(age-keygen -y "$HOME/.config/age/key.txt")"
  age -r "$recipient" -o "$HOME/.agents/secrets/keys.env.age" "$HOME/.agents/secrets/keys.env"
  "$HOME/.agents/.dotpanel/bin/dkey" set OTHER_SECRET fine
  printf 'grant:test:TEST_VALUE=TEST_SECRET\ngrant:other:OTHER_VALUE=OTHER_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"
  dkey on --with test
  test "${TEST_VALUE:-}" = "ok"
  if dkey on --with other > "$TMP/dkey-on-already-active.out" 2>&1; then
    echo "FAIL: dkey replaced an already active grant" >&2
    exit 1
  fi
  grep -q 'dkey is already active' "$TMP/dkey-on-already-active.out"
  test "${TEST_VALUE:-}" = "ok"
  test -z "${OTHER_VALUE:-}"
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

  if dkey on --with 't.*' > "$TMP/dkey-on-regex-grant.out" 2>&1; then
    echo "FAIL: regex-like grant name succeeded" >&2
    exit 1
  fi
  grep -q 'invalid grant name' "$TMP/dkey-on-regex-grant.out"
  test -z "${TEST_VALUE:-}"

  printf 'grant:evil:SAFE_VALUE=TEST_SECRET\nextra:evil:BAD-NAME=payload\n' > "$HOME/.agents/secrets/dkey.conf"
  if dkey on --with evil > "$TMP/dkey-on-invalid-env.out" 2>&1; then
    echo "FAIL: invalid grant env name succeeded" >&2
    exit 1
  fi
  grep -q 'invalid key name: BAD-NAME' "$TMP/dkey-on-invalid-env.out"
  test -z "${SAFE_VALUE:-}"
  test "$_dkey_exports" = "sentinel"

  printf 'grant:control:DKEY_ACTIVE_GRANT=TEST_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"
  if dkey on --with control > "$TMP/dkey-on-control-env.out" 2>&1; then
    echo "FAIL: reserved dkey control env name succeeded" >&2
    exit 1
  fi
  grep -q 'reserved grant env name: DKEY_ACTIVE_GRANT' "$TMP/dkey-on-control-env.out"
  test -z "${DKEY_ACTIVE_GRANT:-}"
  printf 'grant:path:SAFE_VALUE=TEST_SECRET\nextra:path:PATH=/tmp/unsafe\n' > "$HOME/.agents/secrets/dkey.conf"
  if dkey on --with path > "$TMP/dkey-on-path-env.out" 2>&1; then
    echo "FAIL: reserved shell control env name succeeded" >&2
    exit 1
  fi
  grep -q 'reserved grant env name: PATH' "$TMP/dkey-on-path-env.out"
  test -z "${SAFE_VALUE:-}"

  readonly READONLY_DKEY_VALUE=original
  printf 'grant:readonly:SAFE_VALUE=TEST_SECRET,READONLY_DKEY_VALUE=TEST_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"
  if dkey on --with readonly > "$TMP/dkey-on-readonly.out" 2>&1; then
    echo "FAIL: dkey wrapper hid an eval failure" >&2
    exit 1
  fi
  test "$READONLY_DKEY_VALUE" = "original"
  test -z "${SAFE_VALUE:-}"
  test "$_dkey_exports" = "sentinel"
  printf 'grant:test:TEST_VALUE=TEST_SECRET\ngrant:other:OTHER_VALUE=OTHER_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"

  (
    printf 'grant:readonly-off:READONLY_OFF_VALUE=TEST_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"
    dkey on --with readonly-off
    test "$READONLY_OFF_VALUE" = "ok"
    readonly READONLY_OFF_VALUE
    if dkey off > "$TMP/dkey-off-readonly.out" 2>&1; then
      echo "FAIL: dkey off hid a readonly-variable failure" >&2
      exit 1
    fi
    test "$READONLY_OFF_VALUE" = "ok"
    test "$DKEY_ACTIVE_GRANT" = "readonly-off"
    case " $DKEY_MANAGED_VARS " in *' READONLY_OFF_VALUE '*) ;; *) exit 1 ;; esac
  )
  (
    DKEY_ACTIVE_GRANT=tampered
    DKEY_MANAGED_VARS=PATH
    path_before="$PATH"
    if dkey off > "$TMP/dkey-off-tampered-control.out" 2>&1; then
      echo "FAIL: dkey off trusted a tampered control variable list" >&2
      exit 1
    fi
    test "$PATH" = "$path_before"
    test "$DKEY_ACTIVE_GRANT" = tampered
    test "$DKEY_MANAGED_VARS" = PATH
  )
  printf 'grant:test:TEST_VALUE=TEST_SECRET\ngrant:other:OTHER_VALUE=OTHER_SECRET\n' > "$HOME/.agents/secrets/dkey.conf"

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
  if "$HOME/.agents/.dotpanel/bin/dkey" reset > "$TMP/dkey-reset-missing.out" 2>&1; then
    echo "FAIL: dkey reset accepted a missing harness" >&2
    exit 1
  fi
  grep -q 'reset requires: claude, codex, or all' "$TMP/dkey-reset-missing.out"

  mkdir -p "$HOME/.claude" "$HOME/.codex"
  cat > "$HOME/.claude/settings.json" <<'JSON'
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "managed-placeholder",
    "ANTHROPIC_BASE_URL": "https://managed.invalid",
    "API_TIMEOUT_MS": "3000000",
    "USER_OWNED_ENV": "keep"
  },
  "user_setting": {"keep": true}
}
JSON
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
model = "model-pro"
review_model = "model-review"
user_setting = "keep"

[model_providers.ok]
name = "Managed"
base_url = "https://managed.invalid/v1"

[model_providers.user_owned]
name = "User Owned"
base_url = "https://user.invalid/v1"

  [user_section]
  model = "keep-inside-indented-table"
  feature = true
TOML
  cat > "$HOME/.codex/auth.json" <<'JSON'
{
  "auth_mode": "apikey",
  "OPENAI_API_KEY": "legacy-placeholder",
  "tokens": {"access_token": "oauth-placeholder"},
  "user_owned": "keep"
}
JSON
  "$HOME/.agents/.dotpanel/bin/dkey" reset all > "$TMP/dkey-reset-all.out"
  jq -e '
    (.env.USER_OWNED_ENV == "keep") and
    (.env.ANTHROPIC_AUTH_TOKEN == null) and
    (.env.ANTHROPIC_BASE_URL == null) and
    (.env.API_TIMEOUT_MS == null) and
    (.user_setting.keep == true)
  ' "$HOME/.claude/settings.json" >/dev/null
  ! grep -q '^model_provider = "ok"$' "$HOME/.codex/config.toml"
  ! grep -q '^model = "model-pro"$' "$HOME/.codex/config.toml"
  ! grep -q '^review_model = "model-review"$' "$HOME/.codex/config.toml"
  ! grep -q '^\[model_providers.ok\]$' "$HOME/.codex/config.toml"
  grep -q '^user_setting = "keep"$' "$HOME/.codex/config.toml"
  grep -q '^\[model_providers.user_owned\]$' "$HOME/.codex/config.toml"
  grep -q '^  \[user_section\]$' "$HOME/.codex/config.toml"
  grep -q '^  model = "keep-inside-indented-table"$' "$HOME/.codex/config.toml"
  jq -e '
    (.auth_mode == null) and
    (.OPENAI_API_KEY == null) and
    (.tokens.access_token == "oauth-placeholder") and
    (.user_owned == "keep")
  ' "$HOME/.codex/auth.json" >/dev/null

  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = 'ok'
model = 'managed-model'
[model_providers.ok] # managed legacy provider
name = "Managed"
TOML
  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder","user_owned":"keep"}\n' > "$HOME/.codex/auth.json"
  "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-single-quoted-provider.out"
  ! grep -q '^model_provider' "$HOME/.codex/config.toml"
  ! grep -q '^\[model_providers.ok\]' "$HOME/.codex/config.toml"
  jq -e '(.auth_mode == null) and (.OPENAI_API_KEY == null) and (.user_owned == "keep")' \
    "$HOME/.codex/auth.json" >/dev/null

  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "user_owned"
model = "user-model"
review_model = "user-review"

[model_providers.ok]
name = "Managed"

[model_providers.user_owned]
name = "User Owned"
TOML
  cat > "$HOME/.codex/auth.json" <<'JSON'
{"auth_mode":"apikey","OPENAI_API_KEY":"user-placeholder","user_owned":"keep"}
JSON
  cp "$HOME/.codex/auth.json" "$TMP/user-owned-auth-before.json"
  "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-user-provider.out"
  grep -q '^model_provider = "user_owned"$' "$HOME/.codex/config.toml"
  grep -q '^model = "user-model"$' "$HOME/.codex/config.toml"
  ! grep -q '^\[model_providers.ok\]$' "$HOME/.codex/config.toml"
  grep -q '^\[model_providers.user_owned\]$' "$HOME/.codex/config.toml"
  cmp -s "$TMP/user-owned-auth-before.json" "$HOME/.codex/auth.json"

  cp "$HOME/.agents/secrets/dkey.providers.json" "$TMP/providers-valid.json"
  jq '.providers = {}' "$TMP/providers-valid.json" > "$HOME/.agents/secrets/dkey.providers.json"
  cp "$HOME/.codex/config.toml" "$TMP/empty-registry-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/empty-registry-auth-before.json"
  "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-empty-registry.out"
  cmp -s "$TMP/empty-registry-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/empty-registry-auth-before.json" "$HOME/.codex/auth.json"
  cp "$TMP/providers-valid.json" "$HOME/.agents/secrets/dkey.providers.json"

  jq '.version = 2' "$TMP/providers-valid.json" > "$HOME/.agents/secrets/dkey.providers.json"
  cp "$HOME/.codex/config.toml" "$TMP/unknown-registry-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/unknown-registry-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-unknown-registry.out" 2>&1; then
    echo "FAIL: dkey reset accepted an unknown providers registry version" >&2
    exit 1
  fi
  grep -q 'providers registry invalid' "$TMP/dkey-reset-unknown-registry.out"
  cmp -s "$TMP/unknown-registry-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/unknown-registry-auth-before.json" "$HOME/.codex/auth.json"
  cp "$TMP/providers-valid.json" "$HOME/.agents/secrets/dkey.providers.json"

  printf '{"env":false,"user_setting":{"keep":true}}\n' > "$HOME/.claude/settings.json"
  cp "$HOME/.claude/settings.json" "$TMP/invalid-settings-before.json"
  cp "$HOME/.codex/config.toml" "$TMP/invalid-settings-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/invalid-settings-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset all > "$TMP/dkey-reset-invalid-settings.out" 2>&1; then
    echo "FAIL: dkey reset accepted a non-object Claude env" >&2
    exit 1
  fi
  grep -q 'Claude settings file is not a JSON object' "$TMP/dkey-reset-invalid-settings.out"
  cmp -s "$TMP/invalid-settings-before.json" "$HOME/.claude/settings.json"
  cmp -s "$TMP/invalid-settings-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/invalid-settings-auth-before.json" "$HOME/.codex/auth.json"

  cat > "$HOME/.claude/settings.json" <<'JSON'
{"env":{"ANTHROPIC_AUTH_TOKEN":"managed-placeholder","USER_OWNED_ENV":"keep"}}
JSON
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
model = "managed-model"
[model_providers.ok]
name = "Managed"
[user_section]
model = "keep"
TOML
  printf '{invalid json\n' > "$HOME/.codex/auth.json"
  cp "$HOME/.claude/settings.json" "$TMP/invalid-auth-settings-before.json"
  cp "$HOME/.codex/config.toml" "$TMP/invalid-auth-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/invalid-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset all > "$TMP/dkey-reset-invalid-auth.out" 2>&1; then
    echo "FAIL: dkey reset accepted invalid Codex auth JSON" >&2
    exit 1
  fi
  grep -q 'Codex auth file is not a JSON object' "$TMP/dkey-reset-invalid-auth.out"
  cmp -s "$TMP/invalid-auth-settings-before.json" "$HOME/.claude/settings.json"
  cmp -s "$TMP/invalid-auth-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/invalid-auth-before.json" "$HOME/.codex/auth.json"
  test -z "$(find "$HOME" -name '*.dkey-reset.*' -print -quit)"

  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder","tokens":{"access_token":"oauth-placeholder"}}\n' > "$HOME/.codex/auth.json"
  cat > "$HOME/.codex/config.toml" <<'TOML'
user_note = """
model_provider = "ok"
This is string content, not a top-level assignment.
"""
model_provider = "user_owned"
[model_providers.ok]
name = "Managed"
TOML
  cp "$HOME/.codex/config.toml" "$TMP/multiline-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/multiline-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-multiline-toml.out" 2>&1; then
    echo "FAIL: dkey reset rewrote a Codex config with multiline TOML" >&2
    exit 1
  fi
  grep -q 'refusing to rewrite Codex config with multiline TOML strings' "$TMP/dkey-reset-multiline-toml.out"
  cmp -s "$TMP/multiline-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/multiline-auth-before.json" "$HOME/.codex/auth.json"
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
[model_providers.ok]
matrix = [
  [1]
]
TOML
  cp "$HOME/.codex/config.toml" "$TMP/nested-array-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/nested-array-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-nested-array.out" 2>&1; then
    echo "FAIL: dkey reset partially rewrote nested TOML arrays" >&2
    exit 1
  fi
  grep -q 'refusing unsupported Codex TOML table/bracket syntax' "$TMP/dkey-reset-nested-array.out"
  cmp -s "$TMP/nested-array-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/nested-array-auth-before.json" "$HOME/.codex/auth.json"
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
model = "managed-model"
model_providers.ok.name = "Managed"
model_providers.ok.base_url = "https://managed.invalid/v1"
TOML
  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder","tokens":{"access_token":"oauth-placeholder"}}\n' > "$HOME/.codex/auth.json"
  cp "$HOME/.codex/config.toml" "$TMP/dotted-provider-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/dotted-provider-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-dotted-provider.out" 2>&1; then
    echo "FAIL: dkey reset partially rewrote dotted provider keys" >&2
    exit 1
  fi
  grep -q 'refusing unsupported Codex TOML table/bracket syntax' "$TMP/dkey-reset-dotted-provider.out"
  cmp -s "$TMP/dotted-provider-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/dotted-provider-auth-before.json" "$HOME/.codex/auth.json"
  for dotted_provider_line in \
      'model_providers . ok . name = "Managed"' \
      '"model_providers".ok.name = "Managed"' \
      "'model_providers'.ok.name = \"Managed\"" \
      '"model\u005fproviders".ok.name = "Managed"'; do
    printf 'model_provider = "ok"\nmodel = "managed-model"\n%s\n' \
      "$dotted_provider_line" > "$HOME/.codex/config.toml"
    printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder"}\n' > "$HOME/.codex/auth.json"
    cp "$HOME/.codex/config.toml" "$TMP/dotted-provider-variant-before.toml"
    cp "$HOME/.codex/auth.json" "$TMP/dotted-provider-variant-auth-before.json"
    if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-dotted-provider-variant.out" 2>&1; then
      echo "FAIL: dkey reset partially rewrote a dotted provider key variant" >&2
      exit 1
    fi
    grep -q 'refusing unsupported Codex TOML table/bracket syntax' "$TMP/dkey-reset-dotted-provider-variant.out"
    cmp -s "$TMP/dotted-provider-variant-before.toml" "$HOME/.codex/config.toml"
    cmp -s "$TMP/dotted-provider-variant-auth-before.json" "$HOME/.codex/auth.json"
  done
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
model = "managed-model"
[model_providers]
ok = { name = "Managed", base_url = "https://managed.invalid/v1" }
TOML
  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder"}\n' > "$HOME/.codex/auth.json"
  cp "$HOME/.codex/config.toml" "$TMP/provider-root-table-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/provider-root-table-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-provider-root-table.out" 2>&1; then
    echo "FAIL: dkey reset partially rewrote a model_providers root table" >&2
    exit 1
  fi
  grep -q 'refusing unsupported Codex TOML table/bracket syntax' "$TMP/dkey-reset-provider-root-table.out"
  cmp -s "$TMP/provider-root-table-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/provider-root-table-auth-before.json" "$HOME/.codex/auth.json"
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "\u006f\u006b"
model = "managed-model"
[model_providers.ok]
name = "Managed"
TOML
  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"legacy-placeholder"}\n' > "$HOME/.codex/auth.json"
  cp "$HOME/.codex/config.toml" "$TMP/escaped-provider-value-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/escaped-provider-value-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-escaped-provider-value.out" 2>&1; then
    echo "FAIL: dkey reset partially rewrote an escaped model_provider value" >&2
    exit 1
  fi
  grep -q 'refusing unsupported Codex TOML table/bracket syntax' "$TMP/dkey-reset-escaped-provider-value.out"
  cmp -s "$TMP/escaped-provider-value-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/escaped-provider-value-auth-before.json" "$HOME/.codex/auth.json"
  cat > "$HOME/.codex/config.toml" <<'TOML'
model_provider = "ok"
model = "managed-model"
[model_providers.ok]
name = "Managed"
[user_section]
model = "keep"
TOML

  jq '.defaults.claude.settings_path = false' "$TMP/providers-valid.json" > "$HOME/.agents/secrets/dkey.providers.json"
  cp "$HOME/.claude/settings.json" "$TMP/invalid-registry-settings-before.json"
  cp "$HOME/.codex/config.toml" "$TMP/invalid-registry-config-before.toml"
  cp "$HOME/.codex/auth.json" "$TMP/invalid-registry-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset all > "$TMP/dkey-reset-invalid-registry.out" 2>&1; then
    echo "FAIL: dkey reset accepted a scalar settings path" >&2
    exit 1
  fi
  grep -q 'providers registry invalid' "$TMP/dkey-reset-invalid-registry.out"
  cmp -s "$TMP/invalid-registry-settings-before.json" "$HOME/.claude/settings.json"
  cmp -s "$TMP/invalid-registry-config-before.toml" "$HOME/.codex/config.toml"
  cmp -s "$TMP/invalid-registry-auth-before.json" "$HOME/.codex/auth.json"
  cp "$TMP/providers-valid.json" "$HOME/.agents/secrets/dkey.providers.json"

  mv "$HOME/.claude/settings.json" "$HOME/.claude/settings.target.json"
  ln -s settings.target.json "$HOME/.claude/settings.json"
  cp "$HOME/.claude/settings.target.json" "$TMP/symlink-settings-target-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset claude > "$TMP/dkey-reset-settings-symlink.out" 2>&1; then
    echo "FAIL: dkey reset replaced a Claude settings symlink" >&2
    exit 1
  fi
  test -L "$HOME/.claude/settings.json"
  test "$(readlink "$HOME/.claude/settings.json")" = 'settings.target.json'
  cmp -s "$TMP/symlink-settings-target-before.json" "$HOME/.claude/settings.target.json"
  rm "$HOME/.claude/settings.json"
  mv "$HOME/.claude/settings.target.json" "$HOME/.claude/settings.json"

  mv "$HOME/.claude" "$TMP/claude-reset-parent-real"
  ln -s "$TMP/claude-reset-parent-real" "$HOME/.claude"
  cp "$TMP/claude-reset-parent-real/settings.json" "$TMP/parent-symlink-settings-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset claude > "$TMP/dkey-reset-settings-parent-symlink.out" 2>&1; then
    echo "FAIL: dkey reset followed a symlinked Claude settings parent" >&2
    exit 1
  fi
  grep -q 'Claude settings path contains a symlink' "$TMP/dkey-reset-settings-parent-symlink.out"
  cmp -s "$TMP/parent-symlink-settings-before.json" "$TMP/claude-reset-parent-real/settings.json"
  rm "$HOME/.claude"
  mv "$TMP/claude-reset-parent-real" "$HOME/.claude"

  mv "$HOME/.codex/config.toml" "$HOME/.codex/config.target.toml"
  ln -s config.target.toml "$HOME/.codex/config.toml"
  cp "$HOME/.codex/config.target.toml" "$TMP/symlink-config-target-before.toml"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-config-symlink.out" 2>&1; then
    echo "FAIL: dkey reset replaced a Codex config symlink" >&2
    exit 1
  fi
  test -L "$HOME/.codex/config.toml"
  test "$(readlink "$HOME/.codex/config.toml")" = 'config.target.toml'
  cmp -s "$TMP/symlink-config-target-before.toml" "$HOME/.codex/config.target.toml"
  rm "$HOME/.codex/config.toml"
  mv "$HOME/.codex/config.target.toml" "$HOME/.codex/config.toml"

  mv "$HOME/.codex/auth.json" "$HOME/.codex/auth.target.json"
  ln -s auth.target.json "$HOME/.codex/auth.json"
  cp "$HOME/.codex/auth.target.json" "$TMP/symlink-auth-target-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-auth-symlink.out" 2>&1; then
    echo "FAIL: dkey reset replaced a Codex auth symlink" >&2
    exit 1
  fi
  test -L "$HOME/.codex/auth.json"
  test "$(readlink "$HOME/.codex/auth.json")" = 'auth.target.json'
  cmp -s "$TMP/symlink-auth-target-before.json" "$HOME/.codex/auth.target.json"
  rm "$HOME/.codex/auth.json"
  mv "$HOME/.codex/auth.target.json" "$HOME/.codex/auth.json"

  mv "$HOME/.codex" "$TMP/codex-reset-parent-real"
  ln -s "$TMP/codex-reset-parent-real" "$HOME/.codex"
  cp "$TMP/codex-reset-parent-real/config.toml" "$TMP/parent-symlink-config-before.toml"
  cp "$TMP/codex-reset-parent-real/auth.json" "$TMP/parent-symlink-auth-before.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" reset codex > "$TMP/dkey-reset-codex-parent-symlink.out" 2>&1; then
    echo "FAIL: dkey reset followed a symlinked Codex config parent" >&2
    exit 1
  fi
  grep -q 'Codex config path contains a symlink' "$TMP/dkey-reset-codex-parent-symlink.out"
  cmp -s "$TMP/parent-symlink-config-before.toml" "$TMP/codex-reset-parent-real/config.toml"
  cmp -s "$TMP/parent-symlink-auth-before.json" "$TMP/codex-reset-parent-real/auth.json"
  rm "$HOME/.codex"
  mv "$TMP/codex-reset-parent-real" "$HOME/.codex"
  test -z "$(find "$HOME" -name '*.dkey-reset.*' -print -quit)"

  printf '{"env":{"ANTHROPIC_AUTH_TOKEN":"managed-placeholder","USER_OWNED_ENV":"keep"}}\n' > "$HOME/.claude/settings.json"
  cp "$HOME/.claude/settings.json" "$TMP/reset-root-race-settings-before.json"
  mkdir -p "$TMP/dkey-root-race-bin"
  cat > "$TMP/dkey-root-race-bin/mktemp" <<'SH'
#!/bin/sh
case "${1:-}" in
  "$HOME/.claude/settings.json.dkey-reset."*)
    if [ ! -e "$DKEY_TEST_SWAP_MARKER" ]; then
      /bin/mv "$HOME/.claude" "$DKEY_TEST_SWAP_SAVED"
      /bin/mkdir -p "$DKEY_TEST_SWAP_OUTSIDE"
      /bin/cp "$DKEY_TEST_SWAP_SAVED/settings.json" "$DKEY_TEST_SWAP_OUTSIDE/settings.json"
      /bin/ln -s "$DKEY_TEST_SWAP_OUTSIDE" "$HOME/.claude"
      : > "$DKEY_TEST_SWAP_MARKER"
    fi
    ;;
esac
exec /usr/bin/mktemp "$@"
SH
  chmod +x "$TMP/dkey-root-race-bin/mktemp"
  export DKEY_TEST_SWAP_SAVED="$TMP/dkey-reset-root-race-saved"
  export DKEY_TEST_SWAP_OUTSIDE="$TMP/dkey-reset-root-race-outside"
  export DKEY_TEST_SWAP_MARKER="$TMP/dkey-reset-root-race-triggered"
  if PATH="$TMP/dkey-root-race-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dkey" reset claude > "$TMP/dkey-reset-root-race.out" 2>&1; then
    echo "FAIL: dkey reset wrote through a root swapped after validation" >&2
    exit 1
  fi
  grep -q 'Claude settings path contains a symlink' "$TMP/dkey-reset-root-race.out"
  cmp -s "$TMP/reset-root-race-settings-before.json" "$DKEY_TEST_SWAP_SAVED/settings.json"
  test -L "$HOME/.claude"
  rm "$HOME/.claude"
  /bin/mv "$DKEY_TEST_SWAP_SAVED" "$HOME/.claude"
  rm -rf "$DKEY_TEST_SWAP_OUTSIDE" "$TMP/dkey-root-race-bin"
  unset DKEY_TEST_SWAP_SAVED DKEY_TEST_SWAP_OUTSIDE DKEY_TEST_SWAP_MARKER

  printf '{"env":{"ANTHROPIC_AUTH_TOKEN":"managed-placeholder"}}\n' > "$HOME/.claude/settings.json"
  mkdir -p "$TMP/dkey-signal-bin"
  cat > "$TMP/dkey-signal-bin/mv" <<'SH'
#!/bin/sh
last=""
for argument in "$@"; do last="$argument"; done
if [ "$last" = "$HOME/.claude/settings.json" ] && [ ! -e "$DKEY_TEST_SIGNAL_MARKER" ]; then
  : > "$DKEY_TEST_SIGNAL_MARKER"
  kill -TERM "$PPID"
  exit 0
fi
exec /bin/mv "$@"
SH
  chmod +x "$TMP/dkey-signal-bin/mv"
  export DKEY_TEST_SIGNAL_MARKER="$TMP/dkey-signal-triggered"
  if PATH="$TMP/dkey-signal-bin:$PATH" "$HOME/.agents/.dotpanel/bin/dkey" reset claude > "$TMP/dkey-reset-signal.out" 2>&1; then
    echo "FAIL: dkey reset continued successfully after TERM" >&2
    exit 1
  fi
  test -f "$DKEY_TEST_SIGNAL_MARKER"
  unset DKEY_TEST_SIGNAL_MARKER
  rm -rf "$TMP/dkey-signal-bin"

  if "$HOME/.agents/.dotpanel/bin/dot" use codex:ok 2> "$TMP/dot-use-removed.err"; then
    exit 1
  fi
  grep -q 'unknown command: use' "$TMP/dot-use-removed.err"
  "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor.out" 2>&1
  grep -q 'providers registry valid' "$TMP/dkey-doctor.out"
  mv "$HOME/.agents/secrets/dkey.conf" "$HOME/.agents/secrets/dkey.conf.saved"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-missing-grants.out" 2>&1; then
    echo "FAIL: dkey doctor accepted a missing grants file" >&2
    exit 1
  fi
  grep -q 'grants file missing' "$TMP/dkey-doctor-missing-grants.out"
  mv "$HOME/.agents/secrets/dkey.conf.saved" "$HOME/.agents/secrets/dkey.conf"
  cp "$HOME/.config/age/key.txt" "$TMP/dkey-doctor-identity-before"
  : > "$HOME/.config/age/key.txt"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-empty-identity.out" 2>&1; then
    echo "FAIL: dkey doctor accepted an empty age identity" >&2
    exit 1
  fi
  grep -q 'age identity invalid' "$TMP/dkey-doctor-empty-identity.out"
  mv "$TMP/dkey-doctor-identity-before" "$HOME/.config/age/key.txt"
  cp "$HOME/.agents/secrets/keys.env.age" "$TMP/dkey-doctor-keys-before.age"
  : > "$HOME/.agents/secrets/keys.env.age"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-empty-keys.out" 2>&1; then
    echo "FAIL: dkey doctor accepted an empty encrypted keys file" >&2
    exit 1
  fi
  grep -q 'keys file is empty or cannot be decrypted' "$TMP/dkey-doctor-empty-keys.out"
  mv "$TMP/dkey-doctor-keys-before.age" "$HOME/.agents/secrets/keys.env.age"
  jq '.version = 2' "$TMP/providers-valid.json" > "$HOME/.agents/secrets/dkey.providers.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-version.out" 2>&1; then
    echo "FAIL: dkey doctor accepted an unsupported registry version" >&2
    exit 1
  fi
  grep -q 'providers registry invalid' "$TMP/dkey-doctor-version.out"
  echo '{"bad": "json"}' > "$HOME/.agents/secrets/dkey.providers.json"
  if "$HOME/.agents/.dotpanel/bin/dkey" doctor > "$TMP/dkey-doctor-invalid.out" 2>&1; then
    exit 1
  fi
  grep -q 'providers registry invalid' "$TMP/dkey-doctor-invalid.out"
fi

echo "OK"
