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

Keep this entry self-contained at first. Add a route only after its target
exists, and lazy-load only the named files. Link to one source of truth instead
of copying its contents into this entry.

## Hard Edges

Follow the user's direct instructions first.

`~/.agents/.dotpanel/` is managed public tooling; do not edit it unless the
task is about dotpanel itself.

`dkey` is privileged. Subagents must refuse any `dkey` invocation or wrapper
known to use it. Unscoped `dkey on` is disabled. Main-agent credential use
requires `dkey run --with GRANT -- ...`, or `dkey on --with GRANT` only for an
authorized interactive tool. Run `dkey off` before activating another grant.

Never output secret values in logs or responses.

## Memspace Tooling

`dot init` is bootstrap. Install scripts run it once; day-to-day use should not
need it.

Use `dot set -a` after editing `~/.agents/AGENTS.md` or after pulling memspace
changes. It renders the managed Claude, Codex, and Kimi entry files. Use
`dot set claude`, `dot set codex`, or `dot set kimi` for one harness.

Use `dot doctor` for a read-only wiring check (entry wrappers, rendered
plugins, aliases, PATH, dependencies); run it after entry, skill, or routing
changes. Use `dot self status` / `dot self update` to inspect and update the
managed dotpanel checkout itself.

Use `dot sync status`, `dot sync diff`, `dot sync pull`, and `dot sync push` to
move the memspace repo across machines. `dot sync pull` fetches, requires a
clean worktree and a fast-forward path, recursively initializes/updates
submodules, then re-renders entries. `dot sync push` requires a clean worktree
and pushes existing commits only; it never stages or commits files.

Use `dkey keygen` once to create the local age identity. Use
`dkey set NAME VALUE` or `dkey set NAME=VALUE` to create or overwrite encrypted
keys, and `dkey list` to list key names.

Discover grant names with `dkey grants`; it prints each grant and the env vars
it injects, never secret values. Inject credentials with
`dkey run --with GRANT -- COMMAND`. For a non-interactive agent that is the
only functional path — each agent command runs in a fresh shell, so `dkey on`
exports die with the call. Use `dkey on --with GRANT` only for an authorized
interactive shell and `dkey off` to remove what it set. `dkey status` and
`dkey doctor` are read-only health checks.

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
