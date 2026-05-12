---
name: implement-pipeline
description: Execute the code-review-verify loop for an active run.
type: skill
parameters:
  - run_id: string
  - run_manifest: string
  - handoff: string
  - worktree: string
  - scope: string[]
  - verification_seq: string[]
  - max_retries: number      # default 3
supported_harnesses: [kimi, claude]
---

# Implement Pipeline

## Purpose
Drive an active run from implementation through review-ready using a
state-machine loop with sub-agents. This skill does not own roadmap/stage
governance. The active run records execution state; durable design truth lives
in ADRs, specs, rules, or roadmap.

## Pre-conditions
- Repo-local run manifest exists (`{project}/.agents/runs/active.yaml`).
- `handoff.md` has Done / Next / Blocked / Touched / Verification / Resume here.
- The run manifest `revision` matches handoff frontmatter `manifest_revision`.
  Any node that updates run state must write manifest + handoff together and
  increment both values by 1.
- Any durable design doc named by the handoff is accepted, or the handoff says
  implementation is intentionally exploratory.

## State Machine

```
code → review → ui_review → verify → ship → wrap
  ↑      │                     │
  └──────┘ (reject)            │ (fail)
  ↑                            │
  └────────────────────────────┘

↑
└────────── (retry_count >= max_retries) → escalate: blocked_for_redesign
```

## Process

1. **Guardrail Check (before each node)**
   - Call `skills/session-guardrails.md`
   - If checkpoint triggered → pause, do not enter node until resolved

2. **Node: code**
   - Enter code node; retry_count starts at 0, tracked in conversation context
   - Primary agent reads `handoff.md` + run manifest + named ADR/spec/design docs + project `AGENTS.md` to build full context (leveraging prompt cache)
   - Split scope into independent tasks and estimate effort for each
   - **Primary agent handles directly (default path):** tasks with < 100 lines changed. Primary agent context is cached, so marginal cost is lower than delegation.
   - **Delegated (parallel acceleration path):** independent tasks with > 100 lines changed. Dispatch via `delegate-spec.md` scheduling decision tree.
   - **Hybrid mode (optimal):** dispatch large tasks to background while handling small tasks in parallel.
   - Once all changes are complete, run `verification_seq` deterministically (tsc, eslint, vitest, etc.)
   - If fail → investigate first (call `skills/investigate.md`)
   - If pass → enter review node

3. **Node: review**
   - Determine external reviewer per the cross-harness rules in `skills/code-review.md` (different harness family from primary agent)
   - **Launch two reviewers in parallel:**
     - **Internal reviewer (sub-agent, same harness):** spawn reviewer-agent with diff + scope context + handoff-named design artifacts
     - **External reviewer (codex or kimi-cli, different harness):** compose a neutral review brief (format per `skills/code-review.md` §3) and launch in parallel
   - Wait for both to return
   - **Synthesize both results** (rules per `skills/code-review.md` §5):
     - Either says REQUEST_CHANGES with concrete blocker → REQUEST_CHANGES
     - Disagreement → present both, human decides
     - Both APPROVE → approved
   - If approved → enter ui_review node (or skip if no UI changes)
   - If rejected:
     - Increment retry_count in conversation context
     - If retry_count reaches 2 → **Yellow checkpoint**: warn user that review ping-pong is starting
     - If retry_count reaches `max_retries` → enter blocked_for_redesign node
     - Else → return to code node, append feedback to coder prompt

4. **Node: ui_review**
   - If UI files changed (`*.tsx`, `*.astro`, `*.css`, `*.html`):
     - Open dev URL via `agent-browser` or Playwright
     - Screenshot + present to user for approval
     - If issues → treat as reject, return to `code`
   - If no UI files → skip to `verify`

5. **Node: verify** (independent sub-agent)
   - Spawn a **fresh** sub-agent (NOT the coder or reviewer) with `run_in_background: true`
   - Sub-agent receives: run handoff + accepted ADR/spec/design docs named by the handoff + project `AGENTS.md` + codebase access
   - Sub-agent does NOT receive: SUMMARY, commit messages, or any implementer self-report
   - **Goal-backward verification:** per `{{DOTPANEL_ROOT}}/protocol/workspace.md` §"Verification: Goal-Backward", run the 4-level artifact check.
   - **Decision Registry audit:** if a named design doc contains a Decision Registry:
     - Every `locked` decision → grep/read codebase for evidence it was implemented. Cite file:line.
     - Every `deferred` decision → grep for evidence it was NOT implemented. Flag if found.
     - Every `discretion` decision → record what choice the implementer made and whether it's reasonable.
   - Sub-agent runs project verification sequence (from AGENTS.md)
   - Sub-agent appends a verification block to the run handoff and updates the run manifest `verification` block:
     ```yaml
     verified: YYYY-MM-DD
     verdict: pass | pass_with_concerns | fail
     evidence:
       - type: command
         value: npm run typecheck
         status: pass
     ```
     Use the stale-write guard when writing this block: re-read the manifest
     revision, require it to match the handoff frontmatter, then increment both.
     Followed by: checked items (with file:line evidence), concerns (if any), failures (if any)
   - **Gate:**
     - `pass` → enter ship node
     - `pass_with_concerns` → present concerns to user; user decides ship or fix
     - `fail` → return to code node, append failure details to coder prompt, increment retry_count

6. **Node: ship**
   - Call `/ship` skill (or run `skills/ship-pipeline.md`)
   - On success → mark run `ready-for-review` or close via wrap when ship evidence exists
   - On failure → investigate; if blocked, update run manifest `status: blocked` using the stale-write guard

7. **Node: blocked_for_redesign**
   - Update run manifest: `status: blocked` using the stale-write guard
   - Write `handoff.md`: "Implement blocked after {max_retries} review cycles. Return to design/roadmap/ADR to re-scope."

8. **Node: wrap**
   - Call `/wrap` logic (update run manifest, handoff, journal/digest if needed)
