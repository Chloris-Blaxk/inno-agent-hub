---
name: education-survey-instrument-design
category: 教学辅导
description: Use when designing survey instruments, questionnaires, scales, rubrics, or measurement tools for education research after research questions, variables, or constructs are identified. Covers scale selection, construct-dimension mapping, item generation, reverse-coded items, response formats, expert validity review, pilot testing, reliability/validity planning, and questionnaire deployment tools. This is a second-layer execution skill used by quantitative, mixed-methods, program evaluation, psychometric, and action research workflows.
metadata:
  short-description: Design education surveys, scales, and questionnaire instruments
---

# Education Survey Instrument Design

## Goal

Convert constructs/variables into a usable education research questionnaire or scale with dimensions, items, response options, validity checks, and pilot-test plan.

## Use After

Use this skill after one of these stages:

- `education-variable-identification`
- `education-quantitative-study-design`
- `education-mixed-methods-design`
- `education-program-evaluation`
- `education-psychometric-scale-development`

Do not expose the skill name to users. Present this as "问卷/量表设计" or "测量工具设计".

## Inputs

- Research question(s)
- Variable/construct table
- Target participants: students, teachers, parents, administrators
- Education context: grade, subject, school type, region
- Existing scales, if any
- Target language
- Intended analysis: descriptive, regression, mediation/moderation, SEM, EFA/CFA, evaluation

## Workflow

1. Confirm measurement purpose:
   - measure attitudes/perceptions
   - measure behavior/frequency
   - measure ability/performance
   - measure implementation quality
   - screen/group participants
   - validate a new scale
2. Map constructs to dimensions.
3. Search or suggest existing validated scales before creating new items.
4. Decide item source:
   - adopt existing scale
   - adapt existing scale
   - create new items
   - mixed adopt/adapt/create
5. Generate item pool for each dimension.
6. Choose response format:
   - 5-point or 7-point Likert
   - frequency scale
   - agreement scale
   - semantic differential
   - multiple choice
   - open-ended supplement
7. Add reverse-coded items only when useful and age-appropriate.
8. Build questionnaire sections:
   - consent/instructions
   - demographics/background
   - core scale items
   - behavioral/context items
   - optional open-ended item
9. Plan expert review/content validity.
10. Plan pilot test:
   - comprehension check
   - item distribution
   - missing response rate
   - reliability
   - exploratory factor analysis if enough sample
11. Output questionnaire draft and validation plan.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### Literature Search for Existing Scales

Semantic Scholar:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=student%20writing%20self-efficacy%20scale%20education&limit=10&fields=title,year,abstract,citationCount,authors"
```

OpenAlex:

```bash
curl "https://api.openalex.org/works?search=student%20writing%20self-efficacy%20scale%20education&per-page=10&mailto=YOUR_EMAIL"
```

Search patterns:

```text
[construct] scale education students
[construct] questionnaire validation teachers
[construct] instrument reliability validity education
[construct] Chinese scale students
```

### Questionnaire Deployment Tools

```text
Qualtrics: https://www.qualtrics.com/
SurveyMonkey: https://www.surveymonkey.com/
Google Forms: https://forms.google.com/
问卷星: https://www.wjx.cn/
腾讯问卷: https://wj.qq.com/
```

### Reliability and Item Analysis Tools

R:

```r
install.packages(c("psych", "tidyverse", "GPArotation"))
library(psych)
alpha(data_frame_of_items)
describe(data_frame_of_items)
fa(data_frame_of_items, nfactors = 3, rotate = "oblimin")
```

jamovi:

```text
https://www.jamovi.org/
Analyses -> Factor -> Reliability Analysis
Analyses -> Factor -> Exploratory Factor Analysis
```

JASP:

```text
https://jasp-stats.org/
Factor -> Reliability Analysis
Factor -> Exploratory Factor Analysis
```

## Output Format

### 1. Construct-Dimension Map

| Construct | Dimension | Definition | Source Basis | Planned Items |
|---|---|---|---|---|

### 2. Questionnaire Item Table

| Item ID | Dimension | Item Text | Response Format | Reverse Coded | Source/Adaptation |
|---|---|---|---|---|---|

### 3. Expert Review Form

| Item ID | Relevance 1-4 | Clarity 1-4 | Age Appropriateness 1-4 | Revision Suggestion |
|---|---|---|---|---|

### 4. Pilot-Test Plan

| Check | Method | Decision Rule |
|---|---|---|
| Comprehension | Cognitive interview or student feedback | Revise unclear items |
| Missing rate | Item missing percentage | Review items with high missing |
| Item distribution | Mean, SD, skewness | Review extreme ceiling/floor effects |
| Reliability | Cronbach's alpha / omega | Interpret cautiously; revise weak items |
| Structure | EFA/CFA if sample supports | Confirm dimension structure |

## Age-Appropriate Item Rules

- For primary students, use short sentences and concrete behaviors.
- Avoid double-barreled items.
- Avoid abstract constructs unless translated into observable behavior.
- Avoid excessive reverse-coded items for young learners.
- Use examples only if they do not bias answers.

## Quality Rules

- Prefer validated instruments when available.
- Do not claim a new scale is valid before testing.
- Separate dimensions clearly; each item should measure one thing.
- Align every item to a research question or variable.
- Record whether items are adopted, adapted, or newly written.
- Plan permissions/citations for existing scales.

## User-Facing Closure

End by asking the user to confirm practical constraints:

```text
这版问卷已经可以进入专家审阅和小样本预测试。接下来需要确认：你的对象是几年级学生？预计能收集多少份问卷？是否需要我把它整理成问卷星/Qualtrics 可导入格式？
```
