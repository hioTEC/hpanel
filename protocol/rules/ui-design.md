# UI Design Rules

全局基线。项目覆盖规则、设计系统、token 落点由项目 `AGENTS.md` 声明；
不要假设项目一定有 `.agents/rules/ui-design.md`。

---

## Meta Principles

### Journey-First Design
写界面前先画用户旅程图：理想路径是什么？是否存在理想路径？哪些路径会让用户越来越沮丧？界面是旅程的产物，不是功能的容器。每个 state 都要问：用户从哪来、要去哪、卡住了怎么办。

### Unified Information Architecture
同类界面必须共享结构模式——相同的视觉层次、操作位置、说明文本位置、帮助链接位置。变化只在内容，不在骨架。这个约束反而迫使设计者思考什么才是真正重要的细节，而非在装饰性变化上花时间。

### Readability > Consistency
当视觉一致性与可读性冲突时，始终优先可读性。每一次都是如此。字号不够大就放大，对比度不够就加深——不要为了"视觉统一"牺牲用户能不能读懂。

---

## Design System

### Color

**色彩空间：OKLCH**（感知均匀，HSL 不是）。

```css
/* 模板：lightness (0-100%), chroma (0-0.4+), hue (0-360) */
--color-primary: oklch(60% 0.15 250);
--color-primary-light: oklch(85% 0.08 250);   /* 趋白时降 chroma */
--color-primary-dark: oklch(35% 0.12 250);
```

**Palette 角色：**

| Role | 用途 | 规模 |
|------|------|------|
| Primary | 品牌、CTA、关键操作 | 1 色 3-5 阶 |
| Neutral | 文本、背景、边框 | 9-11 阶，带品牌色微 tint (chroma ~0.01) |
| Semantic | success / error / warning / info | 4 色各 2-3 阶 |
| Surface | 卡片、modal、overlay | 2-3 层深度 |

**规则：**
- 60-30-10（视觉权重，不是像素面积）：neutral 60%、secondary 30%、accent 10%
- 不需要 secondary/tertiary 就别加——大多数应用一个 accent 色够用
- Neutral 永远带 tint（`chroma: 0.005-0.01`），纯灰没有生命
- 禁止纯黑 `#000` 做大面积背景——用 `oklch(12-18% 0.01 {hue})`
- 禁止灰色文字放在彩色背景上——用背景色的深阶
- 禁止 AI 调色板：cyan-on-dark、purple-to-blue 渐变、暗底霓虹
- Alpha 透明是 palette 不完整的信号——除 focus ring 外定义显式颜色
- Error 红色只用于 icon，不用于背景或大面积文字——高饱和度红色背景触发 learned helplessness（用户认为是自己的错而放弃），error 文字用 neutral 色

**Token 两层：**
```css
/* Primitive（不因 theme 变） */
--blue-500: oklch(60% 0.15 250);

/* Semantic（dark mode 只改这层） */
--color-primary: var(--blue-500);
```

**Dark mode ≠ 反色：**
- 深度靠 surface 亮度递增，不靠阴影
- Accent 色微降饱和
- 文字字重减 50（400 → 350）
- 背景不用纯黑

**Contrast（WCAG AA）：**

| 内容 | 最低对比度 |
|------|-----------|
| 正文 | 4.5:1 |
| 大字 (18px+ / 14px bold) | 3:1 |
| UI 组件、图标 | 3:1 |
| Placeholder 文字 | 4.5:1（常被忽略） |

### Spacing

- Base unit: 4px
- Scale: 4, 8, 12, 16, 24, 32, 48, 64
- 同容器内 children 用 `gap`，不用单独 `margin`
- 区块之间 gap ≥ 16（呼吸感）
- 工具栏区域 gap ≤ 16（紧凑感）

### Border Radius

- 最多 3 级：sm / md / lg
- 同类组件（按钮与按钮、卡片与卡片）必须一致
- 禁止 `rounded-[Npx]` hardcode
- 内嵌元素圆角 < 外层圆角

### Button

- Min height: 32px (`h-8`)，touch target ≥ 44px
- 同行按钮等高
- 每页按钮样式 ≤ 3 种（primary / secondary / ghost）
- 危险操作用颜色区分 + 二次确认

### Typography

- 字体栈：项目指定（避免 Arial、Inter 等 overused 默认）
- Heading 层级：最多 4 级可见差异（size + weight）
- Body: 16px base，行高 1.5-1.75
- 中文正文推荐 16-18px，行高 1.75-2.0

### Layout

- 优先 CSS Grid / Flexbox，不用 float
- 响应式断点：sm 640 / md 768 / lg 1024 / xl 1280
- 内容最大宽度：prose 65ch，dashboard 1440px
- 移动端优先（min-width 媒体查询）

---

## Implementation Rules

写页面、改组件时必读。每条规则分 DO / DON'T，agent 写代码时对照执行。

### T1. Spacing Rhythm（空间节奏）

> 相关元素紧凑，不相关元素拉开。密度是刻意设计的，不是默认值。

**DO:**
- 工具栏内部按钮用 `gap-1` 或 `gap-2`，区块之间用 `gap-6` 或 `gap-8`
- 使用语义化间距 token（`space-xs/sm/md/lg`），按"关系远近"选择
- 表单 label 与 input 之间 `gap-1.5`，表单组之间 `gap-6`

**DON'T:**
- 所有地方统一 `gap-4`——这让密集区和留白区看起来一样
- 用 `margin` 逐个调——应由父容器的 `gap` 统一控制
- 在紧凑工具栏里加 `p-6` 大内边距——浪费空间且破坏密度感

### T2. Border Radius Scale（圆角统一）

> 全站 3 个圆角值够了。混用 = 无风格。

**规则：** 卡片/Modal `rounded-lg`(8px)，按钮/Input `rounded-md`(6px)，Avatar/Badge `rounded-full`。

**DO:**
- 在 tailwind config 定义 radius scale，组件引用 token
- 嵌套元素内圆角 < 外圆角（卡片 `lg`，内部按钮 `md`）
- 全站搜索 `rounded-` 确认不超过 3 个值

**DON'T:**
- 同一页面出现 `rounded-sm`、`rounded-xl`、`rounded-2xl`、`rounded-[12px]`
- 按钮有的 `rounded-full` 有的 `rounded-md`——同类组件必须同圆角
- hardcode `rounded-[任意px]`——用 scale token

### T3. Button Size & Alignment（按钮尺寸与对齐）

> 同区域按钮必须视觉等高，点击目标 >= 36px。

**DO:**
- 定义 3 个按钮尺寸：`sm`(h-8)、`default`(h-9)、`lg`(h-10)，同行按钮同尺寸
- Icon button 与 text button 等高（用 `aspect-square` + 同 h 值）
- 工具栏按钮统一 `sm`，页面主操作 `default`，hero CTA `lg`

**DON'T:**
- 同一行出现 `h-8` 和 `h-10` 的按钮——视觉不对齐
- 按钮宽度靠 `px` 固定——用 `px-4` padding 让内容决定宽度
- 小于 36px 的点击目标（移动端 44px）

### T4. Layout Stability（布局零偏移）

> 交互状态变化不得改变周围元素的位置。CLS = 0。

**DO:**
- 批量操作栏用 `sticky bottom-0` 或 `fixed` 悬浮，不插入文档流
- 需要显隐的区域预留空间（`min-h` 或 `opacity-0→1` 不改高度）
- Checkbox 选中/取消后，列表项位置不变——选中态的额外 UI 不能推挤内容

**DON'T:**
- 勾选 checkbox 后在列表上方插入工具栏导致内容下移
- 取消选择后工具栏消失但列表不复位（高度闪跳）
- 加载态（skeleton→content）改变容器高度——用固定高度 skeleton

### T5. Visual Zoning（功能分区）

> 不同功能区用背景色/边框/间距区分，像室内设计的功能区隔断。

**DO:**
- 筛选区 `bg-muted`、内容区 `bg-background`、操作区 `bg-muted/50` + `border-t`
- 侧边栏与主内容用 `border-r` 或背景色差分隔
- 页面 header（标题+操作）与内容区之间有明确分界（`border-b` 或间距）

**DON'T:**
- 整个页面同一个白色背景，筛选/内容/操作全混在一起
- 用 `<hr>` 作为唯一分隔手段——背景色差 + 间距更有层次感
- 功能区内部再套功能区背景色——最多 2 层嵌套

### T6. Search & Filter Clarity（搜索/筛选可识别性）

> 同类组件多处出现时，必须有明确的 scope 标识。

**DO:**
- 搜索框 placeholder 标明 scope：`搜索题目...`、`搜索学生...`
- 多个筛选区域各有 section title 或 icon 前缀
- 全局搜索 vs 局部搜索用不同位置（顶栏 vs 页面内）区分

**DON'T:**
- 两个搜索框都写 `搜索...` 但搜不同内容
- 筛选条件散落在页面各处没有分组
- 搜索框没有 `aria-label`——LLM 和屏幕阅读器都无法理解其用途

### T7. Progressive Disclosure（渐进展示 & 右键菜单）

> 主操作 1-2 个按钮，次要操作收进 context menu 或 dropdown。

**DO:**
- 每个卡片/行最多 2 个可见按钮，其余收进 `<DropdownMenu>` 或右键菜单
- 右键菜单用于：复制链接、在新标签打开、导出、删除等低频操作
- 批量操作在选中后才出现（悬浮工具栏），不占常态空间

**DON'T:**
- 一行 5+ 个按钮全部平铺——认知过载
- 右键只有浏览器默认菜单——浪费了一个高效交互通道
- 把"删除"这种危险操作和"编辑"放在同一视觉层级

### T8. Functional Placement Audit（功能归属审视）

> 不只好看不好看，要看功能该不该在这里。

**DO:**
- 每个区域问：用户在此的**核心任务**是什么？当前元素服务于这个任务吗？
- 高频操作放前面/显眼处，低频操作收进 settings 或 context menu
- 危险操作（删除、重置）远离常用按钮，需二次确认

**DON'T:**
- 设置类功能出现在内容浏览页面
- 导出/统计按钮和日常操作按钮混在同一行
- 只因"这里有空间"就把功能塞进去——空间不是理由，任务关联才是

### T9. Machine-Readable & LLM-Governed Access（LLM 可用性）

> 让 LLM 能用功能（skill 化），但不能乱爬数据。

**DO:**
- 关键交互元素加 `aria-label` 和 `data-testid`——LLM agent 和 E2E 测试都能用
- 页面结构用 semantic HTML（`<nav>`、`<main>`、`<aside>`、`<section>`）
- API 暴露 OpenAPI spec，方便 LLM 通过 function calling 调用
- 数据密集 API 加 rate limiting（per-key token bucket）

**DON'T:**
- 全页面 `<div>` 套 `<div>`，无 landmark——LLM 无法理解页面结构
- 把所有数据放在公开 API 没有鉴权——爬虫一次全拿走
- 在 `robots.txt` 禁掉所有路径——合法 LLM 使用也被挡住
- 核心数据没有分页/游标——一次请求返回全量数据

### T10. State Process Transparency（状态过程透明）

> 用户需要知道系统在做什么、做到哪了、接下来会怎样。动态 > 静态。

**DO:**
- 异步操作显示动态进度文案（"正在提取第 3/12 页..." → "提取完成"），不用静态 spinner
- 多步骤流程展示当前步骤 + 总步骤数（stepper / progress bar）
- 操作完成后给明确反馈（toast / 状态变更），不要让用户猜"成功了没"
- Pipeline 状态用动词（"提取中"、"等待审核"），不用名词（"提取"、"审核"）

**DON'T:**
- 只放一个 spinner 不说在做什么——用户不知道要等多久、能不能离开
- 操作后页面无任何变化——用户会重复点击
- 用 "处理中" 概括所有状态——区分 "上传中"、"分析中"、"生成中" 各阶段

### T11. Error Messaging（错误信息设计）

> 错误信息是帮助，不是诊断日志。三层渐进：状态标签 → 排障入口 → 详情。

**DO:**
- 错误文案用用户可操作的语言：✗ "您的设备时钟设置错误" → ✓ "设备时间不正确"
- 错误卡片结构：状态名 → "排查方法" 链接 → 点击展开 modal/详情
- Error icon 用 semantic red，文字和背景用 neutral 色（见全局 Color 规则）
- "反馈" 按钮改用 "排查问题"——承诺解决，不是收集抱怨
- **数据溯源**：涉及多数据源对比的错误，必须标明每个数值的来源。例如 "MS 子題總和 4 ≠ 題目總分 5" 而非 "sub-part sum 4 ≠ expected 5"。用户需要知道哪个值来自 marking scheme 提取、哪个来自题目提取，才能判断该修哪边
- **禁止内部术语**：用户可见的错误文案不得包含代码内部字段名或概念（如 breakdown、markBreakdown、STEP_MARK_MISMATCH）。用自然语言描述同一件事：breakdown → "逐步分數"、step marks → "步驟標註"、marks field → "標註總分"

**DON'T:**
- 在小空间里堆满技术细节——非技术用户看不懂，技术用户不需要
- 用高饱和度红色背景 + 红色文字——触发 learned helplessness
- 错误信息只说出了什么问题，不说用户能做什么——每条 error 必须有 action
- 用内部变量名或英文缩写作为错误提示（如 "MARK_MISMATCH"、"breakdown≠marks"）——这是给开发者看的日志，不是给用户看的帮助

---

## 执行优先级

写新页面时：T4(零偏移) > T1(节奏) > T5(分区) > T3(按钮) > T2(圆角) > T7(渐进展示) > T10(状态) > T8(归属) > T6(搜索) > T11(错误) > T9(LLM)

改现有页面时：先修 T4 布局偏移（用户体感最差），再统一 T2/T3 token，最后补 T7/T9。新增状态/错误页面时优先 T10/T11。
