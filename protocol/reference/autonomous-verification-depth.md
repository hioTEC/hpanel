# Autonomous verification depth — subagents must verify integration, not just artifact

> Cross-project lesson from the workspace consolidation v4 deployment (2026-05-04).

## The pattern

When delegating a multi-step batch (file edits + git ops + filesystem changes)
to an autonomous subagent, the subagent will report "all verifications PASS"
based on the verification commands it chose. **What it chose is rarely deep
enough.** A separate cross-tool review (here: codex final review) routinely
finds critical bugs the subagent missed.

In one concrete case, after the cleanup subagent reported 8/8 PASS, codex found 6
critical issues:
- The operator's session-bootstrap script still referenced deleted paths → `/go` was
  silently broken (subagent verified `dotpanel doctor` + `dotpanel audit`, never
  invoked the bootstrap script)
- `pyproject.toml` had license/classifier conflict → `python -m build` failed
  (subagent never built a wheel)
- `configure --check` skipped the conflict planner → could pass while real
  configure would fail (subagent ran the wrong code path)
- `README.md` still described v3 architecture (subagent updated
  `architecture.md` and considered docs done)
- Stale tests imported removed symbols (subagent didn't run pytest)
- Bootstrap cycle (historical, pre-slug-removal): identity-scaffolding subcommand
  required `init`; `init` required existing persona — circular (subagent never
  tried fresh-operator path)

## Rule

For any subagent batch that touches **cross-tool integrations** (the subagent's
own repo plus any external tooling that depends on it):

1. The subagent's verification list must include **every external consumer**
   of the changed surface, not just the commands inside the subagent's tool.
2. The subagent must explicitly try **the unhappy path** for each new feature
   (e.g., `--check` is useless if its verification only runs `--check`; you
   need to verify `--check` correctly fails on real conflicts).
3. The subagent must run the **packaging/build** step at least once, even if
   not deploying — packaging exposes config conflicts (license expressions,
   manifest globs, package data) that source-tree verification misses.
4. Documentation surfaces (`README.md`, top-level `AGENTS.md`, public-facing
   first-contact files) are part of the change set; updating
   `docs/architecture.md` does not update `README.md`.
5. Cross-tool integration test: if the subagent changed `tool A` but `tool B`
   reads from `tool A`'s outputs, the subagent must run `tool B` once before
   reporting PASS.

## Mitigation when the subagent budget is tight

If you must spawn a subagent without the depth above, **always** follow with a
fresh-context cross-harness review (codex or kimi) before treating the work as
shipped. The cleanup subagent in our case was working in good faith with
sufficient verification to pass its declared checks — but its declared checks
were narrower than reality. A separate reviewer found the gap in 5 minutes.

The reverse pattern (review without cleanup subagent) is cheaper but doesn't
parallelize execution; pick based on whether the changes are dispersed enough
to benefit from parallel execution.
