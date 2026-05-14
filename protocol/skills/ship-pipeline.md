---
name: ship-pipeline
description: Single delivery entry point after Plan — ADR commit → implementation → dual cross-harness review pass → direct push to main → deploy / smoke → summary. Hands off close-out work to /wrap.
type: skill
parameters:
  - branch: string
  - risk_level: low | medium | high
supported_harnesses: [kimi, claude]
---

# Ship — Post-Plan Implementation Cycle + Delivery

## Purpose

After `/plan` has finalized the approach and obtained user sign-off, this is the single entry point that completes the full flow:
"ADR commit → implementation → cross-harness review → direct push to main → deploy → smoke → summary."

**Intent Model**:
- The user has already signed off during the Plan phase. /ship does not open new decisions — it commits the signed-off decisions to an ADR, implements them, and delivers.
- The agent executes autonomously. By default the user only reviews the final summary + diff, intervening mid-process only when necessary.
- Large-scale multi-agent / multi-session active runs use `implement-pipeline.md`; `/ship` is the single-session self-driven path.

## Pre-conditions

- `/plan` has passed and user has signed off (referenced via plan note / design artifact)
- Current branch is clean
- Project verification baseline is currently green (typecheck / lint / test / build per `AGENTS.md`)

## Hard Constraints

- **2 cross-harness review passes are mandatory**: 1 ADR review + 1 implementation review. Both are required without exception.
- **Directional issues flag → STOP, report to user**; do not paper over them with follow-up commits.
  - Directional = decision misalignment / scope misalignment / scenario anchor misalignment / cross-layer boundary violation
  - Non-directional = style / typo / local boundary / naming / test coverage
- **Default is direct push to main**; feature branch requires an explicit `branch:` parameter. Inherits git-conventions project-level rules.
- **Pre-stage check + explicit `git add <files>`** (inherits `~/.dotfiles` leak-check + workspace.md §4).

## Process

### 1. Pre-flight

- `git status` clean; out-of-scope changes should be stashed or folded into scope first
- Run the project verification sequence baseline once (per `AGENTS.md` §6) to confirm a clean starting point
- Any baseline failure → STOP, enter `skills/investigate.md`

### 2. Commit-1 — ADR Commit

The form of Plan-phase output determines the ADR source:

| Plan Output | Commit-1 Action |
|---|---|
| Plan already wrote an ADR draft (status: `proposed`) | Finalize + add external review pass trace + promote to `accepted` per the §`accepted` checklist |
| Plan only produced a design note / decision registry | Agent drafts a formal ADR (per project ADR template + prefix rules) |
| Decision is small enough to not need a standalone ADR (per template "When to write an ADR") | Skip commit-1; only reference the plan note in commit-2 message body |

**Frontmatter (post-plan scenario)**:

```yaml
status: proposed                         # change to accepted after external review pass-1 completes
reviewers:
  - external (pending)
  - user (signed-off YYYY-MM-DD via /plan — see {plan-note-ref})
decision-makers: [user via /plan]
```

- Pre-stage check + explicit `git add docs/architecture/adr/ADR-{prefix}-{NNN}-{slug}.md`
- Commit message: `docs: ADR-{prefix}-{NNN} {one-line decision}`
- Hook failure → fix root cause + new commit. **Do not** use `--no-verify`, **do not** use `--amend`.

### 3. External Review Pass #1 — ADR Review

- Invoke `skills/code-review.md` external cross-harness review, scope = `design`
- Input: ADR + plan note + referenced design docs
- **Pass criteria (default medium)**: readable + consistent + no obvious gaps (does not require explicit external `APPROVE`, requires "no directional flags")
- **Pass criteria (`risk_level: high`)**: explicit external `APPROVE`
- Update ADR frontmatter `reviewers: external (1 pass; {brief note})`, promote to `accepted` (per ADR template `accepted` checklist)
- If external review flags a **directional issue** → STOP, report to user: "External review found directional issue X in the ADR — do we need to revisit /plan?"
- Otherwise → proceed to implementation

### 4. Commit-2 — Implementation

- Implement per ADR; may be split into multiple commits (by atomicity, not forced into 1)
- Each commit runs `verification_seq` deterministically (per project AGENTS.md §6)
- Any step fails → fix; still failing after 3 attempts → `skills/investigate.md`
- **Implementation reveals an ADR gap (decision gap, not a detail)** → STOP, report to user
- Implementation complete → run full verification + UI changes → screenshot/dev-server validation (per project AGENTS.md frontend rules)

### 5. External Review Pass #2 — Implementation Review

- Invoke `skills/code-review.md` full cross-harness review (sub-agent same harness + external reviewer on different harness in parallel)
- Input: full diff (`git diff {base}...HEAD`) + ADR + referenced design docs
- `risk_level: high` → mandatory adversarial brief mode
- **Directional flags**:
  - Scope / decision misalignment / cross-layer boundary violation → STOP, report to user
  - Local / implementation detail → proceed to revision
- **Non-directional flags** (concerns / suggestions) → proceed to revision

### 6. Commit-3+ — Revision

- Apply changes based on review feedback + agent's own judgment
- Not forced into 1 commit; split by atomicity
- Run verification sequence again to confirm all green
- Agent may make minor ADR revisions (typo / wording); changes to the Decision section must go back to user

### 7. Push + Deploy + Smoke

**Push**:
- `git push` (first push for a branch uses `git push -u origin {branch}`; defaults to `main`)
- Hook failure → fix root cause + new commit. Do not use `--no-verify`, do not `--amend` a published commit.

**Deploy**:
- Use the deploy command declared in the project's `AGENTS.md`
- No automated deploy → write deploy instructions in `handoff.md`, pause and wait for a human
- Deploy failure:
  - Do not immediately `git revert`; first run `skills/investigate.md`
  - Config (env / secrets / DNS) failure → fix config + redeploy, **do not touch code**
  - Build / runtime failure → fix commit + redeploy; unrecoverable → revert to last deployable commit + redeploy
  - Failure reason must be written to `handoff.md`; do not lose it

**Smoke**:
- Use the browser/curl tools declared in the project's `AGENTS.md` to open the production / staging URL
- Run 1-2 critical flows (selected per verification sequence)
- Screenshot key screens and compare against the last deploy to check for visual regressions
- Failure → `skills/investigate.md`; severe → revert deploy
- Pass → append `Deployed: {commit} @ {URL}` to the end of `handoff.md`

### 8. Plan Diff Report — Summary

**This is the basis for the user's quick review.** Provide the user with a brief summary:

```markdown
## /ship Summary

### What external review flagged
- ADR pass-1: {key point 1, key point 2 ...}
- Impl pass-2: {key point 1, key point 2 ...}

### Additional decisions the agent made beyond the original plan
- {decision 1: e.g. "extracted X into a helper instead of inlining"}
- {decision 2: e.g. "named it useFoo rather than getFoo"}
- {decision N}

### Commits
- {sha-1} docs: ADR-...
- {sha-2} feat: ...
- {sha-3} fix: ... (revision)

### Deployed
- {URL} @ {sha-3}
```

### 9. Hand off to /wrap

Invoke `/wrap` (or `skills/session-wrap.md`). Wrap is responsible for:
- Repo-local run manifest update (if there is an active run)
- Closed-run retirement / journal entry
- Publish sync to config repos (persona host / dotpanel) — ship does not touch these

Wrap reads the `Deployed:` line at the end of `handoff.md` as evidence that ship completed.

## Failure Modes (Quick Reference)

| Phase | Failure | Action |
|------|------|------|
| Pre-flight baseline | typecheck / test / build fails | STOP → `skills/investigate.md` |
| External Review Pass #1 (ADR) | directional flag | STOP, report to user |
| Implementation | ADR gap found (decision gap, not a detail) | STOP, report to user |
| Implementation | verification fails 3 times | `skills/investigate.md` |
| External Review Pass #2 (Impl) | directional flag (scope/decision misalignment) | STOP, report to user |
| External Review Pass #2 (Impl) | non-directional flag (concerns/local) | proceed to revision |
| Push | hook failure | fix root cause + new commit; no `--no-verify` / `--amend` |
| Deploy | build / runtime failure | investigate; unrecoverable → revert |
| Deploy | config / secret / DNS failure | fix config + redeploy, do not touch code |
| Smoke | critical flow broken | investigate; severe → revert deploy |

## Notes on relationship to `implement-pipeline.md`

`implement-pipeline.md` is a full multi-node state machine (with active run / verify sub-agent / multi-agent dispatch), suited for long-running multi-session tasks. `/ship` is a simplified path for the post-plan single-session cycle — within one session the agent self-drives ADR + implementation + 2 external review passes + revision + push + deploy + smoke.

| Scenario | Which path |
|---|---|
| Large-scale active run (multi-session, multi-agent, with dedicated verify sub-agent) | `implement-pipeline.md` |
| Post-plan single-session implementation (agent completes in one session) | `/ship` (this skill) |
