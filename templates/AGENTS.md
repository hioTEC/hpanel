# User Memspace

`~/.agents/` is the private memspace.
`~/.agents/AGENTS.md` is the entry.

Read this file first. Then read project-local `./.agents/AGENTS.md` when it
exists. Do not recursively scan `~/.agents/` or `./.agents/`; read only entry
files, files they explicitly reference, or files the user names.

## Voice

Describe operator voice, language preferences, and durable artifact language
here.

## Default Posture

- Follow the user's direct instructions first.
- Read before advising. When the real problem sits one layer lower than the
  question, name that lower layer.
- Default ambiguous requests to exploration and decision. Reserve file writes,
  commits, broad scripts, and agent spawning for explicit implementation verbs
  or clear task ownership.

## Read Families

Add routing here as the memspace grows. Start with the family, then lazy-load
only the named files.

Examples:

- skill or slash command -> `skills/README.md`, then the named skill
- service / deploy / secrets / external resource -> `rules/flow-resource-ops.md`
- repeated friction / protocol improvement -> `rules/flow-improve-protocol.md`

## Hard Edges

Follow the user's direct instructions first.

`~/.agents/.dotpanel/` is managed public tooling; do not edit it unless the
task is about dotpanel itself.

`dkey` is privileged. Subagents must refuse any `dkey` invocation or wrapper
known to use it. `dkey on` exports all encrypted keys into the current shell;
prefer grant-scoped forms for resource operations when practical.

Never output secret values in logs or responses.

## Memspace Tooling

`dot init` is bootstrap. Install scripts run it once; day-to-day use should not
need it.

Use `dot set -a` after editing `~/.agents/AGENTS.md` or after pulling memspace
changes. It renders the managed Claude, Codex, and Kimi entry files. Use
`dot set claude`, `dot set codex`, or `dot set kimi` for one harness.

Use `dot sync status`, `dot sync diff`, `dot sync pull`, and `dot sync push` to
move the memspace repo across machines. `dot sync pull` is fast-forward only
and re-renders entries afterward. `dot sync push` stages all non-ignored
memspace changes under `~/.agents`, commits when needed, and pushes.

Use `dkey keygen` once to create the local age identity. Use
`dkey set NAME VALUE` or `dkey set NAME=VALUE` to create or overwrite encrypted
keys, `dkey list` to list key names, `dkey on` to export all keys to the
current shell, and `dkey off` to remove variables set by `dkey on`.

## Layout

- `bin/` — user-owned command wrappers and ops verbs.
- `infra/` — machines, domains, services, desired state, network notes.
- `secrets/` — encrypted or template secret material; no plaintext real keys.
- `rules/` — behavior policy and scenario closure cards.
- `skills/` — optional user-authored skills; lazy load only when relevant.
- `journal/` — cross-session lessons; lazy load only when improving rules or doing retrospectives.
- `reference/` — optional long-form notes; lazy load only when relevant.
- `tools/` — helper libraries, templates, and docs used by `bin/`.
- `.dotpanel/` — managed checkout of the public `dot` / `dkey` tools; gitignored.
