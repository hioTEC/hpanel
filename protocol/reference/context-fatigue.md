---
name: Context Fatigue in Long Sessions
description: Recognition and recovery protocol for multi-agent sessions that accumulate noise without producing commits.
type: memory
tags: [concept, operations, multi-agent]
related:
  - skills/session-guardrails.md
---

# Context Fatigue

## Definition
The degradation of decision quality in a multi-agent session as turns accumulate without hard checkpoints. Symptoms include goal drift, forgotten constraints, ping-pong bug fixes, and opportunistic refactors.

## Prevention

- `skills/session-guardrails.md` enforces automatic checkpoints at the thresholds above.

> **Executable thresholds and checkpoint actions: see `{{DOTPANEL_ROOT}}/protocol/skills/session-guardrails.md`.**
