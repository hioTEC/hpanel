# Docs Shape Anti-Patterns

> Cross-project methodology — what *not* to do when shaping ADRs / specs / handoffs / memory. Distilled from HioMATH `task-22-docs-consolidation` (2026-05-11, 11 commits, ~3600 net lines deleted, 14 ADRs surviving from ~22 originals).
>
> If a new project finds itself instituting one of these patterns, treat this doc as the back-pressure — the pattern was tried and retired for the reasons below.

## TL;DR

| Anti-pattern | Why it fails | Replace with |
|---|---|---|
| Doc-shape CI audits | LLMs spend cycles shaping the doc to pass the audit, not solving the problem | PR review for shape; CI only for behaviour invariants |
| Process lineage at decision fidelity | "Pass-1 REQUEST_CHANGES; commit-2 closed P1×9; pass-2 …" accumulates in body | Process → git log; body presents final-state decision narrative only |
| Amendment as "old + change log" | Reader must mentally diff old + amendment to know current state | Fold amendments into the canonical section; preserve flip lineage in a 1-line title note when reversal happened |
| Spec-shaped audit drives doc creation | Agent writes `## Domain vocabulary` section just to pass `audit-spec-shape`; content is filler | Default-no docs; write only when a real consumer needs it |
| Default-keep on stale execution evidence | `.agents/evidence/task-N/` accumulates after task closes; competes with current authority | Default-delete after graduation; Lindy 90-day test (no re-read in 90 days = retire) |
| Bidirectional reciprocation enforced by script | Symmetric `governs:` ↔ `realized_by:` link drift gets re-checked every commit | PR review confirms when the ADR / scenario edit lands |
| Drift-status as persisted state | "this spec is N revisions behind ADR-X" lives in spec frontmatter | Drift is derived from `proposed` ADR + `supersedes:` list; `grep "status: proposed"` answers in 2 seconds |

## The 7 Lessons

### 1. Decision lineage vs process lineage are different fidelity classes

**Decision lineage** is small and durable: "we picked PG over Mongo because X". Worth keeping verbatim. Rereadable indefinitely. Belongs in ADR body + frontmatter.

**Process lineage** is large and ephemeral: pass-1/2/3 review trail, "considered A then B then C with operator", REQUEST_CHANGES rebuttals, commit-level revision notes. Worth zero in the curated doc; worth full audit detail in git.

The original sin: storing both at the same fidelity. The ADR body grows to 1000+ lines as pass narratives accumulate; the decision becomes unreadable inside the process noise.

**Rule**: ADR `## Decision` reads as a final narrative. Pass trail belongs in git log + frontmatter `reviewers:` collapsed line. No `## Updates Log` section, no `(per codex pass-2)` inline citations, no `## ADDITIONS` headers, no `v4-final` meta-banners.

### 2. Lindy 90-day default

If no one has re-read a doc in 90 days, it is dead. **Default-do-not-preserve.** Burden of proof on "why keep", not "why delete".

Applies to:

- `.agents/evidence/task-N/` after the task closes
- `.agents/runs/<id>/` after `handoff.md` graduates durable knowledge to ADR / spec / rule / roadmap
- `docs/engineering/concerns/<slug>.md` after `status: fixed` or after the concern's framing is invalidated by an ADR
- Older active.yaml entries whose runs are closed
- Project-specific TODO / followup docs whose contents have all shipped or been re-tracked elsewhere

If the doc is genuinely re-read (operator opens it; agent cites it in a recent commit; CI grep'd it), the 90-day clock resets. If not, default to delete on next pass — git preserves it for recovery.

### 3. CI for behaviour = good; CI for doc shape = bad

**Behaviour invariants** belong in CI (hard-fail blocks PR):

- table prefix check (wrong prefix → query routing breaks)
- destructive migration check (DROP TABLE without allowlist → staging data loss)
- domain shape check (missing `index.ts` → module seam broken)
- dependency-cruiser cross-domain check (illegal import → coupling)
- context coverage / depth audit / lint-rule etc.

**Doc shape rules** belong at PR review (human enforces, no CI):

- ADR has §Scenario Impact section
- ADR `status: accepted` ⇒ no `## Updates Log` section
- spec.md has `## Domain vocabulary` section
- scenario `realized_by:` ↔ ADR `governs:` reciprocate
- ADR body has no pass-trail noise

The cost of CI for doc shape: LLM cycles spent satisfying the checker rather than solving the underlying problem. Agent re-runs the audit after each ADR edit. Agent adds a `## Domain vocabulary` heading because the audit expects it, even when the term list adds no information. Agent gets a false sense of completeness when the audit passes. The value (catching a typo a PR reviewer would catch anyway) is dwarfed by the cost.

**HioMATH evidence**: 4 doc-policing audits (`audit-adr-clean`, `audit-adr-status`, `audit-spec-shape`, `audit-scenario-adr-coverage`) retired 2026-05-11 after 1-2 months in service. ~1100 lines of script removed. No regressions surfaced in subsequent PR reviews.

### 4. Three layers of "system-thinking anchors" is enough

A new agent reading a project should be able to reconstruct the mental model from:

- `CONTEXT.md` — ubiquitous-language vocabulary, one-line gloss per domain term
- `docs/index.md` + `docs/product/charter.md` — what the system is for, what shape it has
- `docs/product/scenarios/<file>.md` — Layer 1 user-perspective stories
- `src/lib/<domain>/spec.md` — Layer 3 per-domain interface contract

Everything else is derivative. If a doc is not in this list and not directly cited by one of these layers, it is likely process residue.

Avoid: pre-emptive per-feature docs, parallel "design docs" that mirror specs, "explanation" docs that summarize what code already says, "audit" reports that re-run an analysis the agent can perform on demand.

### 5. Amendment as fold, not as appendix

When an `accepted` ADR is revised, two patterns are possible:

- **Fold (do this)**: edit the canonical section to reflect the new state; frontmatter `amendments:` lists the date + 1-line summary; `status: accepted → amended`. The body reads as if the amended state was the original decision. If the amendment *reversed* a prior decision (e.g., snapshot → live-ref), put a 1-line note in the section title so a reader bumping into stale references can locate the flip. Older state belongs in git.
- **Appendix (do not do)**: leave the original section unchanged; add `## Amendment 1 — <Date>` section listing what changed. Reader must mentally diff to know current state.

The fold pattern was used in HioMATH task-22 across ~10 Amendment subsections (Q1/Q8/Q9/Q10/Q12 in arch-009 + Amendment 1 in arch-006 + Amendment 1 in arch-011). Each fold compressed ~30-50 lines of "old + amendment" into ~15-25 lines of "final-state with optional 1-line flip note".

### 6. Ledger-shaped ADRs fold into a single living ledger

If a family of ADRs is structurally "one entry in a chronological log" — each new entry adds a token, a chip, a rule clarification on top of the prior shape — they are not cross-cutting decisions, they are a ledger. Fold the family into a single living memory doc.

HioMATH evidence: `ADR-design-001` through `ADR-design-007` (7 ADRs, ~1580 lines, all design-system evolution entries) folded into `docs/engineering/memory/design-system.md` as one living ledger. 57 references across 18 files bulk-renamed from `ADR-design-NNN` to `design-system memory ledger`. Project-wide cognitive load dropped.

Sister rule: cross-cutting architecture ADRs are NOT ledger-shaped (each is a real decision affecting multiple domains). Those shrink rather than fold (per Lesson 5).

### 7. Reverse experiment — try the task without the scaffolding

When the project is heavy on `design.md` / `handoff.md` / `follow-ups.md` / `commit-N-draft.md` / per-stream scope spec, the assumption is "these scaffolds aid execution". Test the assumption: do a small task **without** any of those scaffolds. Just code + git commit + a short PR description.

What's actually lost? If nothing (the task ships, review catches what it would have caught anyway), the scaffolds were process tax masquerading as discipline. If something real (review missed a constraint that the scaffold would have surfaced), the scaffold has a legitimate role — but probably a narrower one than its current footprint suggests.

This experiment is hard to run because the scaffold-writing habit is sticky and feels productive. The result is usually that 60-80% of the scaffold can be deleted without functional loss.

## Related

- `protocol/rules/content-principles.md` — where information goes; complements this doc with the routing rules
- `protocol/rules/active-run.md` — run lifecycle, including retirement (Lesson 2 in practice)
- `protocol/rules/adr-template.md` — ADR shape (Lesson 1 + 5 in practice)
- `protocol/rules/scenario-driven-flow.md` — bidirectional link rule (Lesson 3: enforced at PR review, not CI)

## When NOT to apply these lessons

- **First few months of a new project** when shape is genuinely unstable. Some early process noise is unavoidable while the team learns what to keep. Apply Lindy after the first 90 days, not from day one.
- **Compliance / audit-driven environments** where regulators require process artifacts. The lessons here optimize for cognition + LLM execution; regulated environments have different optimization functions.
- **Onboarding-critical docs** that exist to teach (e.g., a step-by-step walkthrough for new contributors). These don't have a Lindy clock — they are read by every new hire on day one.

If you find yourself wanting to write a new doc-shape audit "just to keep things tidy", re-read this file first. Almost always, the right move is to simplify the rule so a checker is not needed, rather than write the checker.
