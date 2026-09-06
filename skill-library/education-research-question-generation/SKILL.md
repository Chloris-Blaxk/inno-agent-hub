---
name: education-research-question-generation
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use when generating, refining, comparing, or validating education research questions and hypotheses. Supports qualitative, quantitative, mixed-methods, intervention, design-based research, survey, classroom observation, and systematic review questions using Elicit-style evidence search, Semantic Scholar/OpenAlex, and LLM reasoning.
metadata:
  short-description: Generate and validate education research questions
---

# Education Research Question Generation

## Goal

Produce focused, answerable, evidence-aware research questions for education papers.

## Inputs

- Topic or selected direction
- Study type: qualitative, quantitative, mixed methods, review, intervention, design-based research
- Target population and context
- Available data or planned data
- Expected paper level: course paper, master's thesis, PhD dissertation, journal article

## Question Frameworks

Choose the framework that fits:

- Quantitative: PICOT, PICO, PECO, variable relationship model
- Qualitative: phenomenon + participants + context + meaning/process
- Mixed methods: quantitative relationship + qualitative explanation
- Intervention: population + intervention + comparison + outcome + time
- Review: population/context + concept/intervention + evidence scope

## Workflow

1. Classify the topic by method type and likely evidence base.
2. Generate 8-12 candidate research questions:
   - 3 descriptive/exploratory
   - 3 explanatory/relationship
   - 2 intervention/effectiveness if applicable
   - 2 qualitative mechanism/process questions if applicable
3. Search scholarly databases for each candidate or keyword cluster.
4. Score questions on:
   - clarity
   - answerability
   - novelty
   - data feasibility
   - theoretical contribution
   - method fit
5. Rewrite top questions into publishable form.
6. Generate aligned hypotheses or subquestions.

## Tool Calls

### Elicit

Use Elicit manually or through API if available. Best for evidence-grounded research reports and extraction tables.

- Web: https://elicit.com/
- Query pattern: "What is known about [topic] in [population/context]?"
- Extraction fields: `research question`, `population`, `intervention`, `variables`, `outcomes`, `method`, `limitations`.

### Semantic Scholar Search

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=student%20engagement%20AI%20feedback%20education&limit=20&fields=title,year,abstract,citationCount,authors,venue,fieldsOfStudy"
```

### Semantic Scholar Recommendations

Use after selecting a seed paper:

```bash
curl "https://api.semanticscholar.org/recommendations/v1/papers/forpaper/PAPER_ID?fields=title,year,abstract,citationCount,authors"
```

### OpenAlex Query

```bash
curl "https://api.openalex.org/works?search=student%20engagement%20AI%20feedback%20education&filter=from_publication_date:2020-01-01&sort=cited_by_count:desc&per-page=20&mailto=YOUR_EMAIL"
```

## Output Format

Return:

| Candidate RQ | Type | Variables/Phenomenon | Population/Context | Evidence Base | Feasibility | Risk | Improved Version |
|---|---|---|---|---|---|---|---|

Then provide:

- Recommended main research question
- 2-4 subquestions
- Optional hypotheses
- Required data
- Suggested analysis method
- Why this RQ is stronger than alternatives

## Quality Rules

- Avoid questions that are too broad, e.g. "How does AI affect education?"
- Use measurable verbs for quantitative questions: predict, mediate, moderate, influence, compare.
- Use meaning/process verbs for qualitative questions: experience, perceive, negotiate, construct, adapt.
- Ensure each question implies a feasible method.
