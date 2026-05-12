# Domain Module Shape

> Concrete shape for a `src/lib/<domain>/` library module. Pairs with
> `protocol/rules/module-discipline.md` (the abstract rules) and
> `protocol/reference/scaffolds/domain-spec-template.md` (the spec.md
> template).

## The shape

```
src/lib/<domain>/
  index.<ext>                   # single public entry point — re-exports only
  spec.md                       # interface contract (see scaffold)
  <function-1>.test.ts          # one test file per public business function
  <function-2>.test.ts
  <function-3>.test.ts
  internal/                     # private — only this domain may import from here
    queries.<ext>               # SQL or persistence access
    <adapter>.<ext>             # external-service seam (LLM, payment, OCR, …)
    helpers.<ext>               # internal helpers
  fixtures/                     # test setup
    <test-harness>.<ext>        # e.g. in-memory DB boot + migration apply
    seed.<ext>                  # fixture data
```

## index.<ext> — the public contract

`index.<ext>` is **the only file outside this domain that other code may import from**. It contains exclusively:

1. Public type exports (`Type1`, `Input1`, `<Result>` shapes).
2. Public function exports — the **business functions** the domain offers.
3. Optional re-export of a seam (e.g., `createMockAdapter`) when the seam is used by integration tests outside the domain.

It contains **no business logic itself**. Logic lives in `internal/`.

```ts
// src/lib/<domain>/index.ts
export type Result = { … };
export type Input = { … };

export { businessFunction1 } from "./internal/business-function-1";
export { businessFunction2 } from "./internal/business-function-2";
export { businessFunction3 } from "./internal/business-function-3";

// Optional seam re-export for integration tests:
export { createMockAdapter } from "./internal/adapter";
```

The "single public entry point" rule is what makes the module map check (gate #3 in `ci-hard-gates.md`) tractable: forbidden-import rules apply to one file per domain.

## spec.md — the authoritative interface contract

Lives at `src/lib/<domain>/spec.md`. Template: `protocol/reference/scaffolds/domain-spec-template.md`. Sections:

1. Purpose (what facts this domain resolves; what it is *not*)
2. Public Interface (TypeScript / language signatures, copied verbatim from `index.<ext>`)
3. Adapter / Seam Contract (only if the domain has a replaceable seam)
4. Persistence / Schema Notes (what gets stored, what's derived)
5. Errors (loud-fail policy per workspace.md §3)
6. Transaction Discipline (per-function tx narrative)
7. Critical Invariants (numbered, each pinned by a test file name)
8. Test Fixtures (what the harness boots, what the seed plants)
9. Domain vocabulary (authoritative English definitions; bilingual gloss in `CONTEXT.md` cross-references back here)
10. Forward Notes (deferred work; how the seam absorbs it)

The spec.md is the **single document a reviewer reads to understand what this domain promises**. If the spec disagrees with the code, the spec is wrong (it is the contract; if it's stale, fix it).

## internal/ — private implementation

Files in `internal/` may be imported only from within the same `src/lib/<domain>/` folder. The module map check enforces this.

Common files:

- `queries.<ext>` — DB access. SELECT / INSERT / UPDATE that takes the connection handle and returns typed rows. No business policy lives here.
- `<adapter>.<ext>` — external-service adapter (LLM client, payment SDK, OCR pipeline). Implements the `Adapter` interface defined in `index.<ext>`. Has a sibling mock for tests.
- `<business-function-N>.<ext>` — implementation of one public business function. Composes queries + adapter + policy.
- `helpers.<ext>` — pure utility functions used only inside this domain. If a helper is used by 3+ domains, lift it to `src/lib/_shared/` (project-level shared) or its own micro-domain — apply the deletion test first.

## Tests — one file per public business function

Each public function gets a test file at the domain root: `<function-name>.test.ts`. The file contains:

- ≥ 1 happy-path test (the input shape that the function is built for).
- ≥ 1 error-path test (the loud-fail conditions documented in `spec.md` §Errors).

This is the floor. More tests are encouraged for invariants in `spec.md` §Critical Invariants — each invariant is pinned by a named test that goes red if the invariant breaks.

**Anti-patterns** (caught by domain-shape audit + manual review):

- Test file with `describe.skip` or `it.skip` blocks left in.
- Test file that asserts only on `if (rows.length > 0)` — silent skip when the fixture is empty.
- Test that mocks a private helper (`internal/<file>`) — bad test pressure exposes bad module shape; reshape the test to go through `index.<ext>` instead.

## fixtures/ — test setup

Common pattern for projects with a real DB in tests (recommended over mocking the DB):

- `fixtures/<test-harness>.<ext>` — boots an in-memory or container DB; runs migrations; installs the connection handle as the project's connection singleton via a test-only setter.
- `fixtures/seed.<ext>` — plants the minimum data set each test needs (e.g., one tenant, one user, one of each entity).

Tests do `await harness.boot()` + `await seed.plantBaseline()` and run their assertions against a real persistence layer. This is faster than full E2E (no HTTP) and more honest than DB-mocked unit tests.

## Vocabulary — first-class

`spec.md` §Domain vocabulary contains authoritative English definitions for each term this domain owns. The convention:

- **Noun terms** (entities, types, statuses): authoritative English definition + invariants + `_Avoid_:` list of near-miss terms that mean different things.
- **Verb terms** (actions): subject + side effect + how to distinguish from sibling verbs (e.g., `grade` vs `review` vs `proofread` — each carries a different actor).

`CONTEXT.md`'s bilingual gloss table cross-references the spec.md definition; the spec.md is the single source of truth for the term.

## Cross-domain interfaces

When domain A needs a fact from domain B:

1. Domain A imports a public function from `src/lib/<domain-B>/index.<ext>` (never from `internal/`).
2. The contract is what's in `<domain-B>/spec.md` §Public Interface — return shape, error policy, transaction semantics.
3. If domain A needs to subscribe to events from domain B (e.g., "domain B materializes a row when domain A writes"), the cross-domain edge is documented in **both** spec.md files explicitly. Hidden coupling is the worst kind.

When the cross-domain edge involves write-side coordination (e.g., advisory locks, transactions that span domains), an ADR-arch documents the coordination protocol; both spec.md files cite the ADR.

## When a domain feels wrong

Common symptoms + their fixes:

| Symptom | Likely cause | Fix |
|---|---|---|
| `index.<ext>` exports 15 functions, hard to skim | Domain is doing too many things | Split into two domains by concern; see workspace.md §7 R3 (Progressive Structure) |
| `internal/queries.ts` is 1000 lines | Domain has grown; queries not split by entity | Split into `internal/queries/<entity>.<ext>` files; index.<ext> shape unchanged |
| spec.md disagrees with `index.<ext>` signature | Code drifted; spec is stale | Fix the spec; the contract is the spec, not the code shape |
| A test mocks `internal/` to assert on it | Bad test pressure | Reshape: assert through `index.<ext>` instead, or move what's being tested into a public function |
| Two domains both write the same table | Hidden coupling | One domain owns the table; the other goes through the owner's public functions |
| A "shallow" domain (1–2 public functions, both wrap one query) | Premature seam | Apply the deletion test (workspace.md §7 R5); fold into the caller domain |
