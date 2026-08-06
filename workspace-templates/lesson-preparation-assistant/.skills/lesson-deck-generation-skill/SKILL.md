---
name: lesson-deck-generation-skill
description: 根据中小学教师的课题描述生成教育版课件。适用于课堂 PPT、结构化课堂大纲、教师逐字稿、ED 固定版式 HTML 预览、PPTX-ready 可编辑结构和投影友好课件任务；不用于商业演示稿美化、普通网页工具或创新教案本体生成。
entryName: 课件生成
entryToken: "@课件生成"
displayName: 课件生成
status: runnable_prototype
---

# 课件生成 Skill

## 场景定位

面向中小学教师备课时“只有课题，缺少课堂结构、逐字稿、投影友好版式和可编辑课件产物”的问题，将课题描述转成可确认、可渲染、可校验的教育版课件。

核心闭环：

`课题描述 -> 教学设计稿 -> 教师逐字稿 -> ED 固定版式 deck JSON -> HTML 横向课件 -> PPTX-ready 可编辑结构 -> 质量校验`

本 Skill 的重点不是演讲 PPT 美化，而是课堂节奏正确、学生屏幕清楚、教师备注可上课、PPTX 对象可编辑。

## 入口与路由契约

- 显式入口：`@课件生成`。
- Skill ID：`lesson-deck-generation-skill`。
- 当前状态：`runnable_prototype`。
- 当用户显式使用 `@课件生成` 时，优先进入本 Skill。
- 无显式入口时，由外层 Controller 或 `agent_cases/agent_cli.py` 返回菜单或按用户选择序号路由，不依赖关键词猜测。
- `agent_cases/skill-entrypoints.json` 中的必填槽位为 `subject`、`grade`、`topic`。

## 能力边界

### 可以做

- 生成阶段一教学设计稿：课堂目标、页面规划、教学节奏和版式分配。
- 基于确认后的设计稿生成教师逐字稿、学生屏幕内容、追问和备注。
- 基于完整 deck JSON 渲染单文件 HTML 横向课件。
- 导出 PPTX-ready 可编辑结构，并可调用导出脚本生成基础可编辑 PPTX。
- 校验 JSON 结构、ED 版式、视觉槽位、反馈证据、教师信息泄漏和 HTML 运行约束。

### 不可以做

- 不生成商业演示、营销路演或非教学场景 PPT。
- 不把整页课件做成图片；文本、图形、备注应可编辑。
- 不在学生屏幕中暴露教师逐字稿、预设学生回答或反馈证据。
- 不声明真实教材页码、课标库或图片素材库已接入；缺失时必须写入 `curriculumContext.assumptions`。
- 不跳过三阶段确认直接“一次性全出”作为默认路径。

## 任务模式

本 Skill 用 `--stage` 区分三类可执行任务：

| stage | 场景 | 核心输入 | 核心输出 | 是否可独立运行 |
|---|---|---|---|---|
| `design` | 先确认课堂设计和页面规划 | `--config` | `{prefix}.design.md`、`{prefix}.design.json` | 是 |
| `script` | 基于设计稿生成逐字稿和完整 deck JSON | `--config`，推荐附加 `--design-json` | `{prefix}.md`、`{prefix}.json` | 是 |
| `render` | 将已确认 deck JSON 渲染为 HTML | `--deck-json` | `{prefix}.html` | 是 |

推荐工作流是 `design -> script -> render`。阶段间由外层 Agent 或 Controller 收集教师确认意见，必要时回到上一阶段重新生成。

## 输入契约

请求使用统一信封格式，脚本兼容信封与扁平两种格式（向后兼容）。最小请求结构：

```json
{
  "requestId": "demo-001",
  "sourceRequest": "帮我生成一个五年级数学异分母分数加减法的课件",
  "taskIntent": "script",
  "input": {
    "subject": "数学",
    "grade": "五年级",
    "topic": "异分母分数加减法",
    "lessonType": "new_concept",
    "durationMin": 40,
    "textbookVersion": "人教版",
    "unit": "分数的加法和减法",
    "period": "第 1 课时",
    "studentProfile": {
      "priorKnowledge": ["同分母分数加减法", "通分"],
      "commonDifficulties": ["分母直接相加", "忘记约分"]
    },
    "requirements": "突出通分的本质，包含错误辨析和出门测。"
  },
  "options": {
    "stylePreset": "auto",
    "outputFormat": "html_preview+deck_json+teacher_script_md+pptx_ready"
  },
  "constraints": ["普通教室", "教师电脑投影", "可板书"],
  "assumptions": ["学生已学通分", "使用人教版教材"]
}
```

### 信封字段

| 字段 | 类型 | 说明 | 缺失处理 |
|---|---|---|---|
| `requestId` | string | 请求唯一 ID | 由 Controller 或脚本生成 |
| `sourceRequest` | string | 用户原始请求 | 用于回溯和调试 |
| `taskIntent` | string | 任务阶段：`design` / `script` / `render` | 与 `--stage` 对齐 |
| `input` | object | 核心领域输入 | 必填 |
| `options` | object | 风格、数量、模型、导出等可选参数 | 使用默认值 |
| `constraints` | array | 用户限制和硬约束 | 空数组 |
| `assumptions` | array | 默认值和保守假设 | 空数组 |

### 核心输入（input 子对象）

#### 必需输入

| 字段 | 类型 | 说明 | 缺失处理 |
|---|---|---|---|
| `subject` | string | 学科 | Controller 追问 |
| `grade` | string | 年级或学段 | Controller 追问 |
| `topic` | string | 课题 | Controller 追问 |

#### 推荐输入

| 字段 | 用途 | 缺失影响 |
|---|---|---|
| `lessonType` | 决定课堂节奏 | 默认 `new_concept` |
| `durationMin` | 控制页数和节奏 | 默认 40 |
| `textbookVersion`、`unit`、`period` | 标注教材上下文 | 写入待确认假设 |
| `studentProfile.priorKnowledge` | 影响导入和旧知激活 | 使用通用旧知模板 |
| `studentProfile.commonDifficulties` | 影响错误辨析页 | 使用通用错因模板 |
| `requirements` | 教师个性化要求 | 只按默认课型生成 |

#### 可选参数（options 子对象）

| 字段 | 用途 | 缺失影响 |
|---|---|---|
| `stylePreset` | 控制投影视觉风格 | 自动选择 |
| `outputFormat` | 指定输出产物类型 | 默认全量输出 |
| `model` | 指定生成模型 | 使用环境变量默认值 |

## 信息缺失与降级

- 缺少 `subject`、`grade` 或 `topic` 时，Controller 先问一个最小澄清问题。
- 其他字段缺失时，可按 `references/clarification-flow.md` 保守默认，并写入 `curriculumContext.assumptions`。
- 未命中 `references/subject-knowledge-packs.json` 时，使用 generic 模板并标注假设。
- 缺少真实图片时，只保留 `visualSlots` 占位和可选生成提示，不把占位当作真实素材。
- HTML 或 JSON 校验失败时，不交付为最终课件；需要修正后重新 validate。

## 执行层分工

AgentDesign Skill 清楚区分三层职责。

| 层 | 角色 | 应该做 | 不应该做 |
|---|---|---|---|
| Controller | 外层主控 | 识别入口、抽槽位、组装 config、调用脚本、摘要结果 | 直接编造复杂最终产物 |
| Skill | 能力契约 | 声明流程、资源、输入输出、边界、质量标准 | 承担全局路由或塞满领域资料 |
| Runtime/Script | 执行器 | 渲染、模型调用、校验、导出、错误码 | 隐式吞错或输出不可校验文本 |

核心原则：**Controller 控盘不生成，Generator 生成不控盘**。

- Controller 写请求配置、调脚本、修补结构缺陷、重建可读格式、运行校验——但**不直接生成教育内容**。
- Generator（`qwen3.5-122b-a10b` 或等价模型）根据结构化 prompt + references 生成教育内容 JSON——但**不做路由决策、不与用户交互**。
- Patch 脚本（`patch_lesson_deck.py`）作为流水线的**第二层防护**，在 Generator 输出后修复可预见的结构退化，只修结构不改内容。

## 错误自愈流程

Controller 遇到错误的处理原则：**自主修复，不打断用户**。

```
写入文件
  │
  ▼
立即校验（JSON parse → schema check → 引用完整性 → 业务规则）
  │
  ├─ 通过 → 继续下一步
  │
  └─ 失败 → 诊断原因
              │
              ├─ 编码/转义问题 → 修复后重写 → 再次校验
              ├─ 结构缺失/退化 → 调 Patch 脚本 → 再次校验
              ├─ 引用断裂 → 修正 ID → 再次校验
              └─ Generator 返回空/格式错误
                   └─ 记录 debug 信息 → 重试一次
                        └─ 仍失败 → 降级报告用户
```

**错误只在以下情况呈现给用户**：

- 连续两次 Generator 调用返回无效内容
- API key 缺失或网络不可达
- 请求配置存在 Controller 无法自行解决的逻辑矛盾

## 执行协议

1. Controller 识别 `@课件生成`，抽取 `subject`、`grade`、`topic` 和补充要求。
2. Controller 按 `references/clarification-flow.md` 判断是否需要追问；必需槽位缺失时先追问。
3. Controller 组装标准信封请求，写入 `examples/<case-name>.json`。
4. 阶段一调用 `scripts/render_lesson_deck.py --stage design`，产出设计稿和轻量结构。
5. 教师确认后，阶段二调用 `--stage script`；推荐附加 `--design-json` 锁定阶段一的页数、stage 和 `layoutId`。
6. 教师确认逐字稿后，阶段三调用 `--stage render --deck-json` 渲染 HTML；`render` 阶段不得重新读取 `--config` 生成内容。
7. 输出后运行 `scripts/patch_lesson_deck.py`（结构退化安全网）。
8. 运行 `scripts/validate_lesson_deck.py` 和 `scripts/validate_lesson_deck_html.py`。
9. 需要 PPTX 时，调用 `scripts/export_lesson_deck_pptx.mjs`，并保留可编辑对象和 speaker notes。
10. Controller 摘要呈现核心结果、输出路径、校验状态和下一步建议。

## 资源加载顺序

1. 读本 `SKILL.md`，确认任务阶段、边界和输出约束。
2. 读 `references/input-output-schema.md`。
3. 澄清阶段读 `references/clarification-flow.md`。
4. `design` 阶段读 `references/data-gap-brief.md`、`lesson-layout-lock.md`、`golden-samples.md`、`lesson-flow-templates.md`、`subject-knowledge-packs.json`。
5. `script` 阶段优先读取已确认的 `--design-json`，再生成逐字稿和学生屏幕内容。
6. `render` 阶段读 `references/slide-layouts.md`、`ed-layout-skeletons.md`、`projection-style-rules.md` 和 `assets/lesson-deck-template.html`。
7. 如需要图片素材，按 `references/image-generation-workflow.md` 处理 `visualSlots`。
8. 输出前运行 validate，并对照 `references/quality-checklist.md`。

## 输出契约

阶段输出：

- `design`：`{prefix}.design.md`、`{prefix}.design.json`。
- `script`：`{prefix}.md`、`{prefix}.json`。
- `render`：`{prefix}.html`。
- `export`：`{prefix}.pptx`，需单独调用导出脚本。

完整 deck JSON 必须包含：

```json
{
  "deckMeta": {},
  "curriculumContext": {},
  "designPlan": [],
  "lessonOutline": [],
  "slides": [],
  "teacherScript": [],
  "exportPlan": {},
  "qualityReport": {}
}
```

Controller 面向下游或用户汇总时，建议使用统一信封：

```json
{
  "skillId": "lesson-deck-generation-skill",
  "taskIntent": "design|script|render",
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

产物组织：每次生成产出到 `generated-outputs/<case-name>/` 独立子文件夹。

阶段一：生成教学设计稿。

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/render_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition \
  --config agent_cases/lesson-deck-generation-skill/examples/math-g5-fraction-addition.json \
  --stage design \
  --model qwen3.5-122b-a10b
```

输出：
- `generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.design.md`
- `generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.design.json`

阶段二：基于已确认设计稿生成逐字稿和完整 JSON。

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/render_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition \
  --config agent_cases/lesson-deck-generation-skill/examples/math-g5-fraction-addition.json \
  --design-json agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.design.json \
  --stage script \
  --model qwen3.5-122b-a10b
```

输出：
- `generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.md`
- `generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json`

阶段三：渲染 HTML。

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/render_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition \
  --deck-json agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json \
  --stage render
```

输出：
- `generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.html`

本地模板生成，不调用 LLM：

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/render_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition \
  --config agent_cases/lesson-deck-generation-skill/examples/math-g5-fraction-addition.json \
  --stage script \
  --no-llm
```

结构修复（Generator 输出后的安全网）：

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/patch_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json \
  --dry-run
```

校验：

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/validate_lesson_deck.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json
```

```bash
python3 agent_cases/lesson-deck-generation-skill/scripts/validate_lesson_deck_html.py \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.html
```

PPTX 导出：

```bash
node agent_cases/lesson-deck-generation-skill/scripts/export_lesson_deck_pptx.mjs \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json \
  agent_cases/lesson-deck-generation-skill/generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition-editable.pptx
```

## 联动与 handoff

- 可接收创新教案 Skill 的 `lessonPlanSummary`、`activityFlow`、`objectives` 和 `assessmentRubric` 作为增强输入，但仍需重新生成 `designPlan`。
- 可向课堂互动网页 Skill 传递 `handoff.activityStages`、`handoff.interactionIdeas` 和 `handoff.deckArtifactPaths`。
- handoff 只传结构化摘要和文件路径，不传完整 HTML、PPTX 或大 JSON。
- 本 Skill 不要求创新教案、出题或课堂互动网页作为前置。

## 质量标准

- 开始内容生成前必须有 `designPlan`。
- 每页必须有 `layoutId`、`visualSlots`、`feedbackEvidence`、`teacherScript`、`timing` 和 `notes`。
- HTML 每页 `<section>` 必须有 `data-layout="EDxx"`、`data-slot`、`data-slot-ratio` 和 `data-asset-status`。
- 学生屏幕不得出现教师逐字稿、预设学生回答和反馈方式。
- 练习、互动、错误辨析和出门测必须有可收集的课堂反馈证据。
- 40 分钟课通常 8-12 页；小学低段偏少，高中理科可到 12-14 页。
- 总时长与 `durationMin` 偏差不超过 10%。
- 未接入教材页码或课标边界时，在 `curriculumContext.assumptions` 标注。
- 输出 JSON 必须通过 `scripts/validate_lesson_deck.py`。
- 输出 HTML 必须通过 `scripts/validate_lesson_deck_html.py`。

## 边界

- 当前为可运行原型：结构、HTML 预览、逐字稿、校验和基础 PPTX 导出可用。
- 三阶段流程是默认路径：`design -> script -> render`。
- `render` 阶段仅支持通过 `--deck-json` 读取已确认完整数据，不允许单独使用 `--config` 重新生成。
- 真实教材库、课标库和图片素材库可替换接入；当前必须用 `curriculumContext.assumptions` 和 `visualSlots` 显式标注缺口。
- API key、base URL 和模型名由环境变量或脚本参数注入，不写入请求体和输出文件。

## 资源索引

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `references/input-output-schema.md` | 请求、deck、slide 和三阶段产物结构 | 每次 |
| `references/quality-checklist.md` | JSON/HTML/教学质量检查 | 输出前 |
| `references/clarification-flow.md` | 缺信息澄清和默认策略 | 入口阶段 |
| `references/data-gap-brief.md` | 需求边界和数据缺口 | design |
| `references/lesson-layout-lock.md` | ED01-ED12 版式锁 | design |
| `references/golden-samples.md` | 课时级样板 | design |
| `references/lesson-flow-templates.md` | 课型节奏模板 | design |
| `references/subject-knowledge-packs.json` | hook、概念、例题、练习和错因 | design/script |
| `references/slide-layouts.md` | 页面版式说明 | render |
| `references/ed-layout-skeletons.md` | HTML 骨架 | render |
| `references/projection-style-rules.md` | 投影友好视觉规则 | render |
| `references/image-generation-workflow.md` | 可选配图和回写规则 | 按需 |
| `assets/lesson-deck-template.html` | HTML 横向课件模板 | render |

## 组件地图

- `scripts/render_lesson_deck.py`：三阶段主入口，负责 design、script 和 render。
- `scripts/patch_lesson_deck.py`：结构退化修复脚本，作为 Generator 输出的安全网（第二层防护）。
- `scripts/validate_lesson_deck.py`：deck JSON 结构和教学约束校验。
- `scripts/validate_lesson_deck_html.py`：HTML 版式、槽位和教师信息泄漏校验。
- `scripts/export_lesson_deck_pptx.mjs`：PPTX-ready JSON 到可编辑 PPTX。
- `assets/lesson-deck-template.html`：单文件 HTML 课件模板。
