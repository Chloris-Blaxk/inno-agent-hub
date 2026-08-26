# Voice and format reference

## Default voice

- Sound like a researcher sharing reading notes, not a content marketer.
- Be direct, complete, and calm.
- Prefer plain factual statements over rhetorical contrast, metaphor, or philosophical framing.
- Explain technical mechanisms with their proper names, then translate their role into plain Chinese.
- Keep personal interpretation in `idea启发`; keep methodological caution in `反思`.
- Use compact labels such as `🧩 动机`, `⚙️ 系统工作流程`, `🧪 实验`, `💡 idea启发`, and `🪞 反思` without Markdown-style decorative headings in the publishable body.
- Use 5–8 emoji as stable reading landmarks. Avoid emoji chains, excessive rhetorical questions, exclamation marks, one-sentence suspense, and artificial drama.
- Keep the complete publishable copy, including title and tags, at 650–900 visible characters and never above 950. Keep longer technical verification in a separate `核对版解读`.

## Title pattern

Preferred:

`NAACL｜如何将大模型工作流变成可交互过程`

Pattern:

`会议/期刊简称｜如何…… / 为什么…… / 一种……方法 / 把……变成……`

The title should identify the academic context and state the actual research problem. It does not need a viral hook.

## Paragraph pattern

### Summary

Start with `这篇论文……` and explain the research question, central mechanism, and main finding in 1–2 compact sentences. Do not use `不是……而是……` as an opening frame.

### 动机

Use 1–2 sentences: state the conventional process, its main failure, and what the paper makes manageable.

### 系统工作流程 / 研究方法

Use 3–5 numbered steps when the method is sequential. Preserve named components and their order, but move secondary implementation details to `核对版解读`.

### 实验

State the evaluation type, sample or dataset scale, and the most decision-relevant result. Include model/version only when it affects interpretation. Use `pilot cases` when that is what the paper reports.

### idea启发

Use one concrete methodological or application implication. State what a researcher could measure, manipulate, compare, or design differently. Avoid broad philosophical claims and decorative analogies.

### 反思

Use 1–3 sentences. Name the evidence level, state what cannot be concluded, and retain the most material limitation.

State limitations directly: identify the sample, comparison, metric, or validation that is missing, then specify which conclusion therefore remains unsupported.

## Compression rule

- Shorten by removing repeated motivation, duplicated conclusions, adjectives, and background that the reader does not need.
- Preserve enough implementation detail to reconstruct the causal or computational sequence.
- Preserve the experimental conditions behind each reported number and explain what the number measures.
- Preserve at least one author-stated limitation and one interpretation boundary when both are material.
- If 650–900 characters cannot hold every secondary detail, move those details to `核对版解读`; never replace them with an abstract slogan.

## Topic style

Use one final line with 5–8 directly relevant tags so the tags do not consume the text budget. Preserve the user's recurring tags when appropriate:

`#howto入门codex #科研 #人机交互 #PhD #大模型 #howto用AI抢救一切`

Add venue and topic tags only when relevant. Do not invent trending tags that do not match the paper.
