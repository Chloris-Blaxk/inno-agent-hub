---
name: innovative-lesson-plan-skill
description: 生成 PBL、跨学科和 AI 融合三类创新教案。适用于教师需要把创新课想法转成可落地教案、驱动问题、融合节点、AI 使用边界、活动流程、评价量规和 Word-ready Markdown 的任务；不用于普通课件生成、课堂互动网页生成或商业演示稿制作。
entryName: 创新教案生成
entryToken: "@创新教案生成"
displayName: 创新教案生成
status: runnable_prototype
---

# 创新教案生成 Skill

## 场景定位

面向中小学教师设计 PBL、跨学科融合和 AI 融合课堂时缺少落地脚手架的问题，将“我想做一节创新课”的模糊想法转成结构完整、类型边界清楚、活动和评价可执行的教案。

核心闭环：

`教师初始想法 -> 创新类型澄清 -> 类型专属上下文确认 -> render 脚本生成结构化教案 -> Markdown/DOCX 导出 -> 本地校验`

本 Skill 不负责课件页面、课堂互动 HTML、普通教学反思、论文写作或项目申报。

## 入口与路由契约

- 显式入口：`@创新教案生成`。
- Skill ID：`innovative-lesson-plan-skill`。
- 当前状态：`runnable_prototype`。
- 当用户显式使用 `@创新教案生成` 时，优先进入本 Skill。
- 无显式入口时，由外层 Controller 或 `agent_cases/agent_cli.py` 返回菜单或按用户选择序号路由，不依赖关键词猜测。
- `agent_cases/skill-entrypoints.json` 中的必填槽位为 `subject`、`grade`、`topic`；`innovationType` 由 Controller 通过澄清流程补齐。

## 能力边界

### 可以做

- 生成 PBL、跨学科融合、AI 融合三类创新教案。
- 引导教师明确创新类型、最终产出、融合节点、AI 介入环节和使用边界。
- 输出结构化 JSON、Word-ready Markdown，并默认尝试导出 DOCX。
- 基于本地 schema、行为动词、活动-目标-评价引用关系和类型专属字段做质量校验。
- 使用 `confirmedContext` 约束生成结果，使教案贴合阶段一确认内容。

### 不可以做

- 不把普通教案简单包装成创新教案。
- 不把 PBL 简化成资料搜集、展示汇报或手抄报。
- 不把跨学科融合写成两个学科标签并列，必须说明真实关联和适用边界。
- 不把 AI 融合写成炫技环节，必须服务教学目标并包含学生审辨任务。
- 不生成课件、网页互动工具或完整课堂 PPT；需要时由下游 Skill 承接。
- 不承诺真实课标库、教材库已经接入；当前 `references/` 内为 mock data，可替换。

## 任务模式

本 Skill 用 `innovationType` 区分三类核心任务：

| innovationType | 场景 | 核心输入 | 核心输出 | 是否可独立运行 |
|---|---|---|---|---|
| `PBL` | 项目化学习、真实问题探究、作品产出 | 驱动问题方向、最终产出、项目跨度 | 驱动问题、里程碑、阶段产出、过程/作品评价量规 | 是 |
| `interdisciplinary` | 一个任务需要两个学科知识共同完成 | 主学科、关联学科、融合节点、适用边界 | 学科关联、融合节点、共同产出、跨学科活动流程 | 是 |
| `ai_integrated` | 课堂中使用 AI 工具辅助学习 | AI 介入环节、使用边界、学生审辨方式 | AI 工具角色、人机协同流程、审辨任务、风险边界 | 是 |

执行分为两个阶段：

| 阶段 | 主责 | 产出 |
|---|---|---|
| 需求明确 | Controller | 完整请求 JSON，含 `innovationType` 和 `confirmedContext` |
| 生成执行 | `scripts/render_lesson_plan.py` + Generator | `.json`、`.md`、可选 `.docx`，并运行校验 |

## 输入契约

脚本当前消费扁平 JSON 配置。最小请求结构：

```json
{
  "subject": "科学",
  "grade": "六年级",
  "topic": "校园节水方案设计",
  "innovationType": "PBL",
  "durationMin": 40,
  "constraints": ["普通教室", "可使用平板", "小组合作"],
  "requirements": "生成一份 PBL 教案，包含驱动问题、活动流程、阶段产出和评价量规。",
  "confirmedContext": {
    "drivingQuestionDirection": "基于校园真实用水情况提出可执行方案",
    "finalProductType": "方案海报",
    "projectSpan": "单课时40分钟"
  }
}
```

### 必需输入

| 字段 | 类型 | 说明 | 缺失处理 |
|---|---|---|---|
| `subject` | string | 学科 | Controller 追问 |
| `grade` | string | 年级或学段 | Controller 追问 |
| `topic` | string | 课题或真实任务主题 | Controller 追问 |
| `innovationType` | string | `PBL`、`interdisciplinary`、`ai_integrated` | 进入类型澄清 |
| `durationMin` | number | 课时长度 | 默认 40，并写入 `assumptions` |

### 推荐输入

| 字段 | 用途 | 缺失影响 |
|---|---|---|
| `constraints` | 教室、设备、分组、材料条件 | 缺失时按普通教室保守生成 |
| `requirements` | 教师个性化要求 | 缺失时只按类型默认闭环生成 |
| `confirmedContext` | 阶段一确认的类型专属信息 | 缺失时可生成，但质量报告必须 warning |
| `textbookVersion` | 教材版本 | 缺失时不写实教材页码 |

## 信息缺失与降级

- 缺少 `subject`、`grade` 或 `topic` 时，Controller 先问一个最小澄清问题，不直接生成。
- `innovationType` 不明确时，Controller 读取 `references/innovation-type-guide.json`，用目的和任务特征引导，不直接要求教师理解术语。
- 教师无法回答类型专属问题时，可以降级为 Generator 推荐，但必须写入 `confirmedContext` 的 fallback 或 `qualityReport.warnings`。
- 缺少真实课标、教材页码或学校材料时，不编造来源，只使用 mock curriculum 并标注假设。

## 执行协议

1. Controller 识别 `@创新教案生成`，抽取 `subject`、`grade`、`topic`、`requirements` 和显式约束。
2. 若 `innovationType` 不明确，Controller 读取 `references/innovation-type-guide.json`，完成类型引导和确认摘要。
3. Controller 形成完整请求 JSON，写入 `confirmedContext`。
4. `scripts/render_lesson_plan.py` 读取请求和 `references/`，调用 Generator 生成一个 JSON 对象。
5. 脚本按 `references/export-rules.json` 和 `assets/template-*.md` 生成类型专属 Markdown，并默认尝试 DOCX 导出。
6. 脚本运行 `scripts/validate_lesson_plan.py`；如 `confirmedContext` 覆盖不足，默认 warning，可用 `--strict-context` 转为失败。
7. Controller 向用户摘要核心教案、输出路径、校验状态、warnings 和下一步建议，不重复粘贴完整 JSON。

## 资源加载顺序

1. 读本 `SKILL.md`，确认入口、任务模式、边界和执行协议。
2. 读 `references/input-output-schema.md`，确认请求与输出结构。
3. 阶段一只读 `references/innovation-type-guide.json`。
4. 阶段二按需读 `references/mock-curriculum.json`、`design-scaffolds.json`、`integration-patterns.json`、`lesson-plan-examples.json`、`action-verbs.json`、`export-rules.json`。
5. 导出时按 `innovationType` 使用 `assets/template-pbl.md`、`assets/template-interdisciplinary.md` 或 `assets/template-ai-integrated.md`。
6. 输出前运行 `scripts/validate_lesson_plan.py`，并对照 `references/quality-checklist.md`。

## 输出契约

脚本核心输出：

- `<output>.json`：结构化创新教案。
- `<output>.md`：Word-ready Markdown。
- `<output>.docx`：可编辑 Word 文档，默认导出；如环境无 pandoc 或传入 `--no-docx` 可跳过。

结构化结果必须包含：

```json
{
  "lessonMeta": {},
  "backgroundAnalysis": {},
  "studentAnalysis": {},
  "coreCompetencies": [],
  "objectives": [],
  "teachingFocus": "",
  "teachingDifficulty": "",
  "innovationDesign": {},
  "activityFlow": [],
  "assessmentRubric": [],
  "resources": [],
  "export": {},
  "qualityReport": {}
}
```

Controller 面向下游或用户汇总时，建议使用统一信封：

```json
{
  "skillId": "innovative-lesson-plan-skill",
  "taskIntent": "PBL",
  "status": "pass|warn|failed",
  "inputSummary": {},
  "result": {},
  "artifacts": [],
  "handoff": {},
  "qualityReport": {},
  "warnings": [],
  "nextActions": []
}
```

## 脚本入口

生成样例：

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/render_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving \
  --config agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json \
  --thinking \
  --model qwen3.5-122b-a10b
```

不导出 DOCX：

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/render_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving \
  --config agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json \
  --no-docx
```

只校验已有 JSON：

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/validate_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving.json \
  --request agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json
```

严格校验 `confirmedContext` 覆盖度：

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/validate_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving.json \
  --request agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json \
  --strict-context
```

## 联动与 handoff

- 可向课件生成 Skill 传递 `handoff.lessonPlanSummary`、`handoff.activityFlow`、`handoff.objectives`、`handoff.assessmentRubric`、`handoff.artifactPaths`。
- handoff 只传结构化摘要和文件路径，不传完整 Markdown、DOCX 或大 JSON。
- 下游使用前必须重新按自己的输入契约校验，例如课件生成仍要确认 `subject`、`grade`、`topic` 和课时长度。
- 本 Skill 不要求课件生成、课堂互动网页或其他 Skill 作为前置。

## 质量标准

- 输出符合 `references/input-output-schema.md`。
- `lessonMeta.innovationType` 与请求一致。
- PBL 必须包含驱动问题、里程碑、最终产出和过程/作品评价。
- 跨学科必须包含主学科、关联学科、融合节点、共同产出和适用边界。
- AI 融合必须包含 AI 工具角色、介入环节、使用边界和学生审辨任务。
- 教学目标、活动流程、阶段产出和评价量规互相引用并对齐。
- 教学重点必须对齐主目标，教学难点必须在流程中有支架。
- 活动总时长应等于 `durationMin`。
- 行为动词应来自 `references/action-verbs.json` 且不过级。
- `confirmedContext` 中的类型专属信息应体现在 `innovationDesign`、`activityFlow` 或 `assessmentRubric` 中。

## 边界

- 当前为可运行原型，`references/` 使用 mock data，不声明真实教材页码或权威课标已接入。
- 不承诺一份教案同时完整承载两种以上创新类型。
- 不预测课堂效果、比赛获奖或项目申报结果。
- 模型必须只返回一个 JSON 对象；脚本可提取代码块中的首个合法 JSON，但不接受多个对象混排。
- API key、base URL 和模型名由环境变量或脚本参数注入，不写入请求体和输出文件。

## 资源索引

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `references/input-output-schema.md` | 请求与输出结构 | 每次 |
| `references/quality-checklist.md` | 质量自检 | 输出前 |
| `references/innovation-type-guide.json` | 类型引导、专属追问、确认模板 | 阶段一 |
| `references/mock-curriculum.json` | mock 课标、知识点、教材进度 | 阶段二 |
| `references/design-scaffolds.json` | 三类创新设计脚手架 | 阶段二 |
| `references/integration-patterns.json` | AI 融合和跨学科模式 | 阶段二 |
| `references/lesson-plan-examples.json` | few-shot 教案样例 | 阶段二 |
| `references/action-verbs.json` | 行为动词层级 | 校验 |
| `references/export-rules.json` | Markdown/DOCX 导出章节规则 | 导出 |
| `assets/template-pbl.md` | PBL Markdown 模板 | 导出 |
| `assets/template-interdisciplinary.md` | 跨学科 Markdown 模板 | 导出 |
| `assets/template-ai-integrated.md` | AI 融合 Markdown 模板 | 导出 |

## 组件地图

- `scripts/render_lesson_plan.py`：主生成入口，负责请求预检、模型调用、JSON 提取、Markdown/DOCX 导出和默认校验。
- `scripts/validate_lesson_plan.py`：结构、类型专属字段、时长、行为动词、引用关系和 `confirmedContext` 覆盖度校验。
- `assets/template-*.md`：三类教案的类型专属导出模板。
