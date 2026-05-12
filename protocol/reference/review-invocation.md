---
name: Review tool invocation reference
type: reference
tags: [review, codex, kimi, tools]
---

# Review Invocation Reference

Operational details for invoking external reviewers. The methodology lives in `skills/code-review.md`; this file covers the CLI commands, workarounds, and templates.

## Harness Family Table

| Family | Harness | Sub-agent mechanism | External review capability |
|--------|---------|--------------------|-----------------------------|
| Claude | `claw` (npm `claude`) | `Agent` tool | Primary dev harness |
| Codex | `codex` CLI | codex sub-agent | Diff-native code review |
| Kimi | `kimi` CLI | kimi-cli sub-agent | Prompt-native design review |

## Codex

### Independence preflight

Before counting codex as cross-harness, check `~/.codex/config.toml`: inspect `model_provider` and the active provider's `env_key`. If codex resolves to the Claude/Anthropic family while the primary harness is also claw, route to kimi-cli instead.

Also verify the external process inherits the env var named by `env_key`. Do not print the value.

### Scope modes (mutually exclusive)

| Flag | What it reviews |
|------|-----------------|
| `--uncommitted` | Working-tree changes (staged + unstaged + untracked) |
| `--base <branch>` | Diff between HEAD and a base branch |
| `--commit <sha>` | Changes from a single commit |
| *(positional PROMPT)* | Custom-instructions mode; codex decides scope |

When using `--base`/`--commit`/`--uncommitted`, codex runs its built-in framework (correctness / architecture / tests / security). Do NOT also pass a positional PROMPT.

### Invocation

```bash
# Default framework (most common — branch vs main):
codex --sandbox danger-full-access review --base main --title "{summary}"

# Adversarial (PROMPT mode — handoff + adversarial brief):
codex --sandbox danger-full-access review --title "{summary}" "$(cat /tmp/codex-adversarial-brief.md)"
```

**Sandbox note:** On some Linux hosts, codex's default sandbox fails (`bwrap: loopback: Failed RTM_NEWADDR`). `--sandbox` is a global option — place it before `review`, not after.

**Long runs:** kick off via `Bash(run_in_background: true)`. Claude owns the lifecycle.

### Handoff document

Write a proper handoff — not a one-sentence prompt. Codex reads changed files independently; a vague prompt causes it to scan everything.

```markdown
## What Changed
{2-3 paragraphs: what each file does, why, what problem it solves.}

## Files to Review
{Every file with path and 1-line description.}

## Architecture Context
{Conventions from AGENTS.md. Layer boundaries, key rules.}

## Review Focus
{5-8 specific questions.}
```

## Kimi-cli

Use non-interactive print mode with an explicit work directory:

```bash
kimi --print -w "{repo}" --max-steps-per-turn 20 -p "You are reviewing a {design|code change} for {project}.
{Full review brief}

--- BEGIN {DESIGN|DIFF} ---
{content}
--- END ---

Review this. Output:
## Verdict: APPROVE | REQUEST_CHANGES | NEEDS_DISCUSSION
## Blockers
## Concerns
## Suggestions
## Blind Spots"
```

## Operator Cross-Backend Wrapper (fallback)

Same shape as kimi-cli prompt mode. The exact command is operator-private — see persona. Document the independence level as **cross-backend** (weaker than cross-harness).

## Adversarial Brief Template

Write to `/tmp/codex-adversarial-brief.md`, then invoke codex in PROMPT mode.

````markdown
<role>You are Codex performing an adversarial software review. Your job is to break confidence in the change, not to validate it.</role>

<task>Review the provided context as if you are trying to find the strongest reasons this change should not ship yet.
Target: {e.g. "branch X vs main"}
Focus: {Review Focus questions}</task>

<operating_stance>Default to skepticism. Assume the change can fail in subtle, high-cost, or user-visible ways until evidence says otherwise. Do not credit good intent, partial fixes, or likely follow-up work.</operating_stance>

<attack_surface>Prioritize expensive, dangerous, or hard-to-detect failures:
- auth, permissions, tenant isolation, trust boundaries
- data loss, corruption, duplication, irreversible state changes
- rollback safety, retries, partial failure, idempotency gaps
- race conditions, ordering assumptions, stale state
- empty-state, null, timeout, degraded dependency behavior
- version skew, schema drift, migration hazards
- observability gaps that hide failure</attack_surface>

<finding_bar>Each finding must answer: (1) what can go wrong, (2) why this code path is vulnerable, (3) likely impact, (4) concrete fix. No style nits or speculation without evidence.</finding_bar>

<calibration>Prefer one strong finding over several weak ones. If the change looks safe, say so and return zero findings.</calibration>

<output_format>For each finding:
- file, line_start, line_end
- severity: P0 / P1 / P2
- confidence: 0.0-1.0
- summary (one line)
- recommendation

End with overall verdict: APPROVE | NEEDS-ATTENTION | REJECT.</output_format>

--- BEGIN CONTEXT ---
{handoff content}
--- END CONTEXT ---
````

## Iterative Review Cadence

For ADR-tier proposals, expect 3-5 passes with progressively smaller deltas:

| Pass | Typical pattern |
|------|-----------------|
| 1 | Several blockers + concerns + nits |
| 2 | Partial fixes from pass 1; new issues from the fix attempts |
| 3 | Smaller; missed corners (matrix completeness, fail-closed) |
| 4 | Residual stragglers (stale comments, doc inconsistency) |
| 5 | Clean PASS |

Don't ship after pass-1 PASS unless genuinely clean.
