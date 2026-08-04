---
name: education-learning-analytics-design
category: 教学辅导
description: Use for learning analytics, educational data mining, LMS log analysis, AI platform behavior data, learner modeling, prediction, clustering, sequence mining, early warning, dashboard design, and explainable analytics in education research.
metadata:
  short-description: Design learning analytics and educational data mining studies
---

# Education Learning Analytics Design

## Goal

Turn platform/log/behavior data into a rigorous education research design.

## Inputs

- Data source: LMS, AI platform, app logs, assignments, assessments, clickstream
- Outcome of interest
- Unit of analysis: student, session, class, school, item
- Time window
- Privacy constraints

## Workflow

1. Define research questions and unit of analysis.
2. Build data dictionary.
3. Plan cleaning, anonymization, and feature engineering.
4. Select analysis type: descriptive, clustering, prediction, sequence, causal inference.
5. Plan validation and interpretability.
6. Design visualizations/dashboards if needed.
7. Draft methods and limitations.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

Python:

```bash
pip install pandas numpy scikit-learn statsmodels seaborn matplotlib shap
```

R:

```r
install.packages(c("tidyverse", "caret", "tidymodels", "lme4", "TraMineR"))
```

Tools:

```text
Jupyter, RStudio, Orange, Weka, Power BI, Tableau
```

## Output Format

| Data Field | Meaning | Feature Engineering | Privacy Risk |
|---|---|---|---|

Include:

- Data dictionary
- Feature plan
- Modeling plan
- Evaluation metrics
- Ethics/privacy checklist

## Quality Rules

- Avoid black-box prediction without educational interpretation.
- Do not use identifiable student data without anonymization and consent.
- Define leakage risks when predicting outcomes.
