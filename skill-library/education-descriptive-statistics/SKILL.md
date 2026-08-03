---
name: education-descriptive-statistics
category: 开发工具
description: Use after quantitative education data cleaning to summarize datasets before reliability, validity, inferential, experimental, regression, SEM, multilevel, or learning analytics analysis. Covers means, standard deviations, medians, frequencies, percentages, cross-tabulations, group comparisons, pre/post descriptive summaries, scale/item descriptives, visualization, and APA/education-paper result table wording.
metadata:
  short-description: Produce descriptive statistics and baseline summaries for education data
---

# Education Descriptive Statistics

## Goal

Generate clear descriptive summaries of education research data so the user understands the sample, variables, item distributions, group balance, and baseline patterns before deeper analysis.

## Use After

Use after:

- `education-quantitative-data-cleaning`
- `education-survey-instrument-design`
- `education-quantitative-study-design`
- `education-program-evaluation`
- `education-psychometric-scale-development`
- `education-learning-analytics-design`

Do not expose the skill name to users. Present it as "描述性统计与样本概览".

## Inputs

- Cleaned dataset
- Data dictionary
- Variable roles: demographic, grouping, scale/item, outcome, timepoint, class/school
- Scale score table if available
- Planned analyses

## Workflow

1. Identify variable types:
   - categorical: gender, grade, group, school type
   - ordinal: Likert items, rating levels
   - continuous: scores, scale means, time, counts
   - nested IDs: class, school, teacher
   - timepoint: pre/post/follow-up
2. Produce sample description:
   - N
   - participant categories
   - school/class/teacher structure
   - group allocation
   - attrition if longitudinal/intervention
3. Produce variable descriptives:
   - mean, SD, median, min, max
   - frequencies and percentages
   - missing counts
   - item-level distributions
4. Produce group/timepoint descriptives:
   - experimental vs control
   - pre vs post
   - grade/class/school groups
   - teacher/student groups if relevant
5. Generate cross-tabulations:
   - group x gender
   - group x grade
   - group x school/class
   - intervention completion x group
6. Recommend visualizations.
7. Flag descriptive risks:
   - very small groups
   - skewed variables
   - ceiling/floor effects
   - unbalanced baseline
   - suspicious missing patterns
8. Draft descriptive-results wording.

## Tool Calls

### R

```r
install.packages(c("tidyverse", "psych", "gtsummary", "gt", "janitor", "skimr"))
library(tidyverse)
library(psych)
library(gtsummary)
library(janitor)
library(skimr)
```

Overall descriptives:

```r
psych::describe(data[, c("score_pre", "score_post", "self_efficacy")])
```

Frequency table:

```r
data |> count(gender) |> mutate(percent = n / sum(n) * 100)
```

Cross-tab:

```r
janitor::tabyl(data, group, gender) |> janitor::adorn_percentages("row")
```

Group descriptives:

```r
data |>
  group_by(group) |>
  summarise(
    n = n(),
    mean = mean(score_post, na.rm = TRUE),
    sd = sd(score_post, na.rm = TRUE)
  )
```

Publication-style table:

```r
data |>
  select(group, gender, grade, score_pre, score_post) |>
  tbl_summary(by = group)
```

### Python

```bash
pip install pandas numpy scipy seaborn matplotlib tabulate
```

Overall descriptives:

```python
df[["score_pre", "score_post", "self_efficacy"]].describe()
```

Frequencies:

```python
df["gender"].value_counts(dropna=False)
df["gender"].value_counts(normalize=True, dropna=False) * 100
```

Cross-tab:

```python
pd.crosstab(df["group"], df["gender"], normalize="index") * 100
```

Group descriptives:

```python
df.groupby("group")["score_post"].agg(["count", "mean", "std", "median", "min", "max"])
```

### SPSS

```text
Analyze -> Descriptive Statistics -> Frequencies
Analyze -> Descriptive Statistics -> Descriptives
Analyze -> Descriptive Statistics -> Explore
Analyze -> Descriptive Statistics -> Crosstabs
Analyze -> Compare Means -> Means
Graphs -> Chart Builder
```

## Output Format

### 1. Sample Description Table

| Characteristic | Category | n | % |
|---|---|---|---|

### 2. Continuous Variable Descriptives

| Variable | N | Mean | SD | Median | Min | Max | Missing |
|---|---|---|---|---|---|---|---|

### 3. Group/Timepoint Descriptives

| Group | Timepoint | N | Mean | SD | Median | Min | Max |
|---|---|---|---|---|---|---|---|

### 4. Cross-Tabulation

| Row Variable | Column Variable | Pattern | Note |
|---|---|---|---|

### 5. Visualization Plan

| Purpose | Recommended Chart | Variables |
|---|---|---|
| Sample composition | Bar chart | Gender/grade/group |
| Score distribution | Histogram/density | Achievement/scale score |
| Group comparison | Boxplot/violin plot | Group x outcome |
| Pre-post change | Line/slope chart | Timepoint x score |
| Relationship | Scatterplot | Two continuous variables |

### 6. Descriptive Findings Draft

```text
The final sample included [N] participants from [schools/classes]. [x%] were in the intervention group and [x%] were in the comparison group. The mean pre-test writing score was [M] (SD = [SD]), while the mean post-test score was [M] (SD = [SD]). Descriptive results suggested [brief pattern], which was further examined using [planned inferential analysis].
```

Use Chinese if the paper is Chinese:

```text
本研究最终纳入 [N] 名学生，来自 [学校/班级数量]。实验组占 [x%]，对照组占 [x%]。前测写作成绩均值为 [M]（SD = [SD]），后测成绩均值为 [M]（SD = [SD]）。描述性结果显示 [简要模式]，后续将通过 [统计方法] 进一步检验。
```

## Education-Specific Checks

- Always describe grade, class, school, and teacher where relevant.
- For interventions, report baseline group balance descriptively before inferential tests.
- For longitudinal/pre-post data, report attrition by group.
- For scale items, inspect ceiling/floor effects common in student attitude data.
- For nested data, report number of schools/classes, not only student N.
- For small samples, avoid overinterpreting mean differences.

## Quality Rules

- Descriptive statistics do not prove significance or causality.
- Report missing values and valid N clearly.
- Use SD for approximately continuous variables; use frequencies for categorical variables.
- Do not average categorical codes such as gender or school type.
- Do not hide highly unbalanced groups.
- If Likert items are summarized with means, acknowledge ordinal nature when appropriate; scale scores are usually more defensible.

## User-Facing Closure

End by routing to the next likely analysis:

```text
描述性统计已经能说明样本和变量的基本情况。接下来可以进入三条路线：A. 信效度分析，B. t 检验/方差分析/相关回归，C. 可视化和结果表格整理。你希望先看哪一部分？如果你不确定，我会按论文设计自动推荐。
```
