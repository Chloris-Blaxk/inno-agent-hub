---
name: education-literature-map
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use when creating education literature maps, bibliometric analyses, keyword co-occurrence maps, co-citation maps, research trend summaries, author/institution networks, and topic evolution views using VOSviewer, bibliometrix/Biblioshiny, OpenAlex, Semantic Scholar, or exported citation files.
metadata:
  short-description: Build literature maps and bibliometric views for education topics
---

# Education Literature Map

## Goal

Create a structured map of a research field to support topic selection, literature review, theory matching, and gap identification.

## Inputs

- Topic/search query
- Time range
- Source preference: OpenAlex, Scopus, Web of Science, ERIC, CNKI, Semantic Scholar
- Desired map: keyword co-occurrence, co-citation, bibliographic coupling, author network, trend timeline
- Exported BibTeX/CSV/RIS if available

## Workflow

1. Define search string and inclusion range.
2. Retrieve or import literature metadata.
3. Deduplicate records.
4. Create maps:
   - keyword co-occurrence
   - co-citation clusters
   - bibliographic coupling
   - highly cited papers
   - recent burst/emerging topics
5. Interpret clusters for education writing.
6. Output field structure, dominant themes, emerging gaps, and seed references.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### VOSviewer

Download:

```text
https://www.vosviewer.com/download
```

Use for:

- co-authorship
- co-occurrence
- citation
- bibliographic coupling
- co-citation

Typical flow:

1. Export records from Scopus/Web of Science/OpenAlex as CSV/BibTeX.
2. Open VOSviewer.
3. Create map based on bibliographic data.
4. Choose unit of analysis.
5. Export cluster/table/image.

### bibliometrix / Biblioshiny

Install:

```r
install.packages("bibliometrix")
library(bibliometrix)
bibliometrix::biblioshiny()
```

Download/help:

```text
https://www.bibliometrix.org/download/
```

Use Biblioshiny for no-code analysis:

- sources
- authors
- documents
- conceptual structure
- intellectual structure
- social structure

### OpenAlex API

```bash
curl "https://api.openalex.org/works?search=AI%20feedback%20education&filter=from_publication_date:2020-01-01,to_publication_date:2026-12-31&per-page=200&mailto=YOUR_EMAIL" -o openalex.json
```

Group by publication year:

```bash
curl "https://api.openalex.org/works?filter=default.search:AI%20feedback%20education&group_by=publication_year&mailto=YOUR_EMAIL"
```

Group by OpenAlex topic:

```bash
curl "https://api.openalex.org/works?filter=default.search:AI%20feedback%20education&group_by=topics.id&mailto=YOUR_EMAIL"
```

## Output Format

Return:

| Cluster | Representative Keywords | Core Papers | Main Theory/Method | Time Trend | Research Gap | Writing Use |
|---|---|---|---|---|---|---|

Then include:

- Search strategy
- Dataset size and date
- Top journals/authors if available
- 3-5 literature review section headings
- Suggested figure/table for the paper

## Quality Rules

- Always record search date, database, query, filters, and deduplication logic.
- Do not overinterpret clusters without checking representative papers.
- For education papers, translate clusters into substantive themes, not only tool-generated labels.
