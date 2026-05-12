# Three-Layer Collaboration Protocol

> Decisions split into three layers by who owns them. This is the
> decision-rights contract: who must approve, who drafts, where the
> artifact lands, and how a stalled lower-layer escalates upward.
>
> Pairs with `scenario-driven-flow.md` (how a Layer-1 question becomes a
> Layer-2 ADR becomes Layer-3 code) and `adr-template.md` (the artifact
> form for Layer-2 decisions).

## Decision-rights summary

| Layer | Owner | Artifact home | Examples (one-glance scope) |
|---|---|---|---|
| **L1 Mental model** | Operator | `docs/product/charter.md`, `docs/product/design-system.md`, `docs/product/scenarios/*.md` | Product intent, who owns what, ubiquitous-language anchor terms, the visual identity, what scenarios exist |
| **L2 Architecture** | Agent drafts + cross-harness review + operator sign-off | `CONTEXT.md`, `docs/architecture/adr/ADR-arch-NNN-*.md`, `docs/engineering/memory/design-system.md` (living ledger — replaces append-style `ADR-design-NNN-*.md` per Lesson 6 fold), `src/lib/{domain}/spec.md` | Aggregate boundary, schema rebase, cross-domain interface, **first definition of a component public API**, design token additions, dependency / deployment shape |
| **L3 Component** | Agent self-decides (operator may review after the fact) | `.agents/runs/{run-id}/handoff.md` for execution state, `docs/architecture/adr/ADR-comp-NNN-*.md`, `docs/engineering/concerns/{slug}.md` (agent-owned debt records) | Internal column name (under a locked schema), enum value, test fixture shape, share-code length / charset, internal helper shape, ID format, internal CSS class |

`docs/engineering/concerns/{slug}.md` is **L3 by default** — agent records technical debt / followups discovered during implementation. **If the operator surfaces a concern**, the agent first discusses, then decides:

- (a) record as an L3 concern entry with status (`open` / `workaround` / `fixed`), or
- (b) fix it directly and skip the entry.

"Operator-writes / agent-refuses-to-cross" stop traps live in `protocol/workspace.md` §4 + project AGENTS.md §Stop Rules + scenarios — not in `concerns/`.

## Decision flow per layer

### Layer 1 — Mental model (operator owns)

- Open product / scenario / ground questions go to the operator.
- When asking, the agent offers a recommendation with reasoning so the operator reads-and-confirms rather than picks-from-options. (See `protocol/rules/interaction.md` §Be Opinionated.)
- For SaaS-shaped products, the recommendation defaults to **a SaaS-industry standard + 1–2 sentences of tradeoff** — not a blank slate, not an A/B/C ballot.
- Examples: ownership level of a domain entity, how many submission rails exist, how the workspace splits roles.
- Artifact home: `docs/product/charter.md`, `docs/product/design-system.md`, `docs/product/scenarios/*.md`.

### Layer 2 — Architecture (agent drafts + cross-harness review + operator sign-off)

- Agent drafts a proposal.
- Agent runs an **independent harness or backend** review for blind-spot catch (see `adr-template.md` §Status lifecycle for the cross-harness review requirement).
- Agent merges into one consolidated proposal; presents one merged artifact to the operator for sign-off, **not** a debate transcript.
- Examples: aggregate boundary, seam split, subscription model, schema migration shape, cross-domain interface, component first public API.
- Artifact home: `CONTEXT.md` (vocabulary delta), `docs/architecture/adr/ADR-arch-NNN-*.md`, or — for design-system evolution — `docs/engineering/memory/design-system.md` ledger §B (ledger fold pattern per `protocol/reference/docs-shape-anti-patterns.md` Lesson 6; `ADR-design-NNN-*.md` is legacy, retained for cross-project decisions that cross ≥3 non-design domains).

### Layer 3 — Component (agent self-decides)

- Agent decides and records (`ADR-comp-NNN-*.md` or run handoff).
- Operator does not need to be in the loop unless the decision touches Layer 2 or above; if it does, escalate (see "Escalation flow" below).
- Examples: internal column name **under a locked schema**, enum value, test fixture shape, share-code length / charset, internal helper function shape, ID format, internal CSS class.
  - **Schema / public field names that enter migrations or contracts are L2** — they cross interface seams.
  - **Component first public API (props / event / state) is L2**, not L3.
- Artifact home: `.agents/runs/{run-id}/handoff.md` for execution state, `docs/architecture/adr/ADR-comp-NNN-*.md`, `docs/engineering/concerns/{slug}.md`. Durable design belongs in ADR / spec / rules / roadmap; historical evidence files are audit evidence only.

## Escalation flow (the layer model is bidirectional)

When a lower-layer decision keeps producing edge cases, contradicting itself, or feeling forced — the problem is not at that layer. Escalate the **thinking** one level up, step by step (L3 → L2 → L1). Do not skip layers; the intermediate-layer lens often reveals that the issue is solvable without going all the way to product.

- **L3 → L2** — Component implementation cannot cleanly satisfy the requirement, leaks across module boundaries, or contradicts existing architecture. Stop the component work; agent proposes a Layer 2 adjustment (with cross-harness review trace) for operator sign-off, then resumes Layer 3 from the revised architecture.
- **L2 → L1** — Architecture proposal stalls because two valid options both feel wrong, or the choice would force a product-form change. Stop the architecture work; frame the issue as a product question and escalate to the operator.
- **At L1** — Collaborate with the operator to revise the mental model (`docs/product/charter.md` / `docs/product/design-system.md` / `docs/product/scenarios/*.md`). After Layer 1 lands the revision, **re-derive top-down**: re-draft Layer 2 (possibly invalidating prior `ADR-arch-*`), then Layer 3 (possibly invalidating prior `ADR-comp-*`). Do **not** retrofit old lower-layer artifacts to the new Layer 1 — re-derive cleanly from the revised top.

This is the principle that prevents:

- "I'll just hack it at Layer 3 to work around the bad architecture."
- "I'll bend the architecture to avoid asking the operator about product intent."

Both are silent-degradation patterns the layer model exists to surface.

## Layer 3 parallelization via spec-linking

Layer 3 is the most parallelizable layer — each active run touches a bounded surface (one lib domain, one spec.md, one set of tests). When Layer 2 ADRs link explicitly to the specs each delta affects, Layer 3 work can be offloaded for speed.

**Offload candidates** (ranked by independence):

1. Cross-harness CLI agent — strongest independence, has tools (≥ 10 files / ≥ 500 LOC threshold)
2. Cross-backend single-call helper — medium independence, single LLM call (single-file / spec critique / brief)
3. Same-harness sub-agent — weakest independence
4. Human collaborator

**Required handoff artifact:** Layer 2 ADR with explicit per-delta links —

```
spec to follow → src/lib/{domain}/spec.md
files to touch → src/lib/{domain}/internal/queries.ts, src/db/schema/{table}.ts, …
tests to write → src/lib/{domain}/{name}.test.ts
acceptance gate → typecheck + lint + map:check + test pass
```

**Cross-review pass:** a different harness / backend reviews the implementation before the primary agent's final acceptance. Cross-harness > cross-backend > same-backend sub-agent.

**Acceptance gate:** primary agent reads diff, runs full verify chain (typecheck / lint / test / module-map / audits / build), confirms intent matches Layer 2 ADR + Layer 1 scenarios. `ADR-comp-*` records the decision trace from offload → review → acceptance.

This is what unlocks parallel active-run execution — non-overlapping L2 specs ship in parallel. Without spec-linking, all Layer 3 work serializes through the primary author.

**Anti-pattern:** offloading Layer 3 implementation **without** a Layer 2 ADR + spec link → the offloaded worker has no anchor for "what is intended" beyond the diff context. Always require the ADR + spec to exist first.

## Anti-patterns the agent must avoid

- **"A or B?" without a recommendation** — bounces a Layer 1 / Layer 2 decision and wastes a round trip. The agent always recommends one option with reasoning; the operator confirms or overrides.
- **Asking the operator to pick a column name, code length, ID format, test fixture shape** — this is Layer 3, decide and document.
- **Drafting an architecture proposal without a cross-harness independent review pass** — skips the cross-backend independence the protocol relies on.
- **Conflating layers in a single ADR** — one ADR addresses one layer; cross-layer concerns get one ADR per layer linked together.
- **Retrofitting a Layer 2 ADR after Layer 1 changes** — re-derive from the revised top, do not patch downstream.
