# Design Contract — 设计阶段交付物

> 防止"框架搭得快、真实数据暴露隐性假设、然后反复补漏"的循环。

任何涉及**状态变化**、**字段增减/语义变更**、**部署环境差异**的方案，在编码前必须依次完成以下四张检查表，再视情况产出后续三单。

Execution state belongs to active runs. Durable design truth belongs to ADRs,
module specs, project rules, or roadmap. Do not create a design document only to
satisfy an execution lane.

---

## Frontmatter 模板

每个 durable design document（ADR / spec / roadmap section / project rule）必须清楚标出状态和更新时间。旧 track-era `design.md` may still exist as historical evidence, but new durable decisions should not depend on track directories.

```yaml
---
status: draft        # draft | proposed | accepted | deprecated | superseded
related-run: import-pipeline    # optional active-run id
updated: 2026-04-14       # 最后更新日期
---
```

**状态含义：**
- `draft` — 尚未确认，下次读到时必须重新验证有效性
- `proposed` — 已通过设计四检查 + 技术三单，等待 review/sign-off
- `accepted` — 设计冻结，作为实现契约
- `deprecated` / `superseded` — 已被推翻或替代，保留供追溯

**关键约束：** active run 不拥有 durable design lifecycle。Run 的 `handoff.md` only points to the accepted ADR/spec/roadmap and records execution state + verification evidence.

---

## 0. Frontend-Backend Design Separation (2026-04-16)

**触发条件：** 任何 full-stack feature（有 UI + API + DB 的变更）。

前后端设计**必须并行独立**，在 API contract 层对齐：

```
1. 用户旅程 → 前端线框（心智模型驱动，不看 API）
2. 前端线框 → 推导需要什么 API contract
3. 后端 schema + API 独立设计（数据完整性驱动）
4. 对齐审查：前端需要的 ≟ 后端提供的
5. 实现
```

**反模式：** 后端 schema → API → 从 API 推出 UI。这导致 UI 暴露实现细节（batch list、pipeline steps），而非用户心智模型。

**检查点：** 在 /plan 阶段，design.md 必须包含独立的「用户视角」和「系统视角」两节。如果只有系统视角（schema + API），前端设计不完整。

---

## 1. 场景穷举单 (Scenario Enumeration)

**触发条件：** 任何新功能、流程改动、或 bug 修复。

Agent 不得只输出一段"设计方案"文字，必须显式产出以下三张表：

| 输出物 | 内容 | 强制检查项 |
|--------|------|-----------|
| **Happy Path** | 理想流程 | 主用户旅程是否完整？关键步骤的数据从哪来、到哪去？ |
| **Edge Cases** | 空数据、超时、部分失败、并发操作 | 每个边界是否有明确的系统行为定义？（不是"稍后处理"） |
| **Regression Risks** | 修改 A 会不会破坏 B？ | 是否列出了跨模块影响清单？（如修改 `figureUrl` 是否影响 review 页？） |

**执行规则：** 表格填不满，视为 plan 不完整，不得进入 implement。

---

## 2. 走查脚本 (Walkthrough Script)

**触发条件：** 任何涉及用户交互、多步骤流程、或 pipeline 的方案。

要求写一段**伪代码级别的用户旅程**，按时间线推演，例如：

```
1. 老师上传 PDF (2023 P1 中英混合卷)
2. Pipeline 分类出 24 页 question, 4 页 answer, 2 页 skip
3. 第 5 题有图，OCR 识别出 figure bounds
4. 中英双语提取完成后，merge 阶段需要决定 figureUrl 取哪边
5. 老师进入 review 页，看到第 5 题，图在题干后、答案前
6. 老师接受第 5 题，随后发现图位置不对，想重新 run
7. 系统应该允许/禁止什么操作？状态如何变化？
```

**目的：** 让 agent 在设计阶段就走完完整剧本，很多 fix 会在写代码前被发现。

---

## 3. 对立面审查 (Devil's Advocate Review)

**触发条件：** 任何非 trivial 的方案（>50 行或跨模块）。

在方案定型后，agent 必须**切换角色**执行一次挑刺审查，输出显式段落：

> "从'这个设计哪里会出问题'的角度审查，重点看：数据一致性、并发冲突、部署兼容性、前后端字段映射。"

执行 adversarial review 须按 `{{DOTPANEL_ROOT}}/protocol/skills/code-review.md` §"Design/Plan Review" checklist 逐项产出风险分析。

---

## 4. 测试用例预写 (Test Case Pre-writing)

**触发条件：** 任何方案。

设计文档的最后一节必须是 **"Test Cases"**。不是泛泛的"需要测试"，而是**具体写出测试标题和断言意图**：

```ts
it('should preserve figureUrl when merging bilingual items with image only in EN', ...)
it('should lock rerun after all answers in a task are accepted', ...)
it('should recover sharp binaries after Docker cross-platform build', ...)
```

**核心原则：** 如果 agent 想不出测试用例，说明它还没想清楚边界情况。测试用例数量不得少于场景穷举单中 Edge Cases 的行数。

---

## 5. 技术变更三单 (State · Field · Deployment)

---

## 1. 状态转换单 (State Transition Sheet)

**触发条件：** 新增/修改实体状态、审核工作流、批处理任务生命周期、权限/锁定逻辑。

| 当前状态 | 事件 | 下一状态 | 前端显示 | 后端行为 | DB 约束 |
|---------|------|---------|---------|---------|---------|
| `{state}` | `{event}` | `{next}` | UI 变化 | 业务动作 | 索引/非空/唯一性 |

**必须回答：**
- 每个状态有哪些允许的事件？非法事件是忽略、报错还是静默拒绝？
- 状态变更后前端哪些按钮/入口必须禁用或隐藏？
- 是否存在并发场景下的竞态条件？（同一任务被多人同时操作、批量操作中部分失败）
- 是否有需要"冻结"或"级联锁定"的关联实体？

---

## 2. 字段生命周期单 (Field Lifecycle Sheet)

**触发条件：** 新增/重命名字段、多语言字段、跨层传递的复合字段、合并/回退策略。

| 字段 | 写入方 | 读取方 | 合并/转换规则 | 空值含义 | 回归测试用例 |
|------|--------|--------|--------------|---------|-------------|
| `{field}` | `{layer}` | `{consumers}` | 优先级/回退 | `null` / `[]` / `""` | 场景简述 |

**必须回答：**
- Schema 层是否已显式定义？（禁止运行时推断出新字段）
- 多语言/多来源合并时的优先级和回退策略是什么？
- 旧数据如何迁移？空值在 UI 上渲染成什么？
- 如果该字段改名，有哪些 grep 不到的隐式引用？（如 localStorage key、URL param、导出文件列名）

---

## 3. 部署环境差异单 (Deployment Delta Sheet)

**触发条件：** 引入 native binary、文件系统依赖、环境变量、Docker/build 配置变更、跨平台构建。

| 依赖/假设 | 开发环境 | 生产环境 | 差异影响 | 验证方式 |
|----------|---------|---------|---------|---------|
| `{dep}` | 状态 | 状态 | 失败模式 | 命令/检查点 |

**必须回答：**
- 是否引入了平台相关依赖？（sharp, puppeteer, OCR 模型, Python 包等）
- 是否依赖 `public/`、`data/` 或外部目录下的动态文件？
- 构建产物中是否有符号链接、硬编码路径、或架构敏感二进制？
- 如果生产是 Docker 构建或 rsync 部署，新增的文件/目录是否在 `.dockerignore` / `rsync` 规则中被意外排除或重复包含？

---

## Agent 执行规则

- **/plan Phase 3：**
  - 任何非 trivial 方案，plan 必须依次包含：场景穷举单 → 走查脚本 → 对立面审查（→ skills/code-review.md §"Design/Plan Review"）→ 测试用例预写。
  - 如涉及状态/字段/部署变更，再追加对应技术变更三单。
  - 任何一张表缺失或流于形式，视为 plan 不完整，不得进入 implement。

- **Active-run pre-implementation gate：**
  - 在某个 active run 进入 implement 前，检查 plan 是否完成了应有的设计四检查；缺失则暂停并回到 plan 补全，不直接开始写代码。
  - 特别检查：Test Cases 一节是否存在、是否具体、是否覆盖了 Edge Cases。

- **Investigate 子流程：**
  - 遇到回归 bug 时，先用设计四检查追溯根因——是场景穷举遗漏、走查脚本没覆盖该分支、还是测试用例预写时就没想清楚边界？
  - 再视需要追溯到技术三单：状态机遗漏、字段 Owner 不清、或部署差异未声明。
