# Skill Library

Inno Agent Skill 集合整理 —— 每个 Skill 是独立目录，可直接下载打包上传到工作区。



---

## 快速使用

从本仓库下载 Skill 目录（或自行打包为 `.zip`），按需求选择**全局**或**工作区**上传入口：

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>工作区 Skill（局部）</h3>
      <p>仅对绑定该工作区的会话生效。在工作区「预览」页，点击文件树工具栏 <strong>✦</strong> 按钮，上传 <code>.md</code> 或 <code>.zip</code>。</p>
      <img src="./assets/upload-workspace-skill.gif" alt="工作区 Skill 上传示意" width="100%">
    </td>
    <td width="50%" valign="top">
      <h3>全局 Skill</h3>
      <p>对所有工作区的会话生效。点击右侧「<strong>技能</strong>」标签页 → 右上角「<strong>上传</strong>」。</p>
      <img src="./assets/upload-global-skill.gif" alt="全局 Skill 上传示意" width="100%">
    </td>
  </tr>
</table>


## Skill 列表

按场景分组，便于按需取用。

> ⚠️ **新增 Skill 必须在 frontmatter 加 `category` 标签** —— Inno Agent 客户端按 `category` 分组并支持搜索,缺失会落到「未分类」组。可用分类: `教学辅导` / `内容创作` / `文档处理` / `研究检索` / `开发工具`。详细约定见仓库根目录 [README.md 的「分类标签 (必填)」](../README.md#分类标签-必填) 一节。

### 🌐 工具 · 信息获取

| Skill | 类型 | 一句话 |
|---|---|---|
| [tavily-search](./tavily-search/) | 原创 | 实时网络搜索，补充过时信息（需申请 [Tavily API Key](https://www.tavily.com/)，免费 1000 次/月） |

### 📐 教育 · 数学

| Skill | 类型 | 一句话 | 引用 | 效果 |
|---|---|---|---|---|
| [edu-solid-geometry](./edu-solid-geometry/) | 收集 | 立体几何题 → Three.js 交互 3D 解题页 | [wy51ai/edulab](https://github.com/wy51ai/edulab/tree/master/skills/edu-solid-geometry) | [demo](./assets/edu-solid-geometry/demo.gif) |
| [edu-analytic-geometry](./edu-analytic-geometry/) | 收集 | 圆锥曲线题 → Canvas 2D 动态画板 | [wy51ai/edulab](https://github.com/wy51ai/edulab/tree/master/skills/edu-analytic-geometry) | [demo](./assets/edu-analytic-geometry/demo.gif) |

### 📚 教育 · 备考与刷题

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [Exam2Knowledge](./Exam2Knowledge/) | 收集 |  | 把考题逆向拆成高频考点、解题模板与错题库，构建应试模式识别（理科优先） | [AtomerCore/Exam2Knowledge-skill](https://github.com/AtomerCore/Exam2Knowledge-skill) |

### 🧑‍🏫 教育 · 教案与教学设计

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [k12-lesson-planning](./k12-lesson-planning/) | 收集 |  | K-12 从零备课：教案＋学生用材料＋课堂观察表，分学科（数学/ELA/科学/社会），输出可编辑 Word | [anthropics/k12-teacher-skills](https://github.com/anthropics/k12-teacher-skills/tree/main/plugin/skills/k12-lesson-planning) |
| [k12-lesson-differentiation](./k12-lesson-differentiation/) | 收集 |  | 把已有 K-12 课按学生水平分层：1 份教师分层方案＋3 份学生分层材料，全为可编辑 Word | [anthropics/k12-teacher-skills](https://github.com/anthropics/k12-teacher-skills/tree/main/plugin/skills/k12-lesson-differentiation) |
| [backwards-design-unit-planner](./backwards-design-unit-planner/) | 收集 |  | 逆向设计（UbD）：从学习成果倒推评估证据与学习活动，产出完整单元教学计划 | [GarethManning/education-agent-skills](https://github.com/GarethManning/education-agent-skills/tree/main/skills/curriculum-assessment/backwards-design-unit-planner) |
| [scope-and-sequence-designer](./scope-and-sequence-designer/) | 收集 |  | 课程范围与进度：跨年级/学期的纵向进阶与横向衔接，带先修依赖与连贯性检查 | [GarethManning/education-agent-skills](https://github.com/GarethManning/education-agent-skills/tree/main/skills/curriculum-assessment/scope-and-sequence-designer) |
| [explicit-instruction-sequence-builder](./explicit-instruction-sequence-builder/) | 收集 |  | 显性教学课时序列（I Do/We Do/You Do），含理解检查点与时间分配的可上课教案 | [GarethManning/education-agent-skills](https://github.com/GarethManning/education-agent-skills/tree/main/skills/explicit-instruction/explicit-instruction-sequence-builder) |
| [differentiation-adapter](./differentiation-adapter/) | 收集 |  | 同一任务按学困/超常/多动/读写障碍等差异化适配，保持学习目标不变 | [GarethManning/education-agent-skills](https://github.com/GarethManning/education-agent-skills/tree/main/skills/curriculum-assessment/differentiation-adapter) |
| [formative-assessment-technique-selector](./formative-assessment-technique-selector/) | 收集 |  | 按教学时刻挑随堂检测/形成性评估技术，含实施步骤与学生应答解读 | [GarethManning/education-agent-skills](https://github.com/GarethManning/education-agent-skills/tree/main/skills/curriculum-assessment/formative-assessment-technique-selector) |

### 🧑‍🏫 教育 · 教师与批改

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [comment-on-docx](./comment-on-docx/) | 收集 |  | 给 Word（.docx）加原生批注式反馈，定位到具体词句、不改原文，适合作文/论文/作业批改 | [tim-hua-01/comment-on-docx](https://github.com/tim-hua-01/comment-on-docx) |
| [homework-grader](./homework-grader/) | 收集 |  | 量规驱动批改作业：证据引用打分、批量处理、生成评语、师生评分校准、导出 Excel | [ChantillyAn/homework-grader](https://github.com/ChantillyAn/homework-grader) |

### 🎓 教育 · 自学与辅导

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [tutor](./tutor/) | 收集 |  | 像优秀人类家教一样教任何学科，建立可迁移的真正理解而非直接给答案 | [cdmorozov/claude-tutors](https://github.com/cdmorozov/claude-tutors) |
| [math-tutor](./math-tutor/) | 收集 |  | 数学自学家教：引导建立真正理解，检查解法/证明而非直接给步骤 | [cdmorozov/claude-tutors](https://github.com/cdmorozov/claude-tutors) |
| [socratic-tutor](./socratic-tutor/) | 收集 |  | 苏格拉底式引导讲题：0-4 级提示阶梯，绝不直接给完整答案（编程教学） | [Pyroxin/opinionated-claude-skills](https://github.com/Pyroxin/opinionated-claude-skills) |
| [learning-opportunities](./learning-opportunities/) | 收集 |  | AI 辅助编码后塞入循证学习练习，对抗 vibe coding 的能力退化 | [DrCatHicks/learning-opportunities](https://github.com/DrCatHicks/learning-opportunities) |

### 📄 文档 · 办公与转换

> 「通过验证」:✅ = 已人工验证可用,留空 = 未验证。

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [xlsx](./xlsx/) | 收集 |  | 处理 .xlsx/.csv/.tsv 表格的读取、编辑、修复、分析与公式计算 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/xlsx) |
| [pdf](./pdf/) | 收集 |  | 处理重排版的 PDF 读取、创建与审阅，借 Poppler 渲染与 Python 库 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/openai-office-skills/skills/pdf) |
| [docx](./docx/) | 收集 |  | 创建、读取与编辑 Word（.docx）文档 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/anthropic-office-skills/skills/docx) |
| [pptx](./pptx/) | 收集 |  | 处理任何涉及 .pptx 的场景：创建、读取、解析或提取幻灯片内容 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/anthropic-office-skills/skills/pptx) |
| [markitdown](./markitdown/) | 收集 |  | 用 MarkItDown 将 PDF、Office 文档、图片、音频等转换为 Markdown | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/markitdown) |

### 🔎 学习 · 研究与笔记

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [paper-lookup](./paper-lookup/) | 收集 |  | 通过 REST API 检索 PubMed、arXiv、OpenAlex 等 10 个学术论文库 | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/paper-lookup) |
| [citation-management](./citation-management/) | 收集 |  | 学术引用管理：检索 Google Scholar 与 PubMed，校验文献并生成 BibTeX | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/citation-management) |
| [baoyu-youtube-transcript](./baoyu-youtube-transcript/) | 收集 |  | 按 URL 或视频 ID 下载 YouTube 字幕与封面，支持翻译与分章 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-youtube-transcript) |
| [baoyu-url-to-markdown](./baoyu-url-to-markdown/) | 收集 |  | 用 baoyu-fetch 抓取任意 URL 转为 markdown，内置 X、YouTube 等适配器 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-url-to-markdown) |
| [understand](./understand/) | 收集 |  | 分析代码库生成交互式知识图谱，理解架构、组件与关系 | [Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything/tree/HEAD/understand-anything-plugin/skills/understand) |
| [storm-research](./storm-research/) | 收集 |  | 多视角提问 + 联网检索 + 强制引用，产出维基百科式带来源的深度研究报告 | [openwhat007/storm-research](https://github.com/openwhat007/storm-research) |

### 🎨 创作 · 知识可视化

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [baoyu-comic](./baoyu-comic/) | 收集 |  | 知识漫画创作，支持多种画风与基调，分镜排版并按序生成图像 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-comic) |
| [baoyu-infographic](./baoyu-infographic/) | 收集 |  | 用 21 种布局与 21 种风格生成可发布的专业信息图 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-infographic) |
| [baoyu-slide-deck](./baoyu-slide-deck/) | 收集 |  | 从内容生成专业幻灯片图像，先出带风格的提纲再逐页生图 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-slide-deck) |
| [smart-illustrator](./smart-illustrator/) | 收集 |  | 智能配图与 PPT 信息图生成器，三种模式（文章配图 / 批量信息图 / 封面图） | [axtonliu/smart-illustrator](https://github.com/axtonliu/smart-illustrator) |
| [ian-xiaohei-illustrations](./ian-xiaohei-illustrations/) | 收集 |  | 生成 Ian「小黑」风格的中文正文配图（手绘、怪诞、16:9 解释图） | [helloianneo/ian-xiaohei-illustrations](https://github.com/helloianneo/ian-xiaohei-illustrations) |

### 🧩 元能力 · 技能与提示词

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [skill-creator](./skill-creator/) | 收集 |  | 创建、修改、优化 skill 并运行评测衡量其表现（自带 Apache-2.0 LICENSE） | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/skill-creator) |
| [prompt-engineer](./prompt-engineer/) | 收集 |  | 编写、重构与评估 LLM 提示词，产出优化模板、结构化输出 schema 与测试套件 | [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills/tree/HEAD/skills/prompt-engineer) |

### 🎨 创作 · 视觉与设计

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [algorithmic-art](./algorithmic-art/) | 收集 |  | 用 p5.js 创作算法生成艺术，支持随机种子与交互式参数探索 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/algorithmic-art) |
| [canvas-design](./canvas-design/) | 收集 |  | 运用设计理念创作海报、艺术品等静态视觉作品，输出 PNG 与 PDF | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/canvas-design) |
| [theme-factory](./theme-factory/) | 收集 |  | 用预设主题为幻灯片、文档、HTML 落地页等产物统一配色与字体 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/theme-factory) |
| [frontend-slides](./frontend-slides/) | 收集 |  | 一句话 / PPT → 零依赖单文件动画网页幻灯片，内置 12 配色预设 + 34 设计模板 | [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) |

### 📝 写作 · 文档协作

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [doc-coauthoring](./doc-coauthoring/) | 收集 |  | 引导结构化协作流程，共同撰写技术文档与规范 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/doc-coauthoring) |

### 💻 开发 · 构建与测试

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [claude-api](./claude-api/) | 收集 |  | 构建、调试与优化 Claude API / Anthropic SDK 应用，含 prompt caching 与版本迁移 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/claude-api) |
| [mcp-builder](./mcp-builder/) | 收集 |  | 构建高质量 MCP (Model Context Protocol) 服务器以让 LLM 接入外部服务 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/mcp-builder) |
| [web-artifacts-builder](./web-artifacts-builder/) | 收集 |  | 用 React、Tailwind CSS 与 shadcn/ui 构建复杂多组件的 claude.ai HTML artifact | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/web-artifacts-builder) |
| [webapp-testing](./webapp-testing/) | 收集 |  | 用 Playwright 测试本地 Web 应用，验证前端功能、调试 UI 并截图取日志 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/webapp-testing) |
| [frontend-design](./frontend-design/) | 收集 |  | 打造高设计品质的生产级前端界面、页面与作品 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/frontend-design) |








---

## 目录结构

```
skill-library/
├── README.md
├── assets/                          # 文档展示用，不参与上传
│   ├── upload-workspace-skill.gif   # 工作区上传示意
│   ├── upload-global-skill.gif      # 全局上传示意
│   ├── edu-solid-geometry/demo.gif
│   └── edu-analytic-geometry/demo.gif
├── edu-solid-geometry/              # ← 可直接打包上传
│   ├── SKILL.md                     # 含 frontmatter description：用途与效果
│   └── lib/  scripts/  template/  references/
└── edu-analytic-geometry/
    └── ...
```

---

## 贡献新 Skill

### 必填: `category` 分类标签

在 `SKILL.md` frontmatter 的 `name:` 后加一行 `category: <值>`:

```yaml
---
name: my-awesome-skill
category: 教学辅导
description: >-
  一句话讲清这个 skill 做什么...
---
```

可用分类(从下面五个里挑一个,**不要新造**):

| 分类 | 适用场景 |
|---|---|
| `教学辅导` | 家教/讲题/讲解、自学陪练、作业批改、考点拆解 |
| `内容创作` | 视觉/图文/幻灯片/前端艺术等创作产出 |
| `文档处理` | Office / PDF / Markdown / 网页 → 结构化文本读写转换 |
| `研究检索` | 学术检索、联网搜索、引用管理、深度研究 |
| `开发工具` | LLM 应用开发、提示词工程、MCP / Skill 元能力、代码理解与测试 |

> 需要新增分类? 先提 issue 讨论再加,避免一堆只含 1 个条目的孤立分组。客户端会按字符串完全匹配做分组,**标签拼写要和上表完全一致**(包括中文标点)。

完整贡献流程见仓库根目录 [README.md 的「贡献」一节](../README.md#贡献)。


