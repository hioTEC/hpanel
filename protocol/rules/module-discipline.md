# Module Discipline

> Module design, organization, and change discipline. Always-on, embedded in workspace.md. Detailed process in `skills/grill-me.md` / `skills/decision-gate.md`.

## Vocabulary (use these terms exactly)

| Term | Meaning | Avoid |
|------|---------|-------|
| **Module** | 一个 interface + 一个 implementation。粒度无关：函数、类、目录、跨层切片都算。 | unit / component / service |
| **Interface** | 调用者要正确使用模块**必须知道**的全部事实：类型签名、不变量、错误模式、ordering 约束、配置、性能特征。**不只是 type signature。** | API / signature |
| **Implementation** | 模块内部的代码体。 | — |
| **Depth** | Interface 的杠杆 — 调用者每学一点 interface 能调动多少行为。**Deep** = 高杠杆；**shallow** = interface 几乎和 implementation 一样复杂。 | Ousterhout 的"行数比"，奖励 implementation 灌水 |
| **Seam** | Interface 所在的位置；可以替换行为而不修改原地的"接缝"。 | boundary（与 DDD bounded context 撞名） |
| **Adapter** | 在 seam 上满足 interface 的具体实现。 | — |
| **Leverage** | 调用者从 depth 里拿到的东西：少学多用。 | — |
| **Locality** | 维护者从 depth 里拿到的东西：变更、bug、知识、验证集中在一处。 | — |
| **Ubiquitous Language** (DDD) | 项目内每个领域的术语词典，业务语 = 代码语 = 测试语，三者必须同字面。**项目根的 `CONTEXT.md` 是 SoT。** | — |

## The Five Rules (no exceptions inside this project, ask before exception)

### R1. Grill Before Code

**任何 plan / new-feature / refactor / upgrade / new-tool moment** —— 写第一行代码前必须走完 grill-me 流程：
- 一问一答，**每问只问一件**，AI 给出 recommended answer 等用户决定
- 把 decision tree 的每个分支问到底（依赖、约束、deepening 机会、测试如何穿过 interface）
- grill 的产物是 `design.md` 的 `## Decision Audit` 段（格式见 `skills/decision-gate.md`）
- Decision row 全部有定 → 设计才能从 `draft` 转 `proposed`

**反模式：** 不要把多个独立问题混成"你想要 A 还是 B 还是 C？"——这是把判断扔回给用户。每次只问一个、给推荐、等回复。

### R2. Map Before Plan

**任何跨多文件的改动开始前**，必须先从**模块地图**入手，不是从某个文件入手：
- 项目根有可机器化生成的 module map（脚本：`scripts/module-map.ts` 或等价）
- Map 字段：module 名、interface 入口、依赖（in-process / local-substitutable / remote-owned / true-external）、调用者数量、行数、深度评分
- 改动前 list 受影响的 modules + 它们的 interfaces，回答："本次改动是否变更 interface？变更了哪些 caller 必须更新？"
- 没有 map = 凭印象规划 = 漏 caller / 不必要扩界

**反模式：** "我先打开这个文件看看再说"——这是 implementation-first thinking，会把 grilling 引到错误层级。

### R3. CONTEXT.md is Project Truth

每个项目根有 `CONTEXT.md`，是该项目 **ubiquitous language** 的 SoT：
- 列出每个 domain 的术语 + 一句话定义（不写 implementation 细节）
- 命名 grilling / refactor / 新模块时**只能用 CONTEXT.md 里的词**；引入新概念 → 先把它加进 CONTEXT.md，再开始写代码
- 函数名、变量名 AI 自由选；**模块名、接口名、错误名、测试描述必须严格用 CONTEXT.md 的词**
- AI 内部代码命名（local var、helper fn、闭包）不用受 CONTEXT.md 约束 —— 只 AI 自己读，不出现在 module interface 上

**反模式：** 在代码里出现 `FooBarHandler` / `OrderService` / `XHelper` 这种万能后缀名 —— 没用 CONTEXT.md 的词、interface 自暴自弃。

### R4. Vertical TDD, Never Horizontal

写测试 + 写实现时强制 vertical slice：
```
RIGHT:
  RED → GREEN: test1 → impl1
  RED → GREEN: test2 → impl2
  RED → GREEN: test3 → impl3
WRONG:
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5
```
- **一次写一个测试 → 走到 GREEN → 才能写下一个**
- 测试断言 **observable behavior through interface**，不测内部状态
- Interface 即测试面（test surface）；**想测穿过 interface 的东西 = 模块形状错了**
- Refactor 只在 GREEN 时做，绝不在 RED 中做
- 所有需求开始前先和用户对齐 **(a) interface 长什么样 (b) 哪些 behavior 最值得测**

**反模式 ①：** "我先把所有测试写出来，再来填 implementation" —— horizontal slice，测的是想象中的行为，不是实际行为。
**反模式 ②：** "这个测试 mock 了内部 helper 函数" —— 在测 implementation，不是 interface。重构必坏。

### R5. Deepen, Don't Multiply

接到"重构"任务时，**默认动作是合并而不是拆分**：
- 跑 **deletion test**：想象删掉某个模块。如果复杂度消失，它是 pass-through，删；如果复杂度跨 N 个 caller 重现，它在挣钱（earning its keep）
- "再抽一层"通常是错的诊断 —— 真正的问题往往是第一层抽错了，去修第一层
- **One adapter = 假 seam。Two adapters = 真 seam。** 没有两个真实 adapter 就别引入 port —— 单 adapter seam 只是 indirection
- 验证：跑 `scripts/depth-audit.ts`（或等价工具），输出 module 列表 + interface size + impl size + caller count；shallow module（interface ≈ impl 大小、caller ≤ 1）进 candidate list，逐个 grilling 决定 deepen / inline / delete

**反模式：** 看到一个文件超 400 行就拆 —— 行数不是 depth signal。Deep 模块可以很大；shallow 模块可以很小。

## Validation Scripts (must exist per project)

每个 production 项目根目录至少存在：

| 脚本 | 输出 | 用途 |
|---|---|---|
| `scripts/module-map.ts` | JSON / Markdown：modules + interfaces + dependencies + callers | R2 必读 |
| `scripts/depth-audit.ts` | shallow module 候选清单（interface lines ≈ impl lines, callers ≤ 1） | R5 工具 |
| `scripts/context-coverage.ts` | module / interface 名字未出现在 `CONTEXT.md` 的清单 | R3 工具 |

脚本在 CI 跑，结果进 PR comment。规则违反不一定 fail build（默认 warn），但 PR 必须显式回应。

## When to Pause and Ask

| Signal | Reason |
|--------|--------|
| 用户给的需求一句话能有 ≥ 2 种合理解读 | grill-me，列出解读让用户挑 |
| Refactor 候选会改动 interface（impact > 单文件） | grill-me，把 caller 影响摆出来再做 |
| 引入第三方 dep / 新 SDK / 新 service | decision-gate，走 ADR |
| 测试要绕过 interface 测内部状态 | 模块形状错了，停 |
| 命名出现 CONTEXT.md 之外的术语 | 先 grill 是不是新概念，是的话写进 CONTEXT.md |

## Interaction with Other Rules

- **engineering-principles.md** — 本文件细化"Layer Purity"、"Naming is Semantics"、"Solution Discipline"
- **execution-rules.md** — 本文件 R4 (Vertical TDD) 是 "Goal-driven execution" 的强化
- **decision-gate.md** — 本文件 R1 是 process（grill-me），decision-gate 是 output format（Decision Audit）。两者必须同时跑：grill-me 收集 → decision-gate 落档
- **design-contract.md** — 本文件 R2 (Map Before Plan) 是其 prerequisite

## Anti-Patterns to Watch

- **"FooManager / FooHandler / FooService"** — 万能后缀，意味着 interface 没说清职责
- **"utils.ts / helpers.ts / common.ts"** — 垃圾袋，shallow modules 的集中地
- **"v2/ / v3/ / legacy/"** — 没删旧版的现场，多份 SoT
- **"我先在 CLAUDE.md / AGENTS.md 写一条规则"** — 规则进文档不进 lint = 自然腐烂；boundary 必须进 lint
- **"加个 flag / 加个开关"** — 见 engineering-principles "Config flags cost more than hardcoding"
