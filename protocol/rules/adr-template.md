# ADR Template

Architecture / data-model / auth / deployment / pricing / design-system decisions — hard to reverse, must be understood by future agents.

Lighter execution decisions stay in a run handoff or in a project's Decision Registry table. Promote to a full ADR when the decision needs a longer life than the current active run.

## Prefix families

ADRs are grouped by **prefix** so the filename signals scope at a glance:

- `ADR-arch-NNN-{slug}.md` — **Layer 2** (architecture, schema, cross-domain interface, deployment, dependency choice). **Must include cross-harness review trace** in frontmatter `reviewers:` (see §Authorship convention below).
- `ADR-comp-NNN-{slug}.md` — **Layer 3** (single-component / single-domain decisions). Agent self-decides; operator reviews after the fact when desired.
- `ADR-design-NNN-{slug}.md` — **legacy** (design system evolution). Prefer fold-into-ledger at `docs/engineering/memory/design-system.md` §B Evolution Log per `protocol/reference/docs-shape-anti-patterns.md` Lesson 6 (ledger-shaped families fold into one living memory doc). Only re-spawn an `ADR-design-*` file when a design decision crosses ≥3 non-design domains (schema + auth + visual together) where its dedicated file genuinely earns space.

Existing un-prefixed `ADR-NNN-{slug}.md` from before this convention may be kept verbatim — the prefix discipline is forward-only.

## Format

```markdown
---
adr: arch-NNN
title: <Title>
status: draft | proposed | accepted | amended | deprecated | superseded
kind: scenario-driven | infrastructure   # see §Scenario Impact below
created: YYYY-MM-DD
updated: YYYY-MM-DD
authors: [agent]                          # or [operator] / [agent, operator]
decision-makers: [operator]               # optional — when operator picked against agent's recommendation
reviewers:
  - <harness/backend> (PASS | REQUEST_CHANGES note)
  - operator (signed-off YYYY-MM-DD | pending sign-off)
amends: <ADR-id>                          # optional
supersedes: <ADR-id>                      # optional
governs:                                  # required
  - scenarios/<scenario-file>.md          # for kind: scenario-driven
  # or
  - all (auth seam)                       # for kind: infrastructure
related:
  - <other ADRs / specs / scenarios>
---

# ADR-{prefix}-{NNN}: {Title}

## Status

`accepted` — operator signed off YYYY-MM-DD

(While in flight, this line carries reviewer state, e.g.
`proposed` — cross-harness pass 1/2 PASS; pending operator sign-off.)

## Scenario Impact

> **Required.** Decisions answer to product scenarios; an ADR must surface
> which scenarios it lands in (`kind: scenario-driven`) or what it
> underwrites for all scenarios (`kind: infrastructure`).

**Scenario-driven** ADRs list affected scenarios + the user-visible step that changes:

| Scenario | Step affected | Before → After |
|---|---|---|
| `<scenario-file>.md` | "user does X" | three rails → single rail |

**Infrastructure** ADRs (auth seam, schema isolation, build/deploy, dependency pinning) name how scenarios depend on the underwriting decision and how:

> indirect — supports all scenarios that need authenticated user identity on
> domain rows; identity consistency contract documented in `CONTEXT.md`
> Auth seam.

## Context

What problem? What constraints? What forces are at play?

## Decision

What was decided? Be specific — technology, pattern, boundary, policy.

## Trade-offs explicitly considered

One short paragraph per rejected alternative, in the form "**(a)** option name — rejected because <one sentence>". Use a full options table only when the comparison axes are themselves load-bearing decision content (rare). Default is paragraph form — exhaustive options tables invite filler "fake alternatives" the agent invents to populate cells, and the rejected variants are recoverable from git anyway.

## Consequences

What becomes easier? What becomes harder? What follow-up work is triggered?

### Positive

-

### Negative

-

### Follow-ups (not in this ADR)

-

## Open Questions

-
```

**Do NOT add** `## Updates Log` — the table accumulates pass-trail process noise that belongs in git log, not the ADR body (per §`accepted` checklist below + `protocol/reference/docs-shape-anti-patterns.md` Lesson 1). Same for `## Pass-N`, `## ADDITIONS`, `## Amendment <N> — <Date>` (append-style amendments — fold revisions into the canonical section instead; see Amendment folding rule below).

## Status lifecycle

ADRs walk a 4-state lifecycle. Each transition has explicit conditions; transitions cannot be skipped.

```
draft  ──(agent finished drafting + scenario anchor exists)──>  proposed
         │
         ↓ cross-harness review (≥ 1 independent harness pass)
         │
         ├─ PASS  ──>  operator sign-off  ──>  accepted
         │
         └─ REQUEST_CHANGES
              ├─ issue in ADR (technical decision wrong, options missing) → back to draft
              └─ issue in L1 (scenario / charter / vocabulary drift)      → escalate to L1, revise scenario / charter / CONTEXT, re-derive ADR draft
```

| State | Meaning | Enters when | Exits when |
|---|---|---|---|
| `draft` | Author working in private | (created) | scenario anchored + frontmatter complete → `proposed` |
| `proposed` | Sent for cross-harness review | from `draft` | reviewer PASS + operator sign-off → `accepted`; REQUEST_CHANGES → back to `draft` or escalate to L1 |
| `accepted` | Operator signed off; this is SoT | reviewer PASS + operator sign-off | revisions go to `amended` / `superseded` / `deprecated` |
| `amended` | In-place revision of an accepted ADR (additions / clarifications, not direction reversal) | edit-in-place + new sign-off date in frontmatter `amendments:` | superseded if the next change reverses direction |
| `deprecated` | Decision no longer applies; not replaced | operator marks deprecated | (terminal) |
| `superseded` | Replaced by a later ADR | new ADR points back via `supersedes:` | (terminal) |

**Hard rules**:

- **Cross-harness review is required.** `draft → proposed` requires at least one **independent harness** pass (different model family or different agent backend). Same-model self-review does not count. Frontmatter `reviewers:` records the full pass history.
- **Operator sign-off is the only path to `accepted`.** Agent does not self-accept.
- **REQUEST_CHANGES has two routes:**
  - Issue in **the ADR itself** (wrong technical call, missing option, bad constraint) → revise ADR, re-enter `proposed` after another review pass.
  - Issue in **Layer 1** (scenario misframed, vocabulary drift, product intent unclear) → escalate to L1, revise scenario / charter / `CONTEXT.md` first, then re-derive ADR draft cleanly. This is not failure — it is the layered model working as intended.
- **`accepted` shape is locked by the §`accepted` checklist below.** Pass-trail noise is collapsed; the accepted ADR reads as a final-decision narrative.

## `accepted` checklist (do at sign-off commit)

When an ADR flips to `accepted` (or `amended`), it should read as the final decision narrative — review history belongs in git log + a collapsed `reviewers:` line, not in the body. **All of the following must be true in the same commit that flips `status:` to `accepted`:**

- [ ] Frontmatter `reviewers:` collapsed to one of:
  - `[<harness> (PASS), operator (signed-off YYYY-MM-DD)]`
  - `[operator (signed-off YYYY-MM-DD) — pre-cross-harness-review era]` (legacy ADRs only)
- [ ] `## Status` reduced to a single line: `` `accepted` — operator signed off YYYY-MM-DD `` (or `` `amended` — operator signed off YYYY-MM-DD `` with `amendments:` listed in frontmatter).
- [ ] `## Decision` and other body sections stripped of inline pass-trail notes (`(pass-1 #N)`, `(revised: pass-2 …)`, `Pass-2 closed …`).
- [ ] No `## … Pass-N …` or `## … ADDITIONS` section headers remain.
- [ ] `## Updates Log` table absent (git log is the audit trail; the table should never have been written — see §Format scaffolding "Do NOT add" note).
- [ ] No top-of-file meta banners like `v4-final — pass-4 residual cleanup`.
- [ ] PR reviewer confirmed the above checklist (no CI script; see §Project tooling for the rationale).

## Amendment folding (do not append; fold)

When an `accepted` ADR is revised, fold the new state into the canonical section — do NOT add a `## Amendment N — <Date>` section at the bottom listing what changed (reader would have to mentally diff to know current state).

- Edit the relevant `## Decision` subsection in place to reflect the new state.
- Frontmatter `status: accepted → amended`; frontmatter `amendments:` lists `"<N> (YYYY-MM-DD): <1-line summary>"` per amendment.
- If the amendment **reversed** a prior decision (e.g., snapshot semantics flipped to live-ref), put a 1-line note in the section title so a reader bumping into stale references can locate the flip: `### 3. New table hm_X (live-ref; original snapshot model flipped YYYY-MM-DD per QN)`. Older state lives in git.

See `protocol/reference/docs-shape-anti-patterns.md` Lesson 5 for the rationale + HioMATH evidence (~10 Amendment folds in task-22; each compressed ~30-50 line "old + amendment" pair into ~15-25 lines of final-state).

## Scenario Impact discipline

ADRs that govern user-visible behaviour ground in product scenarios — discussion starts from `docs/product/scenarios/*.md`, decision lands in ADR, traceability runs both ways.

- `kind: scenario-driven` — ADR changes a step inside one or more scenarios. Frontmatter `governs:` lists the scenario file(s); body §Scenario Impact has the per-scenario before/after table. The scenario(s) listed here must reciprocate via their own frontmatter `realized_by: [<this ADR id>]`.
- `kind: infrastructure` — ADR underwrites a cross-cutting capability (auth seam, schema isolation, build / deploy, dependency pinning). Frontmatter `governs:` may say `all` or name the indirect dependency surface; body §Scenario Impact says how scenarios depend on it indirectly. Scenario `realized_by:` does **not** include infrastructure ADRs (would be noise).
- Skipping §Scenario Impact for any new ADR is rejected at sign-off (PR review enforces, not CI; see §Project tooling).

**Forward-only**: legacy ADRs created before this convention keep their current shape; PR review for new ADRs (created on or after the convention's adoption date in the project's `AGENTS.md`) confirms §Scenario Impact + bidirectional reciprocation are present.

## Authorship convention

- `authors: [agent]` — agent drafted, or operator default-authorized agent to decide.
- `authors: [operator]` or `authors: [agent, operator]` — operator co-authored.
- `decision-makers: [operator]` — explicitly use this when the operator decided against the agent's recommendation, or when a Layer 1 question got resolved by the operator.
- `reviewers:` field tracks the cross-harness / cross-backend / operator review trace:

```yaml
reviewers:
  - <harness-A> (3 passes; pass-1 REQUEST_CHANGES on X; pass-2 REQUEST_CHANGES on Y; pass-3 PASS)
  - operator (signed-off 2026-MM-DD)
```

Once accepted, the reviewers line collapses (see §`accepted` checklist) to:

```yaml
reviewers: [<harness-A> (PASS), operator (signed-off 2026-MM-DD)]
```

## Storage + numbering

- Active: `<project>/docs/architecture/adr/ADR-{prefix}-{NNN}-{slug}.md`
- Deprecated / superseded: keep file in place; update `status:` and add the pointer in frontmatter (`superseded-by: ADR-{prefix}-{NNN}` or body §Status note).
- Numbering is sequential **within each prefix family**. Check existing files before assigning.
- The project's Decision Registry table (in `DESIGN.md` or equivalent) links to ADRs by full filename.

## When to write an ADR vs use the Decision Registry table

| Criterion | Decision Registry table | Full ADR |
|---|---|---|
| Affects single domain | ✓ | — |
| Affects multiple domains or whole project | — | ✓ |
| Reversible in < 1 day | ✓ | — |
| Hard to reverse (schema, auth model, infra, brand color) | — | ✓ |
| Uncontroversial, one obvious choice | ✓ | — |
| Has cost, security, compliance, accessibility implications | — | ✓ |
| Useful only during implementation | ✓ | — |
| Must be referenced by future active runs / ADRs | — | ✓ |

## Project tooling

**Doc-shape audits are an anti-pattern** — see `protocol/reference/docs-shape-anti-patterns.md` for the empirical lesson. The §`accepted` checklist, the §Scenario Impact bidirectional link, and the frontmatter integrity rules below are **enforced at PR review**, not via a CI script.

What belongs in a project's CI (per `protocol/reference/ci-hard-gates.md`): behaviour invariants — table prefix, destructive migration safety, domain shape (every lib has `index.ts` + `spec.md` + tests), dependency-cruiser cross-domain rules, context-coverage advisory. Each of these catches a real failure mode a PR reviewer can miss.

What does NOT belong in CI: ADR body has no `## Updates Log`; scenario `realized_by:` reciprocates ADR `governs:`; spec.md has a `## Domain vocabulary` section. These trigger LLMs to spend cycles shaping the doc to pass the checker rather than solving the problem; they have been tried and retired.

If a future shape rule feels worth mechanizing, re-read `docs-shape-anti-patterns.md` first. Almost always the right move is to simplify the rule (so it doesn't need a checker) rather than write the checker.

## Active-run ↔ ADR linkage

Each active run names the ADR(s) it implements via `realizes_adrs:` in `active.yaml` (see `protocol/rules/active-run.md` §2). This closes the loop: ADR captures the decision; active run captures the implementation; the linkage lets either side be audited from the other.
