---
name: paper-to-xhs
category: 内容创作
subject: 跨学科
kind: 内容创作
description: Convert an academic paper, PDF, DOI, arXiv page, or publisher link into a Chinese Xiaohongshu paper note in the user's established voice, including a detailed verification layer, a self-contained sub-1000-character publishable post with functional emoji, topics, and 4–6 screenshot-led portrait images. Use for 论文分享、论文解读、小红书科研笔记、论文做小红书、paper-to-XHS, or when the user sends a paper and asks to “生成笔记/生成吧”.
---

# Paper to Xiaohongshu

Create a precise, natural, technically informative paper-sharing post in plain language.

## Required workflow

1. Read the complete paper. For PDFs, follow the PDF skill: extract text, render relevant pages, and inspect figures visually.
2. Verify title, authors, venue, year, DOI, URL, and license from the paper or an authoritative index.
3. Build an evidence map: motivation, system/method, evaluation, main claim, limitations, and any missing validation.
4. Read [references/voice-and-format.md](references/voice-and-format.md) before drafting text.
5. Draft two clearly separated text layers: a source-grounded `核对版解读` for content verification and a compact `小红书发布版` using the fixed structure below. Only the publishable layer is intended for direct posting.
6. Select 2–3 original paper visuals: homepage, overview/teaser, method/system figure, result/case figure, or limitations excerpt.
7. Create 4–6 portrait images using [assets/ocean-fruit-background.png](assets/ocean-fruit-background.png) as the default background. Keep paper screenshots dominant.
8. Render and visually inspect every final image. Fix clipping, tiny text, broken mixed-language wrapping, misleading crops, and missing attribution.
9. Save the Markdown note, images, and a ZIP of the images in one paper-named folder.

## Text output contract

### Two-layer delivery

- `核对版解读`: preserve the evidence map, technical details, numerical results, and caveats needed to verify the reading. It may exceed the platform limit, but must not be mixed into the publishable copy.
- `小红书发布版`: write a self-contained post that can be copied directly. Count all visible text from title through topic tags and keep it at **650–900 characters, with a hard maximum of 950 characters** to leave platform headroom below 1000.
- Treat brevity as removal of repetition and decorative phrasing. Do not shorten by removing the causal chain, implementation details needed to understand the method, the meaning of the main result, or the evidence boundary.
- Save both layers in the Markdown note under explicit headings. Put `小红书发布版` first, followed by `核对版解读` or `事实核查`.

Use this order in `小红书发布版` unless the paper lacks a section:

1. Title: `会议/期刊｜一句准确的问题或核心机制`
2. One-paragraph summary without a heading.
3. `🧩 动机`
4. `⚙️ 系统工作流程` or `⚙️ 研究方法`, using a compact numbered list when procedural.
5. `🧪 实验`
6. `💡 idea启发`
7. `🪞 反思`
8. Topic tags on one final line.

Use 5–8 purposeful emoji in total, primarily as section markers or to distinguish mechanism, evidence, insight, and limitation. Do not insert emoji inside technical terms, numerical results, citations, or every sentence.

When the first draft is too long, compress in this order: remove repeated motivation; retain only 3–5 method steps; keep only the evaluation numbers needed to establish scale and the main result; reduce `idea启发` to one concrete interpretation; preserve at least one evidence limitation. Never solve the limit by deleting the technical mechanism or the evidence boundary.

Prefer complete compact paragraphs. Preserve useful English terms such as Planning LLM, Executing LLM, pilot cases, workflow, and SOP only when they improve precision; otherwise translate them to concise Chinese.

Open by stating what the paper studies, how it studies it, and the central finding. Do not open with a rhetorical contrast such as `不是……而是……`; avoid that construction throughout unless a literal experimental distinction cannot be stated more directly.

Do not use metaphors, philosophical abstractions, or slogans in place of technical explanation. Explain named variables, update rules, experimental conditions, and result direction in concrete language. Do not add a generic lifestyle hook, rhetorical question, decorative emoji chain, or “颠覆认知/必看/封神” language. Do not force a call to action.

## Evidence rules

- Separate what the paper proposes, demonstrates, measures, and proves.
- Name the model/version, sample, datasets, and evaluation type when available.
- Call demonstrations `cases`, `pilot cases`, or `qualitative examples`; do not call them controlled experiments.
- Do not infer superiority without an appropriate comparison.
- State missing user studies, baselines, statistical tests, or quantitative metrics in `反思` when material.
- Distinguish author-stated limitations from the writer's own interpretation.
- Use paper screenshots only when the license or quotation context permits; preserve figure labels and cite author, year, and Figure/Table number.

## Visual output contract

- Canvas: 1242 × 1660 px, 3:4 portrait.
- Default mode: conclusion-first. Page 1 directly summarizes the core idea and includes an original figure crop.
- Alternative: paper-homepage-first when the title/homepage already communicates the value.
- Pages 2–5/6: homepage, framework/method, core evidence/case, and limitations/reflection.
- For technical method papers, do not rely on a screenshot plus a one-sentence callout. Include at least one mechanism page with 3–5 concrete implementation steps or notation mappings, one evidence page explaining how the figure supports the claim, and one trade-off page separating advantages, prerequisites, and costs. An analogy may introduce the method but must not replace the technical account.
- Keep image copy compact: title no more than 18 Chinese characters when possible; subtitle no more than 30; callout no more than 55; each detail item no more than 32 and no more than four items per page. Put extended explanations in the Markdown `核对版解读`, not on the card.
- Use the ocean-fruit background only as atmosphere. Cover most of its center with readable paper or cream cards; keep the whale, citrus, waves, and starfish at the edges.
- Original screenshots should occupy at least 60% of evidence pages.
- Add no more than three Chinese annotations per screenshot.
- Keep original axes, legends, error bars, conditions, authorship, and watermarks intact.
- Footer format: `图源：Author et al. (Year), Figure X · License`.
- Use dark teal text, pale aqua cards, muted coral only for warnings, and minimal branding.

Use `scripts/compose_post.py --config <json>` for standard screenshot-led pages. It expects rendered page PNGs and supports `hero`, `paper`, `evidence`, `technical`, and `limits` layouts. Use `technical` with a `details` list when a method needs step-by-step explanation beneath the source crop.

## Final QA

- Confirm the written title matches the paper and venue.
- Confirm every numerical or evaluative statement against the paper.
- Confirm limitations are visible in both the note and final image set.
- Count the complete `小红书发布版`, including title, section labels, emoji, and topic tags. Revise if it exceeds 950 visible characters; target 650–900.
- Confirm the publishable copy uses 5–8 functional emoji and remains readable without them.
- Confirm all images are 1242 × 1660 and readable at phone size.
- Deliver the Markdown note, ZIP, and a preview of page 1.
