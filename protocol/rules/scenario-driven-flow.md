# Scenario-Driven Decision Flow

> New product / architecture discussion starts from a **scenario**, not
> from an ADR. Scenarios are the operator-owned mental model (Layer 1);
> ADRs are the agent-drafted decision record (Layer 2); specs are the
> per-domain authoritative interface (Layer 3).
>
> Pairs with `three-layers.md` (decision rights) and `adr-template.md`
> (artifact form, including §Scenario Impact + bidirectional linkage).

## The flow

```
docs/product/scenarios/*.md   →   docs/architecture/adr/ADR-*.md   →   src/lib/{domain}/spec.md   →   implementation
   (L1: user-perspective story)     (L2: decision record, must                (L3: authoritative                (code)
                                     include §Scenario Impact)                 definition + back-ref scenario)
```

- Scenarios are the **product-perspective story**: who does what, in what order, what they see, what state changes — written from the user's viewpoint, in the operator's language.
- ADRs are the **decision record**: which option got picked, what got rejected, what the consequence is. Each ADR `kind: scenario-driven` cites the scenario step(s) it changes; `kind: infrastructure` cites the indirect surface it underwrites.
- Specs are the **per-domain interface contract**: function signatures, transaction discipline, invariants, error shapes, vocabulary. Specs back-reference the scenarios they realize.

## Hard rules

### 1. Agent does not draft an ADR without a scenario anchor

A scenario-driven ADR draft must cite at least one scenario file + the specific step that changes. "We are deciding X about feature Y" is not enough — the agent must point to "this is the step in `scenarios/<file>.md` that this decision changes; before X, after Y".

Infrastructure ADRs (auth seam, schema isolation, table-prefix policy, build / deploy, dependency pinning) are exempt from the per-scenario step citation but must still write a §Scenario Impact paragraph that names the indirect surface (e.g., "supports all scenarios that need authenticated user identity on domain rows").

### 2. Bidirectional link

Every `kind: scenario-driven` ADR has frontmatter `governs: [scenarios/<file>.md, …]`. Each named scenario reciprocates via its own frontmatter `realized_by: [<this ADR id>, …]`. **PR review enforces** the bidirectional link when an ADR / scenario edit lands (no CI audit — `protocol/reference/docs-shape-anti-patterns.md` Lesson 3 covers why mechanizing this drove LLMs to shape-the-doc instead of solve-the-problem).

Infrastructure ADRs do **not** appear in any scenario's `realized_by:` (that would be noise). Their §Scenario Impact paragraph is the trace.

### 3. Open product questions grill — agent recommends, does not ballot

When a commit touches an item under a scenario's `## Open product questions` section, the agent **does not self-decide**. The agent asks the operator, and the question is shaped per `protocol/rules/interaction.md` §Be Opinionated:

- The agent attaches **one recommendation** + 1–2 sentences of tradeoff.
- For SaaS-shaped products, the recommendation defaults to a SaaS-industry standard.
- The agent **does not** pass blank options or A/B/C ballots.
- After the operator accepts / reverses / rewrites the recommendation, the decision is recorded under the scenario's `## Decision provenance` section (or its operator-language equivalent), and any product-invariant addition lands under `## Key product invariants` (likewise), before the implementing commit lands.

### 4. L1 vocabulary soft constraint

Scenarios are operator-language-friendly, but **domain terms** that appear in code or interfaces (e.g., `AnswerSheet`, `Submission`, `Mistake`) must be ⊂ the project's `CONTEXT.md` anchor table. Narrative words (people, time, physical actions, generic verbs) are unconstrained.

PR review enforces the subset relationship between scenario domain terms and `CONTEXT.md` (same rationale as Rule 2 — see `protocol/reference/docs-shape-anti-patterns.md` Lesson 3).

### 5. REQUEST_CHANGES that trace back to a scenario error escalate to L1

When cross-harness review on an ADR comes back with REQUEST_CHANGES, the agent classifies the cause:

- **Issue is in the ADR itself** (technical decision wrong, options missing, constraint misread) → revise ADR, re-enter `proposed`.
- **Issue is in the scenario** (product step framed wrong, vocabulary drift, intent unclear) → **escalate to L1**: revise the scenario / charter / `CONTEXT.md` first, then re-derive the ADR draft cleanly.

Escalating to L1 is not failure — it is the layered model working as intended. Patching the ADR to work around a misframed scenario is the silent-degradation anti-pattern.

## Scenario file shape

A scenario file lives at `docs/product/scenarios/<slug>.md`. Recommended frontmatter:

```yaml
---
layer: 1
owner: operator
status: draft | stable
created: YYYY-MM-DD
updated: YYYY-MM-DD
realized_by:
  - <ADR-id>          # scenario-driven ADRs that govern steps in this scenario
---
```

Recommended sections:

- **Scenario positioning** — one paragraph: who, when, what for. Anchor the user-facing entry point + what is *not* in scope.
- **Main flow** — ASCII / Mermaid / numbered list of the user's path through the system.
- **What the actor can do** — bullet list of capabilities, grouped by sub-step (upload / process / decide / archive).
- **Visible states / chips / status enums** — table of (state, subject, label, UI hint).
- **Design-principle mapping** — how this scenario embodies the project's product principles.
- **Edge cases** — bullet list of "what if X happens"; mark `**Open**` for ones still unresolved.
- **Out of scope** — what this scenario explicitly does *not* cover (with pointers to where it does).
- **Open product questions** — bullet list of unresolved product calls (these are the grill targets per Hard Rule #3).
- **Decision provenance** — table of (decision, date, decision-maker, content) capturing the L1 calls that shaped this scenario.

A scaffold example lives at `protocol/reference/scaffolds/scenario-template.md`.

## When *not* to start with a scenario

- **Pure infrastructure** (auth seam, dependency pinning, build-tool selection, schema isolation, deployment topology) — write a `kind: infrastructure` ADR directly. The §Scenario Impact section names the indirect surface; no scenario file needs to exist.
- **Naming a domain term** — add it to `CONTEXT.md` with the gloss + owner-spec link. No ADR needed unless the term implies a structural decision.
- **Internal-only refactor under a locked interface** — Layer 3, agent self-decides, recorded in `ADR-comp-*` or run handoff.

## Forward-only adoption

A project adopting this flow mid-life leaves legacy ADRs in their original shape. PR review applies the §Scenario Impact + bidirectional link rules to ADRs created on or after the adoption date; legacy ADRs are left as-is. The adoption date is recorded in the project's `AGENTS.md` (project-specific delta section).
