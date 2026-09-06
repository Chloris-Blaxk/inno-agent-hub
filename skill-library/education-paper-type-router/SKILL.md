---
name: education-paper-type-router
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use after an education research topic and research questions are drafted, or whenever the user is unsure what type of education paper to write. Routes the project to empirical quantitative, qualitative, mixed methods, action research, design-based research, literature review, systematic review, meta-analysis, psychometric scale development, learning analytics, policy/comparative analysis, or program evaluation without exposing internal skill names to the user.
metadata:
  short-description: Route education papers to the right research path
---

# Education Paper Type Router

## Goal

Decide the best research path before formal drafting. Do not ask the user to call a skill; present plain-language paper routes.

## Inputs

- Topic and selected direction
- Research question(s)
- Available data/access: class, students, teachers, documents, platform logs, literature only
- Expected output: course paper, thesis, journal article, proposal
- Time and feasibility constraints

## Workflow

1. Infer feasible paper types from the topic, RQs, and data access.
2. Recommend 2-3 paths with reasons.
3. Ask the user to confirm a path or ask the agent to decide.
4. Store the selected path in the research brief as `paper_type`.
5. Route internally:

| Selected Path | Next Skill |
|---|---|
| Quantitative survey/correlational/experimental | `education-quantitative-study-design` |
| Qualitative case/interview/grounded/phenomenology | `education-qualitative-study-design` |
| Mixed methods | `education-mixed-methods-design` |
| Teaching practice/action research | `education-action-research-design` |
| Design-based research | `education-design-based-research` |
| Systematic/scoping review | `education-systematic-review-preparation` |
| Meta-analysis | `education-meta-analysis-preparation` |
| Scale/test development | `education-psychometric-scale-development` |
| Learning analytics/educational data mining | `education-learning-analytics-design` |
| Policy/comparative education | `education-policy-comparative-analysis` |
| Program/curriculum/platform evaluation | `education-program-evaluation` |

## User-Facing Prompt Pattern

```text
现在选题和研究问题已经初步明确。接下来需要确定论文路线，因为不同路线后面的材料、方法和正文结构不一样。

根据你的主题和条件，我建议优先考虑：
A. 实证研究：适合能收集问卷、作文、测验、课堂数据
B. 教学实践/行动研究：适合你有真实教学场景
C. 文献综述/系统综述：适合暂时没有一手数据

你想走哪条？如果你不确定，我可以按“可完成性、创新性、论文规范性”帮你推荐。
```

## Output Format

| Route | Fit | Required Data | Main Deliverables | Difficulty | Recommendation |
|---|---|---|---|---|---|

End with one plain-language decision question.

## Quality Rules

- Do not begin formal writing before the paper path is confirmed.
- Do not expose internal skill names in normal user-facing text.
- Prefer a feasible thesis route over a flashy but impossible route.
