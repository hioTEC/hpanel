---
name: Run integrity audit
description: Periodic checklist for active-run state, handoffs, memory hygiene, and project AGENTS.md links. Run every 3-5 sessions, separately from /wrap.
type: reference
tags: [active-runs, audit, maintenance]
---

# Run Integrity Audit

A small set of integrity checks that catch drift between active-run state and
its on-disk artifacts. Run every 3-5 sessions per project, or whenever
something feels off (mismatched handoff state, stale memory references).

Active runs are **repo-local**: this audit operates on a single project's
`.agents/runs/` and `.agents/memory/`. There is no global active-run index.

This is intentionally **separate from `/wrap`** so the session-close path stays
focused on the session that just happened. Audit is about accumulated drift,
not the current session.

## Checks

| # | Check | Failure smell |
|---|-------|---------------|
| 1 | Each active-run `handoff.md` has a `Resume here` section | Next session resume picks wrong reentry point |
| 2 | Active-run manifest `revision` matches each handoff `manifest_revision` | Two writers raced; one is stale |
| 3 | Closed runs have verification/evidence and no unresolved blockers | Closure was premature |
| 4 | **No closed runs sit in `runs/`.** Closed runs must be retired (deleted) once durable knowledge has graduated to ADR/spec/rule/roadmap. See `protocol/rules/content-principles.md` §Run Retirement | Runtime accumulating; runs/ becoming a graveyard |
| 5 | **No `archive/` directories exist** (`.agents/archive/`, `docs/archive/`, etc.) | Archive convention drift; git history is the archive |
| 6 | Historical `.agents/evidence/**` folders are not being treated as current authority | Evidence drift — old data masquerading as truth |
| 7 | Memory files are not stale or absorbed (i.e. their content has not migrated to ADR/spec/code without removing the original) | Two sources of truth |
| 8 | Project `AGENTS.md` links still point to existing files | Broken doc-routing surface |

## Procedure

1. Open the project's `.agents/runs/active.yaml` to enumerate active / blocked / ready-for-review runs.
2. For each entry, open the per-run handoff and run checks 1-3.
3. List directories under `.agents/runs/`; flag any that are not in the manifest (check 4 — closed-but-not-retired).
4. `find {project} -type d -name archive` should return nothing under `.agents/` or `docs/` (check 5).
5. Open `{project}/AGENTS.md` and resolve every link (check 8).
6. Sweep `.agents/evidence/**` and `.agents/memory/` for staleness signals (checks 6-7): timestamps older than 30 days *and* contradicted by current code, or content that already exists in an ADR/spec.
7. Report findings as a punch list. Fix or open follow-up runs; do not fix silently.

## What this audit is NOT for

- It does not commit or push — `/wrap` and `/dot` own publication.
- It does not write new memory entries or ADRs — fixes go through their normal authoring path.
- It does not modify `voice.md` / protocol files — those have their own review cycle.
