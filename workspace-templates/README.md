# Workspace Templates

按场景整理的**工作区模板**(预设)。每个模板是一个目录,把一个学习/创作场景所需的 **Agent 人格 + 专项技能**打包在一起,让你开箱即用。

Inno Agent 的「简单模式」会直接把这些模板渲染成欢迎页的**预设卡片**,点一下就进入一个配好的工作区开始对话。你也可以手动把模板内容上传到任意工作区(见下文)。

---

## 目录结构

每个模板目录包含:

```
<模板 id>/
├── preset.json        # 元数据:id / name / description / icon(App 预设卡片读它)
├── agent.md           # 工作区上下文:每次对话注入到 Agent 系统提示
└── .skills/           # 可选,工作区私有技能
    └── <技能名>/
        └── SKILL.md   # 技能定义(name 与目录名一致)
```

### `preset.json` 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✅ | 唯一标识,**必须与目录名完全一致**(防路径穿越)。只用字母/数字/`._-`。 |
| `name` | ✅ | 显示名,出现在预设卡片标题。 |
| `description` | | 一句话说明这个模板帮用户做什么,显示在卡片副标题。 |
| `category` | ✅ | 分类标签,客户端按此分组与筛选。当前可用: `教学` / `演示` / `verymath`。**缺失会落到「未分类」组**,详见仓库根目录 [README.md 的「分类标签 (必填)」](../README.md#分类标签-必填)。 |
| `icon` | | [lucide](https://lucide.dev/icons/) 图标名,如 `presentation` / `book-open` / `lightbulb`。 |

---

## VeryMath AI4Math 系列

本目录收录了来自 [**VeryMath**](https://github.com/VeryMath) 的 7 个 AI4Math 工作区模板（分类标签：`verymath`）。

[VeryMath](https://github.com/VeryMath) 是一个专注于 **AI 辅助数学研究** 的开源社区，目标是让 AI Agent 成为数学家的协作伙伴。其仓库覆盖从论文阅读、形式化证明到自动科研的完整研究链路，每个仓库提供对应场景的 Skill 定义与工作流指导。

| 模板 | 上游仓库 | 场景 |
|---|---|---|
| `ai4math-lean-agents` | [AI4Math-Lean-Agents](https://github.com/VeryMath/AI4Math-Lean-Agents) | Lean 4 定理形式化、证明修复、sorry 补全 |
| `ai4math-paper-reading` | [AI4Math-Paper-Reading](https://github.com/VeryMath/AI4Math-Paper-Reading) | 数学论文结构化阅读、论文转 Skill |
| `ai4math-paper-writing` | [AI4Math-Paper-Writing](https://github.com/VeryMath/AI4Math-Paper-Writing) | 数学论文起草、修订与审稿回复 |
| `ai4math-computational-mathematics` | [AI4Math-Computational-Mathematics](https://github.com/VeryMath/AI4Math-Computational-Mathematics) | 有限元、不变量计算、科研代码复现 |
| `ai4math-optimization` | [AI4Math-Optimization](https://github.com/VeryMath/AI4Math-Optimization) | LP / MIP / SOCP / CDOpt 流形优化 |
| `ai4math-auto-research` | [AI4Math-Auto-Research](https://github.com/VeryMath/AI4Math-Auto-Research) | 问题发现、猜想生成、证明蓝图审查 |
| `ai4math-evolving` | [AI4Math-Evolving](https://github.com/VeryMath/AI4Math-Evolving) | OpenEvolve 进化实验与迭代改进 |

> 如需了解 VeryMath 的整体愿景与更多子项目（如 [co-mathematician](https://github.com/VeryMath/co-mathematician)、[AI4Math-Sagemath-skill](https://github.com/VeryMath/AI4Math-Sagemath-skill)），请访问 https://github.com/VeryMath 。

---

## 模板列表

| 目录 | 场景 | 包含 Skill | 状态 |
|---|---|---|---|
| [ielts-prep/](./ielts-prep/) | 雅思英语备考 | card-maker(词汇卡片生成器)| ✅ 可用 |
| [ielts-coach/](./ielts-coach/) | 雅思备考(英文闭环版) | card-maker / essay-grader / reading-trainer / weekly-review | ✅ 可用 |
| [ppt-creation/](./ppt-creation/) | PPT / 演示文稿制作 | ppt-builder(结构化幻灯片生成)| ✅ 可用 |
| [teaching-webpage-en/](./teaching-webpage-en/) | 课堂互动网页(英文版) | webpage-builder / claude-design / visual-explainer | ✅ 可用 |
| [math-interactive-en/](./math-interactive-en/) | 数学交互解题(英文版) | edu-analytic-geometry / edu-solid-geometry | ✅ 可用 |
| [adaptive-math-learning-agent/](./adaptive-math-learning-agent/) | 中小学数学错因诊断、多表征修复与自适应巩固 | math-task-structurer / math-reasoning-trace-analyzer / math-misconception-verifier / multi-representation-repair / math-visual-repair / adaptive-math-practice / math-learning-progress-reporter | ✅ 可用 |
| [lesson-plan/](./lesson-plan/) | 结构化教案生成 | — | 🚧 骨架(工作流待细化)|
| [scenario-explain/](./scenario-explain/) | 情景化讲题 | — | 🚧 骨架(工作流待细化)|
| [ai4math-paper-reading/](./ai4math-paper-reading/) | 数学论文阅读：PDF 摄入、论文转 Skill | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-computational-mathematics/](./ai4math-computational-mathematics/) | 计算数学：有限元、不变量、最小二乘、代码复现 | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-optimization/](./ai4math-optimization/) | 数学优化：LP / MIP / SOCP / CDOpt / COPT | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-lean-agents/](./ai4math-lean-agents/) | Lean 4 形式化、证明修复、sorry 补全 | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-auto-research/](./ai4math-auto-research/) | 自动数学科研：问题发现、证明蓝图生成与审查 | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-evolving/](./ai4math-evolving/) | 进化 Agent：OpenEvolve 实验配置与迭代改进 | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [ai4math-paper-writing/](./ai4math-paper-writing/) | 数学论文写作：起草、修订、结构化与审稿回复 | — | ✅ 可用（[VeryMath](https://github.com/VeryMath)）|
| [_template/](./_template/) | **新模板起点** | example-skill(示例)| 📋 模板 |

---

## 怎么用

### 方式一:简单模式预设卡片(推荐)

Inno Agent 默认从本仓库的 `workspace-templates/` 拉取模板。打开「简单模式」,欢迎页会列出上面这些预设,点卡片即创建并绑定一个配好的工作区。

> 拉取源可在 App 设置 →「内容源」中切换(公共仓库 / 私有 GitHub 仓库 / 自托管服务)。

### 方式二:手动上传到工作区

1. 在 Inno Agent 新建一个工作区。
2. 把模板的 `agent.md` 放到工作区根目录(让 Agent 创建,或拖拽到文件树空白区域)。
3. 把模板 `.skills/` 下每个技能的 `SKILL.md`(或自行打包的 `.zip`)通过文件树工具栏 **✦ 按钮**上传,落到工作区的 `.skills/<名称>/SKILL.md`。
4. 新建会话绑定该工作区即可。

> 详细操作步骤参见 [`how-to/skill-tutorial.md`](../how-to/skill-tutorial.md)。

---

## 贡献一个新模板

1. 复制 [`_template/`](./_template/),重命名为你的模板 id(如 `my-template`)。
2. 编辑 `preset.json`:把 `id` 改成新目录名,填好 `name` / `description` / **`category`**(必填,见下) / `icon`。
3. 编辑 `agent.md`:定义这个工作区的 Agent 人格与工作流程。
4. 按需在 `.skills/` 下增删技能(每个技能一个目录,内含 `SKILL.md`)。
5. 在上面的「模板列表」表格里加一行。
6. 提交 PR。

> **`category` 必填** —— 客户端按 `category` 分组显示预设卡片,缺失会落到「未分类」组。当前可用: `教学` / `演示` / `verymath`(从这三个里挑,不要新造)。新增分类请先提 issue。详见仓库根目录 [README.md 的「分类标签 (必填)」](../README.md#分类标签-必填)。

> 命名约定:`id` 用小写连字符(`kebab-case`);以 `_` 或 `.` 开头的目录(如 `_template`)不会被当作可用预设拉取,适合放骨架/草稿。
