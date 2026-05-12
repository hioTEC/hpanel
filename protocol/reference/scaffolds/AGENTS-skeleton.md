# <Project Name>

> <One-line product pitch — what this is, who it's for, what stage it's at.>
> Internal entrypoint for agents. Public-facing pitch lives in [README.md](README.md).
>
> **Global defaults, hard constraints, stop rules, engineering principles, module discipline — see `<DOTPANEL_ROOT>/protocol/workspace.md`; operator voice lives at `<DOTPANEL_ROOT>/persona/voice.md`.** This file is **<Project Name>-specific delta only**: routing, decision rights, project predicates, project hard constraints.

> **Lite project note:** if your project is single-domain / single-actor / no schema migrations, you may delete §1 (Decision Rights), §4 (Conditional Context Loading), §8 (ADR Prefix Convention), §9 (Deltas) and run with §0 + §2 + §3 + §5 + §6 + §7 + §10. The remaining sections are still useful even for a small tool.

## §0 — Project Intent + Stack

<2–3 sentences on the product thesis. Anchor the **stage** this project is at — what's in scope now, what is *not* in scope. Useful pattern: "Stage-1 (timeline) = X. Stage-2 (+timeline) = Y. NOT stage-1: Z.">

**Core thesis:** <one sentence: what's the differentiator / wedge / contrarian bet?>

- **Stack:** <framework + runtime + DB + test runner + linter — one line>
- **Code root:** `<absolute path or repo root pointer>`
- **Database:** <ownership model — shared / isolated / none>
- **Roadmap authority:** `docs/product/roadmap.md`
- **Human docs index:** `docs/index.md`

## §1 — Decision Rights

> Three-layer ownership table — pick this up first when starting a task. Body: `<DOTPANEL_ROOT>/protocol/rules/three-layers.md`.

| Layer | Owner | Artifact home | Examples (one-glance scope) |
|---|---|---|---|
| **L1 Mental model** | <operator-handle> | `docs/product/charter.md`, `docs/product/design-system.md`, `docs/product/scenarios/*.md` | <product-intent calls specific to this project> |
| **L2 Architecture** | <agent-handle> drafts + cross-harness review + <operator-handle> sign-off | `CONTEXT.md`, `docs/architecture/adr/ADR-arch-*.md`, `docs/architecture/adr/ADR-design-*.md`, `src/lib/{domain}/spec.md` | <architecture calls specific to this project> |
| **L3 Component** | <agent-handle> self-decides | `.agents/runs/{run-id}/handoff.md` for execution state, `docs/architecture/adr/ADR-comp-*.md`, `docs/engineering/concerns/{slug}.md` | <component calls specific to this project> |

### Scenario-driven decision flow

> Body: `<DOTPANEL_ROOT>/protocol/rules/scenario-driven-flow.md`.

```
docs/product/scenarios/*.md   →   docs/architecture/adr/ADR-*.md   →   src/lib/{domain}/spec.md   →   implementation
```

Open product questions inside scenarios are grilled per `<DOTPANEL_ROOT>/protocol/rules/interaction.md` §Be Opinionated — agent recommends one option + 1–2 sentences of tradeoff, does not pass blank options or A/B/C ballots.

## §2 — Offload Candidates

> Cheat sheet — when work is too large for in-session implementation, who picks it up.

| Task shape | Tool | Trigger |
|---|---|---|
| ≥ 10 files / ≥ 500 LOC implementation | <cross-harness CLI agent — name + invocation> | L3 with locked L2 ADR + spec-link |
| Single-file / spec critique / brief | <cross-backend single-call helper> | L3 brief, no tools needed |
| Architecture cross-backend review | <independent harness for review> | L2 drafted, pre-sign-off |
| Cross-harness final verification | <different harness from primary> | merge gate |

## §3 — Authority Order

When docs disagree, resolve in this order:

1. Latest accepted ADR (or accepted amendment)
2. `CONTEXT.md` for project domain language
3. Code, build manifest, CI for executable reality
4. This `AGENTS.md` for routing and local conventions
5. `README.md` as public pitch, not architecture authority
6. Historical evidence files only as evidence when the current accepted ADR / spec / handoff explicitly points to them

## §4 — Conditional Context Loading

> Trigger → file map for picking up a new task. Skip when context is already explicit.

| Trigger | Read |
|---|---|
| Named active run | `<active-run bootstrap pointer>` → `.agents/runs/active.yaml` → `.agents/runs/{run-id}/handoff.md` + handoff-named ADR / spec / design docs |
| Small bug / narrow refactor | This file + touched source. No design doc required |
| Naming / new term / external-facing identifier | `CONTEXT.md` |
| State / field / schema / migration / deploy change | `<DOTPANEL_ROOT>/protocol/rules/design-contract.md` + `docs/architecture/rules/architecture-boundaries.md` |
| Cross-file refactor / interface change | `docs/architecture/rules/architecture-boundaries.md` + `scripts/module-map.<ext>` |
| UI / UX / visual uncertainty | `docs/architecture/rules/frontend-discipline.md` + `docs/product/design-system.md`; `<DOTPANEL_ROOT>/protocol/rules/ui-design.md` if visual |
| <domain-A> work | `src/lib/<domain-A>/spec.md` + `docs/product/scenarios/<related-scenario>.md` |
| <domain-B> work | `src/lib/<domain-B>/spec.md` + `docs/product/scenarios/<related-scenario>.md` |

## §5 — Docs vs Runtime Layout

```
docs/
  index.md
  product/            Layer 1: charter, roadmap, design system, scenarios
  architecture/       Layer 2: ADRs and rules
  engineering/        durable concerns and memory

.agents/
  runs/               active.yaml + {run-id}/handoff.md (active execution state only)
  evidence/{task-id}/ historical task evidence (not current authority)
```

Create on first need; never pre-populate empty directories. **No `archive/` convention** — shipped run rationale lands in ADR / spec / rule / roadmap, then long handoff is removed; git history retains execution detail.

## §6 — Verification Sequence

Before reporting `done` — **hard gates** (zero tolerance, CI blocks):

- [ ] `<typecheck command>` (zero errors)
- [ ] `<lint command>` (zero warnings — warnings are errors)
- [ ] `<module-map check>` (cross-domain boundary lint)
- [ ] `<schema / migration audit>` (no destructive SQL + idempotency check; project-specific predicate)
- [ ] `<domain-shape audit>` (lib domain has `index.<ext>` + `spec.md` + tests)
- [ ] `<scenario-ADR coverage audit>` (ADR ↔ scenario bidirectional + scenario domain terms ⊂ CONTEXT)
- [ ] `<test command>` (zero failures)
- [ ] `<build command>` (required for ship / review)

**Advisory audits** (run + read findings, don't block on count):

- [ ] `<context coverage>` — list public exports not in `CONTEXT.md`; review and decide (cover or hide)
- [ ] `<depth audit>` — list shallow lib modules; address per the deletion test

**Eyes-required** (frontend / UI changes per `docs/architecture/rules/frontend-discipline.md`):

- [ ] UI change → screenshot or E2E evidence + dev-server walk
- [ ] AI output surface → uncertainty marker visual confirmation

Generic `done = predicate-passed` chain (4-level: Exists / Substantive / Wired / Data flows) → `<DOTPANEL_ROOT>/protocol/workspace.md` §2.

## §7 — Stop Rules + Hard Constraints

Generic stop rules + hard constraints (secrets / destructive / dependency review / sync) → `<DOTPANEL_ROOT>/protocol/workspace.md` §4 + §5.

<Project Name>-specific (refuse to execute, do not "work around"):

| Trigger | Action / Why |
|---|---|
| <e.g. importing a banned library / using a deprecated path> | <e.g. reject — ADR-XXX rejected this; sole entry point is `<path>`> |
| <e.g. introducing a stage-2 type into stage-1 code> | <e.g. reject — pre-coupling> |
| <e.g. collapsing two preserved fields into one> | <e.g. reject — original signal must be preserved per ADR-YYY> |
| <e.g. drive-by editing of `README.md` / `CONTEXT.md` / `AGENTS.md` / `charter.md` in a feature commit> | <e.g. reject — deliberate edit, separate commit> |

## §8 — ADR Prefix Convention

> Body: `<DOTPANEL_ROOT>/protocol/rules/adr-template.md`.

New ADRs use these prefixes (legacy un-prefixed ADRs may keep their original names):

- `ADR-arch-NNN-{slug}.md` — Layer 2; **must include cross-harness review trace** in frontmatter `reviewers:`
- `ADR-comp-NNN-{slug}.md` — Layer 3; agent self-decides, operator may review after the fact
- `ADR-design-NNN-{slug}.md` — design system evolution (token / anchor / atom abstraction time-points)

`authors: [<agent-handle>]` indicates agent-drafted or operator-default-authorized. Explicit operator decisions write `decision-makers: [<operator-handle>]` or `authors: [<agent-handle>, <operator-handle>]`.

Template + lifecycle + accepted checklist → `<DOTPANEL_ROOT>/protocol/rules/adr-template.md`. Worked examples live in `docs/architecture/adr/`.

## §9 — Project Deltas (intentional divergences)

> Class D: deliberate divergences from generic protocol or from a precursor project — not drift. Detail lives in the ADRs cited.

- **<Delta 1>** — <one-line summary>. See ADR-arch-NNN.
- **<Delta 2>** — <one-line summary>. See ADR-arch-NNN.

## §10 — What NOT to Do (pointer)

- Generic don'ts (defensive programming for internal code / one-shot abstraction / DB mocking in integration tests / commit `--amend` after pre-commit hook fail) → `<DOTPANEL_ROOT>/protocol/workspace.md` §3 + §4
- <Project Name>-specific git / commit / branch / co-author conventions → `docs/architecture/rules/git-conventions.md`
- Detailed pitfalls (lessons inherited from precursor + project-specific anticipations) → `docs/architecture/rules/common-pitfalls.md` + `docs/engineering/memory/feedback.md`
- Frontend-specific don'ts (atom threshold / story granularity / test boundary / a11y baseline) → `docs/architecture/rules/frontend-discipline.md`
