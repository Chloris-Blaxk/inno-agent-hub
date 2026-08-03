---
name: education-coder-reliability
category: 开发工具
description: Use when education qualitative or content-analysis projects involve multiple coders, coding reliability, coding agreement, pilot coding, codebook calibration, coding conflict resolution, Cohen's Kappa, Krippendorff's Alpha, percent agreement, inter-rater reliability, or reporting coder agreement. This second-layer execution skill supports qualitative coding, content analysis, discourse coding, classroom observation coding, policy text coding, open-ended survey coding, and AI-assisted coding review.
metadata:
  short-description: Check coder agreement and reliability in education qualitative/content analysis
---

# Education Coder Reliability

## Goal

Design and report a transparent coder agreement process for education qualitative/content analysis.

## Use After

Use with:

- `education-qualitative-coding-analysis`
- `education-ai-assisted-qualitative-analysis`
- `education-qualitative-study-design`
- `education-mixed-methods-design`
- `education-policy-comparative-analysis`
- `education-program-evaluation`

Do not expose the skill name to users. Present it as "编码一致性检查" or "多人编码质量控制".

## When Needed

Use when:

- two or more coders code the same material
- the study uses structured categories/content analysis
- classroom observation or discourse moves are coded
- open-ended survey responses are categorized
- AI-suggested coding is reviewed by humans
- the paper needs evidence that the coding scheme is stable

Do not force numeric reliability for all interpretive qualitative traditions. For reflexive thematic analysis, use coder discussion and reflexive memoing rather than treating Kappa as mandatory.

## Inputs

- Codebook
- Coding unit
- Number of coders
- Pilot coding sample
- Coded matrix: unit ID x coder x code/category
- Code type: nominal, ordinal, binary, multi-label, continuous score
- Whether codes are mutually exclusive

## Workflow

1. Confirm coding design:
   - unit of analysis
   - single-label or multi-label
   - mutually exclusive categories or overlapping codes
   - nominal/ordinal scale
2. Create pilot coding set:
   - 10-20% of corpus, or enough units to test category clarity
   - include diverse cases and difficult examples
3. Train/calibrate coders:
   - review code definitions
   - code pilot independently
   - compare disagreements
   - revise codebook
4. Choose agreement metric:
   - percent agreement for simple descriptive check only
   - Cohen's Kappa for 2 coders, nominal categories
   - weighted Kappa for ordinal categories
   - Fleiss' Kappa for more than 2 coders with nominal categories
   - Krippendorff's Alpha for multiple coders, missing values, different measurement levels
5. Calculate reliability on pilot or formal subset.
6. Resolve disagreements:
   - discussion
   - third coder/adjudicator
   - consensus coding
7. Record revisions and final coding rules.
8. Draft reporting paragraph.

## Tool Calls

### R Packages

```r
install.packages(c("irr", "psych", "krippendorffsalpha", "tidyverse"))
```

Cohen's Kappa:

```r
library(irr)
kappa2(data.frame(coder1, coder2), weight = "unweighted")
```

Weighted Kappa:

```r
kappa2(data.frame(coder1, coder2), weight = "squared")
```

Krippendorff's Alpha:

```r
library(krippendorffsalpha)
krippendorffs.alpha(coded_matrix, level = "nominal")
```

### Python Packages

```bash
pip install pandas scikit-learn krippendorff statsmodels
```

Cohen's Kappa:

```python
from sklearn.metrics import cohen_kappa_score
cohen_kappa_score(coder1, coder2)
```

Krippendorff's Alpha:

```python
import krippendorff
krippendorff.alpha(reliability_data=coded_matrix, level_of_measurement="nominal")
```

### Qualitative Software

```text
MAXQDA: Intercoder Agreement
NVivo: Coding Comparison Query
ATLAS.ti: Inter-Coder Agreement
Dedoose: Training Center / coder reliability features
```

## Output Format

### 1. Coding Reliability Plan

| Item | Decision |
|---|---|
| Coding unit |  |
| Coders |  |
| Pilot sample |  |
| Code type | Nominal/Ordinal/Binary/Multi-label |
| Agreement metric |  |
| Acceptable threshold |  |
| Conflict resolution |  |

### 2. Pilot Coding Matrix

| Unit ID | Excerpt Summary | Coder A Code | Coder B Code | Agreement | Notes |
|---|---|---|---|---|---|

### 3. Codebook Revision Log

| Revision | Trigger | Change | Example |
|---|---|---|---|

### 4. Reliability Results

| Code/Category Set | Metric | Value | Interpretation | Action |
|---|---|---|---|---|

### 5. Disagreement Resolution Table

| Unit ID | Coder A | Coder B | Issue | Final Decision | Rule Updated |
|---|---|---|---|---|---|

### 6. Reporting Template

```text
Two coders independently coded [sample size/percentage] of the materials using the initial codebook. After pilot coding, disagreements were discussed and the codebook was revised to clarify [main revisions]. Inter-coder reliability was calculated using [metric], yielding [value]. Remaining disagreements were resolved through [discussion/third coder/consensus]. The finalized codebook was then applied to [remaining corpus/full corpus].
```

## Metric Selection Guide

| Situation | Recommended Metric |
|---|---|
| 2 coders, one nominal category per unit | Cohen's Kappa |
| 2 coders, ordinal ratings | Weighted Kappa |
| 3+ coders, nominal categories | Fleiss' Kappa or Krippendorff's Alpha |
| Missing coder values | Krippendorff's Alpha |
| Different measurement levels | Krippendorff's Alpha |
| Multi-label overlapping codes | Calculate per-code binary agreement or use specialized multi-label agreement; explain method clearly |
| Reflexive thematic analysis | Use reflexive discussion/audit trail; do not overclaim Kappa |

## Quality Rules

- Percent agreement alone is usually insufficient for formal reliability claims.
- Do not calculate Kappa on a codebook that coders revised after seeing each other's coding unless reporting the process clearly.
- Low reliability may indicate unclear definitions, overlapping categories, weak training, or poor unitization.
- Report both the metric and the coding process.
- For education classroom data, coders must agree on event boundaries before coding event types.
- For AI-assisted coding, human agreement should be calculated on human decisions, not raw AI suggestions.

## User-Facing Closure

End by asking for the coding setup:

```text
为了做编码一致性检查，我需要知道：这批材料会有几位编码者？每个片段是单选一个类别，还是可以同时打多个代码？
```
