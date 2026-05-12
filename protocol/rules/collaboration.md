# A2A Collaboration

Shared infrastructure, no claiming protocol, no git-lock ceremony.

## Layers & Access

| Layer | Lives in | Read | Write | Notes |
|---|---|---|---|---|
| **protocol** | dotpanel public repo (`{{DOTPANEL_ROOT}}/protocol/`) | everyone (public/fork) | dotpanel maintainers | Universal methodology, skills, rules, reference. Public; pull-request style for outside contributors, direct edit for maintainers. |
| **persona** | the operator's persona host (operator-private) | operator only | operator only | Operator **data**: voice, identity, machine-setup data, keyword-router rules, private reference. No methodology, no program logic, no runtime state — those live in protocol or at the project layer. Each operator owns one persona host; multi-operator teams sharing a machine each have their own. |
| **project `.agents/`** | `{project}/.agents/` | project collaborators | project collaborators | Per-project conventions, run handoffs, decisions, project-scoped memory. Travels with the project repo. |

The privacy boundary is **structural** — different repositories, different audiences, different sync owners — not enforced by lint rules inside one tree.

## Per-Operator Data (Within Persona)

Inside a single operator's persona host, the canonical layout is:

- **Voice:** `{{DOTPANEL_ROOT}}/persona/voice.md` — communication preferences for agents
- **Identity:** `{{DOTPANEL_ROOT}}/persona/identity.yaml` — git config, email, role
- **Rules table:** `{{DOTPANEL_ROOT}}/persona/rules/interaction-triggers.md` — operator-private keyword routing
- **Reference:** `{{DOTPANEL_ROOT}}/persona/reference/` — operator infrastructure descriptions, machine gotchas, private knowledge

Persona has no runtime. Active runs live under each project's `.agents/runs/`. Project-scoped journal entries live under `{project}/.agents/journal/`. Cross-project journal entries live under the operator's designated **central-node repo's** `.agents/journal/` (the operator's persona names which repo serves as central node).

Multi-operator teams sharing one machine: each operator has their own persona host. They do not edit each other's persona files. Cross-operator coordination happens through **project `.agents/`** (the project layer is shared), not through cross-persona writes.

## Per-Project State

- **Repo-local run manifest:** `{project}/.agents/runs/active.yaml` — source of truth for run owner, scope, status
- **Run handoffs:** `{project}/.agents/runs/{run-id}/handoff.md` — self-describing resume pointer; readable with or without dotpanel installed
- **Project memory:** `{project}/.agents/memory/` — project-scoped facts; travels with the project

A project handoff is intentionally self-describing: a fresh collaborator who clones only the project repo can resume without having dotpanel or the operator's persona.

## Rules

1. **Owner decides when.** No deadlines, no standups.
2. **No claiming.** `owner` in the repo-local run manifest is the source of truth. If you need to work on someone else's run, say it in chat.
3. **Shared visibility:** the same repo-local run can be referenced from multiple operators' active-runs indexes (each in their own persona). It still has one owner in the run manifest; use `contributors` for helpers and `handoff_to` for transfer.
4. **Blocked?** Write it in handoff.md. The other picks it up when they can.
5. **Ship when ready.** Push main when it works.
6. **Architecture changes** (skills/rules/workspace.md): discussed openly, direct edit. Public protocol changes go through dotpanel's normal contribution path; private persona changes are operator-internal.

## Touch Scope

When starting work on an active run, note in handoff.md which files/modules you're touching. This lets others spot conflicts without reading your code.

## Stale-Write Guard

Repo-local run manifests are updated with optimistic concurrency. Each run entry has `revision: N`; its handoff frontmatter has `manifest_revision: N`.

Before changing run status, owner, scope, blocker, verification, or `Resume here`, read both values. Write manifest + handoff together and increment both to `N + 1`. If the values differ, or the manifest revision changed since you read it, stop and re-read/merge instead of overwriting.

**High-conflict resources** — flag in handoff.md when modifying:
- `{project}/.agents/runs/active.yaml` (run manifest — source of truth, shared across collaborators)
- Project schema files (e.g., `src/db/schema.ts` — cascading impact)
- Project shared types/constants (`src/lib/shared/` — cross-cutting)
- Project config files (`next.config.ts`, `tailwind.config.ts`, `package.json`)

## Communication

When a proposed change touches shared infrastructure, public interfaces, deployments, credentials, domain/DNS config, or anything others depend on, pause and flag it explicitly. Don't let changes that affect others go through silently.

`/wrap` commits + pushes through the operator's sync tool. That's the sync.
