---
name: education-validity-reliability-analysis
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use when education research uses scales, questionnaires, tests, rubrics, or latent constructs and needs reliability and validity analysis, including Cronbach's alpha, McDonald's omega, item-total correlations, EFA, CFA, CR, AVE, convergent validity, discriminant validity, factor loadings, model fit, and measurement reporting. This second-layer execution skill supports quantitative, mixed-methods, psychometric, program evaluation, and survey studies.
metadata:
  short-description: Analyze reliability and validity for education scales and questionnaires
---

# Education Validity Reliability Analysis

## Goal

Evaluate whether education research instruments and latent constructs are measured reliably and validly enough for the intended analysis.

## Use After

Use after:

- `education-survey-instrument-design`
- `education-quantitative-data-cleaning`
- `education-descriptive-statistics`
- `education-psychometric-scale-development`
- `education-quantitative-study-design`

Do not expose the skill name to users. Present it as "信效度分析" or "量表质量检验".

## Inputs

- Cleaned item-level dataset
- Construct-dimension map
- Item-to-dimension mapping
- Reverse-scored item list
- Response scale
- Sample size
- Whether the instrument is established, adapted, or newly developed
- Intended later analysis: regression, SEM, group comparison, evaluation

## Workflow

1. Confirm item preparation:
   - reverse-coded items correctly recoded
   - missing values handled
   - item ranges valid
   - dimension membership clear
2. Conduct item analysis:
   - item mean/SD
   - item-total correlation
   - alpha if item deleted
   - ceiling/floor effects
3. Reliability analysis:
   - Cronbach's alpha
   - McDonald's omega when possible
   - split-half/test-retest/inter-rater if relevant
4. Choose factor analysis path:
   - established scale: CFA preferred
   - adapted scale: CFA, or EFA if structure uncertain
   - new scale: EFA first, then CFA on separate sample if possible
5. EFA if needed:
   - KMO and Bartlett's test
   - extraction method
   - rotation
   - number of factors
   - item loading/cross-loading decisions
6. CFA if needed:
   - specify measurement model
   - inspect standardized loadings
   - model fit indices
   - modification indices cautiously
7. Convergent validity:
   - factor loadings
   - CR
   - AVE
8. Discriminant validity:
   - Fornell-Larcker criterion
   - HTMT when appropriate
9. Produce reporting tables and method/results wording.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### R

```r
install.packages(c("psych", "lavaan", "semTools", "GPArotation", "EFAtools", "performance"))
library(psych)
library(lavaan)
library(semTools)
```

Cronbach's alpha:

```r
psych::alpha(data[, c("item1", "item2", "item3_r", "item4")])
```

McDonald's omega:

```r
psych::omega(data[, c("item1", "item2", "item3_r", "item4")], nfactors = 1)
```

KMO and Bartlett:

```r
psych::KMO(items)
psych::cortest.bartlett(cor(items, use = "pairwise.complete.obs"), n = nrow(items))
```

EFA:

```r
psych::fa(items, nfactors = 3, rotate = "oblimin", fm = "ml")
```

CFA:

```r
model <- '
  feedback_quality =~ item1 + item2 + item3 + item4
  writing_self_efficacy =~ item5 + item6 + item7 + item8
'
fit <- lavaan::cfa(model, data = data, estimator = "MLR", missing = "fiml")
summary(fit, fit.measures = TRUE, standardized = TRUE)
semTools::reliability(fit)
```

### Python

```bash
pip install pandas factor-analyzer pingouin semopy
```

Cronbach's alpha:

```python
import pingouin as pg
pg.cronbach_alpha(data=df[["item1", "item2", "item3_r", "item4"]])
```

EFA:

```python
from factor_analyzer import FactorAnalyzer
fa = FactorAnalyzer(n_factors=3, rotation="oblimin")
fa.fit(items)
fa.loadings_
```

### jamovi / JASP / SPSS / AMOS / Mplus

```text
jamovi: Factor -> Reliability Analysis; Factor -> Exploratory Factor Analysis
JASP: Factor -> Reliability Analysis; Factor -> Exploratory Factor Analysis
SPSS: Analyze -> Scale -> Reliability Analysis; Analyze -> Dimension Reduction -> Factor
AMOS: CFA/SEM graphical modeling
Mplus: CFA, SEM, latent variable modeling
```

## Output Format

### 1. Item Analysis Table

| Dimension | Item | Mean | SD | Item-Total r | Alpha if Deleted | Decision |
|---|---|---|---|---|---|---|

### 2. Reliability Table

| Construct/Dimension | Items | Cronbach's alpha | Omega | Interpretation |
|---|---|---|---|---|

### 3. EFA Table

| Item | Factor 1 | Factor 2 | Factor 3 | Cross-Loading | Decision |
|---|---|---|---|---|---|

Include KMO, Bartlett's test, extraction method, rotation, and variance explained.

### 4. CFA Model Fit Table

| Model | chi-square/df | CFI | TLI | RMSEA | SRMR | Decision |
|---|---|---|---|---|---|---|

### 5. Convergent / Discriminant Validity Table

| Construct | CR | AVE | sqrt(AVE) | Correlations / HTMT | Decision |
|---|---|---|---|---|---|

### 6. Reporting Template

```text
首先对量表进行信度检验。结果显示，各维度 Cronbach's α 系数介于 [ ] 至 [ ] 之间，表明量表内部一致性达到可接受水平。随后进行 [探索性/验证性] 因子分析，结果显示 [KMO/拟合指标/因子载荷] 符合研究要求，说明量表具有一定的结构效度。
```

## Decision Guidance

| Situation | Recommended Action |
|---|---|
| Alpha very low | Check reverse scoring, unclear items, weak item-total correlations |
| Alpha too high (> .95) | Check redundant items |
| Item cross-loads strongly | Revise/remove item or reconsider construct structure |
| CFA fit poor | Check model theory, item wording, data issues; do not modify only to improve fit |
| AVE low but CR acceptable | Report limitation and inspect loadings |
| Adapted scale with new population | Provide evidence for this population, not only original scale citation |

## Quality Rules

- Reliability is not validity.
- Do not claim a scale is "valid" universally; specify context and evidence.
- Always verify reverse-coded items before alpha/EFA/CFA.
- EFA and CFA ideally use separate samples for new scales.
- Do not delete items only because statistics improve; consider theory and content.
- Report sample size and response scale.

## User-Facing Closure

End by routing to the next statistical step:

```text
信效度分析完成后，量表分数才适合进入后续统计。接下来我可以帮你生成维度得分，并进入相关/回归/中介调节分析，或者先整理信效度结果表。
```
