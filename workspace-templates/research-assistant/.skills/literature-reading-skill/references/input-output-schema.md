# 输入输出 Schema

> 📖 本文档定义所有数据对象。按 taskIntent 只读对应部分：
> - `literature_discovery` → `CorpusSearchReport` + `LiteratureRecord`
> - `quick_read` → `QuickReadCard` + `readingDecision` 字段
> - `deep_read` → `DeepReadCard` + `deepReadSessions` + `EvidenceCard`
> - `compare_papers` → `ComparisonMatrix`
> - `evidence_carding` → `EvidenceCard`

本 Skill 使用科研线统一请求/输出信封，但可独立运行，不依赖研究选题、论文写作或项目申报 Skill 的结果。

统一设计来源：`agent_design/improvement/research-line-unified-skill-data-structure.md`。
公共信封、`LiteratureRecord` 和 `EvidenceCard` 以 `../research-line-common/schemas/` 为准；本文件只描述文献阅读 Skill 的扩展字段。

## 请求对象

```json
{
  "requestId": "req-literature-reading-001",
  "entryToken": "@文献阅读助手",
  "skillId": "literature-reading-skill",
  "taskIntent": "literature_discovery",
  "sourceRequest": "围绕这个选题推荐优先阅读文献",
  "teacherProfile": {},
  "input": {
    "researchTopic": "小学数学课堂即时反馈对错因诊断的支持研究",
    "keywords": ["即时反馈", "错因诊断", "小学数学"],
    "readingGoal": "筛选 5 篇优先阅读文献，并对用户上传摘要生成速读卡。",
    "availablePapers": []
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
| `literature_discovery` | 基于选题、关键词或用户提供清单筛选优先阅读文献 |
| `quick_read` | 生成速读卡，帮助判断是否精读 |
| `deep_read` | 对摘要/全文/用户上传原文生成精读卡 |
| `compare_papers` | 生成横向比较矩阵 |
| `evidence_carding` | 抽取可追溯证据卡 |

## 固定入口与可选联动

- 用户使用 `@文献阅读助手` 时，本 Skill 独立处理，不要求先调用研究选题生成。
- 可从 `researchTopic`、`keywords` 或 `availablePapers` 任一输入启动；缺少选题时用候选文献或关键词生成保守阅读建议。
- 来自研究选题的关键词只用于候选排序，不自动生成支撑性引用。

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

## 输出对象

```json
{
  "requestId": "req-literature-reading-001",
  "skillId": "literature-reading-skill",
  "taskIntent": "literature_discovery",
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
    "corpusSearchReport": {},
    "literatureRecords": [],
    "quickReadCards": [],
    "deepReadCards": [],
    "deepReadSessions": [],
    "comparisonMatrix": [],
    "evidenceCards": []
  },
  "handoff": {
    "literatureRecords": [],
    "evidenceCards": []
  },
  "qualityReport": {
    "status": "pass",
    "checks": [],
    "warnings": [],
    "metrics": {
      "literatureHitCount": 0,
      "metadataOnlyCount": 0,
      "abstractAvailableCount": 0,
      "fulltextAvailableCount": 0,
      "userUploadedCount": 0,
      "deepReadCardCount": 0,
      "deepReadSessionCount": 0,
      "comparisonRowCount": 0,
      "evidenceCardCount": 0,
      "searchCandidateCount": 0,
      "searchReturnedCount": 0,
      "priorityReadCount": 0
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

### CorpusSearchReport

```json
{
  "indexName": "edu-lit-mock-2026-05",
  "indexSource": "local_mock_index",
  "simulatedCorpusSize": 1500000,
  "query": {
    "researchTopic": "小学数学课堂即时反馈对错因诊断的支持研究",
    "keywords": ["即时反馈", "错因诊断", "小学数学"],
    "filters": {
      "subjectCategory": "不限",
      "yearRange": "不限",
      "requireReadableText": false
    }
  },
  "candidateCount": 8,
  "returnedCount": 5,
  "rankingSignals": ["keyword_overlap", "topic_overlap", "text_availability"],
  "topHits": [
    {
      "paperId": "paper-index-001",
      "score": 7,
      "matchedKeywords": ["即时反馈", "错因诊断", "小学数学"],
      "textAvailability": "abstract",
      "sourceStatus": "external_verified",
      "selectionReason": "关键词和主题高度匹配，且具备可读文本。",
      "source": "mock-edu-index"
    }
  ]
}
```

### ReadingCard

```json
{
  "cardId": "read-001",
  "paperId": "paper-demo-001",
  "cardType": "quick|deep",
  "researchProblem": "",
  "method": "",
  "findings": "",
  "limitations": "",
  "readingDecision": "priority_read|optional_read|skip",
  "evidenceLevel": "abstract_verified"
}
```

### DeepReadCard

```json
{
  "cardId": "deep-001",
  "paperId": "paper-demo-001",
  "cardType": "deep",
  "researchProblem": "",
  "method": "",
  "findings": [],
  "limitations": [],
  "usableIdeas": [],
  "evidenceRefs": [],
  "evidenceLevel": "abstract_verified",
  "sourceTextScope": "abstract|fulltext|user_uploaded_text"
}
```

### DeepReadSession

```json
{
  "question": "这篇论文采用了什么研究方法？",
  "answer": "基于原文片段的回答。",
  "agent": "method|result|discussion|review|general",
  "citations": [
    {"chunkIndex": 1, "page": "", "section": "研究方法"}
  ],
  "_mock": false
}
```

### ComparisonMatrix

```json
{
  "matrixId": "cmp-001",
  "topic": "课堂即时反馈与错因诊断",
  "rows": [
    {
      "paperId": "paper-demo-001",
      "problem": "",
      "method": "",
      "finding": "",
      "limitation": "",
      "usableFor": ["论文引言"]
    }
  ]
}
```

### EvidenceCard

```json
{
  "cardId": "ec-001",
  "claim": "课堂即时反馈有助于教师调整教学决策",
  "evidenceText": "摘要或全文片段",
  "paperId": "paper-demo-001",
  "quoteLocation": "abstract",
  "supportType": "background",
  "evidenceLevel": "abstract_verified",
  "usableFor": ["论文引言", "项目研究背景"],
  "limits": ["仅基于摘要，不能支撑因果结论"]
}
```

## 独立运行要求

- 本 Skill 只依赖本目录 `references/` 中的本地文献索引样例、文献白名单样例、文本可用性规则、阅读卡模板、证据卡规则和质量清单。
- 可以接收用户直接提供的 `availablePapers`，不要求先由研究选题 Skill 生成选题。
- 未获得原文证据时只能生成“推荐阅读”或摘要级卡片，不得输出支撑性引用。
- `corpusSearchReport` 只说明检索和排序过程；不能把命中文献自动升级为支撑性引用。
- `render_literature_reading.py` 必须按 `taskIntent` 分流：发现模式只输出检索与文献记录，速读模式输出速读卡，精读模式输出 `deepReadCards` 与 `deepReadSessions`，比较模式输出矩阵，证据卡模式输出 EvidenceCard。
