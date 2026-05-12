# Work Quality

> Universal quality gate for bug fixes, new features, refactors, docs, UI, data,
> and infrastructure work. Project `AGENTS.md` supplies the concrete commands and
> artifact homes; this file supplies the work-type protocol.

## Purpose

Quality is not owned by an active run. An active run is a resumable execution
lane (state, owner, scope, evidence) at the project layer; it does not define
a software development lifecycle.

Quality is also not owned by `/wrap`. `/wrap` checks that evidence and durable
truth landed in the right place before the session closes.

Every task starts by classifying the work type, naming an acceptance predicate,
then using the project verification sequence to prove the predicate.

## Authority Split

| Layer | Owns | Does not own |
|---|---|---|
| `{{DOTPANEL_ROOT}}/protocol/rules/work-quality.md` | Work-type protocol, acceptance predicate shape, evidence expectations | Repo-specific commands, schema names, product decisions |
| Project `AGENTS.md` | Verification sequence, authority order, project-specific constraints | Global agent behavior |
| active run (repo-local, `{project}/.agents/runs/`) | Resume pointer, workspace/scope, handoff, revision guard | Roadmap, backlog, design truth, quality policy |
| `/wrap` | Evidence check, handoff update, memory/ADR/spec promotion check | Inventing acceptance criteria after the work |

## Task Start Gate

Before implementation, state:

1. Work type: `bug fix`, `new feature`, `refactor`, `docs`, `UI`, `data`, `infra`,
   or `mixed`.
2. Difficulty: `Trivial`, `Feature / Refactor`, or `Architecture / Selection`.
3. Acceptance predicate: a test, command, screenshot, render inspection, diff
   target, smoke flow, or explicit human-review note.
4. Project verification source: usually project `AGENTS.md`.

If the task is mixed, list the primary work type and the additional gates that
apply.

## Work-Type Gates

| Work type | Before change | Required proof |
|---|---|---|
| Bug fix | Reproduce the failure, or record the observed failing command/log/UI state. State one root-cause claim before fixing. | Regression test or failing-path rerun; explain why the same failure cannot recur. |
| New feature | Define user-visible behavior and L1/L2/L3 impact. If interface, schema, auth, deployment, or terminology changes, use the relevant design gate first. | Behavior test through the public interface, route, UI, or documented human-review predicate. |
| Refactor | State the unchanged behavior predicate. For cross-file/interface work, read the module map and list affected modules/callers. | Existing behavior still passes; callers updated; no private-helper tests added to force the old shape. |
| Docs | State the reader outcome and authority level. | Links resolve; stale references updated; no doc claims conflict with accepted ADR/spec/code. |
| UI | Name the user flow and viewport/state to inspect. | Screenshot, E2E, Storybook, or render check; record what still needs the operator's eyes when judgment is visual/product-heavy. |
| Data / persistence | Identify the owning domain and write invariant. | Transactions live in the owning domain; no route/presentation direct DB access; migration/audit command passes where applicable. |
| Infra / deploy | Identify external side effects, rollback path, and environment. | Preflight complete; approved side effect if required; smoke check after mutation. |

## Bug Fix Protocol

Use `{{DOTPANEL_ROOT}}/protocol/skills/investigate.md` when the failure is non-trivial, recurring,
or not locally reproduced yet.

Minimum bar:

1. Observed symptom.
2. Root-cause claim: "X happens when Y, causing Z."
3. Smallest fix that changes the recurrence path.
4. Regression proof.

Do not patch symptoms first and reverse-write a root cause later.

## New Feature Protocol

Minimum bar:

1. Behavior contract: what the user/system can do after the change.
2. Design gate only when the change crosses a stop rule: interface, schema, auth,
   deployment, new dependency, new public term, or architecture selection.
3. One vertical test or inspection through the public surface before broadening.
4. Project verification sequence.

Do not create an active run just because work is a feature. Create one only for
parallel execution, workspace/worktree isolation, or cross-session handoff.

## Refactor Protocol

Minimum bar:

1. Unchanged behavior predicate.
2. Affected modules/callers for cross-file or interface work.
3. Deletion/deepening test when adding an abstraction.
4. Tests through the stable interface, not private helpers.

Refactor quality is proven by preserved behavior plus simpler ownership. File
count, smaller files, or new layers are not proof.

## Data / Persistence Protocol

Persistence is an implementation responsibility of the owning domain unless the
project explicitly defines another architecture.

Default monolith rule:

- Presentation and routes do not import database tables, database clients, or
  domain internals.
- Domain public surfaces own business invariants.
- Domain internals own query shape, row mapping, and transactions.
- Shared repositories are design pressure, not default structure.
- Cross-domain write transactions require an explicit design update before
  implementation.

Project ADRs/specs override these defaults when they intentionally choose a
different architecture.

## Evidence

Every completed task must leave enough evidence for the next agent to avoid
trusting memory:

- commands run and result
- tests or checks added/changed
- screenshots or human-review notes for UI/product judgment
- files or modules touched
- residual risk or skipped validation, with reason

For active runs, write this into the run handoff/manifest. For single-session
work, the final response is enough unless the project requires a durable note.

## Done

Done means:

1. Acceptance predicate passed, or residual risk is explicitly recorded.
2. Project verification sequence was run at the right scope, or the reason for
   not running it is stated.
3. Durable truth moved to the project authority layer: ADR/spec/roadmap/rule,
   not an active-run handoff.
4. No new silent compatibility path, undocumented symlink, or hidden fallback was
   introduced.
