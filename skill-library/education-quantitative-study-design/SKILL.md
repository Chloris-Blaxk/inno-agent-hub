---
name: education-quantitative-study-design
category: 教学辅导
subject: 跨学科
kind: 教研科研
description: Use for education papers using quantitative survey, correlational, regression, experimental, quasi-experimental, causal-comparative, mediation/moderation, SEM, multilevel, or longitudinal designs. Produces variables, hypotheses, sampling, instruments, power/sample-size guidance, statistical plan, and methods-section structure.
metadata:
  short-description: Design quantitative education studies
---

# Education Quantitative Study Design

## Goal

Create a defensible quantitative research design aligned with research questions and variables.

## Inputs

- Research questions/hypotheses
- Population and setting
- Available data or planned data collection
- Variable model from `education-variable-identification`
- Desired design: survey, experiment, quasi-experiment, regression, SEM, multilevel, longitudinal

## Workflow

1. Confirm design type and feasibility.
2. Define population, sampling, inclusion/exclusion, and sample size logic.
3. Finalize IV/DV/mediator/moderator/control variables.
4. Identify instruments/scales/tests and reliability/validity evidence.
5. Specify data collection procedure.
6. Specify statistical analysis plan.
7. Produce a method-section skeleton.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

Sample size/power:

```text
G*Power: https://www.psychologie.hhu.de/arbeitsgruppen/allgemeine-psychologie-und-arbeitspsychologie/gpower
```

Open-source analysis:

```r
install.packages(c("tidyverse", "psych", "car", "lavaan", "lme4", "effectsize", "mediation"))
```

No-code/low-code:

```text
jamovi: https://www.jamovi.org/
JASP: https://jasp-stats.org/
```

## Output Format

| Component | Design Decision | Rationale | Tool/Analysis |
|---|---|---|---|

Include:

- Hypotheses
- Variable table
- Sampling plan
- Instrument table
- Statistical analysis plan
- Method section draft

## Quality Rules

- Causal claims require experimental/quasi-experimental logic.
- For pre/post studies, include baseline equivalence and appropriate controls.
- For nested education data, consider multilevel modeling.
