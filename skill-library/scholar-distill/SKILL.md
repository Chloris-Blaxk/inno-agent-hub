---
name: scholar-distill
category: 研究检索
subject: 跨学科
kind: 教研科研
description: Use when distilling a scholar, professor, research group, or intellectual lineage into an evidence-grounded research assistant for academic background mapping, topic selection, research-question generation, Survey or literature-review outlining, theory/method choice, and paper positioning. Trigger when the user mentions 学者蒸馏, 人物蒸馏 for academic research, scholar persona, academic style distillation, research background, 选题, Survey, literature review, professor profile, AMiner/Google Scholar/Semantic Scholar/OpenAlex profile, or wants to learn from a scholar's publications without impersonating them.
---

# Scholar Distill

## Goal

Build an evidence-grounded "scholar lens" from public academic traces, then use that lens to help the user understand a field, choose researchable topics, frame a Survey, and position a paper.

Do not impersonate the scholar, claim private access, fabricate beliefs, or write as if the scholar personally endorsed the output. Phrase outputs as "inferred from public works" and keep citations or evidence notes attached to claims.

## Inputs

Collect only missing essentials:

- Scholar identity: name, institution, profile URL, OR 3-5 seed papers.
- User goal: background梳理, 选题, Survey, proposal, paper positioning, theory/method advice.
- Field boundary: discipline, population/context, time range, language/database preference.
- Output depth: quick sketch, structured memo, Survey outline, candidate topics, or writing-ready section.
- Constraints: available data, target journal/course/thesis type, region, methods the user can actually use.

If identity is ambiguous, ask for a profile URL or affiliation before searching.

## Evidence Workflow

1. Gather public evidence:
   - Scholar profile: university page, AMiner, Google Scholar, Semantic Scholar, OpenAlex, DBLP, ORCID, lab page.
   - Publication evidence: titles, abstracts, venues, years, citation signals, coauthors, grants/projects when public.
   - Field evidence: recent/highly cited papers around the scholar's core topics.
2. Separate evidence types:
   - Direct evidence: paper titles, abstracts, keywords, methods, datasets, venues.
   - Inference: recurring problem choices, theoretical preferences, methodological habits, collaboration patterns.
   - User-facing recommendation: how those patterns can guide the user's topic or Survey.
3. Build a scholar research map:
   - Core problems: what repeated research problem the scholar returns to.
   - Concept vocabulary: constructs, keywords, datasets, populations, technologies, theories.
   - Method repertoire: empirical designs, modeling, qualitative approaches, system building, evaluation metrics.
   - Temporal evolution: early, middle, recent themes.
   - Collaboration ecology: recurring coauthors, labs, regions, venues, interdisciplinary bridges.
4. Convert the map into useful research moves:
   - Background framing: how to narrate why the field matters.
   - Topic generator: adjacent, underexplored, localized, methodological, or application-transfer topics.
   - Survey scaffold: field taxonomy, historical arc, methods comparison, open challenges.
   - Positioning: what gap the user's work can credibly occupy.

## Scholar Lens Template

Use this compact template before giving recommendations:

| Dimension | Evidence | Distilled Pattern | How To Use It |
|---|---|---|---|
| Core research problem | Papers/profiles | Recurring problem logic | Background paragraph or topic boundary |
| Key concepts | Keywords/abstracts | Vocabulary and constructs | Search terms and Survey taxonomy |
| Methods | Methods/datasets/tasks | Preferred ways of producing evidence | Feasible study design options |
| Field position | Venues/citations/coauthors | Intellectual neighborhood | Related work positioning |
| Evolution | Year-by-year clusters | Newer shifts and stable commitments | Emerging topic choices |
| Limits | Missing contexts/methods | Blind spots or risks | Research gap candidates |

## Topic Selection Output

When the user asks for 选题, return 5-8 candidate directions:

| Direction | Inspired Scholar Pattern | Research Gap | Possible RQ | Data/Corpus | Method | Novelty Signal | Feasibility Risk |
|---|---|---|---|---|---|---|---|

Then recommend the best 2-3 directions using:

- Fit with the user's constraints.
- Evidence that the topic is active but not saturated.
- Availability of data, instruments, or cases.
- Clear contribution type: theory extension, method improvement, context transfer, dataset/resource, empirical validation, or critical synthesis.

## Survey Output

When the user asks for Survey or literature review, produce:

1. Review scope: field, time range, inclusion/exclusion criteria.
2. Search strategy: databases, queries, seed papers, citation chasing plan.
3. Taxonomy:
   - problem dimension
   - theory/concept dimension
   - method/dataset dimension
   - application/context dimension
   - evaluation/outcome dimension
4. Draft outline:
   - Background and motivation
   - Historical development
   - Core themes/clusters
   - Methodological comparison
   - Representative scholars/labs
   - Open problems and future directions
5. Evidence table with 10-20 seed papers if data is available.

## Research Background Output

When the user asks for 背景梳理, write in layers:

1. Macro layer: why this field matters socially, scientifically, or educationally.
2. Field layer: what the research community has already established.
3. Scholar layer: how the target scholar's work reframes or advances the problem.
4. Gap layer: what remains unresolved.
5. User layer: how the user's intended project can enter the conversation.

Keep background paragraphs evidence-linked; avoid grand claims without source support.

## Search Guidance

Use scholarly search when current or accurate publication data matters. Prefer primary or academic sources:

- OpenAlex for broad metadata and topic grouping.
- Semantic Scholar for abstracts, citation counts, influential citations, and recommendations.
- Google Scholar or AMiner pages for identity disambiguation and profile-level overview.
- University/lab pages for projects, teaching areas, and biography.
- DBLP for computer science publication trails.

Suggested OpenAlex query:

```bash
curl "https://api.openalex.org/works?search=SCHOLAR_OR_TOPIC&filter=from_publication_date:2018-01-01&sort=cited_by_count:desc&per-page=25&mailto=YOUR_EMAIL"
```

Suggested Semantic Scholar query:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=SCHOLAR_OR_TOPIC&limit=20&fields=title,year,abstract,citationCount,authors,venue,fieldsOfStudy"
```

## Safety And Quality Rules

- Distill public scholarly patterns, not private personality or hidden intentions.
- Never state "the scholar would say" unless quoting a public source. Prefer "a lens inspired by the scholar's public work would emphasize..."
- Distinguish direct evidence from inference and recommendation.
- Do not label a gap as novel until recent literature search supports it.
- Avoid copying the scholar's prose style; emulate analytical moves, not personal voice.
- If the user wants a named scholar's "persona", reframe to an academic lens: research priorities, questions, methods, and critique patterns.
- For living people, keep the result respectful, bounded, and citation-aware.

## Final Response Shape

For most tasks, answer with:

1. Evidence base checked or still needed.
2. Scholar lens summary.
3. Research map or topic/Survey table.
4. Recommended next move.
5. Caveats: uncertain identity, insufficient sources, or claims needing verification.
