---
name: education-quantitative-data-cleaning
category: 研究检索
description: Use after quantitative education data are collected and before descriptive, inferential, reliability, validity, SEM, multilevel, or learning analytics analysis. Covers data import checks, data dictionary validation, missing values, invalid values, outliers, duplicate records, participant attrition, variable coding, reverse scoring, scale scoring, group/timepoint coding, dataset versioning, and reproducible cleaning logs.
metadata:
  short-description: Clean and prepare quantitative education research data
---

# Education Quantitative Data Cleaning

## Goal

Prepare education research datasets for trustworthy statistical analysis while preserving a reproducible cleaning trail.

## Use After

Use after data collection or import:

- `education-sampling-data-management`
- `education-survey-instrument-design`
- `education-quantitative-study-design`
- `education-mixed-methods-design`
- `education-program-evaluation`
- `education-psychometric-scale-development`
- `education-learning-analytics-design`

Do not expose the skill name to users. Present it as "量化数据清洗与准备".

## Inputs

- Raw dataset file(s): Excel, CSV, SAV, XLSX, log export
- Data dictionary
- Questionnaire/item list and reverse-coded item list
- Participant ID scheme
- Group/timepoint variables if experimental or longitudinal
- Planned analysis
- Missing value codes used in the dataset

## Workflow

1. Preserve raw data:
   - never overwrite the original file
   - create a cleaned copy
   - create a cleaning log
2. Import and inspect:
   - row count
   - variable names
   - data types
   - duplicate IDs
   - unexpected columns
3. Validate IDs and structure:
   - participant IDs
   - class/school/teacher hierarchy
   - group assignment
   - timepoint/pre-post matching
4. Check missing values:
   - system missing
   - custom missing codes
   - item-level missing
   - participant-level missing
   - attrition between waves
5. Check invalid values:
   - outside Likert range
   - impossible ages/grades
   - inconsistent group/timepoint values
   - duplicate submissions
6. Check outliers:
   - univariate outliers
   - multivariate outliers if needed
   - impossible response patterns
   - extremely fast survey completion
7. Recode variables:
   - demographic categories
   - group variables
   - time variables
   - dummy variables if needed
8. Reverse-score items:
   - verify scale range
   - compute reversed values
   - preserve original item variables if useful
9. Score scales:
   - mean or sum scores
   - dimension scores
   - total scores
   - item count used per score
10. Export cleaned data and cleaning report.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### R

```r
install.packages(c("tidyverse", "readxl", "janitor", "naniar", "skimr", "psych", "haven"))
library(tidyverse)
library(readxl)
library(janitor)
library(naniar)
library(skimr)
library(psych)
```

Import:

```r
raw <- readxl::read_excel("raw_data.xlsx") |> janitor::clean_names()
skimr::skim(raw)
```

Missing summary:

```r
naniar::miss_var_summary(raw)
naniar::miss_case_summary(raw)
```

Reverse scoring for a 1-5 Likert item:

```r
clean <- raw |>
  mutate(item3_r = 6 - item3)
```

Scale score:

```r
items <- c("item1", "item2", "item3_r", "item4")
clean <- clean |>
  mutate(
    self_efficacy_n = rowSums(!is.na(across(all_of(items)))),
    self_efficacy = if_else(
      self_efficacy_n >= 3,
      rowMeans(across(all_of(items)), na.rm = TRUE),
      NA_real_
    )
  )
```

Set the minimum valid-item threshold before scoring; the example requires at least 3 of 4 items. Keep the valid-item count in the cleaning report.

### Python

```bash
pip install pandas numpy missingno openpyxl scipy
```

Import and inspect:

```python
import pandas as pd
df = pd.read_excel("raw_data.xlsx")
df.info()
df.describe(include="all")
df.isna().mean().sort_values(ascending=False)
```

Reverse scoring for a 1-5 Likert item:

```python
df["item3_r"] = 6 - df["item3"]
```

Duplicate IDs:

```python
df[df.duplicated("participant_id", keep=False)]
```

### SPSS

Use:

```text
Analyze -> Descriptive Statistics -> Frequencies
Analyze -> Descriptive Statistics -> Explore
Transform -> Recode into Different Variables
Transform -> Compute Variable
Data -> Identify Duplicate Cases
```

Reverse scoring example for 1-5:

```text
COMPUTE item3_r = 6 - item3.
EXECUTE.
```

## Output Format

### 1. Data Intake Summary

| Item | Value |
|---|---|
| Raw file |  |
| Rows |  |
| Variables |  |
| Unit of analysis |  |
| ID variable |  |
| Group variable |  |
| Timepoint variable |  |

### 2. Data Quality Report

| Check | Issue Found | Action |
|---|---|---|
| Duplicate IDs |  |  |
| Missing values |  |  |
| Invalid ranges |  |  |
| Outliers |  |  |
| Reverse-coded items |  |  |
| Attrition |  |  |

### 3. Variable Coding Table

| Variable | Original Coding | Cleaned Coding | Notes |
|---|---|---|---|

### 4. Reverse-Scoring Table

| Item | Scale Range | Reverse Formula | New Variable |
|---|---|---|---|

### 5. Scale Score Table

| Scale/Dimension | Items Used | Scoring Rule | Minimum Valid Items | New Variable |
|---|---|---|---|---|

### 6. Cleaning Log

| Step | Decision | Reason | Rows/Variables Affected |
|---|---|---|---|

## Education-Specific Checks

- Preserve class, school, and teacher IDs for nested data.
- For pre/post designs, verify each student has correct matched timepoints.
- For intervention studies, verify group assignment and attrition by group.
- For student questionnaires, check straight-lining and unrealistically fast completion.
- For teacher surveys, check duplicate school/teacher records.
- For learning outcomes, check scoring range and rubric consistency.
- For AI tool studies, separate tool usage variables from outcome variables.

## Missing Data Guidance

- Do not silently delete rows.
- Report missingness by item and participant.
- For scale scores, define the minimum number of valid items.
- For longitudinal data, distinguish missing item response from participant attrition.
- Imputation decisions should be aligned with analysis plans and reported.

## Outlier Guidance

- Do not remove outliers only because they are inconvenient.
- Distinguish impossible values from extreme but possible values.
- For achievement scores, confirm scoring range before labeling outliers.
- Keep an exclusion log.

## Quality Rules

- Raw data must remain unchanged.
- Every derived variable must be documented.
- Reverse scoring must be verified before reliability analysis.
- Use consistent missing-value codes.
- Cleaned data should be reproducible from raw data and cleaning script/log.

## User-Facing Closure

End by asking for the next required artifact:

```text
数据清洗方案已经确定。接下来你可以上传原始数据和数据字典，我会先生成数据质量报告，再决定是否进入描述统计、信效度分析或推断统计。
```
