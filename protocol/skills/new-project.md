---
name: new-project
description: Bootstrap a new project against the dotpanel protocol. Resolves Lite vs Full shape, seeds AGENTS.md / CONTEXT.md / first scenario / first ADR-arch from scaffolds, and wires CI hard gates. Use when the operator says "new project" / "bootstrap this repo" / "scaffold project X".
type: skill
supported_harnesses: [claude, codex, kimi]
depends:
  - rules/three-layers.md
  - rules/scenario-driven-flow.md
  - rules/adr-template.md
  - reference/scaffolds/index.md
  - reference/ci-hard-gates.md
  - reference/domain-module-shape.md
  - skills/grill-me.md
---

# New Project

> Bootstrap a project against the protocol's full decision flow
> (scenario → ADR → spec → code) and three-layer ownership model.
>
> The skill resolves project shape via grill, seeds the right
> subset of scaffolds, and wires the CI hard gates. The output is a
> project that can pass the predicates listed in
> `protocol/reference/ci-hard-gates.md` from day 1, even if trivially
> (empty codebase + green gates).

## When to Trigger

- Operator says: "new project" / "bootstrap this repo" / "scaffold project X" / "set up X to use the protocol".
- Operator points at a fresh git repo and asks for the right starting layout.
- Operator wants to retrofit an existing project to the protocol — same skill, but step 6 (CI hard gates) takes longer (codebase already has shape that may need cleanup).

## Pre-flight

Before any scaffolding, confirm one fact: **does the project root exist as a git repository?** If not, ask whether to `git init` here or whether the operator wants to point somewhere else. The protocol assumes git history is the audit trail; without it, several gates lose their meaning.

## Step 1 — Lite vs Full grill

Run a single grill question per `protocol/skills/grill-me.md` discipline (one question at a time, attach a recommendation, do not ballot).

The signals to weigh, paraphrased to the operator in one paragraph:

> *"Bootstrapping <project>. Two shapes are common — **Lite** (single-domain or single-actor, < 5 ADRs over project lifetime, no schema migrations beyond initial) or **Full** (multi-domain, multi-role, ongoing schema work, scenario-driven flow). My recommendation: <Lite | Full>, because <one-sentence read of the project: e.g. 'sounds like a CLI tool with one user — Lite' or 'multi-role platform with teacher / student / admin — Full'>. Confirm or correct."*

Operator confirms or overrides. The verdict pins which scaffolds get seeded in step 4.

| Verdict | Scaffolds seeded |
|---|---|
| **Lite** | `AGENTS-skeleton.md` (trimmed: §0, §2, §3, §5, §6, §7, §10) + `adr-arch-skeleton.md` |
| **Full** | All five scaffolds: `AGENTS-skeleton.md` (full), `CONTEXT-skeleton.md`, `scenario-template.md`, `adr-arch-skeleton.md`, `domain-spec-template.md` |

## Step 2 — Bind L1 anchors

Walk the operator through three L1 questions (one at a time, recommendation attached). Record answers in a scratch buffer; they are the placeholders that get filled into the scaffolds in step 4.

1. **Project intent + stage scope.** *"In one sentence, what is <project>? What is in scope for stage-1, what is explicitly NOT in stage-1?"* Recommendation: agent reads any existing `README.md` / `package.json description` / pitch text in the repo and proposes a thesis sentence; operator confirms or rewrites.

2. **Stack binding.** *"What's the stack: language + framework + DB + test runner + linter + build tool?"* Recommendation: agent infers from the repo (existing `package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml`) and proposes; operator confirms additions or substitutions. Empty repo → operator names the stack.

3. **Decision-rights binding.** *"Who is the operator (L1 owner)? Who is the agent (L2 drafter / L3 self-decider)?"* For a solo operator, this is one handle for L1 and one handle for L2/L3. For multi-operator projects, list each + which layer they own.

For Full projects, also bind:

4. **Domain seed list.** *"Name the 2–4 domains you expect for stage-1."* Recommendation: agent proposes from the project intent (e.g., for a teacher-grading platform: `catalog`, `quiz`, `assignment`, `submission`, `grading`). Operator confirms or trims. These become the initial `src/lib/<domain>/` folders + their initial spec.md files (lazy-created when each domain gets its first ADR).

## Step 3 — Seed first scenario (Full only)

For Full projects, seed one scenario file before the first ADR. The scenario captures the **anchor user journey** for stage-1 — the single most important "user does X" story.

Process:

1. Agent asks: *"What's the single most important user journey for stage-1? One paragraph from the user's perspective."*
2. Operator answers in their language; agent expands the answer into the scenario shape (`protocol/reference/scaffolds/scenario-template.md`).
3. The scenario file lands at `docs/product/scenarios/<slug>.md` with `status: draft`.
4. Agent does **not** populate `## Open product questions` exhaustively at seed time — only the questions that are blocking the first ADR. Other open questions surface naturally as scenarios get used.

Lite projects skip this step. Their first decision is captured directly in an ADR, no scenario file required.

## Step 4 — Render scaffolds

Copy the scaffolds (per the Lite / Full verdict from step 1) into the project root, **substituting the bound values from steps 2–3** for the `<placeholders>`. Do not commit blank skeletons; every placeholder either gets a value or gets explicitly marked `<TBD — see <scenario or ADR file>>` with a follow-up commit planned.

Files written, in order:

1. **`CONTEXT.md`** at project root (Full only). Section structure from `CONTEXT-skeleton.md`; populated with the domain group skeletons from step 2's domain seed list; vocabulary tables empty (will fill as terms get grilled).
2. **`AGENTS.md`** at project root. Sections from `AGENTS-skeleton.md`; values from step 2; §1 (Decision Rights) only included for Full; §4 (Conditional Context Loading) populated with rows for each seed domain (Full only).
3. **`docs/product/scenarios/<slug>.md`** (Full only). The scenario from step 3.
4. **`docs/architecture/adr/ADR-arch-001-<slug>.md`** (the first decision). For Full: the ADR that grounds the scenario from step 3. For Lite: the first architectural decision the operator wants to record (often: stack choice rationale, or initial deployment topology). Frontmatter `kind: scenario-driven` (Full) or `infrastructure` (Lite); `status: draft`.
5. **`src/lib/<seed-domain>/spec.md`** for each seed domain (Full only). Use `domain-spec-template.md`; populate `## 1. Purpose` and `## 9. Domain vocabulary` with placeholders that the first real implementation will fill. The domain folder may not have any `index.<ext>` or test files yet — the spec is the contract that will guide the first implementation active run.

## Step 5 — Wire CI hard gates

Per `protocol/reference/ci-hard-gates.md` §"Adopting these gates mid-project", wire the gates **in order**, not all at once:

**Always** (gates 1, 2, 8, 9):

- Type-check
- Lint (warnings = errors)
- Test
- Build

These are stack-standard. Add the invocations to the project's CI config (GitHub Actions, GitLab, etc.). The codebase passes trivially at this point (empty), so all four are green from commit 1.

**Add when domains land** (gates 3, 6):

- Module map (project ships `scripts/module-map.<ext>` — wraps `dependency-cruiser` or equivalent for the project's stack)
- Domain shape (project ships `scripts/audit-domain-shape.<ext>` — checks each `src/lib/<domain>/` has `index.<ext>` + `spec.md` + tests)

**Add when schema lands** (gates 4, 5):

- Schema-isolation / table-prefix (project-specific predicate)
- Migration safety (project ships `scripts/audit-migrations.<ext>`)

**Add when scenario-driven flow is adopted** (gate 7):

- Scenario ↔ ADR coverage (project ships `scripts/audit-scenario-adr-coverage.<ext>`); forward-only — pre-adoption ADRs are advisory.

For each gate added, the gate is **hard-fail from the moment it's added**. The codebase passes when the rule is added; new violations block. Do not add a rule in advisory mode "for now" — that pattern fails (see `ci-hard-gates.md` §"Why hard gates from day 1").

## Step 6 — Declare adoption date

In the project's `AGENTS.md` §9 (Project Deltas), record:

```markdown
- **Protocol adoption** — <YYYY-MM-DD>. ADRs created on or after this date follow `<DOTPANEL_ROOT>/protocol/rules/adr-template.md` (frontmatter, lifecycle, accepted checklist). Pre-adoption ADRs (if any retrofitted from elsewhere) are forward-only-advisory.
```

This is the line the audit scripts read to decide which ADRs to hard-fail on.

## Step 7 — Verify

Run the full hard-gate suite once. All gates should pass (trivially or non-trivially depending on what's in the codebase). If a gate fails, fix the cause before the bootstrap commit lands — do **not** ship a project with a red gate.

Recommended bootstrap commit shape:

```
chore: bootstrap project against dotpanel protocol

- AGENTS.md / CONTEXT.md / docs/{product,architecture}/ scaffolded
- ADR-arch-001 (draft) + first scenario seeded (Full only)
- CI hard gates wired: typecheck / lint / test / build
- Protocol adoption date: <YYYY-MM-DD>
```

## Output: bootstrap manifest

After the skill finishes, write a manifest to `.agents/bootstrap.md` recording the choices made. This is the audit trail for "why does this project look this way":

```markdown
# Bootstrap manifest

- Date: YYYY-MM-DD
- Verdict: <Lite | Full>
- Stack: <bound from step 2>
- Operator: <handle>
- Agent: <handle>
- Seed domains: <list, Full only>
- First scenario: <slug>.md, Full only
- First ADR: ADR-arch-001-<slug>.md
- CI hard gates wired: <list>
- Protocol adoption date: YYYY-MM-DD
- Open follow-ups:
  - [ ] <e.g. fill CONTEXT.md as terms get grilled>
  - [ ] <e.g. wire scenario↔ADR coverage gate when scenario count ≥ 2>
```

## Rules

- **One grill question at a time.** Steps 1–3 each contain multiple questions; ask them sequentially, never as a batch ballot. Per `protocol/skills/grill-me.md`.
- **Always recommend, never ballot.** Every grill question carries the agent's recommendation + 1–2 sentences of rationale. Operator confirms or overrides; the agent does not pass blank options or A/B/C lists.
- **No empty placeholders in committed files.** Every `<placeholder>` either gets a value at bootstrap time or gets marked `<TBD — see <follow-up artifact>>` with the follow-up named. Empty placeholders signal incomplete bootstrap.
- **Hard gates from day 1.** No advisory mode. The bootstrap commit ships green gates; the codebase grows under the gates' protection.
- **Lite is a real choice, not a downgrade.** A small project with a small protocol footprint is correct. Over-protocol-ing a single-purpose tool is the same anti-pattern as one-shot abstraction (workspace.md §3 R3). The Full shape exists for projects that need it.
- **Retrofit ≠ greenfield.** Existing-project retrofits run the same skill but spend most of the time in step 5 (CI hard gates) cleaning up violations. Time-box: if a retrofit would take more than half a day to get to green gates, surface that to the operator and ask whether to defer some gates to a follow-up commit (still hard-fail at the moment they land, just landed in stages).
