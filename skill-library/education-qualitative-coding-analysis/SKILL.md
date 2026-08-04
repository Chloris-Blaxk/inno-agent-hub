---
name: education-qualitative-coding-analysis
category: 研究检索
description: Use when analyzing qualitative education data such as interviews, focus groups, classroom observations, reflective journals, student work, policy documents, teaching artifacts, AI feedback texts, and open-ended survey responses. Covers open coding, axial coding, selective coding, thematic analysis, grounded theory, content analysis, discourse-oriented coding, memo writing, evidence extraction, codebook development, and qualitative findings structure. This is a second-layer execution skill for qualitative, mixed-methods, action research, DBR, policy/comparative analysis, program evaluation, and AI-assisted education research.
metadata:
  short-description: Execute qualitative coding and thematic analysis for education data
---

# Education Qualitative Coding Analysis

## Goal

Turn qualitative education data into a transparent coding process, evidence-backed themes, and a findings section.

## Use After

Use after data sources and qualitative design are defined:

- `education-qualitative-study-design`
- `education-mixed-methods-design`
- `education-action-research-design`
- `education-design-based-research`
- `education-policy-comparative-analysis`
- `education-program-evaluation`

Do not expose the skill name to users. Present it as "质性材料编码分析" or "访谈/观察/文本分析".

## Inputs

- Research questions
- Data type: interview, focus group, observation, document, policy, student work, AI feedback text, open-ended survey
- Corpus description and file list
- Chosen qualitative tradition if any: thematic analysis, grounded theory, case study, content analysis, discourse analysis
- Whether multiple coders are involved
- Language and anonymization requirements

## Workflow

1. Prepare corpus:
   - transcribe audio/video
   - clean obvious transcription errors
   - anonymize names, schools, locations, accounts
   - assign document and participant IDs
2. Choose analysis approach:
   - thematic analysis for patterns of meaning
   - grounded theory for model/theory building
   - content analysis for categories/frequency
   - case analysis for bounded cases
   - discourse-oriented analysis for language/interaction patterns
3. Create initial coding unit:
   - sentence
   - paragraph
   - speaking turn
   - classroom episode
   - document section
   - artifact segment
4. First-cycle coding:
   - open coding
   - descriptive coding
   - in vivo coding
   - process coding
   - values/emotion coding where relevant
5. Build codebook:
   - code name
   - definition
   - inclusion/exclusion rules
   - example quote
6. Second-cycle coding:
   - axial coding
   - pattern coding
   - focused coding
   - category aggregation
7. Theme/model development:
   - theme names
   - theme definitions
   - relationships among themes
   - negative cases/contradictions
8. Write analytic memos throughout.
9. Build evidence table linking claims to excerpts.
10. Draft findings structure and discussion implications.

## Tool Calls

Dependency policy: inspect the current environment first. Do not install packages, clone repositories, or change the user's environment without explicit approval. Prefer a project-local Python virtual environment or R library, and record package versions used for reproducibility.

### Transcription

```text
Whisper: https://github.com/openai/whisper
Otter: https://otter.ai/
讯飞听见: https://www.iflyrec.com/
```

### Qualitative Coding Software

```text
NVivo: https://lumivero.com/products/nvivo/
MAXQDA: https://www.maxqda.com/
ATLAS.ti: https://atlasti.com/
Dedoose: https://www.dedoose.com/
Taguette: https://www.taguette.org/
QualCoder: https://github.com/ccbogel/QualCoder
```

### Lightweight Text Analysis

R:

```r
install.packages(c("tidyverse", "tidytext", "quanteda", "readtext"))
```

Python:

```bash
pip install pandas nltk spacy scikit-learn
```

Use NLP only as support. Human interpretation remains required for qualitative analysis.

## Output Format

### 1. Corpus Inventory

| Document ID | Data Type | Participant/Source ID | Date | Length | Anonymized | Notes |
|---|---|---|---|---|---|---|

### 2. Coding Plan

| Decision | Choice |
|---|---|
| Analysis approach |  |
| Coding unit |  |
| First-cycle coding |  |
| Second-cycle coding |  |
| Software/tool |  |
| Multiple coders | Yes/No |
| Reliability check | Yes/No/Not applicable |

### 3. Codebook

| Code | Definition | Include When | Exclude When | Example Excerpt | Notes |
|---|---|---|---|---|---|

### 4. Category / Theme Table

| Theme | Related Codes | Meaning | Evidence Count | Representative Excerpts | Negative Cases |
|---|---|---|---|---|---|

### 5. Evidence Table

| Finding Claim | Supporting Excerpt ID | Excerpt Summary | Data Source | Strength | Caveat |
|---|---|---|---|---|---|

### 6. Findings Section Outline

```text
Finding 1: [Theme name]
  - Main claim
  - Representative evidence
  - Variation across participants/cases
  - Negative or boundary case

Finding 2: [Theme name]
...
```

## Approach-Specific Guidance

### Thematic Analysis

Use when the goal is to identify patterns of experience, perception, practice, or meaning.

Steps:

1. Familiarize with data.
2. Generate initial codes.
3. Search for themes.
4. Review themes against data.
5. Define and name themes.
6. Write findings with evidence.

### Grounded Theory

Use when the goal is to build a process model or explanatory theory from data.

Steps:

1. Open coding.
2. Constant comparison.
3. Axial coding.
4. Theoretical sampling if possible.
5. Selective coding.
6. Theoretical saturation judgment.
7. Model construction.

Output model:

```text
Conditions -> Actions/Interactions -> Consequences
```

### Content Analysis

Use when categories and frequencies matter, such as policy texts, textbooks, AI feedback comments, classroom discourse moves, or open-ended survey responses.

Steps:

1. Define coding categories.
2. Define coding unit.
3. Code sample and refine categories.
4. Code full corpus.
5. Count and interpret category patterns.
6. Combine frequency with qualitative examples.

## Quality Rules

- Do not treat AI-generated codes as final findings.
- Every major theme needs multiple pieces of evidence unless it is explicitly a rare/negative case.
- Keep raw excerpt, code, category, and theme traceable.
- Distinguish participant claim from researcher interpretation.
- Include negative cases or contradictions when they matter.
- For classroom data, preserve context: lesson phase, activity, teacher/student role, task.
- For minor students, anonymize names and identifiable writing details.

## User-Facing Closure

End with the next practical decision:

```text
现在可以进入正式编码。你希望我先帮你做一版初始代码本，还是先根据 2-3 份材料做试编码，再修订代码本？
```
