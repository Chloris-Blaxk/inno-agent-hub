# 输入与输出结构

## 阶段一：初始请求 JSON（可能不完整）

阶段一是主控模型（Controller）与教师的引导对话，初始请求可能只包含部分字段：

```json
{
  "subject": "科学",
  "grade": "六年级",
  "topic": "校园节水方案设计",
  "innovationType": null,
  "durationMin": 40,
  "constraints": ["普通教室", "可使用平板", "小组合作"],
  "requirements": null
}
```

**说明**：
- `innovationType` 为 `null` 表示教师未明确创新类型，需要进入类型引导决策。
- `requirements` 为 `null` 时，主控模型（Controller）应通过追问补齐。
- `subject` 和 `grade` 也可能为 `null`，但属于基本槽位，通常在入口解析时就能提取。

### 阶段一确认后的完整请求 JSON

经过引导对话和教师确认后，请求 JSON 应包含全部必要字段：

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

`innovationType` 取值：

- `PBL`
- `interdisciplinary`
- `ai_integrated`

`confirmedContext` 是阶段一对话中提炼的类型专属上下文，各类型的可选字段：

| 类型 | confirmedContext 字段 | 说明 |
|---|---|---|
| PBL | `drivingQuestionDirection` | 驱动问题方向 |
| PBL | `finalProductType` | 最终产出类型 |
| PBL | `projectSpan` | 单课时/多课时 |
| 跨学科 | `linkedSubject` | 关联学科 |
| 跨学科 | `integrationNodeDescription` | 融合节点描述 |
| 跨学科 | `applicableBoundaryHint` | 适用边界提示 |
| AI融合 | `aiInterventionStage` | AI 介入环节 |
| AI融合 | `useBoundaryHint` | 使用边界提示 |
| AI融合 | `critiqueApproach` | 审辨方式 |

阶段二生成脚本会对完整请求做预检：

- `subject`、`grade`、`topic`、`innovationType`、`durationMin` 必须存在且非空。
- `innovationType` 会归一化为 `PBL`、`interdisciplinary`、`ai_integrated` 三种之一。
- `confirmedContext` 必须是对象；若缺少类型专属字段，脚本会给出警告但仍允许生成。
- 生成模型必须显式吸收 `confirmedContext`，本地校验器会对覆盖度给出警告，可用严格模式转为失败。

## 阶段二：输出 JSON

```json
{
  "lessonMeta": {
    "subject": "",
    "grade": "",
    "topic": "",
    "innovationType": "PBL",
    "durationMin": 40,
    "lessonType": ""
  },
  "backgroundAnalysis": {},
  "studentAnalysis": {},
  "coreCompetencies": [
    {
      "id": "cc-1",
      "dimension": "学科核心素养维度（如：科学观念、科学思维、探究实践）",
      "target": "具体表现描述"
    }
  ],
  "objectives": [
    {
      "id": "obj-1",
      "description": "",
      "behaviorVerb": "设计",
      "linkedActivities": ["act-1"],
      "assessmentEvidence": ["rubric-1"]
    }
  ],
  "teachingFocus": "",
  "teachingDifficulty": "",
  "innovationDesign": {},
  "activityFlow": [
    {
      "id": "act-1",
      "stage": "导入",
      "durationMin": 5,
      "teacherActions": [],
      "studentActions": [],
      "outputs": [],
      "assessmentLinks": []
    }
  ],
  "assessmentRubric": [
    {
      "id": "rubric-1",
      "dimension": "",
      "excellent": "",
      "qualified": "",
      "needsImprovement": "",
      "evidence": ""
    }
  ],
  "resources": [
    {
      "type": "",
      "name": "",
      "usage": ""
    }
  ],
  "export": {
    "format": "markdown",
    "markdown": ""
  },
  "qualityReport": {
    "checks": [],
    "warnings": []
  }
}
```

### backgroundAnalysis 类型专属结构

**PBL**：

```json
{
  "backgroundAnalysis": {
    "textbookPosition": "课题对应教材单元、课标知识点及项目如何延伸教材",
    "priorKnowledge": "学生已有的相关知识",
    "inquiryExperience": "学生探究活动经验",
    "collaborationAbility": "学生小组合作能力"
  }
}
```

**跨学科**：

```json
{
  "backgroundAnalysis": {
    "primarySubject": {
      "unitPosition": "主学科单元定位",
      "standardRequirement": "主学科课标要求"
    },
    "linkedSubject": {
      "unitPosition": "关联学科单元定位",
      "standardRequirement": "关联学科课标要求"
    },
    "curriculumIntersection": "两学科在课标层面的交汇依据"
  }
}
```

**AI融合**：

```json
{
  "backgroundAnalysis": {
    "textbookPosition": "课题对应教材单元与知识点",
    "aiInterventionRationale": "该知识点为何适合 AI 辅助"
  }
}
```

### studentAnalysis 类型专属结构

**PBL**：合入 `backgroundAnalysis`，不单独出现。

**跨学科**：

```json
{
  "studentAnalysis": {
    "primarySubjectReadiness": "主学科预备水平",
    "linkedSubjectReadiness": "关联学科预备水平",
    "crossSubjectExperience": "跨学科思维经验"
  }
}
```

**AI融合**：

```json
{
  "studentAnalysis": {
    "priorKnowledge": "先备知识",
    "aiToolExperience": "AI工具使用经验",
    "critiqueAbility": "信息审辨能力",
    "independentThinkingHabit": "自主思考习惯"
  }
}
```

### teachingFocus / teachingDifficulty

- `teachingFocus`：字符串，教学重点。PBL 通常为驱动问题的探究过程；跨学科通常为融合节点；AI融合通常为 AI服务的目标达成+审辨。
- `teachingDifficulty`：字符串，教学难点。PBL 通常为保持真正探究+支架时机；跨学科通常为融合自然性+交汇处认知负荷；AI融合通常为人机边界管理+审辨深度。

本地校验范围：

- 根字段完整性（含 `backgroundAnalysis`、`studentAnalysis`、`coreCompetencies` 非空校验，含 `teachingFocus`、`teachingDifficulty` 非空校验）。
- `lessonMeta.innovationType` 与请求一致。
- `activityFlow[].durationMin` 总和等于请求 `durationMin`。
- 学习目标行为动词来自 `action-verbs.json`，且不超过学段建议层级。
- `objectives[].linkedActivities` 必须引用存在的 `activityFlow[].id`。
- `objectives[].assessmentEvidence` 与 `activityFlow[].assessmentLinks` 必须引用存在的 `assessmentRubric[].id`。
- 三类 `innovationDesign` 必须满足各自必需字段。
- 三类 `backgroundAnalysis` 必须满足各自必需字段。
- 跨学科和 AI融合的 `studentAnalysis` 必须满足各自必需字段。
- `confirmedContext` 中的类型专属信息应在 `innovationDesign`、`activityFlow` 或 `assessmentRubric` 中体现。

### innovationDesign 类型专属结构

**PBL**：

```json
{
  "innovationDesign": {
    "drivingQuestion": "",
    "milestones": [
      { "id": "ms-1", "description": "", "durationMin": 15, "outputs": [] }
    ],
    "finalProduct": { "type": "", "description": "", "criteria": [] }
  }
}
```

**跨学科**：

```json
{
  "innovationDesign": {
    "disciplineConnections": [
      { "subject": "", "contribution": "", "standardId": "" }
    ],
    "integrationNodes": [
      { "id": "node-1", "description": "", "linkedActivities": [] }
    ],
    "commonProduct": { "description": "", "criteria": [] },
    "applicableBoundary": ""
  }
}
```

**AI 融合**：

```json
{
  "innovationDesign": {
    "aiToolRoles": [
      { "patternId": "", "toolType": "", "toolRole": "", "interventionStage": "" }
    ],
    "interventionStages": [
      { "activityId": "", "aiAction": "", "studentAction": "" }
    ],
    "useBoundaries": [""],
    "studentCritiqueTasks": [
      { "activityId": "", "taskDescription": "", "evidenceExpected": "" }
    ]
  }
}
```
