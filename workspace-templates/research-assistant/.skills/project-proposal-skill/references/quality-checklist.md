# 质量检查清单

## P0 必须通过

- 生成正文前必须先形成或校验 `ProjectFactTable`。
- 每条事实必须包含 `factId`、`field`、`value`、`sourceRefs`、`confidence`、`status`。
- 文档必填章节必须覆盖目标模板中的 required sections。
- 同一事实在不同章节中不得矛盾。
- `document_set` 必须同时包含申报书、结题报告和成果汇报，且 `crossDocumentConsistencyReport.documentsChecked` 与实际文档类型一致。
- 跨文档共享字段必须通过同一组 `factId` 回链到 `ProjectFactTable`；缺失或冲突时 `qualityReport.status` 不能为 `pass`。
- 不得虚构成果、数据、团队经历、经费明细或中标概率。

## P1 建议通过

- 研究基础章节应引用团队、实践记录和成果清单事实。
- 申报书应对齐评审维度，说明问题价值、研究设计、基础与可行性。
- 结题报告应突出过程节点、实际成果和问题反思。
- 成果汇报应包含量化成果、时间线和推广建议。
- 成果汇报的 `timelineItems`、`chartSuggestions` 和 `achievementHighlights` 应只使用已有事实；没有数量证据时只给 `needs_evidence` 占位。

## 预算检查

- 用户未提供金额时，只给科目建议，不编造金额。
- 预算金额必须先进入 `ProjectFactTable` 的 `budget.total` 或 `budget.items` 事实，再进入正文或 `budgetReport`。
- 预算用途必须关联研究活动、数据采集或成果产出。
- 不确定科目应标记 `budgetWarningCount`。
- 预算总额与明细合计不一致时必须写入 `conflicts`，对应质量状态为 `warn`。

## 降级策略

- 材料不足：输出 `missingFields` 和补充清单。
- 事实冲突：输出 `conflicts`，正文对应章节标记 `needs_user_confirmation`。
- 预算不完整：生成非金额型预算建议。
