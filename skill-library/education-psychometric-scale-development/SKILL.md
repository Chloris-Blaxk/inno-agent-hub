---
name: education-psychometric-scale-development
category: 教学辅导
subject: 跨学科
kind: 教研科研
description: Use for education scale development, questionnaire validation, test development, rubric validation, educational measurement, item analysis, EFA/CFA, reliability, validity evidence, IRT, measurement invariance, and score interpretation.
metadata:
  short-description: Develop and validate education scales/tests
---

# Education Psychometric Scale Development

## Goal

Design and validate scales, tests, questionnaires, rubrics, or educational measurement instruments.

## Inputs

- Construct definition
- Target population
- Item pool or dimensions
- Response format
- Pilot/validation sample plan
- Existing theory/scales

## Workflow

1. Define construct and dimensions.
2. Generate item pool and expert review plan.
3. Plan pilot testing and item analysis.
4. Plan reliability: Cronbach alpha, omega, test-retest, inter-rater if relevant.
5. Plan validity: content, structural, convergent, discriminant, criterion.
6. Choose EFA/CFA/IRT/invariance analyses.
7. Draft measurement paper method/results templates.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

R packages:

```r
install.packages(c("psych", "lavaan", "semTools", "mirt", "ltm", "TAM", "GPArotation"))
```

Interactive:

```text
ShinyItemAnalysis: https://shinyitemanalysis.org/
jamovi: https://www.jamovi.org/
JASP: https://jasp-stats.org/
Mplus: https://www.statmodel.com/
AMOS: https://www.ibm.com/products/structural-equation-modeling-sem
```

## Output Format

| Stage | Task | Output |
|---|---|---|

Include:

- Construct map
- Item generation table
- Expert validity form
- Pilot analysis plan
- EFA/CFA/IRT plan
- Reporting template

## Quality Rules

- Do not claim validity as a property of a scale in general; state validity evidence for a use/context.
- Separate item development sample and validation sample when feasible.
- Match sample size to model complexity.
