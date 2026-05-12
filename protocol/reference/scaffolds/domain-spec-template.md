---
status: draft
owner: <operator-handle>
created: YYYY-MM-DD
updated: YYYY-MM-DD
governing_adrs: [arch-NNN, arch-MMM]   # ADR ids that this spec realizes
---

# <domain> — <one-line domain title> Domain

> Functional contract for `src/lib/<domain>/`. **<The single sanctioned
> entry point for X — the most important invariant to preserve.>**
> <One sentence on stage scope: what's shipping now, what's deferred.>

## 1. Purpose

Resolve the facts the <relevant scenario> flow needs:

- "<question 1>" → `<function1>`
- "<question 2>" → `<function2>`
- "<question 3>" → `<function3>`

What this lib is **not**:

- Not a <other-concern> surface. <which lib owns that, why this is a different concern>
- Not a <other-concern> manager. <which event drives that, why this lib stays out>
- Not a re-<verb> surface. <when re-X happens, why this lib has no path for it>

## 2. Public Interface

<Number of business functions>. Anything else is internal.

```ts
// src/lib/<domain>/index.<ext>

export type <Type1> = {
  <field>: <type>;
  <field>: <type>;
};

export type <Input1> = {
  <field>: <type>;
};

export function <function1>(input: <Input1>, ctx: <Context>): Promise<<Type1>>;
export function <function2>(<args>): Promise<<Return>>;
export function <function3>(<args>): Promise<<Return>>;
```

## 3. <Adapter / Seam Contract> (optional — only if domain has a seam)

<Stage-1: interface + deterministic mock. Real adapter lands at task-X.>

```ts
// src/lib/<domain>/internal/<adapter>.<ext> (re-exported via index.<ext>)

export type <Verdict> = { <fields> };
export type <Adapter> = {
  <method>(<args>): <return>;
};
export function <createMockAdapter>(): <Adapter>;
```

Mock behavior:

- `<method>(<args>)`: <deterministic policy>.
- <…>

## 4. <Persistence / Schema Notes> (optional)

<Per-row state, key columns, range constraints, derived fields, snapshot
sources. If a column is sourced from a snapshot table at write time,
state which one and why.>

## 5. Errors

Loud-fail by design (per `<DOTPANEL_ROOT>/protocol/workspace.md` §3 Loud Failures):

- `<function1>` — throws `Error("<domain>: <subject> <id> not found")` when <precondition fails>.
- `<function2>` — throws `Error("<domain>: <constraint violated>")` when <precondition fails>.
- `<read functions>` — never throw on missing data. Empty array / zero-aggregate is the contract.

## 6. Transaction Discipline

| Function | DB writes | Tx? |
|---|---|---|
| `<function1>` | <list of writes> | YES — `<one-tx description>` |
| `<function2>` | <list of writes> | <YES / NO> — <reason> |
| `<read function>` | 1× SELECT | NO (read) |

<Per-function tx narrative: which boundaries the tx covers, what advisory
locks (if any), what the rollback semantics are, idempotency notes.>

## 7. Critical Invariants

1. **<Invariant 1>.** <Statement of what must always hold. Cite the
   spec test (`<test-file>.test.ts`) that pins it.>
2. **<Invariant 2>.** <Statement.>
3. **<Invariant 3>.** <Statement.>

## 8. Test Fixtures

<Test runner + DB harness pattern. List the fixture files and what
each seeds.>

- `<test-fixture-1>` — <what it seeds>
- `<test-fixture-2>` — <what it seeds>

Each test exercises one public function via `index.<ext>`. ≥ 1 happy + ≥ 1 error per function; no `if (count > 0) expect(...)` silent skips.

## Domain vocabulary

> **Realizes scenarios**: `docs/product/scenarios/<scenario-A>.md` (<which step>), `docs/product/scenarios/<scenario-B>.md` (<which step>).
> **Bilingual gloss + cross-domain index**: `CONTEXT.md` §"<domain group>".

Authoritative English definitions for `<domain>`-domain terms. Bilingual
gloss table in `CONTEXT.md` links here for the full shape.

**<TermA>**:
<Authoritative English definition — 2–4 sentences. Anchor on the backing
schema if there is one. State the invariants that hold for this term
(immutability, cardinality, lifecycle).>
_Avoid_: <near-miss term 1> (use only when X), <near-miss term 2> (different domain).

**<verbA>** (verb):
<Authoritative English verb definition. Subject + produces + side
effects. Don't conflate with <near-miss verb>.>
_Avoid_: <near-miss verb 1>, <near-miss verb 2>.

**<EnumName>** (TS type):
`<value-1>` | `<value-2>` | `<value-3>`. Lives in `src/lib/<domain>/`.
<How it renders + i18n key namespace + per-state semantics.>

## 10. Forward Notes

> Things that aren't shipping now but the seam already accommodates.
> Each entry names the trigger, the work shape, and the impact on the
> contract above (usually: none — the seam covers it).

- **<future capability 1>** (<task-id / stage-N>): <description>; the seam (`<adapter interface>`) is stable across that swap.
- **<future capability 2>** (<stage-N>): <description>.
