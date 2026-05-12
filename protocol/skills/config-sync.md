---
name: config-sync
description: Sync the substrate's configured repos. Push, pull, diff, or get help. The protocol thin-wraps the substrate's configured sync tool.
type: skill
parameters:
  - command: push | pull | diff | help
supported_harnesses: [kimi, claude, codex]
---

# Config Sync

Two classes of synced content:

- The **persona host** (operator-private; contains the persona subtree the active agent reads). Path is operator-private — see persona for its location.
- **dotpanel** (this repo, public; contains protocol/, harness templates, the Python CLI). Configuration changes here may also need `dotpanel configure` to re-render harness adapters.

The substrate's `[sync]` table in `.dotpanel.toml` declares the exact list of repos and their leak-check modes. Harness output dirs (`~/.claude/`, `~/.codex/`) are **not** synced repos. They are rendered output; `dotpanel configure` regenerates them deterministically from dotpanel + persona at any time. Treat them as build artifacts, not source.

If `command` is provided and matches a subcommand (push/pull/diff/help), skip the prompt and go directly to that section.

## push

Skill = thin wrapper. Delegate writes to the substrate's configured sync tool — **never call `git add` / `git commit` / `git push` directly** on synced repos. The substrate's `[sync]` table in `.dotpanel.toml` defines repos and leak modes; the default sync command is `dotpanel sync` (built-in to dotpanel). Operators using a different sync wrapper override via `.dotpanel.toml [harness] sync_command`.

**Flow:**
1. Run the configured sync `status` (or equivalent) — show repo state across the synced repos.
2. For each dirty repo, show `git -C <repo> diff --stat` so the user sees scope (full diff on request).
3. Ask user: proceed with `push`? (single confirm, not per-repo).
4. On confirm: invoke the configured `push`. Report exit code + any safety-check failures.
5. If dotpanel itself was among the changes, the configured `pull` on other machines will trigger `dotpanel configure --check` then real configure (see `pull` below).

**Per-repo selective commit / custom message:** stop and do it deliberately with explicit file paths, then re-invoke the sync skill for publishing. Never use `git add -A` or hand-push synced repos. Harness slash entry point: `/sync` in Claude; `$sync` (or sync skill selector) in Codex.

**What's tracked:**
- The **persona host** (the operator's repo that hosts the persona subtree, e.g. dotfiles): contains the `persona/` data subtree (voice, identity, keyword-router rules, private reference) **plus** any operator-private substrate the host repo carries (secret store, infra inventory, optional `.agents/` for cross-project runtime if this repo serves as the operator's central node, etc.). Exact subtree layout is operator-private. Note: "persona" (the data subtree the agent reads) is a subset of "persona host" (the repo it lives in).
- **dotpanel**: protocol/, harness/, dotpanel/ (the Python package), docs/, tools/. The `persona` symlink at the dotpanel root is gitignored.

## pull

Sync remote changes to local for the substrate's configured repos. If dotpanel changed, this triggers `dotpanel configure` via the dry-run gate.

**Flow:**
1. Fetch all synced repos.
2. Show incoming commits per repo.
3. If all up to date → say so, skip to step 5.
4. Ask user: merge strategy per repo (ff-only / rebase / skip).
5. **dotpanel configure dry-run gate** (typically wired into the configured `pull` tool):
   - Run `dotpanel configure --check`. Exit 0 → proceed to real `dotpanel configure`. Exit 2 (validation) or other non-zero → preserve last-good adapters, print prominent stderr warning, but `pull` itself still exits 0.
   - If the configured tool does not run this automatically, invoke `dotpanel configure --check` then `dotpanel configure --harness all` manually after pull.
6. Run any other substrate-side post-pull hooks (e.g., SSH config regeneration). See persona for details.

## diff

Compare local vs remote (read-only) across the substrate's configured repos.

**Flow:**
1. Fetch all synced repos (quietly).
2. For each repo: show local diff + commits ahead/behind.
3. Present summary, suggest next action per repo (push / pull / nothing).

## help

```
sync — config sync for the substrate's configured repos (persona host + dotpanel)

Commands:
  <sync-tool> push    Sync local -> remote (show diff-stat, single confirm, then configured push)
  <sync-tool> pull    Sync remote -> local (show incoming, ask merge strategy, run dotpanel configure --check gate)
  <sync-tool> diff    Compare local vs remote (read-only)
  <sync-tool> help    This guide
```

Where `<sync-tool>` is the substrate's configured sync command (`dotpanel sync` by default; overridable via `.dotpanel.toml [harness] sync_command`). The harness slash entry renders the concrete command in the wrapper at configure time.
