# dotpanel

[English](README.md)

`dotpanel` 是一个很小的 shell toolkit，用来管理 agent memspace。

核心不变量：

```text
~/.agents/ 是你的 memspace。
~/.agents/AGENTS.md 是入口文件。
~/.agents/.dotpanel/ 是受管理的 tooling，必须被 gitignore。
```

这个 repo 提供一个最小 `AGENTS.md` 模板，以及安装/同步 memspace 需要的小工具。它不会主动创建所有可选的 memspace 目录；agent 和用户可以在真正需要保存 memory 时自然增长这些目录。

- `dot` — memspace 的 sync/render helper。
- `dkey` — 基于 age 的 capability grants，用于短时 CLI secret 注入。

## Install

新机器：

```bash
mkdir -p ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

已有 memspace repo：

```bash
git clone <your-agents-repo> ~/.agents
git clone https://github.com/hioTEC/dotpanel.git ~/.agents/.dotpanel
sh ~/.agents/.dotpanel/bin/dot init
```

`dot init` 只在用户选择/显式请求时创建 `AGENTS.md`，同时配置 harness entry files，并把 `dot` / `dkey` 安装到 `~/.local/bin`。已经打开的 shell 可能需要：

```bash
. ~/.agents/.dotpanel/env.sh
```

## Commands

```text
dot init [--template|--blank|--from PATH|--no-entry] [--yes] [--no-path]
dot set -a|--all
dot set claude|codex|kimi
dot configure [--harness all|claude|codex|kimi]
dot doctor
dot path
dot sync status|diff|pull|push
dot self status|update
```

`dot configure` 是较长的内部形式。人日常使用通常用 `dot set`。

### Daily Workflow

编辑 `~/.agents/AGENTS.md` 后，或者 pull 了 memspace 变更后，使用 `dot set`：

```bash
dot set -a        # 渲染 Claude、Codex、Kimi entries
dot set claude    # 只渲染 ~/.claude/CLAUDE.md
dot set codex     # 只渲染 ~/.codex/AGENTS.md
dot set kimi      # 只渲染 ~/.kimi/AGENTS.md
```

渲染出来的 harness entry 故意保持最小：

```text
`~/.agents/` is your memspace. `~/.agents/AGENTS.md` is the entry.
```

没有 recursive scan，没有 hidden overlay，也没有 private bridge。

用 `dot sync` 在多台机器之间同步 memspace 本身：

```bash
dot sync status
dot sync diff
dot sync pull
dot sync push "sync memspace"
```

`dot sync pull` 会在 `~/.agents` 里执行 `git pull --ff-only`，然后运行 `dot set -a`。`dot sync push` 会 stage 所有 `~/.agents` 变更，在需要时创建 commit，然后 push。

### Script Assumptions

- `dot init` 是 bootstrap 命令。安装脚本通常第一次运行它；日常不需要人手动跑。
- `~/.agents` 是用户自己的 memspace repo。`~/.agents/.dotpanel` 是受管理的 dotpanel checkout，并被 memspace repo ignore。
- `dot` 和 `dkey` 会 symlink 到 `~/.local/bin`。
- shell 会加载 `~/.agents/.dotpanel/env.sh`；已经打开的 shell 可能需要 `. ~/.agents/.dotpanel/env.sh`。
- `dot sync` 假设 `~/.agents` 是 git repo，并且 remote 已配置好。
- `dot sync pull` 只接受 fast-forward pull。
- `dot sync push` 会有意 commit `~/.agents` 下所有 tracked/untracked memspace 变更，忽略 `.dotpanel/` 这类 ignored 文件。

## Templates

tracked templates 位于 `templates/`：

- `templates/AGENTS.md` — 最小 memspace entry scaffold。
- `templates/secrets/dkey.conf` — grant map starter。
- `templates/secrets/keys.env.template` — plaintext env starter template。

`dot init --template` 只复制 entry scaffold。`dkey init` 只创建 `dkey` 需要的 `secrets/` 文件，不会创建 memspace 的其他目录。

## dkey

```text
dkey init
dkey keygen
dkey set NAME VALUE
dkey set NAME=VALUE
dkey edit
dkey list
dkey status
dkey doctor
dkey run --with GRANT -- COMMAND
dkey on [--with GRANT]
dkey off
```

`dkey` 用于 privileged CLI capability grants，不是 routine LLM backend setup。它只在 grant 被使用时解密，并且只把选中的 environment variables 注入到目标进程或当前 shell。

首次 secret setup：

```bash
dkey keygen
dkey set OPENAI_API_KEY sk-...
dkey set ANTHROPIC_API_KEY sk-ant-...
dkey list
```

`dkey keygen` 会在 `~/.config/age/key.txt` 不存在时创建本地 age identity。`dkey set` 会在 `~/.agents/secrets/keys.env.age` 里创建或覆盖一个 encrypted key；设置同名 key 会替换旧值。

当前 shell env workflow：

```bash
dkey on
dkey status
dkey off
```

`dkey on` 会把所有 encrypted keys export 到当前 shell。`dkey off` 会 unset 所有由 `dkey on` 设置的变量。这些命令只有在 `dot init` 已安装来自 `~/.agents/.dotpanel/env.sh` 的 shell function 后，才会影响当前 shell；直接运行 `dkey on` 会拒绝打印含 secret 的 shell code。

更窄的 grant workflow 仍然可用：

```bash
dkey run --with GRANT -- COMMAND
dkey on --with GRANT
dkey off
```

Subagents 不得调用 `dkey` 或已知会使用它的 wrapper。影响外部资源的 credential 使用留在 main agent；scoped grants 优先，但不是强制。
