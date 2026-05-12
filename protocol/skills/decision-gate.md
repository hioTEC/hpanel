---
name: decision-gate
description: Three-step gate (Challenge / Classify / Audit) run before writing implementation code at plan, new-feature, refactor, upgrade, or new-tool moments. Output a Decision Audit block in the design doc.
type: skill
supported_harnesses: [claude, codex, kimi]
---

# Decision Gate

Run this gate before writing implementation code at any plan / new-feature / refactor / upgrade / new-tool moment, and append a **Decision Audit** block to the design doc.

## Step 1 — Challenge Scan

1. **Motive check** — Is this action aligned with the end goal, or drifting?
2. **Path audit** — What are the downsides of the current approach? Any path dependency or cargo-culting?
3. **Alternative** — Propose a faster, cheaper, or more elegant way. If none exists, state why.

## Step 2 — Classify Every Choice

| Class | Meaning | Action |
|-------|---------|--------|
| **Convention** | Industry standard, project convention, or obvious best practice. No real alternative exists. | Note it in the audit, move on. No user confirmation needed. |
| **Decision** | Real tradeoff with long-term consequences (architecture, cost, UX, schema). | Present to user with a clear recommendation. Wait for an answer before locking. |
| **Discretion** | Purely technical tradeoff, within project boundaries, reversible. | Agent decides, documents the choice and rationale. |

## Step 3 — Output: Decision Audit

Append this block to `design.md`, before the Decision Registry:

```markdown
## Decision Audit

### Conventions Followed
| # | Choice | Why it's convention |
|---|--------|---------------------|
| C1 | ... | ... |

### Decisions — Needs Your Input
| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | ... | A) ... B) ... | **B**, because ... |

### Agent Discretion
| # | Decision | Chosen | Rationale |
|---|----------|--------|-----------|
| A1 | ... | ... | ... |
```

## Rules

- Not everything is a decision. If there's no real alternative, it's a convention — don't waste the user's time.
- Each "Needs Your Input" item must include a clear recommendation. Never present raw multiple choice.
- High-impact decisions (data model, auth, deployment, pricing) get a full ADR record in the project ADR path declared by project `AGENTS.md`. Format follows `{{DOTPANEL_ROOT}}/protocol/rules/adr-template.md`.
- The Decision Audit must be written before `design.md` is marked `proposed`. If any Decision row is unanswered, the design stays `draft`.
