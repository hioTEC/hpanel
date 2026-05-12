---
layer: 1
owner: <operator-handle>
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
realized_by:
  # - ADR-arch-NNN-<slug>          # filled in as scenario-driven ADRs land
---

# Scenario: <one-line story title — actor + verb + object>

> Layer 1 mental model — <one paragraph: what story this captures, what stage it belongs to, what entry point it anchors>.

## Scenario positioning

<2–4 sentences. Who is the actor? When does this happen (time, context, location)? What is the user-facing entry point? What is the immediate previous step (cross-link the scenario it follows from) and the immediate next step (cross-link the scenario it leads into)?>

This is the <stage>-<sequence> <single | one of N> entry point for <area>. **Not** in scope: <what this scenario explicitly excludes — point at the scenarios that own those flows>.

> Terms below follow [`CONTEXT.md`](../../CONTEXT.md) §Vocabulary; the English form is given in parentheses on first use.

---

## Main flow

```
<step 1: actor action>
        ↓
<step 2: system response>
        ↓
<step 3: state change>
        ↓
…
```

<Replace with an ASCII / Mermaid flow that walks the user's path through the system. Keep it user-perspective, not implementation-perspective.>

---

## What the actor can do (capability list)

### <Sub-step group 1 — e.g. upload>

- **<Capability A>** — <one sentence on what state this changes / what the user sees>
- **<Capability B>** — <…>
- **<Capability C>** — <…>

### <Sub-step group 2 — e.g. review>

- **<Capability D>** — <…>
- **<Capability E>** — <…>

### <Sub-step group 3 — e.g. archive>

- **<Capability F>** — <…>

---

## Visible states / chips / status enums

| Status | Subject | Label | UI hint |
|---|---|---|---|
| `<state-key>` | `<EntityName>` | <user-visible label> | <chip color / weight / required action> |
| `<state-key>` | `<EntityName>` | <user-visible label> | <…> |

---

## Design-principle mapping (per [`charter.md`](../charter.md))

| Principle | This scenario embodies it as |
|---|---|
| #1 <product principle 1> | <how this scenario shows it> |
| #2 <product principle 2> | <how this scenario shows it> |

---

## Edge cases

- **<edge case 1>** → <handling — what the system does, what the user sees>
- **<edge case 2>** → <handling>
  - **Open**: <sub-question that the handling raises>
- **<edge case 3>** → <handling>

---

## Out of scope (cross-links)

- <Out-of-scope topic 1> → [`<other-scenario>.md`](<other-scenario>.md)
- <Implementation detail of step X> → Layer 2 ADR-arch (see `## Decision provenance`) + `src/lib/<domain>/spec.md`
- <Specific technical sub-decision> → Layer 3 ADR-comp (agent decides)

---

## Open product questions

> These are the grill targets. When a commit touches one of these, the
> agent does not self-decide — it asks the operator with one
> recommendation + 1–2 sentences of tradeoff per
> `<DOTPANEL_ROOT>/protocol/rules/scenario-driven-flow.md` Hard Rule #3.

- **<question 1>** — <framing: what the user-facing surface looks like under each plausible answer>
- **<question 2>** — <framing>
- **<question 3>** — <framing>

---

## Decision provenance

> Each row records a Layer-1 product call that shaped this scenario.
> Decisions that landed via a scenario-driven ADR also appear in that
> ADR's frontmatter `governs:` and the ADR's §Scenario Impact
> table — those are the bidirectional links the audit script checks.

| Decision | Date | Decision-maker | Content |
|---|---|---|---|
| <one-line decision> | YYYY-MM-DD | <operator-handle / agent-handle> | <one-paragraph rationale> |

---

## Key product invariants (optional)

> If a decision in `## Decision provenance` produced an invariant the
> implementation must preserve forever (e.g., "AI score is never
> overwritten by teacher score"), surface it here so future ADRs can
> cite it explicitly.

- **<Invariant 1>** — <statement + which decision row it traces back to>
