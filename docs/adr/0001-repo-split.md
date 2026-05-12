# ADR-001: Repo Split

Date: 2026-05-04
Status: proposed
Related Run: workspace-consolidation-2026-05

## Context

A consolidated agent workspace put public protocol and operator-private
identity, voice, machine inventory, and secrets in the same publication unit.
Earlier iterations tried to make that safe with identity-isolation lint,
file-class taxonomy, render placeholder rules, and privacy leak-window
planning; those concerns were real, but the mechanism was compensating for
the wrong boundary.

Dotpanel must support public reuse while keeping operator voice, identity,
runtime notes, machine inventory, and secrets out of the public repo. It must
also keep project-specific handoffs and memory with the projects that own
them.

## Decision

Use a three-layer architecture.

| Layer | Lives in | Scope | Git tracked | Synced by |
|---|---|---|---|---|
| protocol | `dotpanel/` public repo | Universal methodology, Python tool, reference library | yes, public | anyone fork/install |
| persona | `~/.dotfiles/persona/` private repo | Operator **data**: voice, identity yaml, machine-setup data, keyword-router rules, private reference. **Cross-project only**; no methodology, no program logic, no runtime state. | yes, private | operator across machines |
| project | `{project}/.agents/` | Per-project conventions, run handoffs, decisions, project-scoped memory | yes, per project | collaborators on that project |

`dotpanel` owns CLI source, `protocol/workspace.md`, skills, rules, reference
material, harness templates, marketplace adapters, self-contained `bin/`
utilities, package metadata, and docs.

Dotfiles remains private and contains
`persona/{voice.md,identity.yaml,rules/,reference/,runtime/}`. Each project
keeps its own `.agents/` conventions, decisions, run handoffs, and project
memory.

Create one gitignored bridge:

```text
~/src/dotpanel/persona -> ../../.dotfiles/persona
```

`dotpanel init` creates or repairs it. The symlink gives generated wrappers a
stable path under `$(dotpanel root)` without copying private content into the
public repo.

Generate `~/.claude/CLAUDE.md` as a referencing wrapper. It contains absolute
paths to:

1. `~/src/dotpanel/persona/voice.md`
2. `~/src/dotpanel/protocol/workspace.md`

The wrapper tells the agent to read both in order. Voice and workspace content
edits take effect on next agent startup; structural changes still require
configure.

`dotpanel` reads required secrets only from `os.environ`. Secret management is the
operator's private concern.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|--------|------|------|--------------|
| Keep v3 single private repo | One repo to sync | Public reuse blocked; privacy remains policy inside one repo | Preserves the cause of v3 complexity |
| Public repo with ignored private subdir | Simple tree | Easy to traverse, package, or document private paths | Boundary is too weak |
| Separate private persona repo | Clean split | Adds another private sync channel | Dotfiles already owns private sync |
| Public dotpanel plus dotfiles persona plus project layer | Matches audience and sync owner | Needs symlink and configure checks | Chosen |
| Copy persona into generated wrappers | Single runtime file | Stale output and private rendered artifacts | Rejected |
| Reference source files from wrapper | Thin output; content changes apply immediately | Startup depends on referenced paths | Chosen |

## Consequences

The public/private boundary becomes structural. `dotpanel` can be published
without a privacy flip because private content never belongs in that repo.

Universal memory can move to `protocol/reference/`; operator-private notes
shrink to persona notes; project-specific memory moves to project `.agents/`.

Generated wrappers use absolute paths. Cross-machine comparisons must normalize
`$HOME` instead of expecting byte-identical output.

The Source class must allow runtime references from wrappers. The locked phrase
"agent never reads directly during runtime" conflicts with the CLAUDE wrapper
decision, so v4 defines Source as canonical authored content that is not a
configure target.

Follow-up work:

- exclude the persona symlink target from package builds
- add doctor checks for bridge, active slug, and referenced files
- split old memory by layer
- update protocol text to state the env-var secret boundary
