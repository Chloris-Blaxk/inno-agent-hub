# 输入输出 Schema

本 Skill 使用科研线统一请求/输出信封，但可独立运行，不依赖文献阅读助手先生成证据卡。

统一设计来源：`agent_design/improvement/research-line-unified-skill-data-structure.md`。
公共信封和共享对象以 `../research-line-common/schemas/` 为准；本文件只描述论文写作 Skill 的扩展字段。

## 请求对象

```json
{
  "requestId": "req-paper-writing-001",
  "entryToken": "@论文写作助手",
  "skillId": "paper-writing-skill",
  "taskIntent": "source_trace",
  "sourceRequest": "帮我调研一下这句话出自哪篇文章",
  "teacherProfile": {},
  "input": {
    "queryText": "课堂即时反馈有助于教师及时发现学生的典型错因。",
    "draftText": "",
    "claims": [
      {
        "claimId": "claim-001",
        "claimText": "课堂即时反馈有助于教师及时发现学生的典型错因。"
      }
    ],
    "availableLiteratureRecords": [],
    "availableEvidenceCards": []
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
| `source_trace` | 查找一句话、一个观点或一段表述可能对应的真实来源 |
| `claim_support_check` | 校验论点是否有真实文献和证据支撑 |
| `structure_diagnosis` | 诊断 IMRaD 结构、摘要四要素和章节缺失 |
| `conservative_polish` | 不新增事实的保守学术化润色 |
| `citation_format` | 按 GB/T 7714 等规则输出或检查引用格式 |
| `outline_generation` | 生成 IMRaD 结构大纲，只做结构建议 |
| `chapter_drafting` | 逐章生成 `draft_reference` 参考草稿，需教师逐句确认 |
| `local_rewrite` | 局部缩写、扩写或改写，只处理选中片段 |

## 固定入口与可选联动

- 用户使用 `@论文写作助手` 时，本 Skill 独立处理；`source_trace` 不要求先调用文献阅读助手。
- `input.queryText`、`input.claims` 或 `input.draftText` 任一存在即可启动对应任务。
- `availableLiteratureRecords`、`availableEvidenceCards` 和文献阅读 handoff 都是可选增强输入，必须重新校验真实性和支撑性。
- 当前 Skill 只能基于白名单、证据卡索引、用户候选材料或明确授权检索结果输出来源；找不到证据时输出 `related_sources_only` 或 `no_source_found`。

## 关键输入对象

### LiteratureRecord

```json
{
  "paperId": "paper-demo-001",
  "title": "课堂即时反馈的教学价值研究",
  "authors": ["示例作者"],
  "year": 2023,
  "journal": "示例期刊",
  "doi": "",
  "keywords": ["即时反馈", "课堂评价"],
  "abstract": "本文讨论课堂即时反馈对学生学习投入和教师调整教学的影响。",
  "sourceStatus": "whitelist",
  "textAvailability": "abstract",
  "evidenceLevel": "metadata_verified"
}
```

### EvidenceCard

```json
{
  "cardId": "ec-001",
  "claim": "即时反馈有助于教师调整教学决策",
  "evidenceText": "摘要或全文片段",
  "paperId": "paper-demo-001",
  "quoteLocation": "abstract",
  "supportType": "partial_support",
  "evidenceLevel": "abstract_verified",
  "usableFor": ["论文引言"],
  "limits": ["不能支撑成绩显著提升"]
}
```

## 输出对象

```json
{
  "requestId": "req-paper-writing-001",
  "skillId": "paper-writing-skill",
  "taskIntent": "source_trace",
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
    "sourceTraceResults": [],
    "claimChecks": [],
    "structureDiagnosis": {
      "documentType": "research_paper",
      "sectionCoverage": [],
      "abstractChecklist": [],
      "revisionPriorities": []
    },
    "revisionSuggestions": [],
    "outline": {},
    "documentDraft": {},
    "localRewrite": {},
    "citationChecks": [],
    "insertionSuggestions": [],
    "citationWarnings": []
  },
  "handoff": {
    "claimChecks": [],
    "usableEvidenceCards": [],
    "paperRevisionSummary": {
      "addedFacts": 0,
      "revisionSuggestionCount": 0,
      "needsEvidenceRevisionCount": 0,
      "citationCheckCount": 0,
      "insertionSuggestionCount": 0,
      "draftSectionCount": 0,
      "citationPolicy": "only_verified_sources|no_supporting_citation_inserted"
    }
  },
  "qualityReport": {
    "status": "pass",
    "checks": [],
    "warnings": [],
    "metrics": {
      "claimCount": 0,
      "supportedClaimCount": 0,
      "needsEvidenceCount": 0,
      "sourceTraceHitCount": 0,
      "citationFormatWarnings": 0,
      "structureIssueCount": 0,
      "missingAbstractElementCount": 0,
      "revisionSuggestionCount": 0,
      "addedFactCount": 0,
      "needsEvidenceRevisionCount": 0,
      "citationCheckCount": 0,
      "citationReadyCount": 0,
      "insertionSuggestionCount": 0,
      "pendingTeacherConfirmationCount": 0,
      "outlineSectionCount": 0,
      "draftSectionCount": 0,
      "localRewriteCount": 0
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

### SourceTraceResult

```json
{
  "queryText": "课堂即时反馈有助于教师及时发现学生的典型错因。",
  "candidates": [
    {
      "paperId": "paper-demo-001",
      "matchType": "title|abstract|evidence_card|fulltext",
      "matchSnippet": "",
      "supportStatus": "supports|related_only|not_support",
      "confidence": "high|medium|low",
      "evidenceCardId": "ec-001",
      "quoteLocation": "abstract|fulltext|user_uploaded_text",
      "sourceLocator": {
        "locationType": "abstract",
        "locator": "abstract:sentence-001",
        "page": "",
        "paragraph": "abstract",
        "confidence": "medium"
      },
      "evidenceLevel": "abstract_verified|fulltext_verified|user_text_only|metadata_verified",
      "citation": ""
    }
  ],
  "decision": "verified_source_found|related_sources_only|no_source_found"
}
```

### CitationCheck

```json
{
  "citationId": "cit-001",
  "paperId": "paper-demo-001",
  "evidenceCardId": "ec-001",
  "citationStyle": "GB/T 7714",
  "formattedCitation": "示例作者. 课堂即时反馈的教学价值研究[J]. 示例期刊, 2023, 12(3): 45-48.",
  "formatStatus": "pass|warn|fail",
  "requiredFieldsPresent": true,
  "missingFields": [],
  "sourceLocator": {
    "locationType": "abstract",
    "locator": "abstract:sentence-001",
    "page": "",
    "paragraph": "abstract",
    "confidence": "medium"
  },
  "warnings": ["摘要级证据不能支撑页码级直接引文"]
}
```

### InsertionSuggestion

```json
{
  "insertionId": "insert-001",
  "claimId": "claim-001",
  "paperId": "paper-demo-001",
  "evidenceCardId": "ec-001",
  "inTextMarker": "[1]",
  "formattedCitation": "示例作者. 课堂即时反馈的教学价值研究[J]. 示例期刊, 2023, 12(3): 45-48.",
  "sourceLocator": {
    "locationType": "abstract",
    "locator": "abstract:sentence-001",
    "confidence": "medium"
  },
  "requiresTeacherConfirmation": true,
  "status": "pending_teacher_confirmation",
  "riskNotes": ["教师确认前不得自动插入正文或参考文献表。"]
}
```

### ClaimCheck

```json
{
  "claimId": "claim-001",
  "claimText": "即时反馈能显著提升数学成绩",
  "status": "supported|partially_supported|needs_evidence|unsupported",
  "matchedEvidenceCards": ["ec-001"],
  "riskNotes": ["现有证据只能支撑教学调整，不能支撑成绩显著提升"],
  "recommendedRewrite": "即时反馈有助于教师及时了解学生理解情况并调整教学。"
}
```

### StructureDiagnosis

```json
{
  "documentType": "research_paper",
  "sectionCoverage": [
    {
      "sectionId": "introduction",
      "label": "Introduction",
      "status": "present|missing|weak",
      "missingElements": [],
      "weakElements": ["已有研究不足"]
    }
  ],
  "abstractChecklist": [
    {
      "element": "purpose",
      "label": "目的",
      "status": "present|missing|weak",
      "evidenceSnippet": "本文旨在..."
    }
  ],
  "revisionPriorities": ["补充 Methods：需要说明对象/样本、数据来源、研究过程、分析方法。"]
}
```

### RevisionSuggestion

```json
{
  "suggestionId": "rev-001",
  "originalText": "即时反馈能显著提升学生数学成绩。",
  "revisedText": "即时反馈可能有助于改善学生数学学习表现。",
  "editType": "claim_softening|conservative_polish|structure_prompt",
  "changedFacts": false,
  "addedFacts": [],
  "needsEvidence": true,
  "riskNotes": ["保守改写后仍需文献、数据或课堂材料支撑。"]
}
```

### DocumentDraft

```json
{
  "documentId": "doc-001",
  "documentType": "research_paper",
  "title": "",
  "draftStatus": "draft_reference",
  "requiresTeacherConfirmation": true,
  "sections": [
    {
      "sectionId": "sec-001",
      "title": "引言",
      "required": true,
      "content": "",
      "factRefs": [],
      "evidenceRefs": ["ec-001"],
      "status": "draft_reference|needs_evidence|needs_user_confirmation",
      "requiresTeacherConfirmation": true,
      "needsEvidence": false
    }
  ]
}
```

### Outline

```json
{
  "outlineId": "outline-001",
  "title": "论文题目",
  "researchQuestion": "研究问题",
  "documentType": "research_paper",
  "sections": [
    {
      "sectionId": "introduction",
      "title": "问题提出",
      "coreFunction": "阐明实践背景、研究问题和已有研究不足。",
      "suggestedLength": "800-1200 字",
      "evidenceNeed": "需要用户材料或 EvidenceCard 支撑事实性表述。"
    }
  ],
  "riskNotes": ["大纲属于结构建议，不代表正文已具备事实或引用支撑。"]
}
```

### LocalRewrite

```json
{
  "rewriteId": "local-rewrite-001",
  "rewriteMode": "conservative_polish|shorten|expand",
  "originalText": "",
  "revisedText": "",
  "changedFacts": false,
  "addedFacts": [],
  "scope": "selected_text_only",
  "riskNotes": ["局部改写不得补造研究事实、数据或引用。"]
}
```

## source_trace 判定规则

- `verified_source_found`：真实文献存在，且证据片段能支撑或明确包含查询表述。
- `related_sources_only`：找到主题相关文献，但不能确认该句出自该文，也不能确认直接支撑。
- `no_source_found`：当前白名单、候选文献或证据卡未命中。
- 只有 `verified_source_found` 且存在可用证据卡时，才允许生成 `citationChecks` 和 `insertionSuggestions`。
- `insertionSuggestions` 永远是待教师确认对象，不能代表已经自动插入正文或参考文献表。

## 独立运行要求

- 本 Skill 必须能直接读取本目录 `references/` 中的文献白名单样例、证据卡索引、引用规则、IMRaD 清单和保守润色规则。
- `source_trace` 不能把文献阅读助手作为前置依赖。
- 不得编造作者、年份、期刊、DOI、页码或不存在的支撑关系。
- `structure_diagnosis` 和 `conservative_polish` 可仅凭 `input.draftText` 独立运行；没有查源需求时不得把空查询误判为“已查无来源”。
- 润色建议必须保持 `changedFacts=false`、`addedFacts=[]`，不得新增数字、年份、统计显著性或引用信息。
- `outline_generation` 不生成正文事实；`chapter_drafting` 输出必须标注 `draft_reference` 和 `requiresTeacherConfirmation=true`。
- `local_rewrite` 只处理 `input.selectedText` 或用户给出的局部文本，不得越界改写整篇论文。
