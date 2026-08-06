---
name: exercise-generation-skill
description: 按课标、教材进度、知识点、题型和难度层级生成课堂练习、分层作业、单元测验、阶段测验和专题练习。适用于教师需要结构化题目、答案解析、错因标签、覆盖检查、难度报告、换题建议和超纲风险提示的任务；不用于拍题答疑、知识点讲解、课件生成或真实测量学等值组卷。
entryName: 出题
entryToken: "@出题"
displayName: 出题
status: runnable_prototype
---

# 出题 Skill

## 场景定位

面向教师备课中的出题与组卷需求，解决题目与课标、教材进度、知识点覆盖、题型比例、难度分层不精确对齐的问题。

核心闭环：

`教师出题需求 -> 任务蓝图 -> 课标/教材/知识点边界 -> 种子题选择与变式 -> 答案解析与错因 -> 覆盖/难度/风险报告 -> 本地校验`

本 Skill 不负责拍题答疑、知识点讲解、课件生成、课堂互动网页，也不承诺真实测量学区分度或等值试卷。

## 入口与路由契约

- 显式入口：`@出题`。
- Skill ID：`exercise-generation-skill`。
- 当前状态：`runnable_prototype`。
- 当用户显式使用 `@出题` 时，优先进入本 Skill。
- 无显式入口时，由外层 Controller 或 `agent_cases/agent_cli.py` 返回菜单或按用户选择序号路由，不依赖关键词猜测。
- `agent_cases/skill-entrypoints.json` 中的必填槽位为 `subject`、`grade`、`knowledgePointIds`。

## 能力边界

### 可以做

- 生成课堂练习、分层作业、单元测验、阶段测验和专题练习。
- 根据 `taskType` 选择题量、分层、题型和难度蓝图。
- 基于课标、知识点图谱、教材映射和结构化种子题生成练习。
- 输出题目、答案、分步解析、错因标签、评分点和讲评建议。
- 输出覆盖报告、难度报告、风险报告和换题建议。
- 使用本地脚本校验题量、分层、比例、重复、超纲和结构完整性。

### 不可以做

- 不承诺真实测量学难度、区分度、信度或等值 AB 卷。
- 不自动接入外部题库检索；当前基于本目录结构化种子题与规则变式。
- 不为主观题只给笼统答案；必须给评分点或评分依据。
- 不把超出输入学段、教材进度或知识点边界的内容伪装成可用题。
- 不替拍题答疑 Skill 做学生错步诊断；只提供题目层面的常见错因和讲评建议。

## 任务模式

本 Skill 用 `taskType` 区分出题任务：

| taskType | 场景 | 核心输入 | 核心输出 | 是否可独立运行 |
|---|---|---|---|---|
| `classroom_practice` | 课堂即时练习 | 知识点、题量、题型 | 少量题目、答案解析、易错提醒 | 是 |
| `layered_homework` | A/B/C 分层作业 | 知识点、层级、题量 | 分层题目、分层目标、讲评建议 | 是 |
| `unit_test` | 单元测验 | 单元、知识点集合、题型比例 | 测验题、覆盖报告、难度报告 | 是 |
| `stage_test` | 阶段测验 | 阶段范围、题量、难度范围 | 阶段题组、讲评建议、风险提示 | 是 |
| `topic_drill` | 专题练习或换题 | 单知识点/题型、方法标签 | 专项题组、变式和替换建议 | 是 |

## 输入契约

脚本当前消费扁平 JSON 配置。最小请求结构：

```json
{
  "subject": "数学",
  "grade": "五年级",
  "textbookVersion": "人教版",
  "unit": "分数的加法和减法",
  "period": "第2课时",
  "topic": "异分母分数加减法",
  "knowledgePointIds": ["math-g5-fraction-add"],
  "taskType": "layered_homework",
  "questionCount": 9,
  "layers": ["A", "B", "C"],
  "questionTypes": ["计算题", "应用题"],
  "requirements": "每层 3 题，附答案、分步解析、错因和换题建议。"
}
```

### 必需输入

| 字段 | 类型 | 说明 | 缺失处理 |
|---|---|---|---|
| `subject` | string | 学科 | Controller 追问 |
| `grade` | string | 年级或学段 | Controller 追问 |
| `knowledgePointIds` | string[] | 目标知识点 ID | 若只给 `topic`，尝试由教材/知识图谱映射；仍缺失则追问 |

### 推荐输入

| 字段 | 用途 | 缺失影响 |
|---|---|---|
| `taskType` | 选择蓝图 | 默认按课堂练习或分层作业保守处理 |
| `questionCount` | 控制题量 | 使用蓝图默认题量 |
| `textbookVersion`、`unit`、`period` | 限定教材进度 | 只能按知识点边界判断 |
| `layers` | 分层作业层级 | 分层任务默认 A/B/C |
| `questionTypes` / `questionTypeMix` | 控制题型 | 使用蓝图推荐比例 |
| `difficultyRange` / `difficultyMix` | 控制难度 | 使用蓝图推荐难度 |
| `strictBlueprint` | 是否严格执行比例 | 缺省为非严格，偏差进入 warning |
| `requirements` | 个性化要求 | 只按默认规则生成 |

## 信息缺失与降级

- 缺少 `subject`、`grade` 或可定位的知识点时，Controller 先追问，不直接生成。
- 如果用户只给课题，脚本或 Controller 可通过 `references/textbook-map.json` 与 `references/knowledge-graph.json` 尝试映射知识点。
- 当前题库未覆盖的知识点，不编造题目来源；输出缺口或建议扩充种子题库。
- 题型、难度或分层比例无法完全满足时，写入 `qualityReport` 和比例报告；`strictBlueprint=true` 时应失败。
- 超纲风险写入 `riskReport`，不得静默删除或伪装为合规。

## 执行协议

1. Controller 识别 `@出题`，抽取学科、年级、教材、单元、课题、知识点、题量、题型、难度和要求。
2. `scripts/render_exercise_set.py` 读取请求，按 `taskType` 加载蓝图。
3. 脚本读取课标、知识图谱、教材映射和种子题库，确定可出题范围。
4. 脚本选择或变式种子题，补齐答案、分步解析、常见错因和评分点。
5. 脚本生成覆盖、难度、风险、讲评和换题建议。
6. 输出 JSON 和 Markdown 后，运行 `scripts/patch_exercise_set.py` 修复结构缺陷并重建 Markdown。
7. 运行 `scripts/validate_exercise_set.py`；基础数据可用 `scripts/validate_reference_data.py` 预检。
8. Controller 向用户摘要题组用途、题量、覆盖情况、风险提示和输出路径，不重复粘贴完整 JSON。

## 资源加载顺序

1. 读本 `SKILL.md`，确认任务模式、边界和输出约束。
2. 读 `references/input-output-schema.md`。
3. 读 `references/blueprint-rules.md`，按 `taskType` 选择题量、层级和难度蓝图。
4. 读 `references/curriculum-standards.json`、`knowledge-graph.json`、`textbook-map.json`，确定课标、知识点和教材边界。
5. 读 `references/seed-question-bank.json` 及匹配当前学科/年级的其他 `seed-question-bank-*.json` 文件，选择或变式种子题。
6. 读 `references/difficulty-rules.json` 和 `misconception-tags.json`，补充分层、错因和讲评建议。
7. 读 `references/similar-question-groups.json`，生成换题建议。
8. 输出前运行 validate，并对照 `references/quality-checklist.md`。

## 输出契约

脚本输出：

- `<output>.json`：结构化练习/作业数据。
- `<output>.md`：教师可读题目、答案解析与讲评建议。

结构化结果必须包含：

```json
{
  "exerciseMeta": {},
  "blueprint": {},
  "questions": [],
  "answerKey": [],
  "coverageReport": {},
  "difficultyReport": {},
  "riskReport": {},
  "teachingSuggestions": [],
  "replacementSuggestions": [],
  "qualityReport": {}
}
```

每道题必须包含：

```json
{
  "id": "q001",
  "sourceId": "seed-frac-a-001",
  "layer": "A",
  "questionType": "计算题",
  "difficulty": 1,
  "knowledgePointIds": ["math-g5-fraction-add"],
  "stem": "计算：1/2 + 1/3 = ?",
  "answer": "5/6",
  "solutionSteps": [],
  "commonErrors": [],
  "scorePoints": []
}
```

Controller 面向下游或用户汇总时，建议使用统一信封：

```json
{
  "skillId": "exercise-generation-skill",
  "taskIntent": "layered_homework",
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

生成分层作业样例：

种子库选题模式（默认，毫秒级）：

```bash
python3 agent_cases/exercise-generation-skill/scripts/render_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/math-g5-fraction-layered-homework \
  --config agent_cases/exercise-generation-skill/examples/math-g5-fraction-layered-homework.json
```

动态生成模式（调用 InnoSpark-235B，每层约 15-30 秒）：

```bash
python3 agent_cases/exercise-generation-skill/scripts/render_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/demo-01 \
  --config agent_cases/exercise-generation-skill/examples/demo-01-classroom-quick-check.json \
  --model InnoSpark-235B
```

只校验已有 JSON：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/math-g5-fraction-layered-homework.json
```

严格校验：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/math-g5-fraction-layered-homework.json \
  --strict
```

校验基础数据：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_reference_data.py
```

后处理补丁（修复结构缺陷 + 重建 Markdown）：

```bash
python3 agent_cases/exercise-generation-skill/scripts/patch_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/<case-name>/<case-name>.json
```

扩充种子题库（调用 InnoSpark-235B）：

```bash
python3 agent_cases/exercise-generation-skill/scripts/generate_seed_data.py \
  --subject 数学 --grade 七年级 --topic "一元一次方程" \
  --count 30 --batch-size 10 \
  --knowledge-points agent_cases/exercise-generation-skill/references/knowledge-points-math-g7-linear-equation.json \
  --output agent_cases/exercise-generation-skill/references/seed-question-bank-math-g7-linear-equation.json
```

## 联动与 handoff

- 可向课件生成 Skill 传递 `handoff.exerciseSummary`、`handoff.questions`、`handoff.commonErrors`、`handoff.coverageReport` 和输出路径。
- 可向拍题答疑或知识点讲解 Skill 传递题目、答案、解析步骤、错因标签和知识点 ID。
- handoff 只传结构化摘要、题目对象和文件路径，不传完整题库。
- 下游使用前必须重新按自己的输入契约校验。

## 质量标准

- 题目不超出输入年级、教材进度和知识点边界。
- 每道题包含题干、答案、分步解析、知识点、题型、难度和错因/评分信息。
- 分层作业必须区分 A/B/C 层，且每层题量符合蓝图。
- 试卷型输出必须包含覆盖检查、难度报告和讲评建议。
- 专题练习和试卷草稿应尽量给出可替换题建议。
- 题干不重复；重复风险进入 `riskReport`。
- `strictBlueprint=true` 时，题型或难度比例偏差必须失败。
- 输出 JSON 必须通过 `scripts/validate_exercise_set.py`。

## 边界

- 当前为可运行原型，使用标签和规则近似难度与层级，不承诺真实测量学区分度。
- 暂不承诺等值 AB 卷、完整专题热力图和大规模真实作答统计。
- 种子题库当前覆盖五年级数学分数单元（90题）和七年级数学一元一次方程（30题）。未覆盖的知识点不编造题目来源，输出缺口或建议通过 `scripts/generate_seed_data.py` 扩充。
- 当前换题建议基于相似题组，不自动重算复杂变式答案。
- 扩展到真实业务前，应替换或增补为授权课标、教材、题库和错因数据。

## 双模型架构：Controller × Generator

本 Skill 遵循 AgentDesign 统一的 [Controller+Generator 流水线架构](../../agent_design/docs/教育智能体SKILL统一模板.md#十二双模型-controllergenerator-流水线架构)。

| 角色 | 模型 | 职责 |
| :--- | :--- | :--- |
| **Controller** | deepseek-v4-pro（主控模型） | 意图识别、槽位抽取、配置组装、脚本调度、后处理修复、质量校验、结果呈现 |
| **Generator** | InnoSpark-235B（生成模型） | 种子题库扩充——生成特定学科/年级/知识点的结构化题目 |

本 Skill 的 Generator 采用**离线数据制备模式**：InnoSpark-235B 不参与每次出题的实时生成，而是通过 `scripts/generate_seed_data.py` 批量生成种子题库，供 render 脚本的规则引擎选用。这种模式下：

- **实时出题**：render 脚本进行确定性选题 + 变式，毫秒级响应，结果可复现
- **离线扩充**：当种子题库覆盖不足时，Controller 触发 Generator 批量生成新种子数据
- **质量闭环**：种子数据生成后经 render → patch → validate 校验，确保进入题库的数据结构合规

### 种子数据生成

```bash
python3 scripts/generate_seed_data.py \
  --subject 数学 --grade 七年级 --topic "一元一次方程" \
  --count 30 --batch-size 10 \
  --knowledge-points references/knowledge-points-math-g7-linear-equation.json \
  --output references/seed-question-bank-math-g7-linear-equation.json
```

### 全流水线执行

```
Config → Render (规则引擎 + 种子库) → Patch → Validate → Present
   │          │                           │        │          │
 examples/  generated-outputs/         修复结构   校验通过    Controller
 <name>.json  <name>/<name>.json       重建.md    /失败      摘要呈现
              <name>/<name>.md
```

## 资源索引

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `references/input-output-schema.md` | 请求与输出结构 | 每次 |
| `references/quality-checklist.md` | 质量自检 | 输出前 |
| `references/blueprint-rules.md` | taskType 蓝图 | 生成前 |
| `references/curriculum-standards.json` | 课标边界 | 生成前 |
| `references/knowledge-graph.json` | 知识点、前置关系、边界 | 生成前 |
| `references/textbook-map.json` | 教材单元和课时映射 | 生成前 |
| `references/seed-question-bank.json` | 种子题库（五年级数学） | 生成时 |
| `references/seed-question-bank-math-g7-linear-equation.json` | 种子题库（七年级数学·一元一次方程） | 生成时 |
| `references/knowledge-points-math-g7-linear-equation.json` | 知识点定义（七年级数学） | 种子数据生成时 |
| `references/difficulty-rules.json` | 难度与分层规则 | 生成时 |
| `references/misconception-tags.json` | 错因标签 | 生成时 |
| `references/similar-question-groups.json` | 换题建议 | 生成时 |

## 组件地图

- `scripts/render_exercise_set.py`：主生成入口，负责组卷、Markdown 导出和默认校验。
- `scripts/patch_exercise_set.py`：后处理补丁——修复结构缺陷（必填字段补齐、去重）、重建 Markdown、记录补丁日志到 qualityReport。
- `scripts/validate_exercise_set.py`：结构、题量、分层、答案解析、覆盖和严格蓝图校验。
- `scripts/validate_reference_data.py`：基础 references 数据质量校验。
- `scripts/generate_seed_data.py`：种子题库扩充——调用 InnoSpark-235B 批量生成指定学科/年级/知识点的结构化题目，输出符合 schema 的 JSON。
