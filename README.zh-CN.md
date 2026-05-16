# dotpanel

[English](README.md)

`dotpanel` 是一个公开的小工具集，用来把 agent memspace 接到当前机器上。
它安装两个命令：

- `dot` 负责把 `~/.agents` 接到 Claude、Codex、Kimi 等 harness。
- `dkey` 负责加密保存环境变量 secret，并在明确请求时注入。

它不定义你的私有规则、项目、记忆或基础设施。这些内容都属于你自己的
`~/.agents` repo。

## 心智模型

```text
~/.agents/            你的私有 memspace repo
~/.agents/AGENTS.md   agent 首先读取的入口文件
~/.agents/.dotpanel/  这个公开工具 checkout，被 git 忽略
```

`dotpanel` 故意保持很小：bootstrap、render、sync helper、secret injection。
agent 应该知道什么，由你的 memspace 决定。

## 安装

依赖：

- `git`
- `age` 和 `age-keygen`
- `jq`

Debian/Ubuntu:

```bash
sudo apt-get install -y git age jq
```

macOS:

```bash
brew install git age jq
```

没有现成 memspace 的新机器：

```bash
mkdir -p ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

已有 memspace repo 的机器：

```bash
git clone <your-agents-repo> ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init --no-entry
```

`dot init` 会把 `dot` 和 `dkey` 安装到 `~/.local/bin`，写入 shell
integration，并渲染 harness entry files。当前已经打开的 shell 需要手动加载：

```bash
. ~/.agents/.dotpanel/env.sh
```

shell integration 也会定义两个便捷 alias：

```bash
claw='claude --dangerously-skip-permissions'
codx='codex --dangerously-bypass-approvals-and-sandbox'
```

## 日常命令

编辑 `~/.agents/AGENTS.md` 后重新渲染 harness entry：

```bash
dot set -a
dot set claude
dot set codex
dot set kimi
```

检查本机 wiring：

```bash
dot doctor
dkey doctor
```

同步私有 memspace repo：

```bash
dot sync status
dot sync diff
dot sync pull
dot sync push "sync memspace"
```

更新这个公开工具 checkout：

```bash
dot self status
dot self update
```

## `dot` 做什么

`dot` 管的是 memspace 在本机的 wiring：

- `dot init` 初始化 shell integration 和命令 symlink。
- `dot set` 从 `~/.agents/AGENTS.md` 渲染最小 harness entry。
- `dot sync` 在 `~/.agents` 里执行 git 同步。
- `dot self` 在 `~/.agents/.dotpanel` 里执行 git 同步。
- `dot doctor` 检查本机配置是否一致。

渲染出来的 harness entry 故意很小。它们只告诉 harness 去读
`~/.agents/AGENTS.md`，不会复制你的私有规则。

## `dkey` 做什么

`dkey` 用 age 加密保存 secret：

```bash
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey list
```

把 secret 只注入到一次命令：

```bash
dkey run --with GRANT -- command arg1 arg2
```

或者在 shell integration 已加载时注入到当前 shell：

```bash
dkey on --with GRANT
dkey status
dkey off
```

`dkey on` 只影响当前 shell。直接运行 `command dkey on` 会拒绝输出含 secret
的 shell code；要使用 `dot init` 安装的 shell function。

## 创建的文件

`dot init` 可能创建或更新：

- `~/.local/bin/dot`
- `~/.local/bin/dkey`
- `~/.agents/.dotpanel/env.sh`
- `~/.claude/CLAUDE.md`
- `~/.codex/AGENTS.md`
- `~/.kimi/AGENTS.md`

`dkey init` 可能创建：

- `~/.agents/secrets/dkey.conf`
- `~/.agents/secrets/keys.env.template`
- `~/.agents/secrets/keys.env.age`

## 边界

- `~/.agents` 是用户私有 repo。
- `~/.agents/.dotpanel` 是受管理的公开 checkout，应该被 memspace repo 忽略。
- `dot sync push` 会 stage `~/.agents` 下所有未被 ignore 的变更。
- `dkey` 是 privileged 工具；subagent 或不该看到 secret 的脚本不要调用它。
