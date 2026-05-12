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

## Thresholds & Actions

### 1. Turn Threshold

**Metric:** Total parent + sub-agent turns in current session.

| Level | Threshold | Action |
|-------|-----------|--------|
| Yellow | 30 turns | Output a 1-paragraph status digest to the user (no pause required) |
| Red | 50 turns | **Force pause**. Present a 5-sentence checkpoint. Wait for human A/B/C/D selection. |
| Black | 100 turns | **Recommend landing or reset**. Unless human explicitly overrides, write escalate handoff. |

<!-- User-facing checkpoint prompt — Chinese per voice.md interaction rule -->
**Red checkpoint prompt template:**
```markdown
**强制 Checkpoint — 已运行 {N} turns**

1. 原始目标: {active run outcome / scope summary}
2. 最后 atomic commit: {commit hash + message}
3. 当前正在改: {file + problem}
4. 阻塞点: {blocker}
5. 范围偏离: {none / slight / significant}

请选择:
[A] 继续，方向正确
[B] 我要看 diff 再决定
[C] 回退到 commit {hash} 重新从干净状态开始
[D] 这已超出原 scope，拆成新 active run
```

### 2. Sub-Agent Resume Threshold

**Metric:** How many times a single `agent_id` has been resumed for the same node.

| Level | Threshold | Action |
|-------|-----------|--------|
| Yellow | 3 resumes | Warn in status output: "{role} has been resumed 3 times; watch for circular fixes." |
| Red | 5 resumes | **Force pause**. Recommend killing the agent and spawning a fresh instance with a compressed prompt. |
| Black | 8 resumes | **Auto-kill the agent_id**. Replace with fresh instance. If parent cannot explain the root cause, escalate to human. |

### 3. Handoff Bloat Threshold

**Metric:** Word count of `handoff.md`.

| Level | Threshold | Action |
|-------|-----------|--------|
| Yellow | 300 words | Suggest summarization at next wrap. |
| Red | 500 words | **Force compress** before any new sub-agent is spawned. Move historical rationale to `{project}/.agents/journal/diaries/YYYY-MM-DD-{run}.md` (project-scoped) or the operator's central-node `.agents/journal/diaries/YYYY-MM-DD-{topic}.md` (cross-project). |

### 4. Scope Drift Threshold

**Metric:** Files modified outside active run declared scope.

| Level | Threshold | Action |
|-------|-----------|--------|
| Yellow | 1 file outside scope | Warn and list the file. Ask user if it should be included. |
| Red | 3 files outside scope | **Force pause**. Present drift analysis and options: include in scope (update run manifest) / revert those changes / split new active run. |

### 5. Investigate Ping-Pong Threshold

**Metric:** Failed root-cause hypotheses in `skills/investigate.md`.

| Level | Threshold | Action |
|-------|-----------|--------|
| Red | 3 failed hypotheses | **Auto-escalate to human** with the list of disproven hypotheses. Do not allow a 4th guess. |

### 6. Infra Leak Threshold

**Metric:** Consecutive turns spent on proxy, env vars, package versions, or build tools inside a code run.

| Level | Threshold | Action |
|-------|-----------|--------|
| Yellow | 10 turns | Warn: "This appears to be an infrastructure issue inside a code run. Consider splitting an infra run." |
| Red | 20 turns | **Force pause**. Options: A) Move infra fix to a new run B) Hand-fix outside this session C) Provide one final attempt with explicit rollback plan. |

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
