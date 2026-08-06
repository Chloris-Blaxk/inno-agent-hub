# 输入输出 Schema

## 请求对象

```json
{
  "subject": "数学",
  "grade": "五年级",
  "textbookVersion": "人教版",
  "unit": "分数的加法和减法",
  "topic": "异分母分数加减法",
  "knowledgePointIds": ["math-g5-fraction-add"],
  "taskType": "layered_homework",
  "questionCount": 9,
  "layers": ["A", "B", "C"],
  "questionTypes": ["计算题", "应用题"],
  "layerMix": {"A": 3, "B": 3, "C": 3},
  "questionTypeMix": {"计算题": 5, "应用题": 4},
  "difficultyMix": {"1": 1, "2": 2, "3": 3, "4": 3},
  "difficultyRange": [1, 4],
  "strictBlueprint": false,
  "requirements": "每层 3 题，附答案和分步解析。"
}
```

## taskType

| taskType | 场景 | 首批输出重点 |
|---|---|---|
| `classroom_practice` | 课堂练习 | 少量即时练习、答案解析、易错提醒 |
| `layered_homework` | 分层作业 | A/B/C 分层、每层目标、分层讲评建议 |
| `unit_test` | 单元测验 | 题型比例、难度比例、知识点覆盖 |
| `stage_test` | 阶段测验 | 阶段知识点覆盖、讲评建议 |
| `topic_drill` | 专题练习 | 单知识点或题型专项、变式与重复风险 |

## 输出对象

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

## 题目对象

```json
{
  "id": "q001",
  "sourceId": "seed-frac-a-001",
  "layer": "A",
  "questionType": "计算题",
  "difficulty": 1,
  "cognitiveLevel": "理解",
  "knowledgePointIds": ["math-g5-fraction-add"],
  "stem": "计算：1/2 + 1/3 = ?",
  "answer": "5/6",
  "solutionSteps": ["先通分为 3/6 + 2/6", "分子相加，分母不变，得到 5/6"],
  "commonErrors": ["err-denominator-add"],
  "scorePoints": ["能正确通分", "能正确相加并化简"],
  "teachingNote": "重点追问为什么分母不能直接相加。"
}
```

## 质量报告

`qualityReport.checks` 中每项包含：

```json
{
  "id": "question_count",
  "status": "pass",
  "message": "题量与请求一致。"
}
```

`status` 可为 `pass`、`warn`、`fail`。首批脚本中 `fail` 应导致校验不通过。

## 换题建议

`replacementSuggestions` 用于支持专题练习和试卷草稿的一键换题：

```json
{
  "questionId": "q003",
  "sourceId": "seed-frac-a-001",
  "alternatives": [
    {
      "sourceId": "seed-frac-a-010",
      "groupId": "sim-frac-basic-calc-001",
      "methodTag": "异分母先通分再加减",
      "replaceRule": "保留两项异分母加减结构，优先使用较小公分母，结果需约分。"
    }
  ]
}
```
