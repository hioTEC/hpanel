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

## Core Principle

**Small work (< 100 LOC): do it yourself. Large work (> 100 LOC): orchestrate.**

Parent agent context has prompt cache — files already read cost nearly zero on reuse. Sub-agent context is a fresh window where every token is full price. Delegation has ~50-100 LOC of fixed overhead (writing the prompt, accepting the result). Below that threshold, delegation is a net loss; above it, the parent agent fills context with implementation details and loses strategic oversight.

## Decision Table

| Condition | Action |
|-----------|--------|
| Change < 100 LOC, even across files | Do it yourself |
| Delegation prompt tokens >= actual code | Do it yourself |
| Only 1 task, no parallelism opportunity | Do it yourself |
| Change > 100 LOC or cross-module | **Delegate** |
| 2+ independent tasks can parallelize | **Delegate** |
| Parent context > 70% | **Delegate** (even small tasks) |
| Parent context > 90% | Write handoff, suggest `/clear` |

## Context Strategy

Sub-agent has no cache. Budget every token.

| Content | Strategy | Why |
|---------|----------|-----|
| Parent's synthesized judgments | Inject into prompt | Not in any single file |
| Decision Registry locked entries | Inject into prompt | Few lines, cheaper than whole design.md |
| Relevant passages from large files | Inject distilled version | Parent reads 1000 lines, distills 50 |
| Code files sub-agent will modify | Let sub-agent read | It needs to read anyway to locate edits |
| Project AGENTS.md | Tell the path | Sub-agent needs full content for verification |
| workspace.md / global schedule | Don't provide | Sub-agent doesn't need it |

## Prompt Template

```
Agent({
  prompt: `
    ## Task
    {task_desc}

    ## Design Context
    {parent's synthesized understanding — distilled, not copy-pasted}
    Locked decisions: {D-01: ..., D-02: ...}

    ## Scope
    Files to modify: {list}
    Files NOT to touch: {exclusion list}
    Read project AGENTS.md at {path} for conventions and verification.

    ## Exit
    Update {handoff.md path} with Done/Next/Blocked before returning.
  `,
  run_in_background: true,
  isolation: "worktree"   // Claude only; omit for Kimi
})
```

Don't specify `subagent_type` unless the task is genuinely read-only. The default general-purpose agent has the full toolset; specifying Explore/Plan removes Edit/Write.

## Parallel Dispatch

**File intersection check:** if two tasks touch the same file, they can only parallelize with worktree isolation (Claude). Without worktrees (Kimi), overlapping tasks must serialize.

| Scenario | Claude (worktree) | Kimi (no worktree) |
|----------|-------------------|--------------------|
| No file overlap | Parallelize all | Parallelize all |
| File overlap | Parallelize (merge conflicts are detectable) | Serialize overlapping tasks |
| Mixed large + small | Dispatch large to background, do small yourself | Same |
| All tasks < 100 LOC | Do sequentially (cache advantage) | Same |

**Pilot before fan-out** (mandatory when >= 4 homogeneous sub-agents): run 1 pilot first, validate the prompt template, then fan-out the rest. A pilot failure is a single rollback; a fan-out failure requires N re-runs.

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

When the work is large enough that cross-review matters (> 500 LOC, architecture-tier), offload implementation to a different harness for genuine independence:

```
cross-harness  >  cross-backend  >  same-harness sub-agent
(codex / kimi)     (claw -p)         (Agent tool)
```

**When justified:** Layer 2/3 architecture with spec doc contracts, need for genuine review independence, or parent context budget is tight.

For tool selection, invocation commands, handoff brief templates, and the iterative review cadence pattern, see `reference/review-invocation.md`.
