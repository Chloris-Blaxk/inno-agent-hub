# 质量检查清单

## P0 必须通过

- 根对象包含 `lessonMeta`、`backgroundAnalysis`、`studentAnalysis`、`coreCompetencies`、`objectives`、`teachingFocus`、`teachingDifficulty`、`innovationDesign`、`activityFlow`、`assessmentRubric`、`resources`、`export`、`qualityReport`。
- `lessonMeta.subject`、`lessonMeta.grade`、`lessonMeta.topic`、`lessonMeta.innovationType`、`lessonMeta.durationMin` 非空。
- `lessonMeta.innovationType` 必须为 `PBL`、`interdisciplinary` 或 `ai_integrated`。
- `activityFlow[].durationMin` 总和等于请求的 `durationMin`。
- `objectives[].linkedActivities` 引用存在的 `activityFlow[].id`。
- `objectives[].assessmentEvidence` 和 `activityFlow[].assessmentLinks` 引用存在的 `assessmentRubric[].id`。
- `qualityReport` 必须记录本次校验状态、warnings 或检查项。

## P1 类型专属要求

- PBL 必须包含驱动问题、最终产出、里程碑或阶段产出、过程评价和作品评价。
- 跨学科必须包含主学科、关联学科、融合节点、共同产出和适用边界。
- AI 融合必须包含 AI 工具角色、介入环节、使用边界、学生审辨任务和人机切换说明。
- `backgroundAnalysis` 必须说明课题背景、教材/知识点位置或课程交汇依据。
- 跨学科和 AI 融合必须提供非空 `studentAnalysis`；PBL 可将学情合入 `backgroundAnalysis`。
- `confirmedContext` 中的类型专属信息应体现在 `innovationDesign`、`activityFlow` 或 `assessmentRubric` 中。

## P2 教学有效性

- 教学目标使用可观察行为动词，且行为动词不过级。
- 教学重点对齐核心目标；教学难点在活动流程中有支架。
- 活动流程包含教师行动、学生行动、阶段产出和评价链接。
- 创新环节服务教学目标，而不是装饰性标签。
- 评价量规能收集到课堂或作品证据。
- 教案语言适合教师直接备课和二次修改。

## P3 交付完整性

- 输出结构化 JSON。
- 输出 Word-ready Markdown。
- 默认尝试输出 DOCX；如跳过 DOCX，需要说明原因或使用 `--no-docx`。
- JSON 可通过 `scripts/validate_lesson_plan.py`。
- 需要严格验收时，使用 `--strict-context` 检查 `confirmedContext` 覆盖度。

## 常见错误

- 把 PBL 写成普通小组活动或资料搜集。
- 跨学科只写两个学科名称，没有真实融合节点。
- AI 融合只写“使用 AI 查询资料”，没有审辨任务和使用边界。
- 教学目标、活动和评价量规互相脱节。
- 未提供真实课标或教材依据时，却写成确定来源。
