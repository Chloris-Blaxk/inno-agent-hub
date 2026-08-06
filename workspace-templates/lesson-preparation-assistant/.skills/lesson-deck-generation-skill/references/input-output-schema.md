# 输入输出 Schema

## Request

统一信封格式，兼容扁平 JSON（向后兼容）。

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

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `requestId` | string | 推荐 | 请求唯一 ID，用于追踪多阶段流水线 |
| `sourceRequest` | string | 推荐 | 用户原始请求文本，用于回溯和调试 |
| `taskIntent` | string | 推荐 | 任务阶段：`design` / `script` / `render` |
| `input` | object | 必填 | 核心领域输入（见下方"核心输入"） |
| `options` | object | 可选 | 风格、模型、导出格式等可选参数 |
| `constraints` | array | 可选 | 用户限制和硬约束 |
| `assumptions` | array | 可选 | 默认值和保守假设 |

### 核心输入（input 子对象）

| 字段 | 类型 | 必填 | 说明 | 缺失处理 |
|---|---|---|---|---|
| `subject` | string | 是 | 学科 | Controller 追问 |
| `grade` | string | 是 | 年级或学段 | Controller 追问 |
| `topic` | string | 是 | 课题 | Controller 追问 |
| `lessonType` | string | 否 | 课型 | 默认 `new_concept` |
| `durationMin` | number | 否 | 时长（分钟） | 默认 40 |
| `textbookVersion` | string | 否 | 教材版本 | 写入 assumptions |
| `unit` | string | 否 | 单元 | 写入 assumptions |
| `period` | string | 否 | 课时序号 | 写入 assumptions |
| `studentProfile` | object | 否 | 学情 | 使用通用模板 |
| `requirements` | string | 否 | 个性化要求 | 按默认课型生成 |

### 可选参数（options 子对象）

| 字段 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `stylePreset` | string | 视觉风格 | `auto` |
| `outputFormat` | string | 产物类型 | 全量输出 |
| `model` | string | 生成模型 | 环境变量 |

---

## Response

统一响应信封。Controller 面向下游或用户汇总时使用。

```json
{
  "skillId": "lesson-deck-generation-skill",
  "taskIntent": "script",
  "status": "pass",
  "inputSummary": {
    "subject": "数学",
    "grade": "五年级",
    "topic": "异分母分数加减法",
    "durationMin": 40,
    "assumptions": ["学生已学通分", "使用人教版教材"]
  },
  "result": {
    "deckMeta": {
      "title": "异分母分数加减法",
      "slideCount": 10,
      "durationMin": 40,
      "stylePreset": "chalk-grid"
    },
    "designPlanSummary": [
      {"page": 1, "stage": "cover", "layoutId": "ED01"},
      {"page": 2, "stage": "objective_map", "layoutId": "ED02"}
    ]
  },
  "artifacts": [
    {
      "type": "json",
      "path": "generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json",
      "description": "完整 deck 结构化数据"
    },
    {
      "type": "markdown",
      "path": "generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.md",
      "description": "教师逐字稿"
    },
    {
      "type": "html",
      "path": "generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.html",
      "description": "单文件横向课件预览"
    }
  ],
  "handoff": {
    "skillId": "lesson-deck-generation-skill",
    "taskIntent": "script",
    "activityStages": ["cover", "objective_map", "lead_in", "explore", "concept_build", "example", "guided_practice", "misconception_clinic", "summary", "exit_ticket"],
    "interactionIdeas": ["同桌讨论", "错误辨析", "出门测"],
    "deckArtifactPaths": [
      "generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition.json"
    ],
    "lessonPlanSummary": {
      "title": "异分母分数加减法",
      "durationMin": 40,
      "slideCount": 10
    }
  },
  "qualityReport": {
    "status": "pass",
    "checks": [
      {"id": "schema_valid", "status": "pass"},
      {"id": "layout_lock", "status": "pass"},
      {"id": "feedback_evidence", "status": "pass"}
    ],
    "warnings": [],
    "assumptions": ["学生已学通分", "使用人教版教材"]
  },
  "warnings": [],
  "nextActions": [
    {"action": "review", "description": "教师审阅逐字稿和时间分配"},
    {"action": "render", "description": "确认后执行 --stage render 生成 HTML"}
  ]
}
```

### 响应字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `skillId` | string | 当前 Skill ID |
| `taskIntent` | string | 实际执行的任务阶段 |
| `status` | string | `pass` / `warn` / `failed` |
| `inputSummary` | object | 输入摘要和假设 |
| `result` | object | 核心结果摘要（不含完整 slides） |
| `artifacts` | array | 产物文件列表 |
| `handoff` | object | 给下游 Skill 的结构化摘要 |
| `qualityReport` | object | 校验结果 |
| `warnings` | array | 风险、缺失、降级说明 |
| `nextActions` | array | 用户或系统下一步建议 |

---

## Deck 对象

完整 deck JSON 结构（`result` 中只放摘要，完整数据存为产物文件）。

```json
{
  "deckMeta": {
    "title": "异分母分数加减法",
    "visualSystem": "edu-deck-v1",
    "layoutLockVersion": "edu-layout-lock-v1",
    "subject": "数学",
    "grade": "五年级",
    "lessonType": "new_concept",
    "durationMin": 40,
    "slideCount": 10,
    "stylePreset": "chalk-grid",
    "subjectMark": "MATH"
  },
  "curriculumContext": {
    "textbookVersion": "人教版",
    "unit": "分数的加法和减法",
    "period": "第 1 课时",
    "assumptions": ["未接入真实课标库，知识边界需教师确认。"]
  },
  "designPlan": [
    {
      "page": 1,
      "slideId": "s01",
      "stage": "cover",
      "layoutId": "ED01",
      "reason": "建立学习主题和课堂期待。",
      "visualSlots": ["cover_mark"],
      "feedbackEvidence": "教师观察学生是否进入学习状态。"
    }
  ],
  "lessonOutline": [
    {
      "stage": "cover",
      "title": "异分母分数加减法",
      "layoutId": "ED01",
      "minutes": 1,
      "goal": "建立学习主题和课堂期待。"
    }
  ],
  "slides": [],
  "teacherScript": [],
  "exportPlan": {
    "htmlPreview": true,
    "pptxReady": true,
    "pageSize": "16:9",
    "editableObjects": ["text", "shape", "visual-slot", "speaker-notes"],
    "visualSlotRules": "references/lesson-layout-lock.md"
  },
  "qualityReport": {
    "status": "draft",
    "warnings": [],
    "assumptions": ["未接入真实课标库，知识边界需教师确认。"],
    "checkedRules": ["edu_layout_lock", "visual_slots", "feedback_evidence", "timing", "teacher_script", "projection_density", "html_runtime"]
  }
}
```

## Slide 对象

```json
{
  "id": "s05",
  "page": 5,
  "stage": "concept_build",
  "layoutId": "ED05",
  "title": "先统一分数单位",
  "teachingIntent": "把观察提升为可迁移方法。",
  "screen": {
    "eyebrow": "CONCEPT",
    "headline": "先统一单位",
    "keyIdea": "分母不同，分数单位不同。",
    "bullets": ["看单位", "先通分", "再计算"],
    "visualBrief": "两条等长纸带从 1/2 和 1/3 转成 3/6 和 2/6。"
  },
  "teacherScript": {
    "say": "我们先不急着算答案，先看每一份大小是不是一样。",
    "ask": ["1/2 的一份和 1/3 的一份一样大吗？"],
    "expectedResponses": ["不一样", "要先变成一样大的单位"],
    "transition": "所以第一步不是相加，而是统一单位。"
  },
  "visualSlots": [
    {
      "id": "concept_diagram",
      "type": "editable_diagram",
      "ratio": "16:10",
      "assetStatus": "placeholder",
      "prompt": "16:10 editable classroom diagram, two equal bars comparing 1/2 and 1/3 as sixths, no text baked into image",
      "description": "用纸带图表现通分。"
    }
  ],
  "feedbackEvidence": "学生能说出：分母不同代表单位不同。",
  "timing": {"minutes": 5},
  "notes": ["板书：统一单位 = 通分。"]
}
```

## Design Plan 对象

```json
{
  "page": 5,
  "slideId": "s05",
  "stage": "concept_build",
  "layoutId": "ED05",
  "reason": "用概念画布把学生观察提升为方法。",
  "visualSlots": ["concept_diagram"],
  "feedbackEvidence": "学生能说出关键概念。"
}
```

## 三阶段中间产物

本 Skill 支持分阶段输出，各阶段产物如下：

### 阶段一：教学设计稿（`--stage design`）

输出文件：
- `{prefix}.design.md`：面向教师的可读文档，包含课程背景、课堂大纲、页面设计规划、质量自检。
- `{prefix}.design.json`：轻量结构化数据，仅含 `deckMeta`、`curriculumContext`、`designPlan`、`lessonOutline`、`qualityReport`。

用途：供教师确认教学节奏和页面规划，不含逐字稿与学生屏幕细节。

### 阶段二：逐字稿（`--stage script`）

输入文件：`--config`（原始请求，必填）；可选附加 `--design-json`（阶段一已确认的教学设计）。

当提供 `--design-json` 时，生成器会读取其中已确认的 `designPlan`，在 LLM 返回后对 slides 做**强制后对齐**：
- 页数被修剪/填充至与 `designPlan` 一致；
- 每页的 `stage` 和 `layoutId` 被强制覆盖为 `designPlan` 中的值；
- 确保逐字稿不偏离教师已审定的教学节奏和版式分配。

输出文件：
- `{prefix}.md`：教师逐字稿，逐页包含 `teacherScript.say/ask/expectedResponses/transition`、`feedbackEvidence`、`notes`。
- `{prefix}.json`：完整的 `edu-deck-v1` 结构化数据，含全部 `slides`，供阶段三读取。

用途：供教师确认话术风格、追问深度和时间分配。

### 阶段三：课件渲染（`--stage render`）

输入文件：**必须**提供 `--deck-json` 指向的完整 JSON。**不允许**单独使用 `--config` 重新生成，避免教师在不知情的情况下重新生成内容。

输出文件：
- `{prefix}.html`：单文件横向课件，基于 `assets/lesson-deck-template.html` 模板渲染。
- `{prefix}.pptx`：可编辑 PPTX（需额外调用 `scripts/export_lesson_deck_pptx.mjs`）。

## PPTX-ready 约束

- 不把整页内容做成图片。
- 学生屏幕文本、图示、练习题、备注必须可编辑。
- `visualSlots` 是素材生成和 PPTX 占位的唯一来源。
- 教师逐字稿进入 speaker notes，不进入学生屏幕。

## HTML-ready 约束

- 每页 `<section class="slide">` 必须声明 `data-layout="EDxx"`。
- 每页 `<section>` 必须同步声明 `data-slot`、`data-slot-ratio` 和 `data-asset-status`，来源于首个 `visualSlots`。
- 可见页面不得显示 `teacherScript`、预设回应或反馈证据；这些只进入 `deck-json`、教师备注面板和 speaker notes。
- HTML 输出后必须通过 `scripts/validate_lesson_deck_html.py`。

---

## Handoff

传给下游 Skill（如课堂互动网页生成）的最小结构化摘要。必须满足：

- 只传摘要和文件路径，**不传完整 HTML、PPTX 或大 JSON**。
- 下游 Skill 使用前必须按自己的输入契约重新校验。

```json
{
  "skillId": "lesson-deck-generation-skill",
  "taskIntent": "script",
  "activityStages": ["cover", "objective_map", "lead_in", "explore", "concept_build", "example", "guided_practice", "misconception_clinic", "summary", "exit_ticket"],
  "interactionIdeas": ["同桌讨论", "错误辨析", "出门测"],
  "deckArtifactPaths": [
    "generated-outputs/<case-name>/<case-name>.json"
  ],
  "lessonPlanSummary": {
    "title": "课题名",
    "durationMin": 40,
    "slideCount": 10,
    "subject": "数学",
    "grade": "五年级"
  }
}
```

### Handoff 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `skillId` | string | 来源 Skill ID |
| `taskIntent` | string | 来源任务阶段 |
| `activityStages` | array | 课堂活动阶段列表 |
| `interactionIdeas` | array | 互动方式建议 |
| `deckArtifactPaths` | array | deck JSON 产物路径 |
| `lessonPlanSummary` | object | 课程基本信息摘要 |

---

## Artifacts

输出文件类型、命名规则和用途。

### 文件组织

```
generated-outputs/
└── <case-name>/
    ├── <case-name>.design.md        # 教学设计稿（阶段一）
    ├── <case-name>.design.json      # 设计稿结构化数据（阶段一）
    ├── <case-name>.md               # 教师逐字稿（阶段二）
    ├── <case-name>.json             # 完整 deck 数据（阶段二）
    ├── <case-name>.html             # 单文件横向课件（阶段三）
    └── <case-name>-editable.pptx    # 可编辑 PPTX（导出）
```

### 命名规则

| 产物 | 命名模板 | 说明 |
|---|---|---|
| 设计稿 Markdown | `{prefix}.design.md` | 教师可读的设计规划 |
| 设计稿 JSON | `{prefix}.design.json` | 轻量结构化设计数据 |
| 逐字稿 Markdown | `{prefix}.md` | 教师逐页话术 |
| 完整 Deck JSON | `{prefix}.json` | `edu-deck-v1` 完整数据 |
| HTML 预览 | `{prefix}.html` | 单文件横向课件 |
| PPTX | `{prefix}-editable.pptx` | 可编辑 PowerPoint |

其中 `{prefix}` = `generated-outputs/<case-name>/<case-name>`。

---

## Failure And Degradation

缺输入、缺数据、模型失败、校验失败时的处理方式。

### 缺输入

| 场景 | 处理 |
|---|---|
| `subject` / `grade` / `topic` 缺失 | Controller 追问一个最小澄清问题 |
| 其他字段缺失 | 使用保守默认值，写入 `assumptions` |
| `design-json` 路径无效 | 降级为不使用已确认设计，生成新设计稿 |
| `deck-json` 路径无效 | 报错并终止 `render` 阶段 |

### 缺数据

| 场景 | 处理 |
|---|---|
| 未命中 `subject-knowledge-packs.json` | 使用 generic 模板，标注假设 |
| 真实教材/课标库未接入 | 在 `curriculumContext.assumptions` 显式标注 |
| 图片素材缺失 | 保留 `visualSlots` 占位，设置 `assetStatus: placeholder` |

### 模型失败

| 场景 | 处理 |
|---|---|
| LLM 调用超时 | 重试一次，仍失败则降级为模板生成（`--no-llm`） |
| LLM 返回非 JSON | 尝试提取 JSON 块，失败则报错 |
| LLM 返回结构退化 | 调 `patch_lesson_deck.py` 修复，记录到 `qualityReport.checks` |

### 校验失败

| 场景 | 处理 |
|---|---|
| JSON Schema 校验失败 | 调 `patch_lesson_deck.py` 修复后重试 |
| Patch 后仍失败 | 降级输出，状态设为 `failed`，`warnings` 说明问题 |
| HTML 校验失败 | 不交付 HTML，提示重新执行 `render` 阶段 |
| 总时长偏差 > 10% | 状态设为 `warn`，`warnings` 说明偏差 |

### 降级原则

- 不编造教材页码、课标边界、图片素材。
- 不跳过三阶段确认直接一次性全出。
- 高风险结果需要人工确认时，标注 `needs_user_confirmation`。
- 降级输出必须说明哪些部分可靠、哪些需要补充材料。
