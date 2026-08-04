---
name: education-evidence-check
category: 研究检索
description: Use when checking whether claims, theory choices, research questions, variable relationships, or literature review statements in education papers are supported, contradicted, weakly supported, outdated, or missing citations. Uses Scite-style citation context, Elicit evidence reports, Semantic Scholar citation relationships, and manual source verification.
metadata:
  short-description: Verify evidence and citation strength in education writing
---

# Education Evidence Check

## Goal

Improve paper quality by verifying that important claims are grounded in reliable, recent, and relevant evidence.

## Inputs

- Claim, paragraph, draft section, or citation list
- Target standard: course paper, thesis, journal article, systematic review
- Field/context: education level, region, subject area
- Existing references if available

## Workflow

1. Extract atomic claims from the text.
2. Classify each claim:
   - background claim
   - empirical finding
   - causal claim
   - theory claim
   - method claim
   - policy/practice implication
3. For each high-risk claim, search supporting and contrasting evidence.
4. Check citation quality:
   - relevance
   - recency
   - empirical strength
   - citation context
   - whether later studies support or contradict it
5. Rewrite claims with calibrated strength.
6. Produce a citation-gap list.

## Tool Calls

### Scite

Use for citation context and support/contrast checks.

```text
https://scite.ai/
```

Recommended checks:

- Is the cited paper supported or contradicted?
- Is the citation used for the same claim?
- Are there later reviews or meta-analyses?

### Elicit

Use for evidence reports and structured extraction.

```text
https://elicit.com/
```

Query pattern:

```text
What evidence supports or challenges the claim that [claim] in [education context]?
```

### Semantic Scholar Citation Lookup

Find paper details:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/DOI:10.xxxx/yyyy?fields=title,year,abstract,citationCount,influentialCitationCount,references,citations"
```

Find papers on a claim:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=teacher%20feedback%20student%20writing%20achievement%20meta-analysis&limit=10&fields=title,year,abstract,citationCount,authors,venue"
```

### OpenAlex

```bash
curl "https://api.openalex.org/works?search=teacher%20feedback%20student%20writing%20achievement%20meta-analysis&sort=cited_by_count:desc&per-page=10&mailto=YOUR_EMAIL"
```

## Output Format

Return:

| Claim | Current Citation | Evidence Status | Better Evidence Needed | Suggested Rewrite | Risk |
|---|---|---|---|---|---|

Evidence status:

- Strongly supported
- Moderately supported
- Mixed evidence
- Weak evidence
- Contradicted
- Needs citation
- Overclaimed

## Quality Rules

- Causal language requires causal evidence.
- Prefer systematic reviews, meta-analyses, and recent empirical studies for broad claims.
- Do not cite a paper merely because it is related; verify the specific claim.
- Mark unsupported claims instead of smoothing them over.
- For AI-assisted writing, preserve a clear audit trail of searched sources and citation decisions.
