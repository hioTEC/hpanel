# dotpanel

[English](README.md)

个人 Agent 工作区控制面板。公开的 protocol 库 + Python CLI + harness 适配器生成器，支持 Claude Code、Codex、Kimi。

## 三层模型

| 层级 | 位置 | 职责 |
|---|---|---|
| **Protocol** | 本 repo（公开） | 通用方法论、skills、rules、reference |
| **Persona** | 操作员私有 repo | 声音、身份、keyword routing、私有参考 |
| **Project** | `{project}/.agents/` | run handoffs、决策、项目 memory |

Persona 内容不在本 repo 中。dotpanel 只负责通用 protocol + 渲染 harness 适配器的 CLI。

## Skill 地图

### 用户手动调用（8 个）

| 场景 | Skill | 说明 |
|---|---|---|
| 设计一个功能或方案 | `/plan` | 多 agent 讨论 → 设计产物 + Decision Registry |
| plan 通过后交付 | `/ship` | ADR → 实施 → 跨 harness review → push → deploy → smoke |
| 多条线并行的大 feature | `/teamleader` | 按 stream 分 teammate，协调 cherry-pick |
| session 结束 | `/wrap` | 更新 run manifest，提取 learnings，journal |
| 推/拉 dotpanel + persona | `/sync` | `dotpanel sync` 的 thin wrapper |
| 代码或设计评审 | `/review` | 跨 harness 双审查（sub-agent + external） |
| 评估或退役工具 | `/tool` | try / drop / delete 生命周期 |
| 课纲衔接设计 | `/curriculum-bridge` | 两套教育体系对比，生成衔接课方案 |

### 自动触发（5 个）

| Skill | 谁调用 | 作用 |
|---|---|---|
| `grill-me` | `/plan`、`/ship` | 一次一问，把设计决策树问清楚 |
| `decision-gate` | `grill-me` 输出 | 分类：Convention / Decision / Discretion |
| `delegate-spec` | `implement-pipeline`、`/ship` | 自己做 vs spawn sub-agent（100 行阈值） |
| `implement-pipeline` | 大型多 session run | 状态机：code → review → verify → ship → wrap |
| `session-guardrails` | `implement-pipeline`、`/plan` | 30/50/100 turn 自动 checkpoint |

### 内部参考（2 个）

| Skill | 作用 |
|---|---|
| `investigate` | root cause 分析；3 次假设失败 → 升级给人 |
| `improve-skills` | 扫描 journal 中的摩擦模式 → 提议 protocol 更新 |

### 主流程

```
/plan ──→ /ship ──→ /wrap
  │         │
  └── grill-me, decision-gate,    └── delegate-spec, investigate,
      session-guardrails               code-review, session-guardrails

大项目:  /plan → /teamleader → /wrap
```

## 快速开始

```bash
# 1. 安装（需要 Python >= 3.12）
pip install -e ~/src/dotpanel

# 2. 创建 persona 目录
mkdir -p ~/.persona
# 编写 voice.md 和 identity.yaml（参见 docs/onboarding.md）

# 3. 建立 persona 符号链接
dotpanel init --persona-root ~/.persona

# 4. 渲染 harness 适配器
dotpanel configure --harness all

# 5. 开一个新 shell（或 `source ~/.config/dotpanel/path.sh`）
#    让 `claw` / `codx` / `dot` 进入 PATH

# 6. 验证
dotpanel doctor && dotpanel audit
```

完成第 4 步后，启动 `claude` / `codex` / `kimi` 会自动加载生成的 wrapper，引用你的 persona + 通用 protocol。日常多机同步使用 `dotpanel sync pull`——它会拉取配置的 repo、若 dotpanel 源码变更则重新安装、并重新执行 `configure --harness all`。

## CLI 命令

| 命令 | 用途 |
|---|---|
| `dotpanel root` | 打印安装路径 |
| `dotpanel --version` | 打印版本号 |
| `dotpanel init` | 创建 persona 符号链接，运行 doctor |
| `dotpanel doctor` | 验证安装、符号链接、路径、不变量 |
| `dotpanel audit` | 结构性检查（CI 安全） |
| `dotpanel configure --harness all` | 渲染 `~/.claude/`、`~/.codex/`、`~/.kimi/` |
| `dotpanel configure --check` | 干跑验证 |
| `dotpanel sync pull` | 多阶段：拉取 repo → 若 dotpanel 更新则重装 → 重跑 `configure --harness all` |
| `dotpanel sync push\|status\|diff` | 逐 repo leak 检查后推送；只读 status/diff |
| `dotpanel secrets list\|run\|export\|edit` | 作用域 secrets API（age 加密） |
| `dotpanel context` | 解析身份 + 机器 + 路径锚点 |
| `dotpanel ssh render` | 从 machines.yaml 生成 SSH 配置 |
| `dotpanel install <tool>` | SHA-256 验证的二进制安装器 |
| `dotpanel uninstall --harness all` | 移除 banner 标记的文件 |

## 架构

```
protocol/
  workspace.md          运行原则（始终加载）
  skills/               多步骤过程（14 个 skills）
  rules/                决策框架（14 条 rules）
  reference/            跨项目知识
harness/
  claude/templates/     CLAUDE.md, settings.json, statusline.py
  codex/templates/      AGENTS.md, config.toml
  kimi/templates/       AGENTS.md
dotpanel/               Python CLI 源码
tools/bin/              自带 launcher（claw, codx, dot）
docs/                   ADR、设计文档、onboarding
```

## 文档

- [Onboarding](docs/onboarding.md) — 首次 session 指南
- [架构](docs/architecture.md) — 三层模型、文件分类、configure 协议
- [ADR-0001](docs/adr/0001-repo-split.md) — 公开/私有边界
- [ADR-0002](docs/adr/0002-paths-and-layout.md) — 路径解析 + persona 桥接
- [ADR-0003](docs/adr/0003-configure-protocol.md) — banner 协议、dry-run gate

## 许可

Apache-2.0
