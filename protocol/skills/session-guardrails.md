---
name: session-guardrails
description: Enforce automatic human checkpoints and recovery actions when a multi-agent active run exceeds safe thresholds.
type: skill
parameters:
  - handoff_path: string
  - run_manifest_path: string
supported_harnesses: [kimi, claude]
---

# Session Guardrails

## Purpose
Prevent context fatigue by inserting hard stops when session metrics cross danger thresholds.

## Threshold Types

Guardrails monitor the following metric types. Each type has Yellow / Red / Black levels with escalating actions. Specific threshold values and checkpoint prompt formats are defined in the operator's persona or project `.agents/skills/` override.

### 1. Turn Threshold

**Metric:** Total parent + sub-agent turns in current session.

| Level | Action |
|-------|--------|
| Yellow | Output a 1-paragraph status digest to the user (no pause required) |
| Red | **Force pause**. Present a checkpoint. Wait for human A/B/C/D selection. |
| Black | **Recommend landing or reset**. Unless human explicitly overrides, write escalate handoff. |

### 2. Sub-Agent Resume Threshold

**Metric:** How many times a single `agent_id` has been resumed for the same node.

| Level | Action |
|-------|--------|
| Yellow | Warn in status output: watch for circular fixes. |
| Red | **Force pause**. Recommend killing the agent and spawning a fresh instance with a compressed prompt. |
| Black | **Auto-kill the agent_id**. Replace with fresh instance. If parent cannot explain the root cause, escalate to human. |

### 3. Handoff Bloat Threshold

**Metric:** Word count of `handoff.md`.

| Level | Action |
|-------|--------|
| Yellow | Suggest summarization at next wrap. |
| Red | **Force compress** before any new sub-agent is spawned. Move historical rationale to project or central-node journal. |

### 4. Scope Drift Threshold

**Metric:** Files modified outside active run declared scope.

| Level | Action |
|-------|--------|
| Yellow | Warn and list the file. Ask user if it should be included. |
| Red | **Force pause**. Present drift analysis and options: include in scope (update run manifest) / revert those changes / split new active run. |

### 5. Investigate Ping-Pong Threshold

**Metric:** Failed root-cause hypotheses in `skills/investigate.md`.

| Level | Action |
|-------|--------|
| Red | **Auto-escalate to human** with the list of disproven hypotheses. Do not allow a 4th guess. |

### 6. Infra Leak Threshold

**Metric:** Consecutive turns spent on proxy, env vars, package versions, or build tools inside a code run.

| Level | Action |
|-------|--------|
| Yellow | Warn: "This appears to be an infrastructure issue inside a code run. Consider splitting an infra run." |
| Red | **Force pause**. Options: A) Move infra fix to a new run B) Hand-fix outside this session C) Provide one final attempt with explicit rollback plan. |

### 7. Run Lifecycle Checkpoint

**Trigger condition:** active run enters `blocked`, `ready-for-review`, `closed`, or ownership changes.

**Actions:**
1. Write a rich handoff (see format below) to ensure cold-start resumability
2. Update the run manifest (`status`, `owner`, `handoff_to`, `updated_at`, verification evidence) and synchronously increment the manifest `revision` and handoff `manifest_revision` per the stale-write guard
3. Suggest the user `/clear` and resume from the handoff -- the new session loads only bootstrap + handoff + named design docs, without prior conversation noise
4. The user may choose to continue without `/clear` -- this is not enforced

**Rich handoff format (appended to handoff.md):**
```markdown
### {YYYY-MM-DD} Run checkpoint: {old_status} → {new_status}
**Key files read:** {file list with 1-sentence summary of what was learned from each}
**Decisions made:** {decisions made this session, not recorded elsewhere}
**Completed changes:** {commit hashes or file list}
**Verification / Evidence:** {commands, screenshots, PRs, commits}
**Resume here:** open `{handoff_path}` (e.g. `{project}/.agents/runs/{run_id}/handoff.md`), then {exact next command/edit and expected result}
```

**Purpose:** The next session's agent can fully understand current progress by reading this handoff, without re-reading all files. This is better than timed auto-wrap -- it snapshots only at meaningful boundary points, not at arbitrary moments.

## Integration

`skills/implement-pipeline.md` must check thresholds at every node transition.
`skills/plan-discussion.md` must check turn count before each new round.

> **Conceptual definition and red flag overview: see `{{DOTPANEL_ROOT}}/protocol/reference/context-fatigue.md`.**

## Post-Checkpoint Protocol

After any Red or Black checkpoint:
1. Append the checkpoint summary to the end of handoff.md
2. If the human chooses reset, record the target commit hash
3. If the human chooses split, create a new repo-local active run and add a global pointer only if cross-repo resume is needed
