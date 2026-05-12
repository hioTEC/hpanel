---
name: improve-skills
description: Read recent session digests and propose workspace rule, skill, memory, harness, or audit updates based on recurring patterns.
type: skill
parameters:
  - lookback_days: number   # default 30
supported_harnesses: [kimi, claude]
---

# Improve Skills

## Purpose
Close the learning loop: turn repeated friction into permanent agent workspace
upgrades.

The canonical surfaces are:

| Surface | Use |
|---|---|
| `{{DOTPANEL_ROOT}}/protocol/rules/*.md` | General decision rules, gates, and operating policy |
| `{{DOTPANEL_ROOT}}/protocol/rules/index.md` | Load class and harness exposure registry for rules |
| `{{DOTPANEL_ROOT}}/protocol/skills/*.md` | Reusable procedures with a clear invocation shape |
| `{{DOTPANEL_ROOT}}/protocol/reference/*.md` | Cross-project facts, references, and durable lessons |
| harness wrappers | User-facing skill adapters that point to canonical skills |
| `dotpanel audit` | Mechanical enforcement for rules that must not rely on memory |

Do not create harness-local rule copies or file-level Claude skill symlinks.
Read `{{DOTPANEL_ROOT}}/protocol/rules/harness-bridge.md` before changing harness exposure.

## Process

1. **Gather Digests**
   - Scan project journals under `{project}/.agents/journal/` for the projects the operator has been working on (the operator can list them; persona is data-only and does not maintain a project registry)
   - Also scan the operator's central-node repo's `.agents/journal/` for cross-project / operator-infra entries (the operator designates the central node in their persona)
   - Filter for sessions with friction patterns or unresolved blockers over the last `lookback_days`
   - Skip digests that contain only one-off issues with no pattern

2. **Pattern Extraction**
   - For each digest, ask:
     > "If a rule, skill, memory entry, harness adapter, or audit check had existed, would this friction have been prevented?"
   - Group similar frictions

3. **Proposal Generation**
   - For each pattern, propose ONE of:
     - **Update existing rule**: add or sharpen a gate / constraint
     - **New rule**: add a reusable decision framework and register it in `rules/index.md`
     - **Update existing skill**: add a step, constraint, or example
     - **New skill**: create a reusable procedure with parameters and supported harnesses
     - **Update memory**: add a cross-project fact or reference
     - **Harness adapter update**: add or fix a thin wrapper for a user-facing skill
     - **Audit update**: enforce a rule mechanically via `dotpanel audit`
   - Write the proposed diff in a readable format
   - For Gate rules, include the required `workspace.md` router change
   - For user-facing skills, include Claude/Codex wrapper updates when supported
   - Do not add `~/.claude/commands/` or Codex plugin command files for
     workspace entries; use harness skill discovery.

4. **Human Review**
   - Present proposals grouped by impact
   - For each: "Approve / Modify / Skip"

5. **Apply Approved Changes**
   - Edit the canonical surface under `{{DOTPANEL_ROOT}}/protocol/` (or the persona for operator-private content)
   - If harness exposure changes, update wrappers and `symlink-registry.md` as needed
   - Run `dotpanel audit`
   - Run `git -C {{DOTPANEL_ROOT}} diff --check` on changed paths
   - Do not hand-push the operator's synced configuration repos. Publish through `dotpanel sync push` (or the `/sync` skill) after the user confirms.

## Anti-patterns
- Do not create a skill for something that happened only once
- Do not over-generalize a project-specific quirk into a global skill
- Do not write a skill without parameters — if it can't be invoked with different arguments, it's a memory entry, not a skill
- Do not add a rule without registering it in `{{DOTPANEL_ROOT}}/protocol/rules/index.md`
- Do not add a harness-local copy of a canonical rule or skill body
