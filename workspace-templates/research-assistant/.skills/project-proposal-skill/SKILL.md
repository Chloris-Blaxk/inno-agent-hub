---
name: project-proposal-skill
description: 根据项目材料抽取项目事实表，并生成项目申报书、结题报告、成果汇报或三文档集合的结构化正文、亮点提炼、预算规则提示和跨文档事实一致性检查。
entryName: 项目申报助手
entryToken: "@项目申报助手"
displayName: 项目申报助手
status: runnable_prototype
execution_protocol:
  model_required: true
  model_role: education_content_generator
  model_id: innospark-235b
  model_name: InnoSpark-235B
  model_base_url_env: INNOSPARK_AIECNU_BASE_URL
  model_api_key_env:
    - INNOSPARK_AIECNU_API_KEY
    - INNOSPARK_API_KEY
---

# 项目申报助手 Skill

## 场景定位

面向教师项目申报、结题和成果汇报，解决材料分散、亮点难提炼、格式不熟和事实容易前后矛盾的问题。

本 Skill 的核心闭环是：项目材料 -> `ProjectFactTable` -> 目标文档草稿/文档集合 -> 预算与一致性校验 -> 人工确认清单。

本 Skill 不负责预测立项结果，也不负责凭空补写未提供的成果、数据、团队经历或经费金额。

## 何时使用

- 用户要求生成项目申报书、课题申报书、结题报告或成果汇报。
- 用户已有分散材料，需要先整理项目事实表、时间线、成果清单或团队基础。
- 用户需要检查三份文档之间的目标、周期、成果、预算等事实是否一致。
- 用户需要预算科目、用途和金额一致性提示。

不要用于研究选题发现、文献筛选、论文润色或引用支撑性校验；这些任务分别交给 `@研究选题生成`、`@文献阅读助手` 和 `@论文写作助手`。

## 入口与路由契约

- 显式入口：`@项目申报助手`。
- Skill ID：`project-proposal-skill`。
- 当前状态：`runnable_prototype`。
- 当用户显式使用 `@项目申报助手` 时，优先进入本 Skill。
- 无显式入口时，由外层 Controller 或 `agent_cli.py` 负责菜单选择，不依赖关键词猜测。

## 固定入口与独立性

- 当用户显式使用 `@项目申报助手` 时，优先进入本 Skill；不要求先调用研究选题、文献阅读或论文写作 Skill。
- 本 Skill 可凭 `input.projectMaterials` 独立抽取 `ProjectFactTable` 并生成申报书、结题报告或成果汇报。
- 来自研究选题的题目、来自文献阅读的证据卡、来自论文写作的段落都只能作为候选材料进入事实表；使用前必须重新形成 `factId` 和 `sourceRefs`。
- 真实交互中只能使用当前用户输入、附件、会话上下文或显式传入的项目材料；不得默认读取 `../research-line-test-data/`、旧 `examples/test-data/` 或任意测试材料包。
- 通过 `RESEARCH_LITERATURE_BACKEND=pedascope|hybrid` 可接入 PedaScope KB 作为研究背景题录候选来源；这些候选只能进入 `literatureBackgroundCandidates`，不得进入 `ProjectFactTable.facts`。
- 联动输出只放在 `handoff.projectFactTableSummary` 和 `handoff.documentSummary`；不得把其他 Skill 的结论直接写成项目事实。

## 能力边界

### 可以做

- 从项目材料、团队信息、预算信息中抽取 `ProjectFactTable`。
- 按申报书、结题报告、成果汇报模板生成结构化草稿或三文档集合。
- 输出评审维度对齐建议、预算风险提示和跨文档事实一致性报告。
- 基于事实表生成成果汇报时间线、亮点和基础图表建议。
- 基于 PedaScope 题录生成研究背景阅读候选和参考文献草案入口，但必须标记为 metadata-only。

### 不可以做

- 不预测中标概率、立项概率或评审结果。
- 不虚构成果、数据、团队经历、经费明细、时间节点或推广成效。
- 不把其他 Skill 的输出直接写成项目事实；必须先转成带来源的事实表。
- 不在缺少预算金额时替用户代填具体数值。
- 不把 PedaScope 文献题录写成项目已有成果、团队事实、预算事实、样本量或推广成效。

## 任务模式

| mode/taskIntent | 场景 | 核心输入 | 核心输出 | 是否可独立运行 |
|---|---|---|---|---|
| `fact_extraction` | 用户只要整理项目材料 | `projectMaterials`、`teamInfo`、`budgetInfo` | `ProjectFactTable`、`missingFields`、`conflicts` | 是 |
| `project_application` | 新申报课题或项目申报书框架 | 项目级别、申报通知、团队、过程、成果、预算 | 申报书章节草稿、评审维度对齐、预算提示 | 是 |
| `closing_report` | 项目结题报告或成果总结 | 周期、过程记录、实际成果、问题反思 | 结题报告章节草稿、缺证据清单 | 是 |
| `achievement_report` | 成果汇报 Word/PPT 结构 | 实际成果、样本数据、过程节点 | 成果亮点、时间线、图表建议、汇报章节 | 是 |
| `document_set` | 同时生成申报/结题/成果汇报 | 三类文档共用项目材料和事实表 | `documentSet`、跨文档一致性报告 | 是 |
| `budget_check` | 只检查预算科目和金额 | `budgetInfo` 或材料正文中的预算说明 | `budgetReport`、预算事实和风险提示 | 是 |

## 输入契约

最小请求结构：

```json
{
  "requestId": "req-project-proposal-001",
  "entryToken": "@项目申报助手",
  "skillId": "project-proposal-skill",
  "taskIntent": "project_application",
  "sourceRequest": "根据项目材料生成区级课题申报书框架",
  "teacherProfile": {},
  "input": {
    "documentType": "project_application",
    "projectLevel": "区级课题",
    "projectMaterials": [],
    "budgetInfo": {},
    "teamInfo": {},
    "requirements": ""
  },
  "researchWorkspace": null,
  "constraints": {},
  "assumptions": [],
  "sourceFiles": []
}
```

### 必需输入

| 字段 | 类型 | 说明 | 缺失处理 |
|---|---|---|---|
| `taskIntent` | string | 任务模式 | 默认按 `project_application` 处理，并写入假设 |
| `input.documentType` | string | 目标文档类型 | 可由 `taskIntent` 推断；无法推断时降级为事实表和补充清单 |
| `input.projectMaterials` | array | 项目材料、过程记录、成果、团队或预算说明 | 为空时输出 `missingFields`，不生成具体事实 |

### 推荐输入

| 字段 | 用途 | 缺失影响 |
|---|---|---|
| `input.projectLevel` | 选择评审侧重点和模板语气 | 使用通用区级课题口径 |
| `input.budgetInfo` | 预算科目与金额一致性检查 | 只能给非金额型预算建议 |
| `input.teamInfo` | 团队基础、分工和可行性说明 | 团队章节标记 `needs_evidence` |
| `input.requirements` | 用户或申报通知的特殊要求 | 只按内置模板生成 |

## 信息缺失与降级

- 缺少项目材料时，只输出事实表空壳、`missingFields` 和补材料清单，不生成具体成果或预算金额。
- 只提供“项目负责人 1 人”但没有姓名时，可记录为 `team.leader=项目负责人 1 人（姓名待确认）`；不得代填姓名。
- 预算可从结构化 `input.budgetInfo` 或材料正文中的“预算总额/科目/金额/用途”抽取；没有金额时只给科目建议。
- 实际成果、样本量、经费金额和推广成效必须来自事实表；缺失时章节标记 `needs_evidence`。
- 同一字段出现多个不同值时写入 `conflicts`，相关章节标记 `needs_user_confirmation`。

## 执行协议

- 外层 Controller 只负责入口识别、附件解析、槽位抽取和请求 JSON 组装。
- 本 Skill 负责声明事实表、模板、预算、评审对齐和一致性校验规则。
- 可运行场景优先使用 `scripts/render_project_proposal.py` 生成结构化输出；不要在 Controller 中手写最终 JSON。
- 输出后必须运行 `scripts/validate_project_proposal.py`，或至少对照 `references/quality-checklist.md`。

## 执行流程

1. 读取 `references/input-output-schema.md` 和 `references/project-fact-schema.json`，先抽取或校验 `ProjectFactTable`。
2. 每条事实必须包含 `factId`、`field`、`value`、`sourceRefs`、`confidence`、`status`。
3. 材料缺失写入 `missingFields`；材料冲突写入 `conflicts`，对应文档章节标记 `needs_user_confirmation`。
4. 根据 `input.documentType` 读取 `references/document-templates.json`，覆盖目标模板必填章节。
5. 用 `references/review-rubrics.json` 输出评审维度对齐建议；用 `references/budget-rules.json` 输出预算科目提示。
6. 预算总额和预算明细必须先作为 `budget.total` / `budget.items` 写入事实表；总额与明细不一致时写入 `conflicts`。
7. 当 `taskIntent` 或 `input.documentType` 为 `document_set` 时，输出 `documentSet.documents`，同时覆盖申报书、结题报告和成果汇报三类模板。
8. 成果汇报必须输出 `presentationSupport.timelineItems` 和 `chartSuggestions`；图表数值只能来自事实表中的数量事实，缺数据时输出 `needs_evidence` 占位，不生成数值。
9. 用 `references/consistency-check-rules.md` 检查申报、结题和汇报之间的事实一致性；`references/sanitized-case-patterns.json` 只能参考组织方式。
10. 当 `RESEARCH_LITERATURE_BACKEND=pedascope|hybrid` 或请求显式开启 `enableLiteratureBackground` 时，通过 `../research-line-common/literature_adapter.py` 生成 `literatureBackgroundCandidates`；候选不得进入事实表或事实引用。
11. 输出 `reviewAlignmentReport`、`budgetReport`、`consistencyReport`、`crossDocumentConsistencyReport`，并运行 `scripts/validate_project_proposal.py` 校验。
12. 若产物来自模型生成，render、handoff 或交付前还必须通过 `../research-line-common/model_output_guard.py`；`warn` 只能带警告进入人工复核，`rejected` 不得交付。
13. 需要教师可读交付物时，可用 `../research-line-common/docx_export.py` 导出申报书/结题报告/成果汇报 DOCX；成果汇报 PPTX 骨架用 `scripts/export_project_presentation.mjs` 生成，并保留 factId/来源约束。

## 资源加载顺序

1. 读本 `SKILL.md`，确认任务模式、边界和输出约束。
2. 读 `references/input-output-schema.md` 和 `references/project-fact-schema.json`。
3. 按 `taskIntent` 读取最小必要资源：
   - 文档生成：`references/document-templates.json`、`references/review-rubrics.json`
   - 预算检查：`references/budget-rules.json`
   - 三文档集合：`references/consistency-check-rules.md`
   - 案例组织参考：`references/sanitized-case-patterns.json`
4. 输出前运行 `scripts/validate_project_proposal.py` 或对照 `references/quality-checklist.md`。

## 输出契约

结构化输出使用科研线统一信封：

```json
{
  "requestId": "req-project-proposal-001",
  "skillId": "project-proposal-skill",
  "taskIntent": "project_application",
  "status": "pass|warn|failed",
  "summary": "",
  "result": {
    "projectFactTable": {},
    "documentDraft": {},
    "documentSet": {},
    "reviewAlignmentReport": {},
    "literatureBackgroundCandidates": [],
    "literatureBackgroundReport": {},
    "budgetReport": {},
    "consistencyReport": {},
    "crossDocumentConsistencyReport": {},
    "presentationSupport": {}
  },
  "handoff": {
    "projectFactTableSummary": {},
    "documentSummary": {}
  },
  "qualityReport": {},
  "provenanceReport": {},
  "warnings": [],
  "nextActions": []
}
```

## 边界

- 不预测中标概率。
- 不虚构成果、数据、团队经历或经费明细。
- 成功案例库、大规模政策库和复杂可视化属于后续增强。
- PedaScope 背景候选只作为研究现状阅读入口，不能构成项目事实或评审承诺。
- 用户未提供预算金额时，只能给科目建议，不能代填金额。
- 同一事实在不同章节或多份文档中冲突时，必须提示人工确认。

## 质量标准

- 项目事实表完整且可追溯。
- 文档章节符合目标文档类型。
- 三文档集合必须各自符合模板，且共享事实通过 `crossDocumentConsistencyReport` 回链到同一组 `factId`。
- 亮点提炼基于已有材料。
- `literatureBackgroundCandidates` 如存在，必须保持 `textAvailability=metadata` / `evidenceLevel=metadata_verified`，并不得出现在 `ProjectFactTable.facts.sourceRefs`。
- 同一事实在不同章节中不矛盾。
- 缺失字段、冲突字段和预算警告都必须让 `qualityReport.status` 降级为 `warn`。
- `generated-outputs/sample-valid.json`、`sample-document-set.json`、`sample-evidence-missing.json`、`sample-invalid.json` 是本 Skill 的输出边界样例。

## 脚本入口

```bash
python3 agent_cases/project-proposal-skill/scripts/render_project_proposal.py \
  agent_cases/project-proposal-skill/examples/sample-request.json \
  --output /tmp/project-proposal.json \
  --validate
```

```bash
python3 agent_cases/project-proposal-skill/scripts/validate_project_proposal.py \
  agent_cases/project-proposal-skill/generated-outputs/sample-document-set.json
```

普通试跑优先输出到 `/tmp`；`generated-outputs/` 只保留固定 `sample-*.json`。

## 资源索引

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `references/input-output-schema.md` | 请求、响应、事实表和 handoff 契约 | 每次执行前 |
| `references/project-fact-schema.json` | 必填事实字段、状态和冲突规则 | 抽取事实表时 |
| `references/document-templates.json` | 申报书、结题报告、成果汇报章节模板 | 生成文档时 |
| `references/review-rubrics.json` | 评审维度、分值和填写建议依据 | 申报书或三文档生成时 |
| `references/budget-rules.json` | 预算科目、用途和金额一致性规则 | 预算检查或含预算材料时 |
| `references/consistency-check-rules.md` | 三文档共享事实与降级规则 | `document_set` 时 |
| `references/quality-checklist.md` | 输出前质量底线 | validate 前或人工复核时 |

## 组件地图

- `scripts/render_project_proposal.py`：离线生成入口，负责事实抽取、三类文档草稿、评审对齐、预算检查和一致性报告。
- `scripts/validate_project_proposal.py`：结构化输出校验入口。
- `scripts/export_project_presentation.mjs`：从通过校验的 JSON 导出成果汇报 PPTX 骨架。
- `references/`：schema、模板、预算、评审、质量和一致性规则。
