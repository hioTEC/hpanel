---
name: grill-me
description: Interview the user one question at a time, with a recommended answer, until every branch of the design tree is resolved. Use at any plan / new-feature / refactor / upgrade / new-tool moment, when the user says "grill me" / "challenge this" / "I'm not sure", or when an instruction has ≥ 2 reasonable readings. Replaces decision-gate as the alignment process; decision-gate remains the output format.
type: skill
supported_harnesses: [claude, codex, kimi]
depends: [rules/module-discipline.md, skills/decision-gate.md]
---

# Grill Me

> Adapted from Matt Pocock's `productivity/grill-me` skill, integrated with `decision-gate` output format and project-level `CONTEXT.md` discipline.

## When to Trigger

- Plan / new-feature / refactor / upgrade / new-tool moment (same triggers as `decision-gate`)
- User explicitly says: "grill me" / "challenge this" / "interview me" / "I'm not sure" / "stress-test the plan"
- Instruction has ≥ 2 reasonable readings — list them and grill which one
- About to introduce a name / module / concept that's not in `CONTEXT.md`
- Refactor candidate would change a module's **interface** (R2 of `module-discipline.md`)

## Process

### 1. Map the Decision Tree (silent, before first question)

Before asking anything, list (internally) the decision tree:
- What does "done" look like? Which behaviors must the system exhibit?
- What's the module shape? Where's the seam? What's behind it?
- Dependency category (in-process / local-substitutable / remote-owned / true-external — see `module-discipline` R5)
- Which existing modules are touched? (run / read **module map** — R2)
- Which CONTEXT.md terms apply? Any new term needed?
- Trade-offs: what are we explicitly NOT doing?

This is the **silent** part. Do not dump the tree on the user.

### 2. Ask One Question at a Time

For each unresolved branch:

1. **One question per turn.** Never bundle multiple decisions into "do you want A, B, or C?" Each question stands alone.
2. **Provide a recommended answer.** Format: *"D1: <question>. Options: (a) ... (b) ... (c) ... **My recommendation: (b), because <one-line rationale>**."* Never raw multiple choice.
3. **Wait for the answer.** Do not pre-resolve to your recommendation; the user may have local context you don't.
4. **If the question can be answered by reading code** — read the code instead. Don't ask the user to be a lookup table.
5. **If the user's answer surfaces a new branch** — go deeper before going wider. Resolve subtree first, then surface.

### 3. Sharpen CONTEXT.md In-Place

If during grilling the user names a concept that isn't yet in `CONTEXT.md`, or sharpens a fuzzy term:
- Add the term to `CONTEXT.md` immediately (lazy-create the file if it doesn't exist)
- Use the new term in the rest of the grilling
- Do not "save it for later" — terms drift the moment they're used in code without a definition

### 4. Output: Decision Audit Block

When all branches are resolved, write the result to `design.md` in the format from `skills/decision-gate.md`:

```markdown
## Decision Audit

### Conventions Followed
| # | Choice | Why convention |
|---|---|---|
| C1 | ... | ... |

### Decisions — Resolved by Grill
| # | Decision | User's Answer | Rationale |
|---|---|---|---|
| D1 | ... | ... | ... |

### Agent Discretion
| # | Decision | Chosen | Rationale |
|---|---|---|---|
| A1 | ... | ... | ... |
```

The `design.md` stays `draft` until every Decision row has an answer.

## Rules

- **No bundle questions.** "What about A, B, and C?" → ask A, then B, then C.
- **No raw multiple choice.** Every question carries a recommendation. If you genuinely don't know which is better, say so explicitly: *"D2: <question>. Options ... I genuinely don't have a strong preference; here are the trade-offs ..."* — but this is rare and a signal you didn't grill enough background first.
- **No premature implementation.** Do not write code, edit files (other than `CONTEXT.md` term additions), or run side-effecting commands while grilling.
- **Verifiable answers should be verified, not asked.** "Which version of pg are we on?" — grep `package.json`. Don't ask.
- **High-impact decisions get an ADR.** If the answer would be needed by a future architecture review to avoid re-suggesting the same thing, offer: *"Want me to record this as an ADR so future reviews don't re-litigate?"* See `rules/adr-template.md`.

## Anti-Patterns

- "Should I do X or Y?" without a recommendation → you tossed the ball back to the user.
- Asking questions that grep / Read could answer in 30 seconds → wastes the user's time.
- Resolving a branch by yourself silently mid-grill → user can't intervene if you guessed wrong.
- Writing code "just to show you what I mean" before all D rows resolved → leaks unverified assumptions into the codebase.
- Conflating grilling with planning. Grilling = align on what & why. Planning (separate step) = align on how & when.

## Composition with Other Skills

- `decision-gate` → output format. Grill is the process; Decision Audit is its product.
- Module-discipline R4 (vertical TDD) → after grilling resolves *what to test*, TDD does the vertical RED→GREEN loop.

## Example (compressed)

> User: "Refactor the import pipeline to be faster."

```
Agent (silent): map shows 8 modules in src/lib/ingestion/, depth audit
shows 3 shallow ones; CONTEXT.md has "ingestion / extraction / accept"
but not "fast / slow"; user's "faster" is ambiguous.

Agent: D1: "Faster" can mean (a) lower wall-clock per PDF (latency),
(b) higher throughput across batches, (c) cheaper per page (cost).
**Recommendation: (a)** — current concern is teacher waiting on a single
upload. Which one matters most?

User: a.

Agent (silent): "latency" is now a term — add to CONTEXT.md? It's a
generic engineering term, not a domain term — skip CONTEXT.md.

Agent: D2: Latency is dominated by step S1 (OCR ~12s) or S2 (LLM extract ~45s)?
I can grep the timing logs to verify rather than ask. Hold on.
[reads logs]
S2 dominates. So D2 retracted: target is the LLM extract step. D3: ...
```

(continues until all D rows resolved → write Decision Audit block → user
flips design from `draft` to `proposed` → planning phase begins)
