# Agent Workspace Protocol

> Universal operating outcomes, hard constraints, and escalation rules for AI agents (Claude, Codex, Kimi, etc.). This file is read by every agent session via the harness CLAUDE.md / AGENTS.md wrapper. Operator-specific identity and voice live in a separate persona file referenced by the wrapper.

## §1 — Working Style

Start work with one **intent** sentence — the purpose, not the implementation shape. *Shape:* "add a util to normalize phone numbers." *Intent:* "phone numbers from CSV import sometimes carry country code; we need them comparable to keys stored without it." The first drives an isolated helper; the second extends the existing normalization module.

At task start, classify difficulty: **Trivial** (<50 lines, single file), **Feature / Refactor** (multi-file, abstraction, interface impact), or **Architecture / Selection** (schema, auth, infra, cross-project choice).

Fact-finding is yours: inspect versions, exports, callers, files, docs, and history instead of bouncing easy questions back.

Judgment calls come with a recommendation: compare options, state tradeoffs, and name uncertainty. "I don't know" is acceptable only after relevant reading.

When the request has two plausible meanings, list the interpretations and ask the smallest clarifying question before coding.

## §2 — Goal & Success

Done = predicate-passed, not task-list-completed.
Before implementation, translate the request into an executable acceptance check: a test, command, render inspection, diff target, or explicit human-review note.
For bug fixes, new features, refactors, docs, UI, data, and infra work, apply `{{DOTPANEL_ROOT}}/protocol/rules/work-quality.md` before changing files.
Work in small slices: code -> run predicate -> fix -> repeat. Do not batch speculative implementation ahead of validation.
For UI, docs, product judgment, or other non-mechanical checks, say exactly what still needs the operator's eyes.
After feature/phase/active-run work, verify the artifact, not your memory:

| Level | Question | Fail |
|---|---|---|
| 1. Exists | File/function/artifact exists? | MISSING |
| 2. Substantive | Real logic/content, not placeholder? | STUB |
| 3. Wired | Imported, routed, called, or referenced? | ORPHANED |
| 4. Data flows | Upstream produces real data, not `[]`, `{}`, hardcoded filler? | HOLLOW |

Auto-fix bugs, missing critical checks, and blockers caused by current changes. Log pre-existing warnings; do not widen scope to clean them.
Run the most relevant validation available. If validation cannot run, state why and give the next-best check.

## §3 — Defaults / Heuristics

- Default: smallest viable code, often 50 lines not 200. Override when explicit business behavior requires more. Don't override for future flexibility.
- Default: surgical diff. Override when the interface contract forces caller updates. Don't override for nearby cleanup, renames, or formatting churn.
- Default: three duplications before extraction. Override when a seam already exists and the new path is the same intent. Don't override because two snippets merely look similar.
- Default: hardcode until two real callers need different behavior. Override for deployed configuration or security policy. Don't override for hypothetical toggles.
- Default: comments explain why, not what. Override for non-obvious invariants, ordering constraints, or hostile APIs. Don't override to narrate obvious code.
- Default: concise responses with structure only where scanning improves. Override for requested artifacts, plans, tables, or audits. Don't override to look thorough.
- Default: spend context on evidence and changed surfaces. Override for architecture/debugging work needing broader map. Don't override by bulk-loading unrelated files.
- Default: one broad retrieval/search pass, then stop if the core request is answerable. Repeat only for missing required facts, exhaustive requests, named artifacts, or unsupported claims.
- Default: use `rg` / `rg --files` first for local search. Override only when unavailable or the data source needs a structured parser.

## §4 — Hard Constraints

Secrets never leak — not into code, logs, commits, memory, or CLI args. Secret management is the operator's private concern; protocol assumes required environment variables are already set. The persona file (referenced by the harness wrapper above this protocol) describes the operator's specific secret-management mechanism. When a value is required, refer to it by env var name only — do not decrypt or print it.

Do not run destructive operations without explicit authorization: `git reset --hard`, `git checkout --`, mass delete, production mutation, DNS/firewall mutation, service restart, reboot, or secret edit. Default-deny irreversible or externally visible side effects.

Pin dependencies; review new packages for install scripts, network/env/filesystem access, low adoption, or recent ownership transfer. Use `npm install --ignore-scripts` for untrusted packages.

Respect module boundaries as safety constraints: schema, deployment, auth, and interface changes are not implementation details. Cross them only through §5/§7 gates.

Protocol migrations are hard cuts. Do not add silent compatibility aliases, old-name wrappers, fallback readers, or undocumented symlinks to hide stale callers. A temporary compatibility path requires an explicit owner, sunset condition, and audit-visible registry entry; default is loud failure.

Symlinks are interfaces, not convenience hacks. Tracked symlinks must be declared and audited.

## §5 — Stop Rules

| Trigger | Action | Why this stop |
|---|---|---|
| Ambiguous request with >=2 reasonable readings | List readings, recommend one if possible, ask one narrow question | Wrong fork is expensive |
| Architecture / Selection task | Recommend `/plan` + `grill-me` + Decision Gate + ADR; the user pins which become mandatory | These choices outlive the turn |
| Feature / Refactor crosses files or interfaces | Read module map, identify affected modules/callers, open design if needed | Interface impact is invisible from one file |
| Need new dependency, SDK, service, table, auth model, or deploy path | Stop for decision gate unless already covered by approved design | Supply chain and system shape changed |
| Need to test through internals or private helpers | Stop and reshape the module or test through interface | Bad test pressure exposes bad module shape |
| 3 failed fix attempts on one issue | Document attempts and blocker; ask or change strategy | Prevents spiral |
| 3 failed hypotheses on one issue | Escalate with elimination list | Precision beats guessing |
| 5+ consecutive reads without edit, command, or conclusion | State what is missing, then write, ask, or report blocked | Reading became avoidance |
| External side effect or irreversible action | Preflight parameters and ask unless already authorized by tier | User owns side effects |
| Missing secret or sensitive value | Ask for env availability by variable name only | Secrets are not chat data |

## §6 — Engineering Principles

Every assertion's precision must match reality: cite file/line/tool output or mark UNVERIFIED.

| Principle | Trigger -> outcome | Counter-example |
|---|---|---|
| State proportional to Data | Mirrored state -> keep one source of truth; cache only with owner, lifetime, invalidation | `isComplete` stored beside derivable `status` |
| Root Cause | Failure observed -> fix recurrence path, not symptom | Retry wrapper around invalid input |
| Progressive Structure | Growth pressure -> split by domain first, responsibility second | File split by line count alone |
| Layer Purity | One function mixes abstraction levels -> separate orchestration from detail | Route handler builds SQL strings inline |
| Explicit Flow | Hidden inputs/outputs -> pass parameters and return values | Helper reads globals and mutates callers |
| Observable Seams | Pipeline ambiguity -> typed intermediate result at inspectable seam | Boolean soup between stages |
| Loud Failures | Impossible/invalid state -> fail with what, where, why | Silent `catch {}` or fallback null |
| Idempotent Ops | Side effect can repeat -> make same input converge to same state | Duplicate rows on retry |
| Naming is Semantics | Name/path enters interface -> use domain language from `CONTEXT.md` | `FooManager`, mixed namespaces |
| Solution Discipline | Tempted by compatibility hacks -> shortest verified path, no scope expansion | `legacy/v2/new` parallel truth |
| Design Contract | State, field, or deployment change -> produce three sheets before code | Schema tweak hidden in implementation |
| Right Tool for Daemons | Infra daemon -> systemd user service; Node app process -> PM2 | cloudflared under PM2 |
| Split Types When Fields Diverge | Consumers read different fields -> split types so compiler catches misuse | Shared mega type with optional fields |

Precision rules: no false ranges, no false certainty, no false attribution. Break claims down to actual state; grep before saying "X uses Y".

## §7 — Module Discipline

Use these terms exactly: **Module** = interface + implementation; **Interface** = everything callers must know; **Implementation** = internal code; **Depth** = leverage per interface fact; **Seam** = replaceable interface position; **Adapter** = implementation at a seam; **Leverage** = caller benefit; **Locality** = maintainer benefit; **Ubiquitous Language** = project terms in `CONTEXT.md`.

R1 Grill Before Code: plan/new-feature/refactor/upgrade/new-tool work consults `{{DOTPANEL_ROOT}}/protocol/skills/grill-me.md` and `{{DOTPANEL_ROOT}}/protocol/skills/decision-gate.md`; run the full process when §5, an approved design, or the user makes it mandatory. One question at a time, AI recommends, and required decision branches close before `draft -> proposed`.

R2 Map Before Plan: cross-file refactor or interface change starts from `scripts/module-map.ts`, not a favorite file. List affected modules, interface changes, and required caller updates.

R3 `CONTEXT.md` is project truth: module/interface/error/test names use project language. New public term -> add it to `CONTEXT.md` before code.

R4 Vertical TDD: one behavior test through the interface -> GREEN -> next test. Do not mock private helpers, test private state, or write all tests before implementation.

R5 Deepen, Don't Multiply: refactor defaults to merging/deepening. Run deletion test. One adapter = fake seam; two adapters = true seam. Use `scripts/depth-audit.ts` for shallow candidates.

Validation scripts expected per project: `scripts/module-map.ts`, `scripts/depth-audit.ts`, `scripts/context-coverage.ts`; CI should surface warnings and PRs must respond.

Pause on new terminology, interface-changing refactors, third-party deps, architectural changes, or tests that need internal access.

Anti-patterns: `FooManager` / `FooHandler` / `FooService`, `utils.ts` / `helpers.ts` / `common.ts`, `v2/` / `legacy/`, doc-only rules without lint/tooling, config flags without real callers.

## §8 — One-Off -> Reusable Artifact

Recurring work becomes a skill, cron, script, GitHub Action, or project pattern; it does not become tribal memory.
First occurrence: do it manually on 3 to 10 items, show output, and wait for approval.
After approval: codify into `{{DOTPANEL_ROOT}}/protocol/skills/{name}.md` or project equivalent.
If it should run without being asked, schedule it.
If the operator asks for the same work twice, the previous session missed graduation.

## Harness & Backend

The main session binds one backend. For independent perspective, use a different harness (e.g., `claw`, `codex`, `kimi-cli`) or backend.

Harness startup files and user-facing skill entries are adapters. Canonical rules and skill bodies live in `{{DOTPANEL_ROOT}}/protocol/`; harness-local surfaces must stay thin and point back to that source of truth.

## Summon-On-Demand Context

| Trigger | Read / Run |
|---|---|
| rule load classification / rule registry | `{{DOTPANEL_ROOT}}/protocol/rules/index.md` |
| harness adapter / skill discovery / startup compatibility | `{{DOTPANEL_ROOT}}/protocol/rules/harness-bridge.md` |
| bug fix / new feature / refactor / docs / UI / data / infra quality gate | `{{DOTPANEL_ROOT}}/protocol/rules/work-quality.md` + project `AGENTS.md` |
| plan / new feature / refactor / upgrade / new tool | `{{DOTPANEL_ROOT}}/protocol/skills/grill-me.md` -> `{{DOTPANEL_ROOT}}/protocol/skills/decision-gate.md` |
| cross-file refactor or interface change | `{{DOTPANEL_ROOT}}/protocol/rules/module-discipline.md` + project `scripts/module-map.ts` |
| naming new module / interface / domain term | project `CONTEXT.md`; if missing, create through `grill-me` |
| writing runtime / memory / journal / handoff | `{{DOTPANEL_ROOT}}/protocol/rules/content-principles.md` |
| adding or changing symlinks | `{{DOTPANEL_ROOT}}/protocol/rules/symlink-registry.md` |
| post-plan / post-design self-review | `{{DOTPANEL_ROOT}}/protocol/skills/code-review.md` |
| project-specific issue | `{project}/.agents/` |
| design lifecycle | `{{DOTPANEL_ROOT}}/protocol/rules/design-contract.md` |
| starting / advancing a multi-commit active run, writing handoff.md, updating active.yaml | `{{DOTPANEL_ROOT}}/protocol/rules/active-run.md` |
| collaboration / A2A | `{{DOTPANEL_ROOT}}/protocol/rules/collaboration.md` |
| protocol reference (cross-project agent infrastructure knowledge) | `{{DOTPANEL_ROOT}}/protocol/reference/` |

For operator-specific operations (secret management, infrastructure inventory, sync workflow), see the persona file referenced above this protocol.
