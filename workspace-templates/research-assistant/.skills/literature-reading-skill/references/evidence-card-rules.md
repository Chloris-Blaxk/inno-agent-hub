# 证据卡规则

EvidenceCard 用于沉淀后续论文写作或项目申报可复用的证据，但必须保守标注来源和使用范围。

## 字段

```json
{
  "cardId": "ec-001",
  "claim": "",
  "evidenceText": "",
  "paperId": "",
  "paperTitle": "",
  "paperAuthors": [],
  "paperYear": 0,
  "paperJournal": "",
  "quoteLocation": "",
  "supportType": "direct_support|partial_support|background|not_support",
  "evidenceLevel": "abstract_verified",
  "usableFor": [],
  "limits": []
}
```

> 💡 `paperTitle`、`paperAuthors`、`paperYear`、`paperJournal` 是**推荐填写的 paper 元数据字段**。当下游 Skill（论文写作助手）接收 evidenceCard 时，可以直接用这些字段生成 GB/T 7714 引用草案，无需再通过 paperId 反查 LiteratureRecord。如果上游无法提供（如仅来自 PedaScope 的候选文献），这些字段可以为空，下游回退到 paperId 查找。

## 向教师展示时的规则

- ✅ 卡片标题用论文标题简记（如「📇 来自《学习证据与讲评课》（2023）的证据」），**不要**用 `ec-001` 之类的内部 cardId。
- ✅ `evidenceLevel` 必须附带一句中文边界说明（如「⚠️ 摘要级证据，只能做背景引用」）。
- ✅ `supportType` 用中文说明。

## supportType

| 内部值 | 向教师展示的中文 | 含义 |
|---|---|---|
| `direct_support` | 🟢 直接支撑 | 证据直接支持你的论点 |
| `partial_support` | 🟡 部分支撑 | 证据只支持你的论点的一部分 |
| `background` | 🔵 背景引用 | 只能作为研究背景或意义交代 |
| `not_support` | ⚪ 不支撑 | 证据不支持你的论点，需注意 |

## evidenceLevel 展示映射

见 `availability-levels.md` 的「向教师展示时怎么说」列。

## 质量规则

- `paperId` 必须能回链到 `LiteratureRecord`。向教师展示时，`paperId` 出现在括号或脚注中。
- **推荐填写** `paperTitle`、`paperAuthors`、`paperYear`、`paperJournal`，使下游 Skill 可直接生成 GB/T 7714 引用，无需反查。
- `evidenceText` 不能为空，除非只生成 `LiteratureRecord`。
- `quoteLocation` 必须说明 abstract、页码、段落或用户上传片段。展示给教师时用中文（如「摘要」「第 3 页」「你上传的原文第 2 段」）。
- 摘要级证据不得支撑细粒度实验结论、显著性结论或样本统计。
- **每张 EvidenceCard 面向教师展示时，必须以论文标题为卡片主标签，附带至少一条中文边界说明。**
