---
name: education-meta-analysis-preparation
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use for education meta-analysis papers or systematic reviews that quantitatively synthesize effect sizes. Supports effect-size extraction, coding sheet design, heterogeneity, moderator analysis, publication bias, forest/funnel plots, and R metafor/meta workflows.
metadata:
  short-description: Prepare education meta-analysis workflows
---

# Education Meta-Analysis Preparation

## Goal

Prepare data structures and analysis plans for a defensible education meta-analysis.

## Inputs

- Systematic review question
- Eligible intervention/effect studies
- Outcome types and statistics reported
- Study designs
- Moderator candidates

## Workflow

1. Confirm enough comparable quantitative studies exist.
2. Define effect size metric: SMD/Hedges g, correlation, odds ratio, risk ratio.
3. Create coding manual and extraction sheet.
4. Plan dependency handling for multiple effects.
5. Choose random/fixed effects model.
6. Plan heterogeneity, moderators, sensitivity, publication bias.
7. Produce analysis script skeleton and reporting template.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

R packages:

```r
install.packages(c("metafor", "meta", "dmetar", "clubSandwich", "robumeta"))
```

RevMan:

```text
https://training.cochrane.org/online-learning/core-software/revman
```

Extraction sheet:

```text
Excel/Sheets with study_id, effect_id, n_treat, n_control, mean/sd, outcome, timepoint, moderator fields
```

## Output Format

| Field | Definition | Coding Rule |
|---|---|---|

Include:

- Effect size plan
- Coding sheet
- R analysis outline
- Forest/funnel plot plan
- Reporting checklist

## Quality Rules

- Meta-analysis requires comparable outcomes and enough studies.
- Random effects are common in education due to contextual heterogeneity.
- Record decisions for dependent effect sizes.
