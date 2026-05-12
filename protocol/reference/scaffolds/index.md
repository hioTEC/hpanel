# Project Scaffolds

> Skeletons for the artifacts a project needs in order to use the
> protocol's full decision flow (scenario → ADR → spec → code) and
> three-layer ownership model.
>
> These are **starting points**, not contracts — copy into a project,
> fill in the placeholders, then evolve. Pairs with
> `protocol/skills/new-project.md`, which walks through which scaffolds
> a new project needs based on shape.

## What's here

| File | Purpose | Layer |
|---|---|---|
| `AGENTS-skeleton.md` | Project root agent entry: intent, decision rights, offload candidates, authority order, conditional context loading, layout, verification, stop rules, ADR conventions, deltas | gateway |
| `CONTEXT-skeleton.md` | Bilingual or single-language vocabulary table; Out of catalog; Relationships | L1 vocabulary anchor |
| `scenario-template.md` | A user-perspective story file (lives at `docs/product/scenarios/<slug>.md`) | L1 |
| `adr-arch-skeleton.md` | A minimal `ADR-arch-NNN-{slug}.md` starter that satisfies the upgraded `adr-template.md` shape | L2 |
| `domain-spec-template.md` | A `src/lib/{domain}/spec.md` interface contract template | L3 |

## Lite vs Full project shapes

Not every project needs the full apparatus. Use this to decide which scaffolds to seed.

| Signal | Lite | Full |
|---|---|---|
| Domain count | 1–2 (single-purpose tool, CLI, single-page app) | 3+ (multi-domain platform) |
| Roles | One actor (operator-only, agent-only) | Multi-role (e.g., teacher / student / admin) |
| Schema migrations | None or one initial | Ongoing migrations across releases |
| Cross-domain interfaces | None — single module | Multiple — bounded contexts with seams |
| ADRs expected over project lifetime | < 5 | 10+ |

**Lite project** seeds: `AGENTS-skeleton.md` (trimmed sections per the skeleton's notes) + `adr-arch-skeleton.md`. No scenarios, no `CONTEXT.md`, no domain specs. Decisions go in a Decision Registry table inside `AGENTS.md` until they outgrow it.

**Full project** seeds: all five scaffolds. The full scenario → ADR → spec → code flow applies. The project ships the audit scripts described in `protocol/reference/ci-hard-gates.md`.

The `protocol/skills/new-project.md` walkthrough resolves Lite vs Full via a small set of grill questions; the operator can override the verdict.

## Conventions used in the skeletons

- `<placeholders-in-angle-brackets>` are fill-in slots.
- `# §0` / `# §1` etc. are stable section anchors — keep them so cross-references in protocol rules continue to resolve.
- All scaffold prose is in English. Operators who work bilingually replace the prose in their preferred language at fill-in time; the section structure stays.
- Scaffolds avoid stack-specific assumptions (no Next.js, no Drizzle, no Postgres). They name *roles* (the schema layer, the test runner, the build tool) and let the project bind specific tools.
