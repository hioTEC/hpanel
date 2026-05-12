---
name: code-review
description: Cross-harness dual review — sub-agent (same harness) + external reviewer (different harness) in parallel. Covers code, design, and plan review.
type: skill
parameters:
  - scope: string             # "code" | "design" | "plan"
  - input: string             # file path(s), diff, or design.md content
  - risk_level: low | medium | high
  - base_branch: string       # optional, for code review
supported_harnesses: [claude, codex, kimi]
---

# Review (Code / Design / Plan)

Every non-trivial change or design must be reviewed by **two independent reviewers from different harness families** before advancing. Same-harness review alone is insufficient — a model's blind spots are shared within its family.

## Cross-Harness Rule

```
Primary harness X
  → Sub-agent reviewer: same harness X
  → External reviewer: different harness Y
```

Three harness families: **Claude** (claw), **Codex** (codex CLI), **Kimi** (kimi CLI). Reviewers must come from different families. If the primary is claw:
- Prefer codex for code/diff-heavy reviews (diff-native)
- Prefer kimi-cli for design/plan reviews (prompt-native)
- Fallback: operator's cross-backend wrapper (document as cross-backend, not cross-harness)

Before counting an external reviewer as cross-harness, verify its resolved provider is in a **different model family** from the sub-agent. Same-family codex is NOT cross-harness.

## Resolver (Lightweight Self-Critique)

Use before proposing a plan or design — break your own anchoring bias.

Spawn a sub-agent in the same harness, but pass **only the document** as context. No workspace.md, no memory, no conversation history. The sub-agent reads with fresh eyes.

**Mandatory triggers:**
- design.md complete, before marking `proposed`
- refactor plan complete, before touching code
- 3 same-task commits without fixing the bug

**Resolver vs full Process:**

| | Resolver | Full Process |
|---|---|---|
| Trigger | Pre-proposal sanity check | Pre-merge / pre-deploy gate |
| Reviewers | 1 same-harness sub-agent | Sub-agent + cross-harness external (parallel) |
| Cost | Cheap | Heavy |
| Independence | Limited | Strong (different model families) |

## Process

### 1. Determine Scope

| scope | input | typical trigger |
|-------|-------|----------------|
| `code` | git diff or file list | implement stage review gate |
| `design` | design.md content | plan stage stealth challenge |
| `plan` | full plan doc + design.md | plan convergence review |

### 2. Select External Reviewer

Apply the cross-harness rule above. If both codex and kimi-cli are available: codex for code (diff-native), kimi-cli for design/plan (prompt-native).

### 3. Write the Review Brief

Both reviewers receive the **same neutral brief**. Facts only, no opinions.

**Code review brief:**
- **Project:** one-line from AGENTS.md
- **Architecture:** layer boundaries, conventions
- **What Changed:** which files, what each change does (no value judgments)
- **Design Intent:** quote from design.md or commit message ("No design doc" if absent)
- **Review Focus:** questions ("Does X handle Y?"), not conclusions ("X doesn't handle Y")

**Design/plan review brief:**
- **Design Intent:** what problem this solves
- **Key Decisions:** locked decisions from Decision Registry
- **Architecture Context:** existing constraints the reviewer needs
- **Review Focus:** 5-8 specific questions

**Rules:** no leading language ("unfortunately", "clearly"), no pre-conclusions, state what the code/design DOES not what it SHOULD do.

### 4. Launch Concurrent Reviews

Run sub-agent AND external reviewer **in parallel**, same brief to both.

- **Sub-agent:** spawn via Agent tool with the review brief + diff/design. Output: Verdict / Blockers / Concerns / Suggestions.
- **External reviewer:** invoke via the appropriate CLI tool. See `reference/review-invocation.md` for exact commands, sandbox setup, and adversarial brief template.
- **Adversarial mode** (when `risk_level: high`): external reviewer uses adversarial brief — skeptic framing, structured findings with file/line/severity/confidence. See template in `reference/review-invocation.md`.

### 5. Synthesize

```markdown
## Review Summary

### Consensus
{Points both agree on}

### Divergence
{Disagreements — state each position neutrally}

### Final Verdict: APPROVE | REQUEST_CHANGES | NEEDS_DISCUSSION

### Blockers (must fix)
### Concerns (should fix, can be follow-up)
### Suggestions

---
Reviewers: {sub-agent model} + {external tool} | Scope: {scope} | Independence: {cross-harness | cross-backend}
```

**Synthesis rules:**
- Either reviewer says REQUEST_CHANGES with concrete blocker → final is REQUEST_CHANGES
- Disagreement on severity → present both, let human decide
- Don't dismiss single-source findings — often the most valuable
- Both APPROVE with no blockers → APPROVE

## Review Checklist

### Code
- Correctness: does it do what design intent says? Error paths handled?
- Architecture fit: follows project conventions? Introduces coupling?
- Test coverage: happy path + edge cases tested?
- Security: auth, injection, secrets exposure?

### Design / Plan

For each focus area: (1) what could go wrong? (2) under what conditions? (3) earliest signal of failure?

- **Data consistency:** illegal states? Orphaned records, partial writes, dual sources of truth?
- **Concurrency:** simultaneous mutation? Locks, optimistic concurrency, idempotency?
- **Deployment:** assumes env vars / paths that differ in prod? Works on dev AND target?
- **API contract:** all fields consumed? Null vs empty assumptions? Invisible references on rename?
- **Failure modes:** step fails halfway? Retry / duplicate behavior?
- **Performance (optional):** O(n²)? Unbounded queries? Large files in memory?

Exit rule: if you cannot find at least one concrete risk per focus area, the review is not deep enough.
