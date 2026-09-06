---
name: education-learning-analytics-modeling
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use after learning analytics or educational data mining data are available and cleaned, especially LMS logs, AI platform logs, clickstream, assignment histories, assessment sequences, student writing revision traces, knowledge component data, and learning behavior records. Covers feature engineering, sequence analysis, clustering, prediction, early warning, knowledge tracing, model evaluation, explainability, leakage checks, privacy, and education-paper reporting.
metadata:
  short-description: Model learning logs, behavior data, knowledge tracing, clustering, and prediction
---

# Education Learning Analytics Modeling

## Goal

Turn education platform/log/behavior data into interpretable learning analytics models and paper-ready results.

## Use After

Use after:

- `education-learning-analytics-design`
- `education-sampling-data-management`
- `education-quantitative-data-cleaning`
- `education-descriptive-statistics`
- `education-advanced-quantitative-modeling`

Do not expose the skill name to users. Present it as "学习行为数据建模" or "学习分析建模".

## Inputs

- Cleaned log or learning behavior dataset
- Data dictionary
- Unit of analysis: student, session, event, item, assignment, time window
- Outcome: achievement, completion, engagement, dropout risk, mastery, writing improvement
- Time window and prediction target
- Privacy/anonymization constraints

## Workflow

1. Define modeling objective:
   - descriptive behavior analysis
   - clustering/learner profiles
   - prediction/early warning
   - knowledge tracing/mastery estimation
   - sequence/pathway analysis
   - intervention/effect analysis
2. Define unit and time window:
   - event-level
   - session-level
   - student-week
   - student-course
   - item/knowledge component
3. Check data leakage:
   - features must occur before prediction target
   - no future outcome information in predictors
   - separate training/test by student or time where appropriate
4. Engineer features:
   - frequency/count
   - duration/time-on-task
   - recency
   - regularity
   - completion
   - revision behavior
   - help-seeking
   - AI prompt/feedback usage
   - assessment history
   - knowledge component performance
5. Choose model:
   - descriptive dashboards
   - k-means/hierarchical clustering/GMM/HDBSCAN
   - logistic/linear regression
   - random forest/gradient boosting
   - sequence models
   - Bayesian knowledge tracing/deep knowledge tracing when appropriate
6. Split/evaluate:
   - train/test split
   - cross-validation
   - time-based validation
   - student-level split
7. Evaluate metrics:
   - classification: accuracy, precision, recall, F1, AUC
   - regression: MAE, RMSE, R2
   - clustering: silhouette, stability, interpretability
   - knowledge tracing: AUC, calibration, mastery curve
8. Interpret model:
   - feature importance
   - SHAP/permutation importance
   - profile descriptions
   - educational meaning
9. Produce figures/tables and result narrative.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### Python

```bash
pip install pandas numpy scikit-learn statsmodels seaborn matplotlib shap xgboost lightgbm umap-learn hdbscan lifelines
```

Feature aggregation:

```python
features = (
    logs.groupby("student_id")
    .agg(
        n_sessions=("session_id", "nunique"),
        n_events=("event_id", "count"),
        total_time=("duration_sec", "sum"),
        avg_score=("score", "mean"),
        n_ai_feedback=("ai_feedback_used", "sum")
    )
    .reset_index()
)
```

Prediction:

```python
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, stratify=y, random_state=42)
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)
pred = model.predict(X_test)
proba = model.predict_proba(X_test)[:, 1]
print(classification_report(y_test, pred))
print(roc_auc_score(y_test, proba))
```

Clustering:

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

X_scaled = StandardScaler().fit_transform(X)
km = KMeans(n_clusters=3, random_state=42).fit(X_scaled)
silhouette_score(X_scaled, km.labels_)
```

SHAP:

```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
```

### R

```r
install.packages(c("tidyverse", "tidymodels", "caret", "cluster", "factoextra", "TraMineR", "lme4"))
```

Feature aggregation:

```r
features <- logs |>
  group_by(student_id) |>
  summarise(
    n_sessions = n_distinct(session_id),
    n_events = n(),
    total_time = sum(duration_sec, na.rm = TRUE),
    avg_score = mean(score, na.rm = TRUE),
    n_ai_feedback = sum(ai_feedback_used, na.rm = TRUE)
  )
```

Sequence analysis:

```r
install.packages("TraMineR")
library(TraMineR)
```

### Knowledge Tracing Tools

```text
pyBKT: https://github.com/CAHLR/pyBKT
pyKT: https://github.com/pykt-team/pykt-toolkit
EduKTM: https://github.com/bigdata-ustc/EduKTM
```

Install examples:

```bash
pip install pyBKT
```

Use knowledge tracing only when data include repeated item/skill/knowledge-component interactions.

## Output Format

### 1. Modeling Objective

| Objective | Outcome | Unit | Time Window | Model Family |
|---|---|---|---|---|

### 2. Feature Table

| Feature | Definition | Time Window | Source | Leakage Risk | Educational Meaning |
|---|---|---|---|---|---|

### 3. Model Plan

| Model | Purpose | Inputs | Evaluation Metric | Interpretation Method |
|---|---|---|---|---|

### 4. Results Table

| Model | Metric | Value | Baseline Comparison | Interpretation |
|---|---|---|---|---|

### 5. Learner Profile Table

| Cluster/Profile | Behavioral Pattern | Size | Outcome Pattern | Teaching Implication |
|---|---|---|---|---|

### 6. Knowledge Tracing Table

| Knowledge Component | Initial Mastery | Learning Rate | Guess/Slip | Interpretation |
|---|---|---|---|---|

### 7. Reporting Template

```text
基于学习平台日志，本研究构建了 [特征数量] 个学习行为特征，涵盖学习频率、学习持续时间、任务完成、AI 反馈使用和测验表现等维度。模型以 [结果变量] 为预测目标，采用 [模型] 进行分析。结果显示，模型在测试集上的 [指标] 为 [数值]，其中 [重要特征] 对预测贡献较大。该结果表明 [教育解释]。
```

## Education-Specific Feature Ideas

| Context | Features |
|---|---|
| AI writing platform | prompt count, feedback accepted, revision count, draft length change, time between drafts |
| LMS course | login frequency, video completion, quiz attempts, assignment lateness, forum posts |
| Intelligent tutoring | item attempts, hints requested, skill mastery, response time, error patterns |
| Reading platform | reading duration, pages completed, annotation count, comprehension score |
| Teacher dashboard | feedback frequency, grading turnaround, intervention notes |

## Quality Rules

- Prediction is not explanation unless interpreted carefully.
- Avoid leakage from future behavior or final outcomes.
- Split data at the student level when repeated events exist.
- Report class imbalance and baseline models.
- Prefer interpretable models for educational decision-making.
- Do not label students in stigmatizing ways; use supportive profile names.
- Preserve privacy for logs, prompts, writing samples, and account identifiers.

## User-Facing Closure

End by asking for the modeling objective:

```text
学习行为数据可以进入建模阶段。你更想先做哪类分析：A. 学习者画像/聚类，B. 成绩或风险预测，C. 知识掌握追踪，D. AI 使用行为与写作改进关系？如果你不确定，我会根据数据字段推荐。
```
