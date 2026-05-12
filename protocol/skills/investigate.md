---
name: investigate
description: Root-cause analysis for failures, regressions, or user-reported bugs. Iron law: no fix without root cause.
type: skill
parameters:
  - symptom: string
  - affected_files: string[]
  - logs_or_errors: string   # optional
supported_harnesses: [kimi, claude]
---

# Investigate

## Iron Law
**Do not fix until you can state the root cause as a testable claim.**

## Phase 1: Gather Symptoms

1. Read error messages / stack traces / user description
2. `git log --oneline -10` to see recent changes
3. If UI bug → `agent-browser` screenshot or reproduce
4. Grep for affected code paths and consumers
5. Check `rules/design-contract.md` if the bug involves state, fields, or deployment

## Phase 2: Root-Cause Hypothesis

Formulate ONE specific, testable claim:
> "The bug is caused by X, which happens when Y, leading to Z."

Use `rules/design-contract.md` as a diagnostic lens:
- Is it a **scenario enumeration** miss? (edge case not considered)
- Is it a **walkthrough** gap? (a step in the user journey unhandled)
- Is it a **state transition** error? (illegal state reachable)
- Is it a **field lifecycle** error? (null handling, merge priority, rename drift)
- Is it a **deployment delta** error? (dev/prod mismatch)

## Phase 3: Validate Hypothesis

1. Add temporary logging or assertions
2. Run the failing test / verification step
3. If hypothesis is WRONG:
   - Document the disproof
   - Return to Phase 1 with expanded evidence
   - After **3 failed hypotheses**, pause and escalate to human:
     > "3 hypotheses excluded: {list}. Options: A) I have a new lead B) You take a look C) Add telemetry and capture next time."

## Phase 4: Fix

1. Propose fix with tradeoffs:
   > "Root cause: X. Options: A) ..., B) ..., C) ... . Recommended: B because Y."
2. Wait for user selection (or auto-select if trivial)
3. Apply fix → atomic commit
4. Re-run full verification sequence
5. If UI-related, visual checkpoint to confirm fix

## Scope Lock
During investigate, **only touch files directly related to the root cause**. No opportunistic refactors.
