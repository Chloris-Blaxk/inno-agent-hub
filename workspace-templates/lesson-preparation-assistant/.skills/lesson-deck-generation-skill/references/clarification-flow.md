# 需求澄清流程

本流程借鉴“动手前先澄清”原则，但面向教师备课做最小必要询问。目标是减少返工，不是把教师拦在表单前。

## 触发规则

当用户只给出课题或信息不足时，先判断缺口等级：

| 等级 | 情况 | 处理方式 |
|---|---|---|
| 必问 | 缺少 `subject`、`grade` 或 `topic` | 先问，不生成 |
| 建议问 | 缺少教材版本、单元、课时、课型、学情 | 一次性问 4-7 个短问题；若用户希望立即生成，则用保守默认并写入 assumptions |
| 可默认 | 缺少风格、时长、输出格式 | 直接默认：40 分钟、自动风格、JSON+MD+HTML，PPTX 按需导出 |

## 7 问清单

1. 学科和年级是什么？
2. 课题、教材版本、单元和课时位置是什么？
3. 这节课是什么课型：新授、复习、练习讲评、探究、实验/演示？
4. 课堂时长和预计页数有要求吗？
5. 学生已经学过什么？最常见困难是什么？
6. 需要哪些输出：HTML 预览、教师逐字稿、可编辑 PPTX、配图提示词？
7. 有没有硬约束：学校模板、禁用素材、必须包含的例题/实验/互动？

## 询问话术

信息不足时只问一次，格式保持轻：

> 我可以先按常见 40 分钟课生成，也可以先补齐几个关键信息以减少返工：学科/年级、教材版本与课时、课型、学生常见困难、是否需要 PPTX。你希望我先问清楚，还是先出一版可改草稿？

若用户选择“先出草稿”，必须：

- `curriculumContext.assumptions` 写明未确认项。
- `designPlan` 的 `reason` 避免宣称“严格对应某教材/课标”。
- `qualityReport.assumptions` 保留同样假设。

## 默认策略

- `lessonType`：未给时用 `new_concept`。
- `durationMin`：未给时用 40。
- `textbookVersion` / `unit` / `period`：未给时写 `待确认`。
- `studentProfile.priorKnowledge`：从课题常见前置知识推断，并标注假设。
- `studentProfile.commonDifficulties`：优先查 `subject-knowledge-packs.json`，未命中时使用 generic 错因。
- `stylePreset`：数学/复习优先 `chalk-grid`，理科优先 `science-lab`，人文优先 `humanities-ink`，其他用 `daylight`。
