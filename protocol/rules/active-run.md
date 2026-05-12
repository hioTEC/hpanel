---
name: active-run
description: Evidence layout, progress tracking, and in-flight observation capture for multi-commit active runs.
type: rule
status: accepted
updated: 2026-05-05
---

# Active Run — 多步骤执行轨道的工作流约束

> `design-contract.md` 指明 "Execution state belongs to active runs"，但
> 没规范 active run 自身的 evidence 目录形态、progress 跟踪、execution-time
> observation capture。本规则补这层空白：让 wake-up 0 cost 重建状态、让
> in-flight 期发现的小问题不丢失到 sign-off。

Active run = 多 commit / 跨 session 的执行轨道（最少 2 commit 或跨越 1 次
session boundary）。Single-commit run（hot-fix、简单 ops cutover）走 §4 简化
流程，不被本规则约束。

---

## §1 — Evidence 目录最小布局

每个 multi-commit active run 在 `.agents/evidence/<run-id>/` 必须有这三个
文件，缺一不可：

| 文件 | 角色 | 规则 |
|---|---|---|
| `design.md` | Layer-1/2 决策 + Acceptance | 走 `design-contract.md`；frontmatter 有 `status` + `updated` |
| `handoff.md` | Executable checklist for next session | 一个 §Commit 一个逻辑 commit；frontmatter 有 `for: next-session agent` |
| `follow-ups.md` | In-flight observation scratchpad | **§Pre-flight 0 阶段就 `touch`**，不是 sign-off 时建（见 §3） |

`active.yaml` `runs[<id>].evidence` 字段必须指向这个目录，且
`next_session_entry` 必须指向 `handoff.md` 或其内部锚点（见 §2）。

---

## §2 — `active.yaml` `progress` 字段

每个 multi-commit run 的 active.yaml entry 必须含 `progress` 字段。最低 schema：

```yaml
runs:
  - id: <run-id>
    status: open | done | blocked
    # ...其他字段
    progress:
      last_updated: 2026-05-05
      completed:
        - "§Commit 1 (one-line desc) — <hash>"
        - "§Commit 2 (one-line desc) — <hash>"
      next_commit: "<text pointer into handoff.md, e.g. handoff.md §Commit 4>"
    next_session_entry: .agents/evidence/<run-id>/handoff.md (resume at §Commit 4)
```

可选扩展字段（视 run 复杂度添加）：

| 字段 | 用途 | 何时加 |
|---|---|---|
| `side_quests` | 执行中冒出的需独立收口的工作（含 hash 区间） | 出现 1+ 个 mid-flight 插曲就加 |
| `verify_baseline` | 当前 typecheck / test / audit 状态（含红色基线） | broken-state interleaving 期（见 §5）必加 |
| `realizes_adrs` | 本 run 实装的 ADR(s) 短 id 列表（如 `[arch-008, arch-009]`） | run 实装 1+ accepted ADR 时必加；scenario-driven flow 下连接 run ↔ ADR ↔ scenario 三层 |

**维护节奏**：每个 commit 落地后,追加一行到 `completed`、刷 `next_commit`。
可以同 commit（包含进 commit 的 staged file），也可以独立 commit
（`ops(active-run): ...` 前缀）。**不允许"等到 wrap 时才补"** ——
session 中途断线场景下补不上。

**禁止形态**：
- `status: open` 而 progress 缺失（除非 single-commit run）
- `next_session_entry` 只指 handoff.md 而不带 §Commit 锚点（强迫下个 agent
  全文重读）
- progress.completed 没 hash（grep 不到对应 commit）

---

## §3 — `follow-ups.md` 作为 in-flight scratchpad

§Pre-flight 0 阶段必须 `touch follow-ups.md`，不是等 sign-off 时建。初始内容：

```markdown
---
status: in-flight
created: <date>
updated: <date>
owner: <operator>
---

# <run-id> — Follow-ups (in-flight)

In-flight scratchpad. Sign-off 时再 polish 成 final 形态或合并进
post-review SAFE-TO-MERGE 总结。

## Execution notes (per commit)

(每 commit 后有观察就追加；无观察 skip)

## Risks tracker

(从 design.md §Risks 复制过来作 watch list；状态随执行更新)
```

**维护节奏**：每个 commit 落地后，**有观察就追加 1-3 行**；无观察 **skip**。
明确不强制每 commit 都写。"观察"指：

- handoff 字面要求与现实有 gap（边界、numbers、verify 假设错）
- §Commit N 边界跨到 §Commit M 的目标文件（side-effect 没 documented）
- 中途冒出的依赖问题（surfaced ADR、新约束、新决策点）
- 工作流本身的摩擦（哪个步骤反复出问题、哪条规则模糊）

**形态区分**（避免和 task-12/13 风格混淆）：

| 形态 | 适用 | 触发 | 内容 |
|---|---|---|---|
| **In-flight scratchpad** | 本规则；execution 期 | §Pre-flight 0 创建 | execution notes / risks tracker / handoff doc-quality TODO |
| **Post-review SAFE-TO-MERGE** | 已 cross-review 后 | review 完成时 | findings table / verify chain / cross-review independence |

文件名同名 (`follow-ups.md`)，靠 `status: in-flight | closed (...)` 区分。
Sign-off 时改 `in-flight → closed (...)` 并选择是否 polish 成 final 形态。

---

## §4 — Single-commit run 简化流程

适用：hot-fix、简单 ops cutover、不跨 session、整个 run 1 个 commit 完成。
（典型例：`math-subdomain-takeover` 形态。）

简化要求：
- 不必有 evidence dir 三件套；可以只在 `handoff.md` 形态的单文件归档
- active.yaml entry 不必含 `progress` 字段；`status: done` + `closed_at: <date>`
  + `handoff: <path>` 即可
- 不必有 follow-ups.md；如果有 execution-time 学习，写在 handoff.md 末尾或
  ADR consequences

升级条件：如果 run 推进到第 2 个 commit 还没 done，**回溯补齐 §1-§3 三件套**
（可以一次补齐成 ops commit）。

---

## §5 — Broken-state interleaving discipline (placeholder, 2026-05-05)

> 待 1-2 次 occurrence 验证后落地（task-15 是单一证据点）。临时 convention：
> 当 commit sequence 故意让 verify chain (typecheck / test) 中间红，等后续
> commit 修，handoff 的相关 §Commit verify 行都要 spell broken-state 边界
> （N 引入 / N+1..M-1 carry / M 修复）；并把基线数字记在 active.yaml
> `progress.verify_baseline`。下次 active run 复现这个 pattern 时 promote 成
> 正式 §。

---

## Agent 执行规则

- **新 active run 创建时**：
  1. 写 `design.md` per design-contract.md
  2. 写 `handoff.md` 含 §Pre-flight 序列；§Pre-flight 0 强制为
     `touch follow-ups.md`
  3. 在 `active.yaml runs:` 追加 entry，含 `progress` 字段（multi-commit run）
- **每个 commit 落地后**：
  1. 追加 `progress.completed` 一行 + 刷 `next_commit`（独立 ops commit
     或同 commit 都可）
  2. 有观察就追加 `follow-ups.md §Execution notes` 一条；无观察 skip
- **Wake-up / 接续 session 时**：
  1. 先读 `active.yaml progress.last_updated` + `progress.completed` 确认基线
  2. 读 `next_session_entry` 指向的 handoff §Commit 锚点
  3. 不需要 `git log` 重建状态（如果需要重建说明 progress 字段没维护好,
     当 follow-up 记下）
- **Sign-off**：
  1. `active.yaml runs[<id>].status: open → done` + `closed_at`
  2. `follow-ups.md status: in-flight → closed (...)`，summary 段补
     "what shipped" + handoff doc-quality 表 closure 状态
  3. design.md 顶部加 1 段 "what shipped"
- **任意 destructive 操作**：单独走 stop rule（workspace.md §5），跟本规则
  无关
