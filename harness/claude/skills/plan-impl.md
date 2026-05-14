---
name: plan-impl
extends: protocol:plan-discussion
description: Claude-specific implementation details for multi-agent plan discussion.
harness: claude
---

# Plan Discussion — Claude Implementation

## additional: Stealth Challenge Agent Invocation

### additional: Internal Critic (Same Harness)

Launch the in-harness critic per `skills/code-review.md` section "Resolver" (context = design artifact only; do not pass workspace/memory/history). The critic and the external reviewer must be launched in parallel.

```javascript
Agent({
  agent_id: `${run_id}-critic-stealth`,
  prompt: `Review this design artifact for missed edge cases and gaps.\n\n${designArtifact}`,
  run_in_background: true
})
```

### additional: External Reviewer (Different Harness)

Select the reviewer per `skills/code-review.md` section 2 "Select External Reviewer"; compose the review brief and launch per sections 3-4, scope = "design". For design reviews, prefer kimi-cli (prompt-native). The reviewer must not receive the orchestrator's hidden scenarios.

```bash
# Preferred: kimi-cli for design reviews
kimi-cli --model kimi-k2 "${review_brief}"

# Alternative: codex
codx [repo]
```

### additional: Orchestrator Self-Check

Before summoning any reviewer, independently refine the design artifact, ensuring it is a "complete, serious version" (field definitions, state machines, API contracts, and error paths are all clearly specified). Independently devise at least 3-5 extreme scenarios, but **must not write these scenarios to any file or reveal them to any reviewer**.
