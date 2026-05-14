---
name: delegate-impl
extends: protocol:delegate-spec
description: Kimi-specific implementation details for agent delegation.
harness: kimi
---

# Delegate Spec — Kimi Implementation

## additional: Prompt Template

Kimi does not use the `Agent()` tool syntax. Spawn sub-agents via background bash or direct tool invocation:

```bash
# Background task (for parallel execution)
Shell({
  command: `cd {worktree_path} && {task_command}`,
  run_in_background: true,
  description: "{task_desc}"
})
```

Or delegate via Kimi's native multi-agent mechanism if available in the harness version.

## additional: Parallel Dispatch

Kimi does **not** support worktree isolation. File overlap rules:

| Scenario | Kimi behavior |
|----------|---------------|
| No file overlap | Parallelize all |
| File overlap | **Must serialize** overlapping tasks |
| Mixed large + small | Dispatch large to background, do small yourself |
| All tasks < 100 LOC | Do sequentially (cache advantage) |

**Critical:** Without worktrees, two sub-agents writing to the same file will cause silent overwrites or merge conflicts. Always check file intersection before parallel dispatch.

## additional: Cross-Harness Offload Commands

```bash
# Cross-harness review (Layer 1)
codx [repo]                    # Spawn codex in repo directory
claw -p --<backend> "prompt"   # Quick headless query via claw

# Cross-backend headless query (Layer 2)
kimi-cli --model kimi-k2 "..." # Self-harness query (not true cross-harness)
```

**Note:** Kimi-as-primary offloading to Claude-as-external is the preferred direction for cross-harness review, due to Claude's worktree isolation support.
