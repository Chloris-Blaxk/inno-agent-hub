# 输入输出 Schema

本 Skill 使用科研线统一请求/输出信封，但可独立运行，不依赖文献阅读、论文写作或项目申报 Skill 的结果。

统一设计来源：`agent_design/improvement/research-line-unified-skill-data-structure.md`。
公共信封和 `researchWorkspace` 以 `../research-line-common/schemas/` 为准；本文件只描述研究选题 Skill 的扩展字段。

> ⚠️ **重要**：本文档描述的是 JSON 内部结构（供机器/脚本/跨 Skill 联动使用）。**面向教师输出 Markdown 时，必须遵循 SKILL.md 中的「教师可读性规则」**——选题用标题不用 ID、评分用 ⭐ 不用裸 JSON 数值、枚举值用中文、全文用「你」不用「用户」。

## 请求对象

```json
{
  "requestId": "req-research-topic-001",
  "entryToken": "@研究选题生成",
  "skillId": "research-topic-generation-skill",
  "taskIntent": "mixed_topic",
  "sourceRequest": "根据我的课例和反思生成研究选题",
  "teacherProfile": {},
  "input": {
    "teacherProfile": {},
    "materials": [],
    "targetProjectType": "区级课题",
    "topicCount": {"summative": 3, "planning": 2},
    "requirements": ""
  },
  "researchWorkspace": null,
  "constraints": {
    "language": "zh-CN",
    "allowExternalSearch": false,
    "strictEvidence": true
  },
  "assumptions": [],
  "sourceFiles": []
}
```

## 执行模式

本 Skill 支持双轨执行：

| 轨道 | 条件 | 说明 |
|---|---|---|
| **LLM 轨** | 默认 | 基于 LLM 理解材料 + references 参考数据生成选题，与原有流程一致 |
| **DKG 轨** | `input.enableDKG = true` 且 DKG 已构建 | 优先运行 S1-S9 图计算管线，LLM 仅做结果包装和语言化 |

DKG 轨的请求额外字段：

```json
{
  "input": {
    "enableDKG": true,
    "dkgPath": "research-topic-generation-skill/generated-outputs/teacher-dkg.json",
    "dkgSourcesPath": "research-topic-generation-skill/examples/sample_sources.json"
  }
}
```

## taskIntent

| taskIntent | 说明 |
|---|---|
| `summative_topic` | 从教师已有材料中提炼总结性选题 |
| `planning_topic` | 面向未来 1-3 年规划研究方向 |
| `mixed_topic` | 同时生成总结性和规划性选题 |
| `topic_refine` | 对用户已有题目做聚焦、降重和可行性调整 |

## 固定入口与可选联动

- 用户使用 `@研究选题生成` 时，本 Skill 独立处理，不要求先调用其他科研 Skill。
- `input.materials` 为空时，不能生成总结性选题；可降级为规划性选题和补资料清单。
- 来自文献或项目材料的外部信息只能作为补充材料进入 `MaterialDigest`，不得直接写成教师已有成果。

## 关键输入对象

### TeacherProfile

```json
{
  "subject": "小学数学",
  "gradeBand": "高年级",
  "schoolContext": "城区普通小学",
  "researchExperience": "校级课题 1 项",
  "existingAchievements": [],
  "availableCycle": "1 年",
  "constraints": []
}
```

### SourceMaterial

```json
{
  "materialId": "mat-001",
  "materialType": "teaching_case",
  "title": "异分母分数加减法错因分析课例",
  "content": "围绕通分错误和约分遗漏设计课堂诊断。",
  "sourcePath": "",
  "sensitivityLevel": "internal",
  "licenseStatus": "user_provided"
}
```

## 输出对象

```json
{
  "requestId": "req-research-topic-001",
  "skillId": "research-topic-generation-skill",
  "taskIntent": "mixed_topic",
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
    "materialDigests": [],
    "materialClusters": [],
    "researchTrajectory": {},
    "topicCandidates": [],
    "topicEvaluationReport": {}
  },
  "handoff": {
    "topicCandidates": [
      {
        "topicId": "topic-001",
        "topicTitle": "小学数学课堂即时反馈支持错因诊断的实践研究",
        "topicType": "summative",
        "keywords": ["即时反馈", "错因诊断"],
        "researchQuestion": "",
        "evidenceStatus": "material_backed",
        "feasibilityScore": 4,
        "riskLevel": "medium",
        "nextReadingQuestions": []
      }
    ],
    "materialClusters": [
      {
        "clusterId": "cluster-001",
        "clusterTitle": "错因诊断与精准讲评",
        "materialIds": ["mat-001"],
        "coreSignals": ["错因诊断"],
        "currentStage": "theme_consolidation"
      }
    ],
    "researchTrajectory": {
      "trajectoryId": "trajectory-001",
      "stage": "theme_consolidation",
      "dominantThemes": ["错因诊断与精准讲评"],
      "sourceMaterialIds": ["mat-001"]
    },
    "keywords": [],
    "readingQuestions": []
  },
  "qualityReport": {
    "status": "pass",
    "checks": [],
    "warnings": [],
    "metrics": {
      "topicCount": 0,
      "summativeCount": 0,
      "planningCount": 0,
      "materialEvidenceCoverage": 0,
      "feasibilityWarnings": 0,
      "basisGapCount": 0,
      "differentiationCheckCount": 0,
      "highSimilarityCount": 0,
      "materialClusterCount": 0,
      "clusteredMaterialCoverage": 0,
      "trajectoryStepCount": 0,
      "dkgEnabled": false,
      "dkgCoverage": 0,
      "gapEvidenceCount": 0,
      "trendConfidence": 0,
      "feedbackLoopCount": 0
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

### MaterialDigest

```json
{
  "digestId": "digest-001",
  "materialId": "mat-001",
  "materialType": "teaching_case",
  "title": "异分母分数加减法错因分析课例",
  "keyFacts": [
    {"fact": "围绕通分错误和约分遗漏设计课堂诊断", "confidence": "high"}
  ],
  "topicSignals": ["错因诊断", "即时反馈", "小学数学"],
  "usableFor": ["research_topic", "project_basis"],
  "limitations": []
}
```

### MaterialCluster

```json
{
  "clusterId": "cluster-001",
  "clusterTitle": "错因诊断与精准讲评",
  "materialIds": ["mat-001", "mat-002"],
  "coreSignals": ["错因诊断", "即时反馈", "讲评"],
  "researchAxis": "围绕学生典型错因识别、分类记录和讲评调整形成连续研究。",
  "evidenceSummary": [
    {"materialId": "mat-001", "fact": "围绕通分错误和约分遗漏设计课堂诊断"}
  ],
  "currentStage": "material_accumulation|theme_consolidation|evidence_building",
  "gaps": ["缺少连续课堂观察、学生作品或数据记录。"],
  "usableTopicAngles": ["错因诊断支持精准讲评"]
}
```

### ResearchTrajectory

```json
{
  "trajectoryId": "trajectory-001",
  "stage": "insufficient_material|material_accumulation|theme_consolidation|evidence_building",
  "sourceMaterialIds": ["mat-001"],
  "dominantThemes": ["错因诊断与精准讲评"],
  "trajectorySummary": "已有材料集中在错因诊断与精准讲评，可从零散实践积累升级为连续证据链研究。",
  "pastAccumulation": ["围绕通分错误和约分遗漏设计课堂诊断"],
  "currentFocusableDirections": ["围绕学生典型错因识别、分类记录和讲评调整形成连续研究。"],
  "futureDeepeningPath": [
    {
      "stepId": "path-001",
      "timeframe": "0-1 个月",
      "action": "把已有课例、反思和成果按共同主题整理成问题链。",
      "requiredEvidence": ["mat-001"],
      "output": "研究问题与材料证据对应表"
    }
  ],
  "risks": ["缺少连续课堂观察、学生作品或数据记录。"]
}
```

### ResearchTopicCandidate

```json
{
  "topicId": "topic-001",
  "topicTitle": "小学数学课堂即时反馈支持错因诊断的实践研究",
  "topicType": "summative",
  "researchQuestion": "",
  "existingBasis": [
    {"materialId": "mat-001", "basis": "已有错因诊断课例"}
  ],
  "innovationPoints": [],
  "feasibility": {
    "score": 4,
    "risks": [],
    "neededMaterials": []
  },
  "basisGap": {
    "currentBasis": ["已有错因诊断课例"],
    "targetRequirement": "区级课题申报通常需要问题来源、连续实践证据、研究方法、过程数据和可展示成果。",
    "gaps": ["需要补充连续课堂观察记录"],
    "upgradePath": ["整理已有材料", "补充过程证据", "明确成果形态"]
  },
  "differentiation": {
    "nearestGrantId": "grant-demo-001",
    "nearestGrantTitle": "小学数学课堂即时反馈促进学生深度学习的实践研究",
    "similarityScore": 0.5,
    "riskLevel": "low|medium|high",
    "differenceStrategy": "突出错因分类和课堂调控机制。",
    "differentiatedTitleSuggestion": "小学数学即时反馈支持错因诊断的实践研究"
  },
  "keywords": ["即时反馈", "错因诊断", "小学数学"],
  "nextReadingQuestions": [],
  "dkgEvidence": {
    "enabled": false,
    "gapType": "sparse_region|structural_hole",
    "gapCause": "该缺口围绕主题 X、研究场景 Y，与锚点主题直接相关/为外围延伸方向。",
    "topoEvidence": {
      "indicatorTypes": ["邻域密度", "聚类系数"],
      "thresholdStrategy": "分位阈值（后30%分位）",
      "conclusion": "密度=0.12,聚类=0.08→满足稀疏区域多指标组合判定"
    },
    "trendEvidence": {
      "method": "time_series|relation_evolution|fusion(weighted)|fallback",
      "timeWindow": "2020-2025",
      "conclusion": "上升|下降|平稳|信号不足",
      "confidence": 0.68,
      "fallback": false
    },
    "sourceCoverage": 0.65,
    "graphPath": ["形成性评价", "即时反馈", "AI课堂分析"],
    "scoreBreakdown": {
      "match": 0.85,
      "gap": 0.72,
      "trend": 0.68,
      "feasibility": 0.60,
      "composite": 0.71,
      "synthesis": "weighted"
    },
    "uncertaintyNote": "趋势预测基于当前立项题样本，政策变化未纳入。"
  }
}
```

### TopicEvaluationReport

```json
{
  "materialEvidenceCoverage": 1.0,
  "clusteredMaterialCoverage": 1.0,
  "materialClusterChecks": [
    {"clusterId": "cluster-001", "materialCount": 2, "signalCount": 3}
  ],
  "researchTrajectoryCheck": {
    "stage": "theme_consolidation",
    "sourceMaterialCount": 2,
    "futureStepCount": 3
  },
  "differentiationChecks": [
    {"topicId": "topic-001", "nearestGrantId": "grant-demo-001", "similarityScore": 0.5, "riskLevel": "medium"}
  ],
  "basisGapChecks": [
    {"topicId": "topic-001", "gapCount": 1, "upgradeStepCount": 3}
  ],
  "notes": []
}
```

## 独立运行要求

- 本 Skill 只依赖本目录 `references/` 中的材料解析规则、教师画像 schema、选题评价量规、政策热点标签和立项题样本。
- 文献元数据索引只能作为增强输入；没有文献索引时仍可基于用户材料和教师画像生成保守选题。
- 不得虚构教师已有成果。材料中没有的经历、论文、课题、获奖只能列入“待补充资料”。
- `handoff.topicCandidates` 必须是压缩对象而不是 ID 数组，便于文献阅读直接接收标题、关键词、证据状态和阅读问题。
- DKG 合并路径必须补齐每个候选的 `basisGap`、`differentiation` 和 `nextReadingQuestions`，并同步更新 `topicEvaluationReport` 与 `qualityReport.metrics`。
