---
name: rule-index
description: Load classification and harness exposure registry for dotpanel protocol rules.
type: rule
rules:
  - id: workspace-kernel
    class: kernel
    path: {{DOTPANEL_ROOT}}/protocol/workspace.md
    trigger: cold start
    harness_exposure: startup-adapter
  - id: workspace-router
    class: router
    path: {{DOTPANEL_ROOT}}/protocol/workspace.md
    trigger: cold start
    harness_exposure: startup-adapter
  - id: rule-index
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/index.md
    trigger: rule load classification or harness reachability audit
    harness_exposure: workspace-router
  - id: harness-bridge
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/harness-bridge.md
    trigger: harness adapter, skill discovery, tool exposure, or startup compatibility
    harness_exposure: workspace-router
  - id: work-quality
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/work-quality.md
    trigger: bug fix, new feature, refactor, docs, UI, data, or infra work
    harness_exposure: workspace-router
  - id: module-discipline
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/module-discipline.md
    trigger: cross-file refactor, interface change, module naming, or public term change
    harness_exposure: workspace-router
  - id: design-contract
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/design-contract.md
    trigger: state, field, schema, migration, deployment, or design lifecycle change
    harness_exposure: workspace-router
  - id: active-run
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/active-run.md
    trigger: starting or advancing a multi-commit active run, writing handoff.md, or updating active.yaml
    harness_exposure: workspace-router
  - id: content-principles
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/content-principles.md
    trigger: writing runtime, memory, journal, handoff, ADR, roadmap, or durable truth
    harness_exposure: workspace-router
  - id: symlink-registry
    class: gate
    path: {{DOTPANEL_ROOT}}/protocol/rules/symlink-registry.md
    trigger: adding or changing symlinks
    harness_exposure: workspace-router
  - id: collaboration
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/collaboration.md
    trigger: collaboration, A2A, shared ownership, handoff race, or concurrent writers
    harness_exposure: workspace-router
  - id: ui-design
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/ui-design.md
    trigger: UI, UX, visual audit, screenshot, or design judgment
    harness_exposure: workspace-router
  - id: adr-template
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/adr-template.md
    trigger: writing or reviewing an ADR
    harness_exposure: rules-index
  - id: interaction
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/interaction.md
    trigger: interaction heuristics, learned operating lessons, or summon keyword routing
    harness_exposure: rules-index
  - id: three-layers
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/three-layers.md
    trigger: deciding who owns a decision (operator / agent), escalating across layers, or parallelizing L3 work
    harness_exposure: rules-index
  - id: scenario-driven-flow
    class: specialist
    path: {{DOTPANEL_ROOT}}/protocol/rules/scenario-driven-flow.md
    trigger: drafting an ADR, writing a scenario, or grilling an open product question
    harness_exposure: rules-index
---

# Rules Index

Machine-readable registry above; human summary below.

## Classes

| Class | Meaning |
|---|---|
| Kernel | Always loaded at startup. Agent must know before any action. |
| Router | Always loaded at startup. Points to next needed rule. |
| Gate | Pointer loaded at startup; body read before changing files or state. |
| Specialist | Read only when a task, skill, or project document names it. |

## Registry

| ID | Class | Path |
|---|---|---|
| workspace-kernel | kernel | `protocol/workspace.md` |
| workspace-router | router | `protocol/workspace.md` |
| rule-index | gate | `protocol/rules/index.md` |
| harness-bridge | gate | `protocol/rules/harness-bridge.md` |
| work-quality | gate | `protocol/rules/work-quality.md` |
| module-discipline | gate | `protocol/rules/module-discipline.md` |
| design-contract | gate | `protocol/rules/design-contract.md` |
| active-run | gate | `protocol/rules/active-run.md` |
| content-principles | gate | `protocol/rules/content-principles.md` |
| symlink-registry | gate | `protocol/rules/symlink-registry.md` |
| collaboration | specialist | `protocol/rules/collaboration.md` |
| ui-design | specialist | `protocol/rules/ui-design.md` |
| adr-template | specialist | `protocol/rules/adr-template.md` |
| interaction | specialist | `protocol/rules/interaction.md` |
| three-layers | specialist | `protocol/rules/three-layers.md` |
| scenario-driven-flow | specialist | `protocol/rules/scenario-driven-flow.md` |
