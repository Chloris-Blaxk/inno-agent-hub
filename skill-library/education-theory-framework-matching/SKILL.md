---
name: education-theory-framework-matching
category: 研究检索
description: Use when matching an education research topic, question, or variable model to appropriate theories, conceptual frameworks, and prior research traditions. Supports ResearchRabbit/Litmaps/Connected Papers-style citation exploration, OpenAlex/Semantic Scholar search, and theory-fit scoring.
metadata:
  short-description: Match education topics to theories and frameworks
---

# Education Theory Framework Matching

## Goal

Find and justify suitable theoretical frameworks for an education research paper.

## Inputs

- Topic or research question
- Key constructs/variables
- Population/context
- Method type
- Seed papers if available

## Workflow

1. Identify core constructs and the type of explanation needed:
   - motivation
   - learning process
   - technology acceptance
   - social interaction
   - teacher professional development
   - assessment/feedback
   - equity/inclusion
   - institutional change
2. Generate candidate theories.
3. Use citation-network tools to find seed papers and theory traditions.
4. Score candidate theories:
   - construct fit
   - explanatory power
   - empirical precedent in education
   - compatibility with method
   - novelty/contribution
5. Recommend 1 primary framework and 1-2 secondary lenses.

## Common Education Theory Families

Use as candidates, then verify with literature:

- Self-Determination Theory
- Social Cognitive Theory
- Constructivism / Social Constructivism
- Communities of Practice
- Activity Theory
- Technology Acceptance Model / UTAUT
- TPACK
- Cognitive Load Theory
- Expectancy-Value Theory
- Achievement Goal Theory
- Feedback Intervention Theory
- Formative Assessment Theory
- Universal Design for Learning
- Funds of Knowledge
- Ecological Systems Theory
- Critical Pedagogy
- Culturally Responsive Pedagogy

## Tool Calls

### ResearchRabbit

Use manually for seed-paper expansion and author/topic exploration.

```text
https://www.researchrabbit.ai/
```

Recommended use:

1. Add 3-5 seed papers.
2. Explore similar works, earlier works, later works, and authors.
3. Export candidate theory papers to Zotero.

### Litmaps

Use for visual literature maps and monitoring.

```text
https://www.litmaps.com/
```

### Connected Papers

Use for graphing a key seed paper.

```text
https://www.connectedpapers.com/
```

### Semantic Scholar Search

Search theory + construct + education:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=self-determination%20theory%20student%20engagement%20online%20learning&limit=10&fields=title,year,abstract,citationCount,authors"
```

### OpenAlex

```bash
curl "https://api.openalex.org/works?search=self-determination%20theory%20student%20engagement%20education&sort=cited_by_count:desc&per-page=10&mailto=YOUR_EMAIL"
```

## Output Format

Return:

| Theory / Framework | Fit Constructs | What It Explains | Education Evidence | Method Fit | Limitations | Recommendation |
|---|---|---|---|---|---|---|

Then include:

- Recommended theoretical framework
- Short justification paragraph for paper introduction
- How the theory maps to variables/research questions
- 5-10 seed references to verify

## Quality Rules

- Do not match theory by keyword alone; match by explanatory function.
- Distinguish conceptual framework, theoretical framework, and analytical framework.
- Prefer theories already used in comparable education contexts unless the paper explicitly aims for theoretical innovation.
