---
name: delegate-spec
description: Spawn sub-agents when parallel speedup or context budget justifies the delegation overhead.
type: skill
parameters:
  - task_desc: string
  - max_lines: number
  - modules: string[]
  - verification: string[]
supported_harnesses: [kimi, claude]
---

# Delegate Spec

## Constraints

See `rules/delegation-economics.md` for the core principle, decision table, and context strategy. This skill implements the protocol on top of those constraints.

## Sub-Agent Exit Protocol

Before returning, every sub-agent MUST append to `handoff.md`:

```markdown
### {YYYY-MM-DD} Sub-agent: {task_id}
**Done:** {completed items with file paths}
**Next:** {remaining or "scope complete"}
**Blocked:** {blockers or "none"}
```

In worktree mode, write to the worktree's copy; merge when combining.

## Acceptance

1. Sub-agent returns diff / commit list / summary
2. Parent reads handoff.md update, cross-checks against self-report
3. Parent runs `verification_seq`
4. Rejected → resume sub-agent with specific feedback
5. All parallel sub-agents accepted → run integration verification once

## Cross-Harness Offload

When the work is large enough that cross-review matters (> 500 LOC, architecture-tier), offload implementation to a different harness for genuine independence. See `rules/delegation-economics.md` §Cross-Harness Offload Hierarchy for the decision framework. For harness-specific invocation commands and prompt templates, see `harness/{harness}/skills/delegate-impl.md`.
