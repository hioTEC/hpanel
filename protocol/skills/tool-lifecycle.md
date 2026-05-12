---
name: tool-lifecycle
description: Tool lifecycle management. Evaluate, retire, or permanently remove tools registered in the operator's tool registry.
type: skill
parameters:
  - action: try | drop | delete
  - target: string
supported_harnesses: [kimi, claude]
---

# Tool Lifecycle

Manage the lifecycle of external tools, plugins, and MCP servers.

```
/tool try [url]      Evaluate before installing (read-only)
/tool drop [name]    Archive (keep files, mark inactive)
/tool delete [name]  Permanently remove (files + config)
```

If arguments start with a subcommand, route directly. Otherwise show usage.

The operator maintains a tool registry (a yaml or equivalent index of installed tools, their status, and clone paths). The exact path is operator-private — see your persona for its location. References below to "the tool registry" mean that file.

## try — Evaluate

**Read-only by default. Clone + research + give opinion. User decides.**

1. **Clone** — to a vendor scratch directory (see persona for the operator's convention). Skip if already present.
2. **Research** — README, package structure, dependencies, recent commits, open issues
3. **Check registry** — if the repo is already in the tool registry, read current status
4. **Opinion** — fit, risk, recommended action

## drop — Retire

**Mark inactive in the tool registry. Do not delete files unless explicitly confirmed.**

1. Locate entry in the tool registry
2. Set the entry's `status: archived` field (or equivalent registry marker). Do not create an `archive/` directory.
3. If a local clone exists, optionally compress or remove from the vendor scratch directory
4. Update any dependent configs

## delete — Remove

**Destructive. Requires explicit confirmation.**

1. Read the tool registry entry
2. List all files/config references
3. Show user exactly what will be deleted
4. Only proceed after explicit "yes"
5. Remove clone, remove config entries, clean up references

## Tool registry schema reference

```yaml
tools:
  - name: {string}
    repo: {url}
    status: active | archived | evaluating
    path: {local_path}
    tags: [string]
```
