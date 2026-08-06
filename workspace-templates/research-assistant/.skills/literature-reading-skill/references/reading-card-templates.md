# 阅读卡片模板

## 速读卡 QuickReadCard

用于 5-15 分钟判断是否值得精读。

```json
{
  "cardId": "read-001",
  "paperId": "paper-demo-001",
  "cardType": "quick",
  "topicRelevance": "high|medium|low",
  "researchProblem": "",
  "method": "",
  "findings": "",
  "limitations": "",
  "readingDecision": "priority_read|optional_read|skip",
  "reason": ""
}
```

### 各字段的教师展示映射

| JSON 字段 | 内部值 | 向教师展示时说的中文 |
|---|---|---|
| `topicRelevance` | `high` | ⭐⭐⭐⭐⭐ 极高 / ⭐⭐⭐⭐ 高 |
| | `medium` | ⭐⭐⭐ 中等 |
| | `low` | ⭐⭐ 偏低 |
| `readingDecision` | `priority_read` | 🔴 建议先读 |
| | `optional_read` | 🟡 有空可读 |
| | `skip` | ⚪ 可以先放一放 |
| `evidenceLevel` | 见 `availability-levels.md` 的展示映射表 | — |

> ⚠️ 速读卡面向教师展示时，禁止裸写 JSON 枚举值。

## 精读卡 DeepReadCard

用于摘要、全文或用户上传原文的结构化阅读。

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

### 精读卡向教师展示时的规则

- 卡片标题用论文标题（如「《学习证据视角下的小学数学讲评课改进路径》精读卡」），**不要**用 `paperId` 或 `cardId`。
- `evidenceLevel` 必须附带中文边界说明（如「⚠️ 摘要级证据，全文细节需获取原文确认」）。
- `sourceTextScope` 用中文描述：`abstract` →「仅基于摘要」、`fulltext` →「基于全文」、`user_uploaded_text` →「基于你上传的原文」。
- 「方法」「发现」「不足」若原文未提供，写「原文未提供」，不要猜。

## 横向比较矩阵 ComparisonMatrix

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
      "usableFor": ["研究背景"]
    }
  ]
}
```

### 比较矩阵向教师展示时的规则

- ✅ 行标签用论文标题（超过 15 字可简记为「即时反馈与错因诊断（2024）」之类）。
- ❌ 行标签**禁止**用 `paperId`。
- 列标题用中文：研究问题 / 方法 / 主要发现 / 不足 / 对你的课题有什么用。

## 生成原则

- 卡片只写文本中能支持的信息。
- 摘要级卡片必须标明 `evidenceLevel: abstract_verified`，展示时附带中文边界说明。
- 你上传原文生成的卡片必须标明 `evidenceLevel: user_text_only`，不得声明白名单真实性。
- 如果方法、样本或结论在文本中没有出现，写「未提供」，不要猜。
- **面向教师展示时**：卡片标题 = 论文标题，正文中用中文枚举值，技术字段只保留在括号或脚注。
