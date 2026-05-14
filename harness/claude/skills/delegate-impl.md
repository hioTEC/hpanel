---
name: delegate-impl
extends: protocol:delegate-spec
description: Claude-specific implementation details for agent delegation.
harness: claude
---

# Delegate Spec — Claude Implementation

## additional: Prompt Template

```javascript
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
  isolation: "worktree"
})
```

Don't specify `subagent_type` unless the task is genuinely read-only. The default general-purpose agent has the full toolset; specifying Explore/Plan removes Edit/Write.

## additional: Parallel Dispatch

**File intersection check:** if two tasks touch the same file, they can only parallelize with worktree isolation (Claude). Without worktrees (Kimi), overlapping tasks must serialize.

| Scenario | Claude (worktree) | Kimi (no worktree) |
|----------|-------------------|--------------------|
| No file overlap | Parallelize all | Parallelize all |
| File overlap | Parallelize (merge conflicts are detectable) | Serialize overlapping tasks |
| Mixed large + small | Dispatch large to background, do small yourself | Same |
| All tasks < 100 LOC | Do sequentially (cache advantage) | Same |

**Pilot before fan-out** (mandatory when >= 4 homogeneous sub-agents): run 1 pilot first, validate the prompt template, then fan-out the rest. A pilot failure is a single rollback; a fan-out failure requires N re-runs.

## additional: Cross-Harness Offload Commands

```bash
# Cross-harness review (Layer 1)
codx [repo]                    # Spawn codex in repo directory
kimi-cli --model kimi-k2 "..." # Spawn kimi for coding tasks

# Cross-backend headless query (Layer 2)
claw -p --<backend> "prompt"   # Quick headless query via claw
```
