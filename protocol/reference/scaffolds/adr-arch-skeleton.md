---
adr: arch-NNN
title: <Title>
status: draft
kind: scenario-driven        # or: infrastructure
created: YYYY-MM-DD
updated: YYYY-MM-DD
authors: [<agent-handle>]    # or: [<operator-handle>] / [<agent-handle>, <operator-handle>]
# decision-makers: [<operator-handle>]   # uncomment when operator picked against agent recommendation
reviewers:
  - <harness-name> (pending)
  - operator (pending sign-off)
# supersedes: ADR-arch-NNN
# amends: ADR-arch-NNN
governs:
  # for kind: scenario-driven —
  - scenarios/<scenario-file>.md
  # for kind: infrastructure — replace the line above with:
  # - all (auth seam)              # or another descriptor of the underwriting surface
related:
  - docs/product/charter.md
  - docs/product/scenarios/<scenario-file>.md
  - CONTEXT.md (<entry the ADR touches>)
---

# ADR-arch-NNN: <Title>

## Status

`draft` — agent is drafting; not yet sent for cross-harness review.

(Once sent: `proposed` — cross-harness pass 1/N; pending operator sign-off.)
(Once accepted: `accepted` — operator signed off YYYY-MM-DD. See `<DOTPANEL_ROOT>/protocol/rules/adr-template.md` §`accepted` checklist for body cleanup.)

## Scenario Impact

> Required. Body shape depends on `kind:`.

**Scenario-driven** form:

| Scenario | Step affected | Before → After |
|---|---|---|
| `<scenario-file>.md` | "<user step in scenario>" | <before state> → <after state> |

**Infrastructure** form (replace the table with a paragraph):

> indirect — <which scenarios depend on this and how. e.g. "supports all scenarios that need authenticated user identity on domain rows; identity consistency contract documented in `CONTEXT.md` Auth seam.">

## Context

<What problem? What constraints? What forces are at play? Cite the prior state — current spec, current schema, current scenario step. If this ADR amends or supersedes another ADR, summarize the prior decision in 2–3 sentences and explain what changed in the world to make this revision necessary.>

## Decision

<What was decided? Be specific — technology, pattern, boundary, policy, naming. If the decision has multiple parts, number them so reviewers can cite them.>

1. <Decision part 1>
2. <Decision part 2>
3. <Decision part 3>

## Options Considered

| Option | Pros | Cons | Why rejected |
|---|---|---|---|
| (a) <option a> | <pro> | <con> | <reason rejected> |
| (b) <option b> | <pro> | <con> | <reason rejected> |
| (c) <option c — selected> | <pro> | <con> | **selected** |

## Consequences

### Positive

- <…>

### Negative

- <…>

### Follow-ups (not in this ADR)

- <Implementation active run that lands the decision>
- <Other ADRs that need to amend or supersede in response>
- <Doc / spec / scenario edits that propagate from this decision>

## Open Questions

- <…>
