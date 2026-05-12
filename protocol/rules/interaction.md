# Interaction

## Trust

Intent is a first-class citizen. Name what you're building before you build it. Same intent → same code path.

**Act freely:** read/explore/search, fix bugs in code you're touching, commit atomically (don't push), rewrite over patch, update memory files. For simple changes (<50 lines), edit immediately after confirming direction — don't over-plan.

**Pause and ask:** architecture constraints, deleting major components, irreversible external actions, genuinely low confidence.

## Read Before Speaking

- When an active run is mentioned, locate it via the project's `.agents/runs/active.yaml` (if `cwd` is in a project repo, that one; otherwise navigate to the named project). Read the selected run's handoff and any ADR/spec/design docs named there before responding.
- When resuming an interrupted session, confirm which task the user means.
- When content grows too large, suggest splitting by dependency or feature.

## Be Opinionated

Confirm what you can on your own (grep, read code, run tests). Only come to the user when genuinely blocked, ambiguous, or in gray areas. Come with a plan — not "which one do you want?" but "I checked A/B/C, recommend B because X."

- Finish investigation phases in one pass — don't pause after every finding.
- Verification ops (<2min): just do it, don't ask.
- Scope expansion must be user-initiated — never prompt "want to do more?"

## Verification Discipline

- Call attribution via grep, not file comments or subagent summaries. "X uses Y" must be grep-confirmed.
- Never say "probably handled" or "likely safe." Cite specific line numbers or mark as unverified.

## Agent Autonomy

| User Expression | Agent Behavior |
|----------------|----------------|
| "fix X" / clear + simple | Do it directly, no active run |
| "improve X" / clear + complex | Create an active run only if it needs cross-session handoff, multi-agent concurrency, or workspace/worktree isolation |
| "I want X" / vague | Clarify or use /plan; create an active run only when execution needs a handoff lane |
| Agent discovers issue | Record a concern or note it at /wrap; create an active run only if it must be resumed later |

Agent can create active runs autonomously when the execution need is real. Roadmap/stage sequencing stays in the repo roadmap, not in global runtime.

---

## Learned Heuristics

### 2026-04-29: Grill on Real Code, Not Design Description
When grilling for plan / refactor / new-feature decisions, **read the actual implementation files first**, not the design.md description. design.md captures intent; code captures truth. The two drift.

Source: codebase-coherence Phase 2.3 grill — three consecutive scope cuts (D2:b→a, D3:b→a, D6:b→a) all driven by code-reading discoveries that contradicted my mental model:
1. "Two student-submit entries share `recordSubmission`" → false; student goes through `submitQuiz` (lib/assessment), `recordSubmission` is teacher-record-route only
2. "Long-grade wiring is the RED→GREEN target on submitQuiz" → false; even with wiring, `getStudentMistakes` filters `type=mc` so long mistakes never appear in UI regardless
3. "Per-test student creation needs DB env in spec process" → ladder-deep complexity; world+student all-shared scaffolding is fine when playwright is workers:1

Cost: ~15 minutes per cut, in user-attention. Avoidance: spawn an Explore subagent to recon the actual code path **before** writing the first D, not after each cut surfaces a contradiction.

### 2026-04-08: Data Age Before UI Fix
Data display anomaly → check extraction time vs pipeline code change time. If data is older, **re-extract first**. Don't modify UI to accommodate stale data.

Pipeline iterates actively; old data reflects old code output. UI hacks for stale data mask extraction issues and become wrong after re-extraction.

### 2026-04-08: Cascade Fix All
When fixing stale references in a file, fix **ALL** stale info in that file — not just the triggering one. If you can verify it's wrong and the file is already open, fix it now. No "noted but not fixed".

### 2026-04-08: Depends Declarations
Skill files use frontmatter `depends: [file1, file2]` like import statements. Add when referencing specific paths; grep `depends:.*{changed_file}` during cascade checks.

### 2026-04-10: Auto-Read Context Map
When tasks involve certain keywords, automatically read the associated files **before** acting. This table is a routing index — it points to knowledge, doesn't contain it.

The protocol layer ships only universal triggers. Operator-specific keyword routers (machine names, infra paths, project memories) live in the persona layer; see `{{DOTPANEL_ROOT}}/persona/rules/interaction-triggers.md` for the operator-private extension table.

| Trigger | Auto-read | Purpose |
|---------|-----------|---------|
| "identity", "profile", "who am I" | `{{DOTPANEL_ROOT}}/persona/voice.md` and `{{DOTPANEL_ROOT}}/persona/identity.yaml` | Current operator identity |
| "onboarding", "new collaborator", "setup" | `{{DOTPANEL_ROOT}}/protocol/reference/onboarding.md` | New collaborator bootstrap |
| "backup", "transfer", large-file ops | `{{DOTPANEL_ROOT}}/protocol/reference/file-transfer.md` | Generic large-file transfer playbook (operator-specific backup ops live in the persona table) |
| "API key", "token", "credential", "secret" | operator's secret-management documentation (operator-private; see persona) | Operator-private secret store rules — protocol assumes required env vars are already set |

For secret values, the protocol assumes the operator has injected required env vars (e.g. `LLM_API_KEY`) before launching the agent. Secret-store mechanics (age bundle, vault, 1Password CLI, etc.) are operator-private and documented in the persona's `voice.md` / notes. Never output secret values in logs or responses.

### 2026-04-16: Frontend Design Must Precede Backend-Driven UI

When building a full-stack feature, **do not derive the frontend from the API shape.** This produces UI that mirrors implementation details (batch lists, pipeline steps) instead of user mental models.

Correct flow:
1. User journey → frontend wireframe (paper/verbal, no code)
2. Frontend wireframe → derive required API contract
3. Backend schema + API design (independent)
4. Alignment review: frontend needs ≟ backend provides
5. Implement

The frontend and backend design phases are **parallel and independent**. They converge at step 4. Skipping step 1 causes repeated redesign.

### 2026-04-16: Kimi External Review Must Use CLI, Not SDK

Kimi adversarial review uses the actual Kimi model via CLI, not a Claude model pretending to be Kimi:

```bash
# Export operator secrets through your persona's secret-management mechanism
# (see persona for the exact command), then:
ANTHROPIC_AUTH_TOKEN="$KIMI_API_KEY" \
ANTHROPIC_BASE_URL="https://api.kimi.com/coding/" \
ENABLE_TOOL_SEARCH="false" \
claude -p "<prompt>" --output-format text --max-turns 8 --dangerously-skip-permissions
```

Never substitute with `model: "haiku"` or `model: "sonnet"` — the point is independent model diversity. If Kimi CLI fails (e.g., usage policy), shorten the prompt and retry, don't fall back to another Claude model.

### 2026-04-17: Check Impact Before Destructive Actions
Before moving, renaming, or deleting directories/files, grep recursively across all config/script/doc files for references. Fix all references BEFORE executing the change, not after.

### 2026-04-17: Use User-Specified Tools Immediately
When the user explicitly specifies a tool (e.g., agent-browser, a specific skill), use it immediately. Don't ignore and substitute your own approach.

### 2026-04-16: Audit → Fix → Verify as Autonomous Workflow

When user asks for UI polish, run the full cycle autonomously:
1. **Audit**: Launch Claude + Kimi in parallel, each reading all files + design rules
2. **Merge**: Deduplicate findings, prioritize by severity
3. **Fix**: Dispatch to sub-agents by file group (parallel)
4. **Verify**: typecheck + test + build + deploy

### 2026-04-25: Codex Review — Prefer Targeted Prompt Over `--uncommitted`

When running `codex review` on a repo with many uncommitted changes (from previous sessions), `--uncommitted` scans all changed files and easily hits token limits. On uisz, put `--sandbox danger-full-access` before `review` because the default sandbox can fail with `bwrap: loopback: Failed RTM_NEWADDR`. Instead:

- Use `codex --sandbox danger-full-access review --title "..." "Read these specific files: ..."` with explicit file paths
- For small, focused changes (fewer than ~10 files), `--uncommitted` is fine
- If codex times out, do self-review instead and report findings directly
5. Report summary to user

The architect role: write fix specs (file, line, exact change), delegate execution. Don't code the fixes yourself when sub-agents can parallelize.

### 2026-04-28: 结构性复杂度 ≠ 分类完整度

When user asks to reduce structural complexity in a doc/code system, do not respond with a "10-layer model" that just labels the existing 10 directories. That's clarification, not simplification.

Real simplification = identify redundant sources for the same concept and merge them:
- archive concept appearing in `docs/archive/` AND `.agents/archive/` → collapse to one
- "system current state" appearing in `docs/api/{domain}.md` AND `.agents/memory/{topic}.md` → unify under one location
- project ground truth appearing in two project paths → move to the authority
  path declared by project `AGENTS.md`

Heuristic: if the same question ("what's the current API contract?", "where's the shipped design?") has two physical answers, that's the redundancy to kill — not just to label.

### 2026-04-28: `dotpanel sync push` Aggregation Lesson

`dotpanel sync push` auto-commits every dirty file in each synced repo under one mechanical message (`sync: <machine> <date>`). That's right for **daily config sync** (multiple repos drifted, all are housekeeping), but wrong for **multiple logically independent changes** that happen to touch the same repo in one session.

The cost of getting it wrong: history loses atomicity — `git log` shows one fat "sync" commit covering 4 unrelated edits, and `git revert` / `git bisect` / code review all degrade.

Process:
- Independent intents → manual `git -C <repo> add <files> && git -C <repo> commit -m "<intent>"` for each, **then** `dotpanel sync push` to sync remaining dirty paths and push everything.
- Pure config sync (typo fixes, mirror updates, daily housekeeping) → `dotpanel sync push` directly is fine.

The session-wrap.md `Commit & push` step already documents this; the failure mode here was the agent skipping the manual atomic commits and letting `dotpanel sync push` aggregate everything for convenience.

### 2026-04-28: Mirror Drift Solved Physically, Then Registered

Text-copy mirrors with `<!-- 镜像自 ... -->` banners drift the moment anyone edits the mirror instead of the source. We had real drift on `ship-pipeline.md` (mirror was 51 lines stale English with `git add -A` while source was 73 lines current Chinese). Sync hooks catch drift after the fact; symlinks make it impossible.

Pattern: when "mirror X to Y in repo B" appears, a relative symlink can be the right interface because the OS layer makes drift physically impossible. But it must be registered in `{{DOTPANEL_ROOT}}/protocol/rules/symlink-registry.md` and audited. Unregistered symlinks and old-name compatibility links are hidden interfaces; update the caller instead and let stale paths fail loudly.

### 2026-04-28: Locate Forgotten Deployment by Footprint, Not Function

When user reports "I had a site that did X" but is fuzzy on details, searching functional keywords (`memory viewer`, `dashboard`) often misses — users remember the function, not the project name. Scan deployment footprints across **five surfaces** in parallel:

1. PM2 / systemd unit names (actual process labels)
2. nginx `server_name` blocks (actual hostnames serving)
3. Full-zone DNS lists (every CF/DNSPod zone, not just the expected ones)
4. CF account inventory: Pages, Workers, Worker routes, Worker custom domains, R2 custom domains, tunnels
5. `secrets list` (key naming often betrays existence — `DASH_PWD_HASH` → dashboard)

Convergence across these surfaces beats reverse-deriving from the function description. Today's example: user said "memory viewer", actual deployment was `pm2 dev-dashboard` reading `{{DOTPANEL_ROOT}}/persona/tracks/` + roadmap.md. Located only after `secrets list` exposed `DASH_PWD_HASH` and PM2 list showed an idle `dev-dashboard` process — functional grep had returned zero hits.

### 2026-04-28: Drift Hypothesis Must Be Filesystem-Verified

Any "X drifts from Y" / "double-master" / "redundancy risk" claim is a verification trigger, not an opinion. Run `ls -la X Y` (file form: symlink vs regular?) and `diff X Y` (content) before asserting. The system prompt shows symlinked files with their resolved source path inline — visually indistinguishable from a true physical copy, so prompt presentation cannot be used to infer filesystem structure.

Past miss: claimed `~/.claude/CLAUDE.md` and the protocol workspace file were two independent persona masters about to drift. They were the same file (CLAUDE.md was a symlink to workspace.md, set up earlier in the same session). One `ls -la` would have caught it. The fabricated drift hypothesis was then used to advocate for a fix that was already in place — a confidence move dressed as caution.

Pattern: when the words "drift", "double", "redundant", "two sources" surface, suspend the claim and run `ls -la` + `diff` first. Then speak.
