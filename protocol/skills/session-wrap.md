---
name: session-wrap
description: Session close protocol for active runs, handoff/evidence maintenance, memory graduation, and commit/push.
type: skill
parameters:
  - touched_runs: string[]  # active run ids modified this session
supported_harnesses: [kimi, claude, codex]
---

# Wrap — Session Close

## When to invoke

**Must run** when at least one of:

- an active run's status, owner, scope, or evidence changed this session;
- a file was renamed, moved, or removed and downstream consumers reference it;
- durable knowledge was produced that does not yet live in code / ADR / spec / rule / skill / project memory;
- the operator explicitly says "wrap" / "收尾" / "结束 session".

**Skip** when:

- no active run was touched and no consumer-facing files were renamed/moved;
- the session was Q&A, read-only investigation, or a single small fix with no run-state implication.

Default: state-changing session → wrap; non-state-changing session → skip. Wrap is not a session-end ritual; it is a state-persistence step.

## Steps

### 1. Active Runs + Handoff

Output a structured proposal:

```markdown
## Active Run Update Proposal

| Run | Change | Note |
|-----|--------|------|
| {id} | status: active -> ready-for-review | {evidence} |
| {id} | BLOCKED | {blocker + owner + unblock condition} |
| {id} | close | {done predicate + evidence} |
| {id} | new | {why it needs cross-session / parallel execution} |
```

For each touched run:

- update repo-local run manifest (`status`, `owner`, `handoff_to`,
  `updated_at`, scope, verification/evidence)
- update `handoff.md` with Done / Next / Blocked / Touched / Verification /
  Resume here
- stale-write guard: read the current manifest `revision`, require the handoff
  frontmatter `manifest_revision` to match, then write manifest + handoff
  together with both values incremented by 1. If they differ, re-read and merge
  before writing.
- keep durable design truth out of handoff; move it to ADR/spec/roadmap/rules
- close a run only after evidence exists and durable knowledge has moved out

Active runs are repo-local. Each project owns its own `.agents/runs/active.yaml`
manifest and per-run handoffs. There is no global cross-repo active-run index;
resume from outside a project means navigating to that project's repo.

### 1.1 Retire Closed Runs

If a run is closed in this session — or you notice a previously-closed run
still sitting in `.agents/runs/` — retire it. Runtime is ephemeral; closed
runs do not stay in `runs/`.

Pre-retirement checklist (every item must be true):

- [ ] Architecture / boundary decisions live in project ADR/spec path
- [ ] Module contracts live in `src/{lib,components}/{domain}/spec.md` (or project equivalent)
- [ ] Product sequencing lives in project roadmap
- [ ] Cross-project methodology lives in `{{DOTPANEL_ROOT}}/protocol/reference/` or `rules/`
- [ ] Reusable procedure lives in `{{DOTPANEL_ROOT}}/protocol/skills/`
- [ ] Operational lesson (if any) lives in project or central-node journal

If anything is missing, graduate it first; only then retire.

Retirement (after graduation is complete):

1. `rm -rf {project}/.agents/runs/<id>/`
2. Remove the entry from `{project}/.agents/runs/active.yaml`
3. If `runs/` is now empty, remove the directory itself

**Never create `archive/` directories.** Git history preserves execution
detail. See `protocol/rules/content-principles.md` §Run Retirement.

### 1.5 Cascade Check

For files changed or removed, search references and update direct consumers in
the same session. For protocol-layer renames or moves, scan all synced
configuration surfaces (the operator's persona host, harness output dirs, and
any project `AGENTS.md` referenced from the run handoff). Use `rg` with the
old name as the pattern; broken references must be updated, not left to fail
loudly later.

### 2. Learnings Extraction

Write at most 3 durable learnings only if the session produced knowledge not
already captured in code/ADR/spec/rules.

| Kind | Destination |
|---|---|
| cross-project principle/method | `{{DOTPANEL_ROOT}}/protocol/reference/` or `{{DOTPANEL_ROOT}}/protocol/rules/` |
| project ground truth | project authority path from `{project}/AGENTS.md` |
| architecture decision | project ADR/spec path from `{project}/AGENTS.md` |
| reusable procedure | `{{DOTPANEL_ROOT}}/protocol/skills/{name}.md` |

### 3. Journal

**Default: do not write.** Most sessions do not need a journal entry — their
state is already captured in run handoffs, ADRs, project memory, or rules.

Write only when both hold:

- the session produced an operational lesson or migration history that **will
  still be useful 30 days from now**, AND
- it **does not fit any existing artifact** (handoff, ADR, spec, rule, skill,
  project memory).

Routing rule:

| Scope of the lesson | Path |
|---|---|
| State changes confined to one project | `{project}/.agents/journal/diaries/YYYY-MM-DD-{topic}.md` |
| Cross-project / operator infrastructure / protocol evolution | operator's **central-node** journal path (designated in persona) `.agents/journal/diaries/YYYY-MM-DD-{topic}.md` |

Persona itself stores **no journal** — runtime is project-layer. Project-scoped
diaries belong in the project's own `.agents/journal/`. When unsure, default
to project; only escalate to central-node when the lesson genuinely spans
multiple repos or is operator infrastructure.

### 4. Commit & Push

The operator's synced configuration repos publish through their own sync tool;
do not hand-push them. See your persona for the operator's sync command (the
`/sync` skill is the user-facing entry point in this protocol).

Project repos use normal git with explicit file lists; never `git add -A`.

## Maintenance

`/wrap` is for the session that just happened. Repo-integrity drift checks
(handoff `Resume here` presence, manifest/handoff revision parity, orphaned
index entries, stale evidence/memory, broken `AGENTS.md` links) live in
`{{DOTPANEL_ROOT}}/protocol/reference/run-integrity-audit.md`. Run that
checklist every 3-5 sessions, separately from `/wrap`.
