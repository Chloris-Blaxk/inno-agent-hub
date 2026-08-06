# 质量检查清单

## P0 必须通过

- 根对象包含 `deckMeta`、`curriculumContext`、`designPlan`、`lessonOutline`、`slides`、`teacherScript`、`exportPlan`、`qualityReport`。
- `deckMeta.visualSystem` 为 `edu-deck-v1`。
- 每页使用 ED01-ED12 登记版式，并有 `layoutId`。
- HTML 每个 `<section>` 都有 `data-layout="EDxx"`、`data-slot`、`data-slot-ratio` 和 `data-asset-status`。
- HTML 中的 `data-layout` 顺序必须与 JSON `slides[].layoutId` 一致。
- 每页都有 `visualSlots`、`feedbackEvidence`、`teacherScript`、`timing`、`notes`。
- 练习/出门测任务包含 `target` 和 `feedback`。
- 例题步骤包含 `teacherCue`。
- 错误辨析包含 `misconception`、`correction`、`checkQuestion`。
- 总时长与 `durationMin` 偏差不超过 10%。
- 未接入教材页码或课标边界时，在 `curriculumContext.assumptions` 标注。

## P1 教学有效性

- 教学目标、课堂动作、例题、练习和出门测互相对齐。
- 每页只承载一个课堂动作。
- 逐字稿包含教师说、追问、预设回应、过渡语。
- `studentProfile.priorKnowledge` 影响导入页。
- `studentProfile.commonDifficulties` 影响错误辨析页。

## P2 视觉与投影

- 学生屏幕文字少，标题可在后排扫读。
- 反馈方式不出现在学生屏幕，进入备注/教师面板。
- 版式多样性达标：8 页至少 6 个 ED 版式，9 页以上至少 8 个。
- 不连续 3 页使用同一主体结构。
- 一套课件只使用一个风格 preset。
- 图示和图片都来自 `visualSlots`。
- HTML 演示支持键盘、滚轮、触屏、底部圆点、ESC 索引、N 键教师备注、B 键低功耗模式。
- 正文区避免出现“教师说/预设回应/反馈证据”等教师面板文本。

## P3 交付完整性

- 输出结构化 JSON。
- 输出教师逐字稿 Markdown。
- 输出 HTML 横向翻页预览。
- HTML 预览通过 `scripts/validate_lesson_deck_html.py`。
- 需要 PPTX 时可导出可编辑 PPTX。
- `qualityReport.status` 为 `pass` 或 `warning`。
- 产物按 `generated-outputs/<case-name>/` 子文件夹组织，不裸放根目录。

## P4 响应信封合规

`status` 为 `pass` 时：

- `inputSummary` 包含 `subject`、`grade`、`topic` 和实际使用的假设。
- `result` 只放摘要（`deckMeta`、`designPlanSummary`），不放完整 `slides` 数组。
- `artifacts` 列出所有产物文件，每项含 `type`、`path`、`description`。
- `handoff` 只传下游需要的摘要和文件路径，**不塞完整 HTML、PPTX 或大 JSON**。
- `handoff.deckArtifactPaths` 指向子文件夹内的 JSON 路径。
- `qualityReport.checks` 包含 schema 校验、布局校验、反馈证据校验等结果。
- `warnings` 显式列出所有缺失、降级和需要人工确认的内容。
- `nextActions` 至少包含一项明确的下一步建议（如 `review`、`render`、`export`）。

`status` 为 `warn` 时：

- `warnings` 非空，每条说明哪些部分可靠、哪些需要补充。
- `nextActions` 包含降级后的推荐路径。

`status` 为 `failed` 时：

- `result` 可为空或只含最小摘要。
- `warnings` 说明失败原因和已尝试的修复。
- `nextActions` 明确告知用户需要重新输入或人工介入。

## P5 人工确认标记

- 高风险内容（如教材版本假设、未验证的知识点边界、自动生成的图片提示）有 `needs_user_confirmation` 或等价标记。
- `curriculumContext.assumptions` 中的每项都有来源说明（输入缺失、默认值、推断）。
- 未接入真实教材/课标库时，`assumptions` 显式标注，不静默补全。
- 教师逐字稿中的事实性内容（如例题答案、课标引用）可回链到输入或知识包。

## 常见错误

- 把课件生成做成演讲 PPT 美化。
- 先写内容再硬套版式。
- 学生屏幕堆逐字稿。
- 互动没有反馈证据。
- 题目没有目标和反馈。
- 图示没有槽位或比例。
