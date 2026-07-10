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
git clone --recurse-submodules <your-agents-repo> ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init --no-entry
```

`dot init` 把 `dot`/`dkey` 所在目录（`~/.agents/.dotpanel/bin`）和 `~/.agents/tools/bin`
（claw/codx）加入 PATH（通过 `env.sh`），写入 shell integration，并渲染 harness entry
files。当前已经打开的 shell 需要手动加载：

```bash
. ~/.agents/.dotpanel/env.sh
```

shell integration 不再定义 `claw`/`codx` alias——两者都是 memspace 的 multi-call
PATH 脚本（`~/.agents/tools/bin/`），各自从 `dkey.providers.json` per-invocation
切换后端：

```text
claw / clawb   — claude 前台 / headless 苦力
codx / codxb   — codex  前台 / headless 苦力
```

更新 dotpanel 后（`dot self update` 或 `dot set path`），重新加载：

```bash
. ~/.agents/.dotpanel/env.sh
```

如果 `codx` 仍然缺失（`codx: command not found`），先重新生成 env 文件：

```bash
dot set path && . ~/.agents/.dotpanel/env.sh
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
dot sync push
```

`dot sync push` 只 push 已存在的 commits。只要有 staged、unstaged 或
untracked files，它就会拒绝执行；它绝不会替你 stage 或 commit。请先明确
commit 要分享的路径，再运行这个命令。`dot sync pull` 会先显示 status 并
fetch，然后要求 worktree clean 且可以 fast-forward，再递归初始化/更新
submodules；只有这些步骤全部成功后才重新渲染 harness files。requested
Claude/Codex skill render 与 ownership collision 会在任何 generated harness
state 改变前完成 prepare。

按单次调用切换 AI backend（读取 `~/.agents/secrets/dkey.providers.json`，
需要 key 时通过 `llm-backends` grant 注入）：

```bash
claw deepseek
clawb deepseek "review this change"
codx qwen
codxb qwen "review this change"
```

更新这个公开工具 checkout：

```bash
dot self status
dot self update
```

## `dot` 做什么

`dot` 管的是 memspace 在本机的 wiring：

- `dot init` 初始化 shell integration 和 PATH wiring。
- `dot set` 从 `~/.agents/AGENTS.md` 渲染最小 harness entry。
- `dot sync` 在 `~/.agents` 里执行 git 同步。
- `dot self` 在 `~/.agents/.dotpanel` 里执行 git 同步。
- `dot doctor` 检查 entry 是否存在，以及生成的 wrappers、shell integration、
  Claude plugins 和 declared Codex aliases 是否与 source render 完全一致；
  symlinked/non-regular generated file 与这些一致性错误都会返回非零状态。

渲染出来的 harness entry 故意很小。它们只告诉 harness 去读
`~/.agents/AGENTS.md`，不会复制你的私有规则。

shell rc 修改采用 fail-closed：`dot set path` / `dot unset path` 会拒绝 symlink
或非普通 rc file，写入前重新检查 mutation boundary，保留已有文件的 mode，并在
failure 或 signal 后清理同目录 rewrite temp。`DOT_SHELL_RC` 与 `ZDOTDIR` 仍可把
rc 明确放到 `HOME` 之外。

Claude plugin renderer 只接受 path-safe skill ID、恰好一组 `name` / `description`
且已闭合的 frontmatter，以及不含 symlink 的 source tree。生成目录带普通文件
`.dotpanel-owner`；reconcile、doctor 和 unset 都依赖该 marker。完全匹配旧版 dot
render 的无 marker 目录会迁移一次，unmanaged destination 永远不会被覆盖或删除。

### 可选的 Codex skill aliases

如果存在 `~/.agents/skills/sources.json`，`dot set codex` 和
`dot configure --harness codex` 也会 reconcile 简短的 Codex skill aliases。
最小的 version 1 manifest 如下：

```json
{
  "version": 1,
  "alias_adapter": {
    "owner": "dotpanel",
    "destination": "~/.codex/skills",
    "renderer": "dot set codex",
    "retired_aliases": ["old-name"]
  },
  "aliases": [
    {
      "id": "plan",
      "source": "local",
      "skill": "plan-discussion",
      "target": "plan-discussion/SKILL.md",
      "description": "Use for structured planning and architecture choices.",
      "guidance": "Keep the resulting design proposed until operator sign-off."
    }
  ],
  "sources": [
    {"id": "local", "paths": ["skills/local"]}
  ]
}
```

只有 manifest 本身是普通、非 symlink 文件，且 `owner`、`destination` 和
`renderer` 与上例完全一致时才启用 adapter。

每个被 alias 引用的 source 必须解析为 memspace 的 `skills/` root 下唯一的相对
目录，而且该 root 与 declared source directory 都不能是 symlink；target 必须是
该 source 内普通且非 symlink 的文件，alias 永远不能路由到 `secrets/`。每个
alias 必须提供单行 `description`，也可以提供单行
alias-specific `guidance`，每项最多 500 characters；control characters 和
multiline values 会被拒绝。生成的 `~/.codex/skills/<id>/SKILL.md` 使用这些
discovery metadata，并链接 canonical file，不复制 instructions 或 bundled
resources。

生成的 alias 带有 dot ownership banner。Reconcile 遇到同名但无 banner 的
目录会拒绝覆盖；stale 或 retired 目录也只有带 banner 时才会删除，其他 Codex
skills 保持不变。`dot unset codex` 遵守相同 ownership rule。`dot doctor` 会
报告 missing alias、content drift 和 stale dot-managed alias。manifest 不存在
表示 desired alias set 为空；下一次 `dot set codex` 会删除带 dotpanel ownership
banner 的 stale alias，但不会触碰 unmanaged Codex skill。普通 Codex entry
rendering 仍会继续。

## `dkey` 做什么

`dkey` 用 age 加密保存 secret：

```bash
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey list
```

`dkey set`、`dkey edit` 和 identity import 的敏感中间内容只写入随机 `0600`
temp，并在 success、failure 或 HUP/INT/TERM 后清理；只有验证成功后才替换 encrypted
keys 或 identity target。

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

`dkey on --with GRANT` 只影响当前 shell，unscoped activation 已禁用；切换到另一个
grant 前必须先运行 `dkey off`。activation 与 removal 会先在 subshell preflight，
readonly 或被篡改的 control variable 不会留下未追踪的 partial state。直接运行
`command dkey on` 会拒绝输出含 secret 的 shell code；要使用 `dot init` 安装的
shell function。

AI backend 定义放在 `~/.agents/secrets/dkey.providers.json`。
`claw`/`clawb`、`codx`/`codxb`、`gem`/`gemb` 读取这个 registry，并且只对
本次启动的进程应用 backend 配置。secret 通过 `llm-backends` grant 注入。

```bash
codx qwen "prompt"
clawb kimi "prompt"
```

`dkey use` 已移除，因为它会持久写入全局 harness 设置，并可能把 Codex
ChatGPT/OAuth 登录态覆盖成 API-key mode。`dkey reset codex|claude|all` 只用于
清理旧的持久 backend 设置。reset 会按 ownership 保守清理：Claude 只移除
registry 声明的 managed env keys；Codex 只移除 registry-managed provider，并且
仅在当前 top-level provider 属于 registry-managed 时清除 legacy API-key auth
override。user-owned provider、无关设置和 OAuth token fields 都会保留。input
会先验证并生成 replacement，再替换 target；这不宣称能够抵抗 filesystem
failure 的跨文件 transaction。reset 遇到 multiline TOML 或 conservative legacy
subset 以外的 provider-table 形式会拒绝执行，而不是 partial rewrite。reset
target 必须位于 `HOME` 内，从 home boundary 到 target 的每一层 path component
都不能是 symlink。

Provider registry 位于 `~/.agents/secrets/dkey.providers.json`。参见
[PROVIDERS.md](PROVIDERS.md) 了解完整 schema，模板在
`templates/secrets/dkey.providers.example.json`。

## 创建的文件

`dot init` 可能创建或更新：

- `~/.agents/.dotpanel/env.sh`
- `~/.claude/CLAUDE.md`
- `~/.codex/AGENTS.md`
- `~/.kimi/AGENTS.md`
- `~/.claude/skills/{hio,matt,impeccable}/`，内含 `.dotpanel-owner` marker
- manifest `~/.agents/skills/sources.json` 声明的
  `~/.codex/skills/<alias>/SKILL.md`

`dkey init` 可能创建：

- `~/.agents/secrets/dkey.conf`
- `~/.agents/secrets/keys.env.template`
- `~/.agents/secrets/keys.env.age`
- `~/.agents/secrets/dkey.providers.json`

## 边界

- `~/.agents` 是用户私有 repo。
- `~/.agents/.dotpanel` 是受管理的公开 checkout，应该被 memspace repo 忽略。
- `dot sync push` 会拒绝 dirty memspace，只 push 已存在的 commits；它绝不
  stage 或 commit files。
- `dot sync pull` 会先 fetch，再执行 clean-worktree 与 fast-forward-only gate，
  然后递归初始化/更新 submodules。若 fast-forward 成功后 render preparation
  失败，Git 会停在已拉取 commit，之前的 generated snapshot 保持不变；修复
  source 后重跑 `dot set -a`，再用 `dot doctor` 验证。
- `dot self update` 会拒绝 dirty managed checkout。
- `dkey` 是 privileged 工具；subagent 或不该看到 secret 的脚本不要调用它。

## 参见

- [CHANGELOG.md](CHANGELOG.md)
- [PROVIDERS.md](PROVIDERS.md) — provider registry schema
- [LICENSE](LICENSE)
