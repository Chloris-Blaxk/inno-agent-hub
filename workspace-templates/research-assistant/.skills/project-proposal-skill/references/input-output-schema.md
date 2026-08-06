# 输入输出 Schema

本 Skill 使用科研线统一请求/输出信封，但可独立运行，不依赖研究选题、文献阅读或论文写作 Skill 的结果。

统一设计来源：`agent_design/improvement/research-line-unified-skill-data-structure.md`。

## 请求对象

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
  "constraints": {
    "language": "zh-CN",
    "citationStyle": "GB/T 7714",
    "allowExternalSearch": false,
    "strictEvidence": true
  },
  "assumptions": [],
  "sourceFiles": []
}
```

## taskIntent

| taskIntent | 说明 |
|---|---|
| `fact_extraction` | 只抽取项目事实表并提示缺失/冲突 |
| `project_application` | 生成项目申报书框架或草稿 |
| `closing_report` | 生成结题报告框架或草稿 |
| `achievement_report` | 生成成果汇报框架或草稿 |
| `document_set` | 同时生成申报书、结题报告和成果汇报，并检查跨文档事实一致性 |
| `budget_check` | 检查经费科目、用途和合规风险 |

## 固定入口与可选联动

- 用户使用 `@项目申报助手` 时，本 Skill 独立处理，不要求先调用选题、文献或论文 Skill。
- `projectMaterials`、`budgetInfo`、`teamInfo` 或用户直接给出的项目事实均可作为事实表抽取来源。
- 预算信息优先使用结构化 `budgetInfo`；若教师只上传预算说明文本，可从 `projectMaterials` 中的预算总额、预算科目、金额和用途抽取预算事实。
- 团队负责人优先抽取姓名；若材料只说明“项目负责人 1 人”，可形成“姓名待确认”的人员事实，但不得代填姓名。
- 其他 Skill 的输出只能作为候选材料；写入正文前必须先进入 `ProjectFactTable` 并生成 `sourceRefs`。

## 关键输入对象

### SourceMaterial

```json
{
  "materialId": "mat-001",
  "materialType": "team",
  "title": "团队信息",
  "content": "项目负责人 1 人，核心成员 4 人，均参与过小学数学课堂反馈研究。",
  "sourcePath": "",
  "sensitivityLevel": "internal",
  "licenseStatus": "user_provided"
}
```

## 输出对象

```json
{
  "requestId": "req-project-proposal-001",
  "skillId": "project-proposal-skill",
  "taskIntent": "project_application",
  "status": "pass",
  "summary": "",
  "inputSummary": {},
  "warnings": [],
  "dataSourceReport": {
    "mockDataUsed": true,
    "dataSources": [],
    "overallLimitations": []
  },
  "artifacts": [],
  "result": {
    "projectFactTable": {},
    "documentDraft": {},
    "documentSet": {},
    "reviewAlignmentReport": {},
    "budgetReport": {},
    "consistencyReport": {},
    "crossDocumentConsistencyReport": {},
    "presentationSupport": {}
  },
  "handoff": {
    "projectFactTableSummary": {},
    "documentSummary": {}
  },
  "qualityReport": {
    "status": "pass",
    "checks": [],
    "warnings": [],
    "metrics": {
      "factCount": 0,
      "conflictCount": 0,
      "missingFieldCount": 0,
      "templateSectionCoverage": 0,
      "budgetWarningCount": 0,
      "documentCount": 0,
      "crossDocumentConflictCount": 0,
      "crossDocumentMissingSharedFieldCount": 0
    }
  },
  "provenanceReport": {
    "sourceCount": 0,
    "verifiedSourceCount": 0,
    "unsupportedClaimCount": 0
  },
  "nextActions": []
}
```

## 核心输出对象

### ProjectFactTable

```json
{
  "projectId": "proj-001",
  "facts": [
    {
      "factId": "fact-001",
      "field": "team.memberCount",
      "value": "核心成员 4 人",
      "sourceRefs": ["mat-001"],
      "confidence": "high",
      "status": "confirmed"
    }
  ],
  "missingFields": [],
  "conflicts": [
    {
      "field": "timeline.startDate",
      "values": ["2024-09", "2025-03"],
      "sourceRefs": ["mat-002", "mat-005"],
      "resolution": "needs_user_confirmation"
    }
  ]
}
```

### DocumentDraft

```json
{
  "documentId": "doc-001",
  "documentType": "project_application",
  "title": "",
  "sections": [
    {
      "sectionId": "sec-001",
      "title": "研究基础",
      "required": true,
      "content": "",
      "factRefs": ["fact-001"],
      "evidenceRefs": [],
      "status": "draft|needs_evidence|needs_user_confirmation"
    }
  ]
}
```

### DocumentSet

`taskIntent=document_set` 或 `input.documentType=document_set` 时输出。三份文档仍然共用同一个 `ProjectFactTable`，不得各自生成独立事实。

```json
{
  "setId": "docset-001",
  "generationMode": "three_format_document_set",
  "documents": [
    {"documentType": "project_application", "sections": []},
    {"documentType": "closing_report", "sections": []},
    {"documentType": "achievement_report", "sections": []}
  ]
}
```

### CrossDocumentConsistencyReport

```json
{
  "status": "pass|warn",
  "documentsChecked": ["project_application", "closing_report", "achievement_report"],
  "sharedFactFields": [
    {
      "field": "timeline.cycle",
      "factId": "fact-005",
      "value": "2026-09 至 2027-08",
      "sourceRefs": ["mat-003"],
      "usedInDocuments": ["project_application", "closing_report", "achievement_report"],
      "requiredByDocuments": ["project_application", "closing_report", "achievement_report"],
      "status": "consistent"
    }
  ],
  "conflicts": [],
  "missingSharedFields": [],
  "sectionWarnings": []
}
```

### PresentationSupport

成果汇报模式必须提供基础展示辅助；数值只能来自 `ProjectFactTable` 中的事实。

```json
{
  "timelineItems": [
    {
      "label": "实践积累",
      "description": "已完成 6 节错因诊断课例",
      "factRefs": ["fact-007"],
      "status": "derived_from_fact"
    }
  ],
  "chartSuggestions": [
    {
      "chartId": "chart-001",
      "chartType": "bar",
      "title": "成果数量展示",
      "dataPoints": [{"label": "教学案例", "value": 4}],
      "factRefs": ["fact-010"],
      "status": "derived_from_fact"
    }
  ],
  "achievementHighlights": []
}
```

## 独立运行要求

- 本 Skill 必须先抽取或校验 `ProjectFactTable`，再生成申报书、结题报告或成果汇报正文。
- 本 Skill 只依赖本目录 `references/` 中的项目事实 schema、文档模板、评审量规、预算规则、政策热点标签和质量清单。
- 三文档集合输出时，`crossDocumentConsistencyReport` 必须证明共享事实来自同一组 `factId`，缺失或冲突时降级为 `warn`。
- 不得虚构成果、数据、团队经历、经费明细或中标概率；材料不足时必须标记 `missingFields` 或 `needs_user_confirmation`。
