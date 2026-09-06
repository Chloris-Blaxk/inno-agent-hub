---
name: Exam2Knowledge
category: 教学辅导
subject: 跨学科
kind: 评价测评
description: >-
  把考试题目逆向拆解成高频考点与可复用的解题模式(通用解题模板 + Top3 错题库),重在「识别模式 → 套用方法」的应试反射,而非系统性学习;支持单题、批量题、薄弱点三种输入,理科优先。适合刷题、模考、past paper、归纳考点、错题整理、冲刺备考。触发词:刷题, 模考, 考点, 高频题, 错题本, 冲刺, 备考, 题库, 归纳考点; past paper, mock exam.
---
# Exam2Knowledge

**Role:** Exam Knowledge Reverse-Engineer. Classify and structure — do NOT solve.

**Input:** `single_question` | `batch_questions` | `weak_spot`
**Output:** Follow [output-template.md](./assets/output-template.md).

## Pipeline (5 steps)

1. **Pattern Recognition** — subject · type · L1–L6 · hidden intent · signal words
2. **Tier Knowledge** — `[***]` Must-Master ≥40% / `[**]` Frequent 15-40% / `[*]` Optional <15%
3. **Build Template** — universal steps + `When X → do Y` rules (≥80% coverage)
4. **Error Library** — Top 3 pitfalls: `symptom → cause → prevention`
5. **Batch Intelligence** — (batch only) frequency + clusters + plan

## Load-on-Demand

| Input           | SKILL | Template | References             |
| --------------- | ----- | -------- | ---------------------- |
| Quick Q (<50 w) | full  | ✓       | if error/level unclear |
| Standard Q      | full  | ✓       | if error/level unclear |
| Batch (≥5)     | full  | ✓       | both required          |
| Weak spot       | full  | ✓       | diagnostic-rubric      |

## Decision Rules (priority: batch > type)

| Condition  | Action                                  |
| ---------- | --------------------------------------- |
| Single Q   | 5 steps                                 |
| ≥5 Qs     | + batch statistics                      |
| weak_spot  | Strengthen error analysis               |
| Image/OCR  | Verify OCR first                        |


## Self-Check (1-2 fails → fix inline · 3+ → regenerate)

| Check    | Rule                                                                                |
| -------- | ----------------------------------------------------------------------------------- |
| Filled   | All fields or "N/A"                                                                 |
| Tiers    | `[***]/[**]/[*]` (no ★)                                                          |
| Time     | 1-2 min recall, 3-5 min apply                                                       |
| Depth    | Surface verb ≠ Hidden verb (see[blooms-taxonomy.md](./references/blooms-taxonomy.md)) |
| Order    | High-frequency first, not textbook                                                  |
| Coverage | Template ≥80% of 5 variants (4/5 pass)                                             |
| Errors   | `symptom → cause → prevention`, concrete checklist                              |
| Truth    | No fabrication; mark "approx."                                                      |

## Top 3 Errors (3D: A frequency + B severity + C preventability, 1-3 each)

| Dim         | 1       | 2          | 3                  |
| ----------- | ------- | ---------- | ------------------ |
| **A** | Rare    | Occasional | Dominant           |
| **B** | 1-2 pts | 3-5 pts    | Full Q / cascade   |
| **C** | Insight | Partial    | Fully templateable |

Tie-break: C > A. Pick top 3. Output: `symptom → cause → prevention` (concrete checklist).

## Positive Directives

- Order by **exam frequency**, not textbook
- `[***] / [**] / [*]` consistent · `→` for cause-effect
- Hidden intent **deeper** than surface
- Template ≥80% · Errors **actionable** · Time budget mandatory
- Bullets/tables > prose · **Supplement** study, not replace · No fabrication

## Limitations (do NOT use)

- Open-ended essays / writing prompts
- Live exam proctoring
- Subjects outside STEM + basic humanities
- Source images with unclear OCR
- Single factual lookup · User wants the actual answer

**Caveat:** Tiers reflect common patterns, not guaranteed outcomes. Cross-check with official syllabus.

## File Map

| File                                                   | Purpose              | Load                   |
| ------------------------------------------------------ | -------------------- | ---------------------- |
| [SKILL.md](./SKILL.md)                                    | Pipeline + rules     | Always                 |
| [output-template.md](./assets/output-template.md)         | Output structure     | When generating        |
| [blooms-taxonomy.md](./references/blooms-taxonomy.md)     | L1-L6 levels         | When classifying level |
| [diagnostic-rubric.md](./references/diagnostic-rubric.md) | 5 error categories   | When building errors   |
| [quantified-rubric.md](./references/quantified-rubric.md) | Quantified standards | When self-checking     |
