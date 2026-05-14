# Delegation Economics

> Universal constraint on when to delegate vs. self-do. Embedded in workspace.md §5 Stop Rules and referenced by `skills/delegate-spec.md`.

## Core Principle

**Small work: do it yourself. Large work: orchestrate.**

Parent agent context has prompt cache — files already read cost nearly zero on reuse. Sub-agent context is a fresh window where every token is full price. Delegation carries fixed overhead (writing the prompt, accepting the result). Below the operator-configured delegation threshold, delegation is a net loss; above it, the parent agent fills context with implementation details and loses strategic oversight.

## Decision Framework

| Condition | Action |
|-----------|--------|
| Change below delegation threshold | Do it yourself |
| Delegation prompt tokens >= actual code | Do it yourself |
| Only 1 task, no parallelism opportunity | Do it yourself |
| Change above delegation threshold or cross-module | **Delegate** |
| 2+ independent tasks can parallelize | **Delegate** |
| Parent context above early-delegate threshold | **Delegate** (even small tasks) |
| Parent context above handoff threshold | Write handoff, suggest `/clear` |

> Concrete threshold values are defined in `~/.dotfiles/skills/delegate-defaults.md` (persona layer). Protocol skills reference the abstract thresholds above.

## Context Strategy Principles

Sub-agent has no cache. Budget every token.

| Content | Strategy | Why |
|---------|----------|-----|
| Parent's synthesized judgments | Inject into prompt | Not in any single file |
| Decision Registry locked entries | Inject into prompt | Few lines, cheaper than whole design.md |
| Relevant passages from large files | Inject distilled version | Parent reads 1000 lines, distills 50 |
| Code files sub-agent will modify | Let sub-agent read | It needs to read anyway to locate edits |
| Project AGENTS.md | Tell the path | Sub-agent needs full content for verification |
| Workspace.md / global schedule | Don't provide | Sub-agent doesn't need it |

## Cross-Harness Offload Hierarchy

When work is large enough that cross-review matters (architecture-tier, above cross-review threshold):

```
cross-harness  >  cross-backend  >  same-harness sub-agent
(codex / kimi)     (claw -p)         (Agent tool)
```

**When justified:** Layer 2/3 architecture with spec doc contracts, need for genuine review independence, or parent context budget is tight.

> The cross-review threshold and preferred offload direction are defined in the persona layer (`~/.dotfiles/skills/delegate-defaults.md`).
