---
name: education-inferential-statistics
category: 研究检索
description: Use after descriptive statistics when an education research project needs hypothesis testing or statistical relationships, including t-tests, ANOVA/ANCOVA, chi-square tests, correlations, linear/logistic regression, simple mediation/moderation screening, effect sizes, assumptions, post-hoc tests, and APA/Chinese education paper result reporting. This second-layer execution skill supports quantitative, mixed-methods, experimental, quasi-experimental, survey, program evaluation, and action research studies.
metadata:
  short-description: Run and report common inferential statistics for education research
---

# Education Inferential Statistics

## Goal

Choose, run, interpret, and report common inferential analyses aligned to education research questions, variable types, and study design.

## Use After

Use after:

- `education-descriptive-statistics`
- `education-quantitative-data-cleaning`
- `education-quantitative-study-design`
- `education-program-evaluation`
- `education-mixed-methods-design`

Do not expose the skill name to users. Present it as "假设检验与统计推断".

## Inputs

- Research questions/hypotheses
- Cleaned dataset
- Variable roles and types
- Group/timepoint structure
- Descriptive statistics
- Planned design: survey, experiment, quasi-experiment, pre-post, evaluation

## Workflow

1. Map each hypothesis to variables:
   - outcome/dependent variable
   - predictor/independent variable
   - group/timepoint
   - covariates/controls
2. Select analysis based on question and variable type.
3. Check assumptions:
   - independence
   - normality/large-sample robustness
   - homogeneity of variance
   - linearity
   - multicollinearity
   - expected cell counts for chi-square
4. Run the analysis.
5. Calculate effect size:
   - Cohen's d
   - eta squared / partial eta squared
   - odds ratio
   - r
   - standardized beta where useful
6. Interpret results:
   - statistical significance
   - effect size
   - confidence interval
   - educational/practical meaning
7. Draft result paragraph and table.
8. Warn about overclaiming or method mismatch.

## Method Selection Guide

| Research Question | Variables | Recommended Analysis |
|---|---|---|
| Do two independent groups differ? | Categorical group + continuous outcome | Independent-samples t-test |
| Did the same students improve from pre to post? | Paired timepoints + continuous outcome | Paired-samples t-test |
| Do 3+ groups differ? | Multi-group categorical predictor + continuous outcome | One-way ANOVA |
| Do groups differ after controlling baseline? | Group + continuous outcome + covariate | ANCOVA / regression |
| Are two categorical variables associated? | Two categorical variables | Chi-square test |
| Are two continuous variables related? | Two continuous/ordinal scale variables | Pearson/Spearman correlation |
| Which factors predict outcome? | Continuous/categorical predictors + continuous outcome | Linear regression |
| Which factors predict binary outcome? | Predictors + binary outcome | Logistic regression |
| Does relationship vary by group? | Predictor x moderator | Moderation regression |
| Does one variable explain a pathway? | IV -> mediator -> DV | Mediation analysis |

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### R

```r
install.packages(c("tidyverse", "rstatix", "effectsize", "car", "broom", "performance", "emmeans"))
library(tidyverse)
library(rstatix)
library(effectsize)
library(car)
library(broom)
```

Independent t-test:

```r
t.test(score_post ~ group, data = data)
effectsize::cohens_d(score_post ~ group, data = data)
```

Paired t-test:

```r
t.test(data$score_pre, data$score_post, paired = TRUE)
effectsize::cohens_d(data$score_post, data$score_pre, paired = TRUE)
```

ANOVA:

```r
fit <- aov(score_post ~ group, data = data)
summary(fit)
effectsize::eta_squared(fit)
TukeyHSD(fit)
```

ANCOVA/regression:

```r
fit <- lm(score_post ~ group + score_pre + gender + grade, data = data)
summary(fit)
car::Anova(fit, type = 3)
performance::check_model(fit)
```

Chi-square:

```r
tab <- table(data$group, data$pass)
chisq.test(tab)
```

Correlation:

```r
cor.test(data$self_efficacy, data$score_post, method = "pearson")
```

### Python

```bash
pip install pandas scipy statsmodels pingouin scikit-posthocs
```

t-test:

```python
from scipy import stats
stats.ttest_ind(group_a, group_b, nan_policy="omit")
stats.ttest_rel(pre, post, nan_policy="omit")
```

ANOVA/regression:

```python
import statsmodels.formula.api as smf
import statsmodels.api as sm
model = smf.ols("score_post ~ C(group) + score_pre + gender + grade", data=df).fit()
sm.stats.anova_lm(model, typ=2)
model.summary()
```

Chi-square:

```python
import pandas as pd
from scipy.stats import chi2_contingency
table = pd.crosstab(df["group"], df["pass"])
chi2_contingency(table)
```

Correlation:

```python
from scipy.stats import pearsonr, spearmanr
pearsonr(df["self_efficacy"], df["score_post"])
```

### SPSS

```text
Analyze -> Compare Means -> Independent-Samples T Test
Analyze -> Compare Means -> Paired-Samples T Test
Analyze -> Compare Means -> One-Way ANOVA
Analyze -> General Linear Model -> Univariate
Analyze -> Descriptive Statistics -> Crosstabs
Analyze -> Correlate -> Bivariate
Analyze -> Regression -> Linear
Analyze -> Regression -> Binary Logistic
```

## Output Format

### 1. Analysis Plan

| Hypothesis/RQ | Outcome | Predictor/Group | Covariates | Test | Effect Size |
|---|---|---|---|---|---|

### 2. Assumption Check

| Analysis | Assumption | Result | Action |
|---|---|---|---|

### 3. Result Table

| Analysis | Statistic | df | p | Effect Size | Interpretation |
|---|---|---|---|---|---|

### 4. Regression Table

| Predictor | B | SE | beta/OR | t/z | p | 95% CI |
|---|---|---|---|---|---|---|

### 5. Result Wording Template

Chinese:

```text
独立样本 t 检验结果显示，实验组在后测写作成绩上的平均得分（M = [ ], SD = [ ]）高于对照组（M = [ ], SD = [ ]），差异达到/未达到统计显著水平，t([df]) = [ ], p = [ ]，Cohen's d = [ ]。这表明 [教育意义解释]。
```

English:

```text
An independent-samples t-test showed that the intervention group (M = [ ], SD = [ ]) scored higher/lower than the comparison group (M = [ ], SD = [ ]), t([df]) = [ ], p = [ ], Cohen's d = [ ]. This suggests that [educational interpretation].
```

## Education-Specific Guidance

- For class-based interventions, check whether students are nested within classes.
- For pre/post quasi-experiments, prefer ANCOVA/regression controlling for pretest when comparing posttest.
- For small samples, emphasize effect size and confidence intervals; avoid strong claims.
- For nonrandomized designs, avoid saying "caused" unless design supports it.
- For Likert items, analyze scale scores rather than single items where possible.
- For multiple outcomes, consider multiple-comparison risk.

## Quality Rules

- Do not choose a statistical test only because it is familiar.
- Match test to variable type and design.
- Report effect sizes, not only p-values.
- Statistical significance is not educational importance.
- Correlation/regression does not prove causation.
- If assumptions are badly violated, recommend alternatives or robust methods.

## User-Facing Closure

End by routing to interpretation or next analysis:

```text
统计检验结果可以进入论文“结果”部分了。接下来我可以帮你做三件事：A. 生成结果表，B. 写结果段落，C. 继续做信效度/中介调节/高级模型。你想先看哪一步？
```
