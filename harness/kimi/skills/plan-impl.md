---
name: plan-impl
extends: protocol:plan-discussion
description: Kimi-specific implementation details for multi-agent plan discussion.
harness: kimi
---

# Plan Discussion — Kimi Implementation

## additional: Stealth Challenge Agent Invocation

### additional: Internal Critic (Same Harness)

Kimi does not have a native `Agent()` spawn tool. Use background Shell or inline reasoning:

```bash
# Option A: Background shell with reasoning script
Shell({
  command: `cat design.md | kimi-cli --model kimi-k2 "Review this design for missed edge cases and gaps."`,
  run_in_background: true,
  description: "Internal critic review"
})
```

```bash
# Option B: Inline self-critic (if background spawn unavailable)
# The orchestrator performs the critic role inline, then pauses to 
# compare against the external reviewer result.
```

The critic and the external reviewer must be launched in parallel when possible.

### additional: External Reviewer (Different Harness)

Select the reviewer per `skills/code-review.md` section 2 "Select External Reviewer". For design reviews from Kimi, prefer spawning Claude (`claw` or `claude`) as the external reviewer due to superior long-context handling for design documents.

```bash
# Preferred: Claude as external reviewer for design reviews
claw -p --andy "${review_brief}"

# Alternative: Codex
codx [repo]
```

The reviewer must not receive the orchestrator's hidden scenarios.

### additional: Orchestrator Self-Check

Same as protocol: independently refine the design artifact and devise 3-5 extreme scenarios without writing them to files or revealing to reviewers.
