# Dialogue style

## Roles

- **小鲸 / host:** A careful beginner. Ask one concrete question at a time, restate an understanding when useful, and challenge causal overclaiming.
- **小柚 / explainer:** A patient researcher. Answer directly, define symbols in ordinary language, then explain the implementation and evidence boundary.

## Default structure

1. State the paper, question, method, and central result within the first three turns.
2. Explain why the question matters without a long literature-history preface.
3. Define the model or study objects before describing results.
4. Walk through the actual update, training, sampling, or experimental procedure.
5. Report the strongest result with its setting and magnitude.
6. Explain limitations, alternative explanations, and what remains unproven.
7. End with one concrete takeaway for research or practice.

## Speech rules

- Target 45–90 Chinese characters per turn; split anything that needs two breaths.
- Prefer “这里的 ψ 是所有人两两一致度的方差” to a slogan or analogy.
- Use a brief example only when it resolves a specific technical obstacle.
- Give the opening a brief co-host invitation, for example “今天和我们一起看一篇 PNAS 论文吧”, followed by a short response such as “嗯，对”.
- Allow one light acknowledgement or transition every two to four turns, such as “嗯，对”“明白了”“等一下”“那这里”. Use it to connect ideas, not to pad runtime.
- Keep conversational texture below roughly 10% of the spoken text. Do not add fake laughter, exaggerated interruptions, mutual praise, or repeated greetings.
- Avoid “颠覆”“炸裂”“答案藏在”等 promotional wording.
- Avoid “不是……而是……” as an opening or recurring rhetorical frame.
- Read equations by meaning unless the exact notation is necessary.
- Estimate 260–300 Chinese characters per minute for local TTS.

## Revision passes

1. **Accuracy:** check every claim against the evidence sheet.
2. **Comprehension:** make every question answerable from the next turn.
3. **Speech:** shorten clauses, mark pronunciation, and remove tongue-twisters.
4. **Rhythm:** alternate speakers for conceptual reasons, not mechanically.
5. **Compression:** remove repeated summaries while retaining method, result, and limitation detail.
