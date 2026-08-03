---
name: education-ai-assisted-qualitative-analysis
category: 开发工具
description: Use when applying AI to support qualitative education analysis, including initial coding suggestions, code clustering, theme naming, memo generation, negative-case search, evidence retrieval, contradiction checks, saturation support, and audit-trail creation. This second-layer execution skill complements human qualitative coding and must not treat AI outputs as final findings without researcher confirmation.
metadata:
  short-description: Use AI to support qualitative coding, clustering, and negative-case search
---

# Education AI Assisted Qualitative Analysis

## Goal

Use AI to accelerate qualitative analysis while preserving human interpretation, traceability, and research rigor.

## Use After

Use with or after:

- `education-qualitative-coding-analysis`
- `education-qualitative-study-design`
- `education-mixed-methods-design`
- `education-action-research-design`
- `education-design-based-research`
- `education-program-evaluation`
- `education-policy-comparative-analysis`

Do not expose the skill name to users. Present it as "AI 辅助质性分析" or "AI 辅助编码建议".

## Inputs

- Research questions
- Anonymized qualitative corpus or excerpts
- Existing codebook, if any
- Chosen analysis approach: thematic analysis, grounded theory, content analysis, case analysis
- Whether multiple coders will review AI suggestions
- Privacy constraints and whether cloud AI tools are allowed

## Core Principle

AI can suggest, cluster, retrieve, and challenge. It cannot decide final codes, themes, or findings.

All AI outputs must be marked as:

- suggested
- accepted
- revised
- rejected

## Workflow

1. Privacy check:
   - confirm text is anonymized
   - remove names, school identifiers, student numbers, phone numbers, account IDs
   - avoid cloud tools if data cannot leave local environment
2. Prepare analysis batch:
   - 3-10 excerpts for pilot coding
   - or full corpus split into document/segment IDs
3. Generate initial code suggestions:
   - descriptive codes
   - in vivo codes
   - process codes
   - values/emotion codes if relevant
4. Ask researcher to accept/revise/reject codes.
5. Cluster accepted/revised codes into categories.
6. Generate theme candidates with definitions and evidence links.
7. Search for negative cases:
   - excerpts that contradict the dominant theme
   - participants/cases that differ
   - missing voices or edge cases
8. Generate analytic memos:
   - what pattern appears
   - what evidence supports it
   - what remains uncertain
   - what needs human review
9. Produce audit trail:
   - prompt/task
   - input batch IDs
   - AI suggestion
   - human decision
   - revision note
10. Update codebook and evidence table.

## Tool Calls

### Qualitative Software With AI Features

```text
ATLAS.ti: https://atlasti.com/
MAXQDA AI Assist: https://www.maxqda.com/
NVivo: https://lumivero.com/products/nvivo/
Dedoose: https://www.dedoose.com/
```

### Local / Controlled Analysis

Use local scripts or private LLM infrastructure when sensitive education data cannot be sent to web tools.

Suggested local preprocessing:

```bash
rg -n "姓名|学校|电话|身份证|学号|家长|微信|邮箱" transcripts/
```

Python text clustering support:

```bash
pip install pandas scikit-learn sentence-transformers umap-learn hdbscan
```

Use clustering only to suggest groupings; do not treat clusters as final themes.

## Prompt Templates

### Initial Coding Suggestion

```text
你是教育研究中的质性分析助手。请根据研究问题，对以下匿名访谈片段提出初始编码建议。

要求：
1. 每个代码必须对应具体片段。
2. 区分描述性代码、过程代码、情感/价值代码。
3. 不要生成最终主题。
4. 标注不确定之处。

研究问题：
[RQ]

片段：
[excerpt_id + text]
```

### Theme Clustering

```text
请将以下已人工确认或修订的代码聚合为候选类别和候选主题。

要求：
1. 保留每个代码的来源。
2. 说明聚合理由。
3. 标注边界模糊的代码。
4. 不要删除少数/反常代码。

代码表：
[code table]
```

### Negative Case Search

```text
以下是一个候选主题。请在材料中寻找可能削弱、反驳、限制或复杂化该主题的片段。

候选主题：
[theme]

材料：
[excerpt list]

输出：
反例片段、为什么构成反例、是否需要修改主题。
```

## Output Format

### 1. AI Suggested Codes

| Excerpt ID | Suggested Code | Code Type | Evidence Text Summary | Confidence | Human Decision | Revision |
|---|---|---|---|---|---|---|

Human decision values:

- Accept
- Revise
- Reject
- Needs discussion

### 2. Candidate Theme Clusters

| Candidate Theme | Included Codes | Rationale | Supporting Excerpts | Boundary/Negative Cases | Human Decision |
|---|---|---|---|---|---|

### 3. Negative Case Table

| Theme | Negative/Boundary Excerpt ID | Why It Matters | Suggested Theme Revision |
|---|---|---|---|

### 4. Audit Trail

| Date | Task | Input IDs | Tool/Model | Output Type | Human Reviewer | Decision Summary |
|---|---|---|---|---|---|---|

### 5. Memo Template

```text
Memo ID:
Related RQ:
Related codes/themes:
Pattern:
Evidence:
Negative cases:
Interpretive risk:
Next analytic action:
```

## Quality Rules

- Never call AI-suggested codes "final codes".
- Never report a theme without evidence excerpts.
- Always preserve rejected AI suggestions in the audit trail when the decision affects analysis.
- AI may help find negative cases; the researcher decides whether they alter the theme.
- For minor students, anonymize text more aggressively because writing samples can be identifiable.
- For policy/document analysis, distinguish text frequency from policy importance.
- For classroom discourse, preserve interaction sequence before clustering.

## User-Facing Closure

End by asking the user to choose a review mode, not a tool:

```text
我可以先做两种方式之一：A. 对 3-5 份材料做试编码，帮助你建立初始代码本；B. 基于已有代码本做主题聚类和反例搜索。你想先走哪一步？
```
