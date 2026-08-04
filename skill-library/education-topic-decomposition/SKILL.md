---
name: education-topic-decomposition
category: 研究检索
description: Use when decomposing a broad education research topic into focused subtopics, searchable concepts, research gaps, candidate study designs, and writing directions. Best for thesis/article topic selection, narrowing a vague idea, or turning an education policy/practice issue into researchable tracks using STORM-style multi-perspective questioning plus OpenAlex/Semantic Scholar evidence search.
metadata:
  short-description: Decompose broad education topics into researchable directions
---

# Education Topic Decomposition

## Goal

Turn a broad education topic into 3-8 researchable directions with evidence-backed subtopics, keywords, possible populations, methods, theories, and gaps.

## Inputs

Ask for missing essentials only if absent:

- Broad topic or problem, e.g. "AI feedback in middle-school writing"
- Education level/context, e.g. K-12, higher education, vocational education
- Target paper type, e.g. empirical article, thesis, review, intervention study
- Region/language preference, if relevant
- Constraints, e.g. available data, time, sample access

## Core Workflow

1. Restate the topic as a research landscape.
2. Generate 5-8 perspectives using STORM-style questioning:
   - Learner outcome perspective
   - Teacher practice perspective
   - Technology/tool perspective
   - Equity/inclusion perspective
   - Assessment perspective
   - Policy/institution perspective
   - Methodological perspective
3. For each perspective, generate search keywords in English and Chinese if useful.
4. Search OpenAlex or Semantic Scholar for recent and highly cited work.
5. Identify clusters: mature topics, emerging topics, underexplored intersections, feasible empirical directions.
6. Output a topic-decomposition table and recommend 2-3 best directions.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### OpenAlex Works Search

Use when no API key is available or broad topic exploration is enough.

```bash
curl "https://api.openalex.org/works?search=AI%20feedback%20writing%20education&filter=from_publication_date:2021-01-01&per-page=10&mailto=YOUR_EMAIL"
```

Useful fields:

- `display_name`
- `publication_year`
- `cited_by_count`
- `concepts`
- `topics`
- `abstract_inverted_index`
- `referenced_works`

### Semantic Scholar Search

Use when you need abstracts, citation counts, influential citations, and recommendations.

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=AI%20feedback%20writing%20education&limit=10&fields=title,year,abstract,citationCount,referenceCount,authors,fieldsOfStudy"
```

If an API key exists:

```bash
curl -H "x-api-key: $S2_API_KEY" "https://api.semanticscholar.org/graph/v1/paper/search?query=AI%20feedback%20writing%20education&limit=10&fields=title,year,abstract,citationCount,authors"
```

### STORM

Use when the user wants a deep topic outline or multi-perspective prewriting.

Install:

```bash
git clone https://github.com/stanford-oval/storm.git
cd storm
pip install -r requirements.txt
```

Use STORM as an inspiration engine: generate perspectives, questions, and a structured outline, then verify claims with scholarly search.

## Output Format

Return:

1. Topic landscape summary
2. Decomposition table:

| Direction | Core Problem | Key Concepts | Search Terms | Possible Research Questions | Feasible Data | Suitable Methods | Evidence Signals | Risk |
|---|---|---|---|---|---|---|---|---|

3. Top 2-3 recommended directions with reasons:
   - novelty
   - feasibility
   - available literature
   - fit with education research norms

## Quality Rules

- Do not present a direction as novel unless search evidence supports that it is underexplored.
- Separate "interesting topic" from "researchable topic".
- Prefer directions where variables, population, method, and data source can be named.
- For education papers, always map the topic to learner, teacher, curriculum, assessment, institution, or technology context.
