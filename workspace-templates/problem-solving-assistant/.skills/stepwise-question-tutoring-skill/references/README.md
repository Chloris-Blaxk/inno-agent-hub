# References

本目录存放 `stepwise-question-tutoring-skill` 的教学规则、输入输出约定、知识图谱、错因库、本地题库和质量检查标准。**本 Skill 采用纯智能体驱动模式**，由 Claude Code 直接根据工作流指令、学生输入和知识库执行诊断与推理，无需 Python 脚本调用外部 LLM。

## 文件清单

| 文件 | 作用 | 主要使用场景 |
| --- | --- | --- |
| `input-output-schema.md` | 定义请求和响应 JSON 的字段结构，包括 `unanswered_hint`、`diagnose_answer`、`request_similar`。 | 智能体理解用户请求结构、生成结构化输出。 |
| `scaffolding-strategies.json` | 苏格拉底式分级提示策略，定义 Level 1-4 的目标、模板、约束和披露信息。 | 学生未作答时生成逐级提示（根据学生反馈逐级展开）。 |
| `error-patterns.json` | 高频错误模式库，包含错误类别、典型表现、根因和补救建议。 | 已作答诊断中的错因标签匹配和根因解释。 |
| `step-alignment-rules.md` | 学生步骤和标准步骤的对齐规则，说明如何判断第一处错步。 | 已作答诊断、步骤对齐、定位第一处错误。 |
| `quality-checklist.md` | 输出质量检查标准，包括提示克制性、错误证据性、补救建议清晰度、年级适配和相似题质量。 | 智能体自检和人工复核质量标准。 |
| `knowledge-graph.json` | 本地知识图谱，描述知识点、前置知识、常见错误、能力标签和边界。 | 知识点定位、前置知识诊断、相似题筛选、提示生成。 |
| `difficulty-rules.json` | 难度规则，描述题目层级、难度判断和推荐策略。 | 相似题推荐、继续练/进入下一层建议、难度自适应。 |
| `similar-question-groups.json` | 相似题分组规则，用知识点、方法标签、题型和层级组织练习推荐。 | 相似题召回、分组和去重。 |
| `seed-question-bank.json` | 本地种子题库，包含题干、答案、步骤、知识点、难度、方法标签、常见错误等字段。 | 相似题推荐、练习闭环（复用出题智能体三重匹配逻辑）。 |
| `ocr-config.json` | OCR API 端点、认证方式、置信度阈值配置。 | 图片输入识别（调用外部 OCR 服务）。 |
| `tutoring-voice-guide.md` | 输出语气要求、交互原则、逐级引导规范。 | 智能体生成学生友好输出、避免术语堆叠和居高临下语气。 |
| `README.md` | 本文件。 | 说明 references 目录结构和执行协议。 |

## 运行时加载关系

```text
Claude Code Agent (智能体驱动)
  -> SKILL.md                          # 工作流指令、输入输出模式、边界规范
  -> input-output-schema.md            # 请求和响应结构参考
  -> scaffolding-strategies.json       # 未作答逐级提示策略（Level 1-4）
  -> error-patterns.json               # 错因匹配和根因解释
  -> step-alignment-rules.md           # 步骤对齐和第一错步定位规则
  -> knowledge-graph.json              # 知识点和前置关系
  -> difficulty-rules.json             # 难度和层级规则
  -> similar-question-groups.json      # 相似题分组
  -> seed-question-bank.json           # 本地题库
  -> ocr-config.json                   # OCR API 配置（仅图片输入时）
  -> tutoring-voice-guide.md           # 输出语气和交互原则
  -> quality-checklist.md              # 质量自检标准
```

**执行协议：**
- **纯智能体驱动（agent_driven_prototype）**：无 Python render 脚本，无外部 LLM API 调用
- **工具依赖**：`ocr_api`（图片识别）、`bash_tool`（调用 OCR）
- **智能体能力**：推理、结构化解析、知识匹配、逐级引导、相似题推荐

不是每个模式都会完整使用所有文件：

- **`unanswered_hint`（未作答提示）** 主要依赖：
  - `scaffolding-strategies.json` — Level 1-4 逐级提示策略
  - `knowledge-graph.json` — 知识点边界和前置关系
  - `seed-question-bank.json` — 相似题推荐
  - `tutoring-voice-guide.md` — 输出语气
  - `quality-checklist.md` — 提示克制性检查

- **`diagnose_answer`（已作答诊断）** 主要依赖：
  - `error-patterns.json` — 错因匹配和根因解释
  - `step-alignment-rules.md` — 步骤对齐和第一错步定位
  - `knowledge-graph.json` — 知识点诊断
  - `seed-question-bank.json` — 相似题推荐（答对提高难度、答错降低难度）
  - `difficulty-rules.json` — 难度自适应规则
  - `ocr-config.json` — 图片输入时调用 OCR
  - `tutoring-voice-guide.md` — 输出语气（先接住学生状态，再推进思路）
  - `quality-checklist.md` — 错误证据性、补救建议清晰度检查

- **`request_similar`（只请求相似题）** 主要依赖：
  - `knowledge-graph.json` — 知识点匹配
  - `difficulty-rules.json` — 难度层级规则
  - `similar-question-groups.json` — 相似题分组和去重
  - `seed-question-bank.json` — 本地题库召回

## 当前覆盖范围

当前本地知识图谱和题库主要覆盖**小学五年级分数加减法**相关内容，例如：

- 同分母分数加减法
- 异分母分数加减法
- 分数加减法应用
- 通分、约分、分数单位等前置知识

因此，在五年级分数题中，`knowledgePoints` 和 `similarQuestions` 通常可以正常命中。

**对于其他年级或知识点：**

- 如果 `knowledge-graph.json` 和 `seed-question-bank.json` 没有对应知识点和题目，智能体输出中可能出现：
  ```json
  {
    "knowledgePoints": [],
    "similarQuestions": []
  }
  ```
- 这**不是智能体运行失败**，而是本地参考数据暂未覆盖该知识点。
- 智能体仍可以借助推理能力完成未作答提示和已作答诊断，但相似题推荐和知识点定位会受限于本地数据覆盖范围。

## 关键数据字段

### `knowledge-graph.json`

常见字段：

- `knowledgePointId`：知识点 ID。
- `name`：知识点名称。
- `subject` / `grade` / `unitId`：学科、年级和单元。
- `prerequisites`：前置知识。
- `commonErrors`：关联的高频错误 ID。
- `forbiddenScope`：不应越界讲解的内容。
- `competencyTags`：能力标签。
- `boundaryNotes`：边界说明。

### `seed-question-bank.json`

常见字段：

- `sourceId`：题目 ID。
- `subject` / `grade` / `unit`：题目所属范围。
- `knowledgePointIds`：关联知识点。
- `layer`：练习层级，如 A/B/C。
- `difficulty`：难度等级。
- `questionType`：题型。
- `stem`：题干。
- `answer`：答案。
- `solutionSteps`：标准步骤。
- `commonErrors`：该题常见错误。
- `teachingNote`：教学提示。
- `estimatedTimeSec`：预计用时。

### `error-patterns.json`

常见字段：

- `errorId`：错误模式 ID（如 `fraction-denominator-add`）。
- `category`：错误类别（概念理解、过程错误、粗心大意等）。
- `typicalBehavior`：典型错误表现（用于关键词匹配）。
- `rootCause`：根因解释（学生友好语言）。
- `remedySuggestion`：补救建议（具体可操作）。
- `severity`：严重程度（critical / moderate / minor）。
- `relatedKnowledgePoints`：关联知识点。

### `ocr-config.json`

常见字段：

- `endpoint`：OCR API 端点 URL。
- `authType`：认证方式（如 `bearer`、`apiKey`）。
- `confidenceThreshold`：置信度阈值（< 0.7 时标记为低置信度）。
- `retryPolicy`：重试策略配置。
- `fallbackStrategy`：降级策略（OCR 失败时的处理方式）。

### `scaffolding-strategies.json`

常见字段：

- `level`：提示级别（1-4）。
- `goal`：该级别目标（如"激活记忆"、"给出关键洞察"）。
- `constraints`：约束条件（如"不直接给答案"、"不越界讲解"）。
- `disclosureLevel`：披露信息程度。
- `template`：提示模板（可选，智能体可自由发挥）。

### `difficulty-rules.json`

常见字段：

- `layer`：练习层级（A/B/C 或基础/进阶/挑战）。
- `difficulty`：难度等级（1-5）。
- `recommendationRules`：推荐策略（答对提升、答错降低、未作答同难度）。
- `progressionCriteria`：层级进阶标准。

### `similar-question-groups.json`

常见字段：

- `groupId`：相似题分组 ID。
- `knowledgePointIds`：关联知识点。
- `methodTags`：解题方法标签（如"通分法"、"最小公倍数法"）。
- `questionType`：题型（计算题、应用题、判断题等）。
- `layer`：练习层级。
- `questionIds`：该组包含的题目 ID 列表。

### `tutoring-voice-guide.md`

主要内容：

- 先接住学生当前状态，再推进思路。
- 不急着完整讲完，优先帮助学生迈出下一小步。
- 不使用居高临下、责备或嘲讽语气。
- 不把 JSON 字段、内部标签或质量报告直接暴露给学生。
- Level 1-3 不直接给最终答案；Level 4 才给完整解析。
- 每轮结尾最多留一个关键问题或下一步动作。

### `quality-checklist.md`

主要检查项：

- **提示克制性**：Level 1-3 不直接泄露最终答案。
- **错误证据性**：诊断必须基于学生原始步骤，不替学生补写推导。
- **补救建议清晰度**：具体可操作，避免空泛建议。
- **年级适配**：语言和术语适配学生年级，避免超纲。
- **相似题质量**：知识点+方法+难度三重匹配，避免重复推荐当前题。

## 智能体执行协议

### 工作流概要

1. **输入识别**：文本直接解析，图片调用 OCR API（bash + curl）。
2. **模式路由**：根据 `mode` 字段选择执行分支。
3. **推理执行**：
   - **未作答提示**：读取 `scaffolding-strategies.json`，根据学生反馈逐级生成 Level 1-4 提示。
   - **已作答诊断**：解析学生步骤 → 生成标准解法 → 对比定位第一错步 → 匹配 `error-patterns.json` → 给出根因和补救建议。
   - **相似题推荐**：知识点+方法+难度三重匹配 `seed-question-bank.json`，去重后推荐 2-3 道题。
4. **质量自检**：参考 `quality-checklist.md` 检查输出克制性、证据性、清晰度。
5. **Markdown 输出**：生成学生友好报告，遵循 `tutoring-voice-guide.md` 语气规范。

### 关键设计原则

- **引导而非直接给答案**：Level 1-3 激活记忆、给关键洞察、引导第一步，Level 4 才给完整解析。
- **保持学生原始表述**：不修正学生错误，不替学生补写推导，诊断基于实际步骤。
- **闭环练习推荐**：无论做对、做错还是未作答，都主动推荐 2-3 道相似题。
- **逐级展开**：苏格拉底式提示根据学生反馈逐级给出，不一次性全部展示。
- **学生友好语气**：先接住状态再推进，避免术语堆叠和居高临下。
