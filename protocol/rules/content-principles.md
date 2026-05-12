---
name: content-principles
description: Rules for where information goes — active runs vs memory vs journal vs handoff vs ADR/spec/roadmap vs concerns.
type: rule
supported_harnesses: [claude, codex, kimi]
---

# Content Principles

Three rules govern where information lives. Confusing these boundaries is the
root cause of most context rot.

## 1. Runtime Is Ephemeral

Runtime records current execution state only. **It is not permanent.**

- **Active runs are repo-local.** Each project owns `{project}/.agents/runs/active.yaml` (manifest) and `{project}/.agents/runs/<id>/handoff.md` (per-run state).
- There is no global cross-repo active-run index. Resume from outside a project means navigating to that project's repo.
- `handoff.md` records dynamic execution state, not design truth.
- Each repo-local run entry has `revision`; each handoff has matching
  `manifest_revision`. Updating run state means writing both together and
  incrementing both. This is the optimistic stale-write guard.
- **Closed runs do not accumulate.** Once a run's durable knowledge has graduated to ADR/spec/rule/roadmap, delete the run directory. See `Run Retirement` below.

Historical `{project}/.agents/evidence/**` folders are evidence from older
execution workflows. Do not expand them into active runs, do not register them
globally, and do not treat them as current authority when they conflict with
ADR/spec/roadmap.

## Run Retirement

Active runs exist only for multi-agent concurrency, workspace/worktree
isolation, and long-task handoff. They are **not** roadmap stages, backlogs,
or durable design homes. Closed runs must be retired, not archived.

**Graduation destinations** — before retiring a run, every piece of its
durable knowledge must already live at one of:

| Knowledge kind | Lives in |
|---|---|
| Architecture / boundary decision | project ADR path (per `{project}/AGENTS.md`) |
| Module contract / public API | `src/{lib,components}/{domain}/spec.md` (or project equivalent) |
| Product sequencing / phase plan | project roadmap path |
| Cross-project methodology | `{{DOTPANEL_ROOT}}/protocol/reference/` or `protocol/rules/` |
| Reusable procedure | `{{DOTPANEL_ROOT}}/protocol/skills/{name}.md` |
| Operational lesson (worth 30+ days) | project journal or central-node journal (per §3) |

**Retirement procedure**:

1. Verify all durable knowledge has graduated (run through the table above).
2. Delete the run directory: `rm -rf {project}/.agents/runs/<id>/`.
3. Remove the entry from `{project}/.agents/runs/active.yaml`.
4. If `runs/` is now empty, delete it too. Do not leave empty scaffolding.

**Default = delete; burden on "why keep"** (Lindy 90-day test). If the operator or any agent has not re-read a closed run / handoff / followup file in 90 days, the doc is dead — retire it. The default action when ambiguous is to delete + rely on git for recovery, NOT to keep "just in case". The "just in case" instinct produces stale state that competes with current authority (see `protocol/reference/docs-shape-anti-patterns.md` Lesson 2 for empirical detail).

**No `archive/` convention.** Do not create `.agents/runs/archive/`,
`docs/archive/`, or any other "archive" directory. Git history preserves
execution detail; archive directories accumulate stale state that competes
with current authority. If you find yourself wanting to keep a closed run
"just in case", that is a signal that knowledge graduation was incomplete.

## 2. Memory Is Truth

Memory records verified facts, not exploration process.

- `{{DOTPANEL_ROOT}}/protocol/reference/` — cross-project truth, methodology, reference.
- Project ground truth lives in the project authority path declared by
  `{project}/AGENTS.md`. Do not assume `{project}/.agents/memory/`; some repos
  keep durable project facts in `docs/`, `CONTEXT.md`, specs, or ADRs.

## 3. Journal Is Curation Staging

Project-scoped journal lives at `{project}/.agents/journal/`. Cross-project journal lives at the operator's designated central-node repo's `.agents/journal/` (the operator picks which repo serves as central node — typically the persona host or another operator-private repo). Persona itself stores no journal. Either way, journal records raw observations for future curation. Agent never reads journal proactively. Never modify old entries. If a past entry was wrong, write a new entry and update the relevant memory/rule.

## Handoff Boundary

`handoff.md` must contain:

- Done
- Next
- Blocked
- Touched / Scope
- Verification / Evidence
- Resume here

It must not contain durable design rationale. Durable decisions move to ADRs,
module specs, project rules, or roadmap.

## Where Does This Go?

```text
Need cross-session or parallel execution?      -> {project}/.agents/runs/{run-id}/handoff.md
                                                  (also add an entry to {project}/.agents/runs/active.yaml)
Blocked right now?                             -> active run handoff.md
Confirmed project-specific issue/debt?         -> project concern/debt path from {project}/AGENTS.md
Architecture or boundary decision?             -> project ADR/spec path from {project}/AGENTS.md
Stable module/component contract?              -> src/lib/{domain}/spec.md or src/components/{domain}/spec.md
Product/phase sequencing?                      -> project roadmap path from {project}/AGENTS.md
Project ground truth (system facts)?           -> project authority path from {project}/AGENTS.md
Cross-project truth or methodology?            -> {{DOTPANEL_ROOT}}/protocol/reference/{topic}.md
Project-level rule (override global)?          -> project rules path from {project}/AGENTS.md
Strategic outline?                             -> project product/charter path from {project}/AGENTS.md
Visual system spec?                            -> project design-system path from {project}/AGENTS.md
Visual implementation tokens?                  -> project design-token artifact from {project}/AGENTS.md
Reusable process?                              -> {{DOTPANEL_ROOT}}/protocol/skills/{name}.md
Project-scoped diary?                          -> {project}/.agents/journal/diaries/YYYY-MM-DD-{topic}.md
Cross-project diary or operator-infra lesson?  -> central-node repo's .agents/journal/diaries/YYYY-MM-DD-{topic}.md
                                                  (operator designates central node in persona)
Temporary thought, unverified?                 -> handoff.md or nowhere
```

## Memory File Types

`type` frontmatter applies only to global cross-project memory.

| type | meaning | when to write |
|---|---|---|
| `principle` | Working principle / behavioral constraint | User explicitly stated or repeatedly corrected |
| `feedback` | One-time correction | After user pointed out an error |
| `project` | Cross-project architectural convention | Rare; prefer project ADR/AGENTS for project-bound decisions |
| `memory` | Reusable concept / methodology | When a session produces reusable cognition |
| `reference` | Operational reference | After a new tool or process is established |

Project-level memory, when a project declares one, is single-semantic ground
truth and does not carry `type`.

## What Not To Record

Do not duplicate content already covered by:

- code
- ADR/spec/rules
- project `AGENTS.md`
- PRODUCT/DESIGN/DESIGN.json
- skills
- source-header ADRs
- current active-run handoff

Exploration process belongs in journal or nowhere.

## Memory Lifecycle

| State | Condition | Action |
|---|---|---|
| Active | Still influencing decisions | Maintain normally |
| Stale | Asserted fact no longer holds | Delete directly; git history preserves it |
| Absorbed | Fully covered by rules/skills/ADR/spec | Delete directly |

No `memory/archive/` directory. If you are unsure whether something is stale,
lower it to handoff/journal first; do not stash it in an archive bucket.

**Default = delete; burden on "why keep"** (Lindy 90-day). Same rule as `Run Retirement` — if no operator or agent has re-read the memory file in 90 days and no rule / skill / ADR cites it, it is dead. Delete + let git preserve. The "I might want to refer to this later" instinct is unreliable because the file invisibly competes with current authority every time someone reads adjacent files. See `protocol/reference/docs-shape-anti-patterns.md` Lesson 2.
