# CI Hard Gates

> The `done = predicate-passed` chain (per `protocol/workspace.md` §2)
> only works if a project ships predicates that machine-enforce its
> invariants. This file describes the **shape** of each gate — what it
> checks, why it matters, and what failure looks like — so a project
> adopting the protocol knows what to build.
>
> Implementations are **project-owned**: the script paths, the build
> tooling, and the precise rules vary by stack. dotpanel does not ship
> the scripts. This file is the contract they fulfil.

## Why hard gates from day 1

A common pattern: ship audits in "advisory mode" first, then promote to
hard-fail later "once we have time to clean up". This pattern fails
because the cleanup never gets prioritized; the advisory mode normalizes
warnings, and warnings become invisible.

Recommended posture: **hard gates from day 1, zero tolerance**. Warnings
are errors. The project starts with the gates passing trivially (empty
codebase) and stays passing on every commit. Adding a new rule mid-life
is allowed, but the cleanup commit lands before the rule flips to
hard-fail.

## The 9 gates

| Gate | Layer | What it checks | Failure mode |
|---|---|---|---|
| 1. Type check | language | Static type errors across the codebase | Type errors block the gate |
| 2. Lint | code style + correctness | Lint rules + custom rules (project-specific) | Any warning blocks the gate (warnings are errors) |
| 3. Module map | architecture | Cross-domain dependency boundaries respected | Forbidden import edge blocks the gate |
| 4. Schema-isolation / table-prefix | data model | Project-owned tables follow the agreed naming policy; cross-product tables aren't accidentally written | Naming violation blocks the gate |
| 5. Migration safety | data model | No destructive SQL without explicit allow-list entry; migrations are idempotent | Unauthorized destructive op blocks the gate |
| 6. Domain shape | architecture | Each `src/lib/<domain>/` has `index.<ext>` + `spec.md` + tests; no orphans | Missing required artifact blocks the gate |
| 7. Scenario ↔ ADR coverage | product / architecture | Bidirectional scenario `realized_by` ↔ ADR `governs`; scenario domain terms ⊂ `CONTEXT.md` | Broken link or unknown term blocks the gate |
| 8. Test | correctness | Project test runner; ≥ 1 happy + ≥ 1 error per public function (per spec) | Any test failure blocks the gate |
| 9. Build | deliverable | Production build succeeds end-to-end | Build error blocks the gate |

## Gate-by-gate detail

### 1. Type check

**Predicate:** the language's static type-checker reports zero errors across the codebase.

**Why:** types are the cheapest check. They catch real bugs (wrong shape, missing field, undefined call) before the test runner even starts.

**Failure example:** a refactor renames a field; one caller is missed; type-check catches it before it hits production.

**Project owns:** the type-checker invocation (`npm run typecheck`, `tsc --noEmit`, `mypy`, `cargo check`, etc.).

### 2. Lint

**Predicate:** project lint rules + custom rules report **zero warnings**. Warnings are treated as errors.

**Why:** a "warning" with no enforcement is invisible. Once the codebase has any warning at HEAD, new warnings hide in the noise. The cure is zero tolerance.

**Custom rules** worth adding once the project has them:

- Forbidden imports (e.g., banned library, banned cross-domain reach-through).
- Required headers / required exports.
- Project-specific patterns (e.g., AI-output fields must surface a "needs review" marker; status enums must use the shared visual atom).

**Failure example:** an agent imports a library that an ADR rejected; the lint rule catches the import; the agent must use the sanctioned seam instead.

**Project owns:** the linter invocation + the custom rules (often as a sibling `eslint-rules/` directory or equivalent).

### 3. Module map

**Predicate:** cross-domain dependency edges respect the declared module boundaries.

**Why:** modules drift apart slowly: a one-time helper import becomes a structural dependency that nobody planned. The map check catches this at the import edge.

**Common shapes:**

- `src/lib/<domain-A>/` may not import from `src/lib/<domain-B>/` except through `<domain-B>/index.<ext>`.
- `src/lib/<domain>/internal/` is private; only the same domain may import it.
- Frontend (`src/components/`) may not reach into the persistence layer (`src/db/`) directly.
- App routes (`src/app/`) may import from `src/lib/`, but `src/lib/` may not import from `src/app/`.

**Tooling:** `dependency-cruiser` for TypeScript / JavaScript; `import-linter` or `pylint` rules for Python; language-equivalent for others. The audit script in the project usually wraps the tool with the project's specific edge declarations.

### 4. Schema-isolation / table-prefix

**Predicate:** all project-owned tables follow the project's naming policy; cross-product tables are not accidentally written.

**Why:** when one DB hosts multiple products (or one product has a clear ownership split between auth tables and domain tables), prefix discipline prevents an agent from accidentally writing to a table it doesn't own.

**Common shapes:**

- All project-owned tables carry a project prefix (e.g. `proj_*`); auth-owned tables (`users`, `sessions`, `accounts`, `verification_tokens`) are off-limits.
- Schema files matching `src/db/schema/*.<ext>` declare tables that match the prefix pattern.
- The prefix appears **only on table names**, not on TypeScript types, function names, route paths, or file names (which use the natural domain term).

**Failure example:** an agent introduces a table without the project prefix; the audit catches it before the migration generates.

### 5. Migration safety

**Predicate:** migrations contain no destructive SQL (`DROP COLUMN`, `DROP TABLE`, `TRUNCATE`, `DELETE FROM`) unless explicitly allowed by an entry in the migration allow-list, with one-line rationale citing the ADR that authorized the destruction. Migrations are idempotent (rerunning produces no change).

**Why:** destructive SQL silently lands data loss in production if it slips through review. An allow-list with mandatory ADR rationale forces deliberation.

**Failure example:** an agent generates `DROP COLUMN status` to clean up a deprecated field; the audit catches it; the agent must add an allow-list entry with `# drop deprecated column per ADR-arch-NNN`.

### 6. Domain shape

**Predicate:** each `src/lib/<domain>/` directory contains the required artifacts:

- `index.<ext>` — single public entry point that re-exports business functions and public types
- `spec.md` — interface contract (per `protocol/reference/domain-module-shape.md`)
- One test file per public function (or per concern) at the directory root
- Optionally `internal/` for private code, `fixtures/` for test setup

**Why:** without this shape, agents (and humans) lose track of which functions are "public business actions" vs. "incidental helpers". The spec.md plus index.<ext> together pin the public contract; lint catches drift.

**Failure example:** a new domain folder lacks `spec.md`; the audit catches it; the agent must write the contract before merging.

### 7. Scenario ↔ ADR coverage

**Predicate:** for every `kind: scenario-driven` ADR, every entry in its `governs:` frontmatter is reciprocated by `realized_by:` in the named scenario. Every domain term that appears inside a scenario file is present in `CONTEXT.md`.

**Why:** the bidirectional link is what makes the scenario-driven flow auditable from either side. Without it, ADRs drift away from scenarios and vice versa.

**Forward-only:** legacy ADRs created before the scenario-driven flow was adopted run in advisory mode; new ADRs hard-fail.

**Failure example:** an ADR claims it governs `scenarios/teacher-flow.md`; that scenario file does not list the ADR in `realized_by:`; the audit catches the asymmetry; the agent fixes the link before the commit lands.

### 8. Test

**Predicate:** the project test runner reports zero failures.

**Project-specific spec rule:** at least one happy-path test + at least one error-path test per public function in each domain. No `if (count > 0) expect(...)` silent skips — a test either runs and asserts, or it is removed.

**Why:** "tests pass" is meaningless if the suite is full of skipped or no-op tests. The per-function happy-plus-error rule is a cheap floor that catches "I wrote a test but it never runs".

### 9. Build

**Predicate:** the production build pipeline succeeds end-to-end.

**Why:** type-check + lint + test cover the source-level invariants, but only a real build catches issues like circular imports under tree-shaking, missing build-time env vars, and bundler config drift. Runs at ship gate, not on every commit (cost vs benefit).

## Advisory audits

These run, but failures are reviewed (not blocked). Their job is to surface drift, not gate it.

| Advisory audit | Purpose |
|---|---|
| Context coverage | Lists public exports not present in `CONTEXT.md`. Reviewer decides per export: cover (add to glossary) or hide (make internal). |
| Depth audit | Lists shallow library modules (1–2-line wrappers, single-use abstractions). Reviewer applies the deletion test (per `protocol/workspace.md` §7 R5). |
| ADR clean | Pre-merge advisory that flags pass-trail residue in an ADR that's about to flip to `accepted` (the §`accepted` checklist in `protocol/rules/adr-template.md`). May also be wired as a hard gate at sign-off time, project's call. |

## Eyes-required (not machine-checkable)

Some predicates are necessarily human-checked. The agent surfaces these explicitly when they apply, rather than silently passing CI.

- **UI / visual changes** → screenshot or E2E evidence + dev-server walk-through.
- **AI-output surfaces** → uncertainty marker (chip, hint, badge) visually confirmed.
- **Cross-product or cross-team interfaces** → second-pair-of-eyes review on the diff before merge.

## Adopting these gates mid-project

If a project doesn't ship all 9 gates yet:

1. **Start with type-check + lint + test + build.** These are stack-standard and have low cost to wire.
2. **Add module map + domain shape next.** They become valuable once the project has 2+ domains.
3. **Add migration safety + schema-isolation when the schema lands.** No point before the first migration.
4. **Add scenario ↔ ADR coverage when the scenario-driven flow is adopted.** Forward-only — legacy ADRs are advisory, new ADRs hard-fail.

The order matters: hard-gating coverage rules before the underlying artifacts exist creates noise. Hard-gate **what's already true** of the codebase, then ratchet.
