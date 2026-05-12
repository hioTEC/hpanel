# <Project Name>

<One-line product pitch — same as AGENTS.md §0 first sentence.>

> Single context (one file at project root). If a sub-domain ever
> redefines a term (e.g., "Submission" gains a new meaning under a
> stage-3 live-stream feature), lazy-create a sub-`CONTEXT.md` + a root
> `CONTEXT-MAP.md` then.
>
> Maintenance rules:
> 1. Terms are added / removed only when a grill produces a new concept — not in batches.
> 2. **Each new concept is locked with both a <native-language> anchor + an English authoritative definition simultaneously** — "fill in the native-language part later" is rejected.
> 3. When the agent writes code that touches a public-facing identifier (interface name, public type, error class, HTTP path, file name) **not in this table**, it triggers a grill — the agent does not self-name.
> 4. The project's `<context-coverage audit script>` lists public exports not in this file as a CI signal.

## Vocabulary table

> **Bilingual or single-language anchor table.** If the project is
> bilingual (operator speaks one language, code is in another), this is
> the 1:1 arbiter between the two. Each entry is 1–3 lines of gloss;
> the authoritative English definition lives in the owner domain's
> `spec.md` under `## Domain vocabulary`.
>
> **Usage convention** (bilingual case):
> - L1 docs (`charter.md`, `scenarios/*.md`): primary language; **first occurrence of a domain term carries the English in parentheses**, e.g. `<native term>（Question）`; later mentions use the primary language.
> - Code, interfaces, types, error classes, HTTP paths, file names: **English only**, per the owner spec's `## Domain vocabulary`.

### <Domain group A — e.g. Catalog> → [src/lib/<domain-a>/spec.md#domain-vocabulary](src/lib/<domain-a>/spec.md)

| English | <Native> | One-liner |
|---|---|---|
| `<TermA1>` | <native gloss> | <one sentence> |
| `<TermA2>` | <native gloss> | <one sentence> |

### <Domain group B — e.g. Quiz> → [src/lib/<domain-b>/spec.md#domain-vocabulary](src/lib/<domain-b>/spec.md)

| English | <Native> | One-liner |
|---|---|---|
| `<TermB1>` | <native gloss> | <one sentence> |

<Add one section per bounded domain. Within a domain, list both noun
entities (types, tables, aggregates) and verb actions (`grade`,
`review`, `proofread`) — verbs that distinguish actor or stage are
first-class terms.>

#### Status enum convention (if applicable)

<If multiple domains use `pending` / `confirmed` / etc., document the
shared visual atom + per-domain semantic specialization here. Visual
atom (e.g. `<StatusChip>`) lives in shared UI; semantic wrappers (e.g.
`<DomainAStatus>`, `<DomainBStatus>`) bind the enum + i18n per domain.>

### <Domain group C — Auth seam> → [services/auth/spec.md#domain-vocabulary](services/auth/spec.md)

| English | <Native> | One-liner |
|---|---|---|
| `<TermC1>` | <native gloss> | <one sentence> |

> **Identity / FK note** (if applicable): if auth lives behind a service
> seam with its own DB, document here that domain tables' `user_id`
> columns do not carry SQL FOREIGN KEYs to the auth DB — the typing is
> compile-time only; identity consistency is enforced by the auth
> client at request time, not by RDBMS constraint.

## Out of catalog

These are real codebase concepts that **deliberately don't appear** in the glossary because they are general engineering, not project-domain-specific:

- `<Term1>` / `<Term2>` — auth primitives, owned by `<AuthService>`
- `<Term3>` — RBAC primitive
- `<Term4>` — file-handling internals; surface in CONTEXT only when they cross a domain seam
- `<Term5>` — storage-vendor implementation detail; opaque-string at the seam (lives at `src/lib/<domain>/internal/<file>.<ext>`)

## Relationships

<Bullet list of cross-entity relationships in the domain language. Each
bullet names the concrete table / FK / cardinality that backs the
relationship. The reader should be able to draw the entity-relationship
diagram from this section alone.>

- A **<EntityA>** is owned by a **<EntityB>** (`<fk_column>`); access scope = `<scope-enum>` (`<value-1>` / `<value-2>` / `<value-3>`)
- A **<EntityA>** can belong to many **<EntityC>**s (M2M via `<join_table>`)
- A **<EntityD>** is a **<EntityE>** with role `<role>`; **<AuthService>** is the SoT for who-is-who
