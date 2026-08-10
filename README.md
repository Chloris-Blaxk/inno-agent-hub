# Inno Agent Hub

> Inno Agent 的文档、Skill 与工作区模板合集 —— 一个让你**快速上手、按场景取用、随时贡献**的资源仓库。

[![主项目](https://img.shields.io/badge/main--repo-inno--agent-blue)](https://github.com/hhyqhh/inno-agent)
[![教程](https://img.shields.io/badge/docs-tutorial-green)](./how-to/skill-tutorial.md)
[![Skills](https://img.shields.io/badge/skills-library-orange)](./skill-library/)

---

## 这是什么

[Inno Agent](https://github.com/hhyqhh/inno-agent) 是一个**本地运行、有长期记忆**的个人学习助手。它通过「工作区上下文 + Skill 包」组合，把通用 LLM 变成贴合具体学习场景的专属 Agent。

本仓库收集围绕 Inno Agent 的全部**外部资源**：

- **怎么用** —— 入门教程、专题指南
- **能做什么** —— 自研 / 收集的 Skill 包，开箱即用
- **怎么搭** —— 按场景准备好的工作区模板（agent.md + skills 组合）

主项目代码在 [`hhyqhh/inno-agent`](https://github.com/hhyqhh/inno-agent)；本仓库**不含运行时代码**，纯文档与资源。

---

## 仓库导航

| 目录 | 内容 | 适合谁 |
|---|---|---|
| 🛠 [`how-to/`](./how-to/) | 入门与专题教程：Skill 编写、工作区配置等 | 第一次接触 / 想做点定制 |
| 🎨 [`skill-library/`](./skill-library/) | Skill 收集库，含说明 + 效果展示 | 想直接拿来用 |
| 📦 [`workspace-templates/`](./workspace-templates/) | 工作区模板：agent.md + .skills 组合 | 想一键搭建场景 |

---

## 快速开始

按你的角色选择入口：

**🚀 我是新用户** —— 从 [`how-to/skill-tutorial.md`](./how-to/skill-tutorial.md) 开始，跟着雅思备考的例子跑通第一个工作区。

**🎯 我想试试现成 Skill** —— 浏览 [`skill-library/`](./skill-library/)，挑一个 Skill 包下载，按教程上传到工作区。当前已收录：

- [`edu-solid-geometry`](./skill-library/edu-solid-geometry/) — 立体几何题 → Three.js 交互解题页
- [`edu-analytic-geometry`](./skill-library/edu-analytic-geometry/) — 圆锥曲线题 → Canvas 交互解题页

**📦 我想按场景一键搭建工作区** —— 去 [`workspace-templates/`](./workspace-templates/) 选模板，复制 `agent.md` + `.skills/` 即可。当前已收录：

- [`ielts-prep`](./workspace-templates/ielts-prep/) — 雅思英语备考工作区
- [`question-led-learning`](./workspace-templates/question-led-learning/) — Agent 给概念线索、学习者主动追问的深度学习工作区
- [`task-alignment`](./workspace-templates/task-alignment/) — 复杂任务先探索对齐、确认后执行并按证据验收
- **VeryMath AI4Math 系列**（7 个模板） — 来自 [VeryMath](https://github.com/VeryMath) 开源组织，覆盖数学形式化、论文读写、计算数学、优化、自动科研、进化实验等场景

**🧑‍🏫 我想自己写 Skill** —— 读 [`how-to/skill-tutorial.md`](./how-to/skill-tutorial.md)，看 `agent.md` 与 SKILL 包的设计与上传方式。

---

## Skill 与 Workspace 的关系

```
┌──────────────────────────────────────────────────────────┐
│  Inno Agent 工作区                                       │
│                                                          │
│   agent.md             ← 工作区上下文（学习背景/偏好）   │
│   .skills/             ← 专项能力（触发条件/格式/流程）  │
│     └─ xxx/SKILL.md                                      │
│   files/               ← 你的学习资料                    │
│                                                          │
└──────────────────────────────────────────────────────────┘
              ▲                       ▲
              │                       │
   workspace-templates/        skill-library/
   （拿走整套工作区）          （单挑某个能力）
```

详见 [`how-to/skill-tutorial.md`](./how-to/skill-tutorial.md) 的「设计思路」一节。

---

## 贡献

欢迎提交你自己的 Skill 或工作区模板：

1. **新 Skill** → 在 `skill-library/` 下新建目录，包含 `SKILL.md` + 必要的 `lib/scripts/template/references/`。用途与效果写在 `SKILL.md` 的 frontmatter `description` 里，并在 `skill-library/README.md` 的 Skill 列表登记一行。效果图请放到 `skill-library/assets/<skill-name>/`。
2. **新 Workspace 模板** → 在 `workspace-templates/` 下新建目录，包含 `agent.md` 与 `.skills/`，并在该目录的 `README.md` 描述适用场景。
3. **教程或文档勘误** → 直接 PR 到 `how-to/`。

> ⚠️ **必填:`category` 分类标签** —— Inno Agent 客户端会按 `category` 对技能/预设做分组与筛选,**不写就会被甩到「未分类」分组**。提交新 Skill 或新 Workspace 模板时,**必须在 frontmatter / `preset.json` 里加 `category` 字段**。详细分类列表与写法见下方「[分类标签 (必填)](#分类标签-必填)」一节。

提交前请确认：
- **已加 `category` 字段**(见下文「分类标签」)
- 不要把 `.DS_Store`、屏幕录像（`*.mov`）等本地文件入库（已在 `.gitignore` 中忽略）
- 效果展示用 GIF / PNG，不要直接放视频文件
- 中文文档优先，必要时附英文说明

---

## 分类标签 (必填)

Inno Agent 客户端会按 `category` 把技能/预设分组显示(技能库浏览器、简单模式预设卡片均按此分组),并支持搜索过滤。**所有新增条目必须带 `category`**;遗漏会落到「未分类」组,体验明显变差。

### 当前分类列表

**Skill 分类** (写在 `SKILL.md` frontmatter):

| 分类 | 适用场景 |
|---|---|
| `教学辅导` | 家教/讲题/讲解、自学陪练、作业批改、考点拆解(如 tutor、math-tutor、socratic-tutor、homework-grader、comment-on-docx、edu-* 系列) |
| `内容创作` | 视觉/图文/幻灯片/前端艺术等创作产出(如 baoyu-comic、smart-illustrator、frontend-design、canvas-design、theme-factory) |
| `文档处理` | Office / PDF / Markdown / 网页 → 结构化文本的读写转换(如 docx、pdf、pptx、xlsx、markitdown、baoyu-url-to-markdown) |
| `研究检索` | 学术检索、联网搜索、引用管理、深度研究报告(如 paper-lookup、tavily-search、citation-management、storm-research) |
| `开发工具` | LLM 应用开发、提示词工程、MCP / Skill 元能力、代码理解与测试(如 claude-api、mcp-builder、prompt-engineer、skill-creator、understand、webapp-testing) |

**Preset 分类** (写在 `preset.json`):

| 分类 | 适用场景 |
|---|---|
| `教学` | 备课、出题、讲解、辅导类工作区(如 lesson-plan、classroom-quiz、knowledge-explain、math-interactive、scenario-explain、teaching-webpage、ielts-prep) |
| `演示` | 幻灯片/演示文稿/分享页类工作区(如 ppt-creation) |
| `verymath` | AI 辅助数学形式化工作区(Lean 4 / mathlib 环境配置、定理形式化、证明修复；来源：[VeryMath/AI4Math-Lean-Agents](https://github.com/VeryMath/AI4Math-Lean-Agents)) |

> 新分类不在表里? 提 issue 讨论再加。**不要随手新造一个分类**,会让客户端出现一堆 1 个条目的孤立分组。

### 怎么加

**Skill** — 在 `SKILL.md` frontmatter 的 `name:` 后插一行 `category: <值>`:

```yaml
---
name: my-awesome-skill
category: 教学辅导
description: >-
  用一段话讲清这个 skill 做什么...
---
```

**Preset** — 在 `preset.json` 里加 `category` 字段(放在 `description` 与 `icon` 之间最直观):

```json
{
  "id": "my-template",
  "name": "我的模板",
  "description": "一句话说明用途",
  "category": "教学",
  "icon": "book-open"
}
```

> `category` 是简单的顶层字符串字段,**不要嵌套**、不要用数组、不要本地化(中文标签即可,客户端按字符串匹配分组)。

---

## 关联项目

- [`hhyqhh/inno-agent`](https://github.com/hhyqhh/inno-agent) — 主项目（Inno Agent 运行时）
- [`wy51ai/edulab`](https://github.com/wy51ai/edulab) — 教育领域 Skill 上游来源
- [**VeryMath**](https://github.com/VeryMath) — AI4Math 数学智能体，本仓库 `verymath` 分类下 7 个工作区模板的上游来源。VeryMath 专注于用 AI Agent 辅助数学研究，涵盖 Lean 4 形式化证明、计算数学、数学优化、论文读写、自动科研等方向。对应仓库：
  - [`AI4Math-Lean-Agents`](https://github.com/VeryMath/AI4Math-Lean-Agents) → 模板 `ai4math-lean-agents`
  - [`AI4Math-Paper-Reading`](https://github.com/VeryMath/AI4Math-Paper-Reading) → 模板 `ai4math-paper-reading`
  - [`AI4Math-Paper-Writing`](https://github.com/VeryMath/AI4Math-Paper-Writing) → 模板 `ai4math-paper-writing`
  - [`AI4Math-Computational-Mathematics`](https://github.com/VeryMath/AI4Math-Computational-Mathematics) → 模板 `ai4math-computational-mathematics`
  - [`AI4Math-Optimization`](https://github.com/VeryMath/AI4Math-Optimization) → 模板 `ai4math-optimization`
  - [`AI4Math-Auto-Research`](https://github.com/VeryMath/AI4Math-Auto-Research) → 模板 `ai4math-auto-research`
  - [`AI4Math-Evolving`](https://github.com/VeryMath/AI4Math-Evolving) → 模板 `ai4math-evolving`

---

## License

文档与 Skill 内容按各子目录所注协议提供；如未单独标注，默认遵循主项目协议。
