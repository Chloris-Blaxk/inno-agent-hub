# 跨文档一致性与生成规则

本文件用于项目申报书、结题报告和成果汇报之间的事实一致性检查。核心原则：`ProjectFactTable` 是唯一事实来源。

## 唯一事实来源

以下内容必须来自 `ProjectFactTable.facts`：

- 项目名称、级别、负责人、团队人数。
- 研究周期、阶段安排、实践过程。
- 已有基础、实际成果、预期成果、样本范围。
- 经费金额、预算科目和用途。

未进入事实表的内容不能直接写入正文；应先补 `factId` 或进入 `missingFields`。

## 冲突检测

| 字段类型 | 常见冲突 | 处理方式 |
|---|---|---|
| team.* | 成员数、负责人姓名不一致 | 标记 `conflict`，章节状态改为 `needs_user_confirmation` |
| timeline.* | 起止时间、阶段数量不一致 | 保留多个值，等待用户确认 |
| outcomes.* | 成果数量、成果类型前后不一致 | 不取较好版本，必须回到来源材料 |
| data.* | 样本班级、人数、年级不一致 | 不能生成量化结论 |
| budget.* | 明细合计与总额不一致 | 预算报告标记 warning 或 fail |

## 文档生成降级

- 申报书：缺少研究基础时，保留章节但标记 `needs_evidence`。
- 结题报告：缺少实际成果时，不写“取得显著成果”，只列待补材料。
- 成果汇报：缺少量化数据时，可以给图表建议，不能生成虚构图表数值。
- 预算：缺少金额时，只给科目和用途建议。

## 三文档集合

- `documentSet.documents` 必须同时包含 `project_application`、`closing_report`、`achievement_report`。
- `crossDocumentConsistencyReport.sharedFactFields` 记录三份文档共同使用或分别需要的事实字段，每条必须回链到事实表中的 `factId`。
- `missingSharedFields` 或 `conflicts` 非空时，`crossDocumentConsistencyReport.status` 与 `qualityReport.status` 都不能为 `pass`。
- 成果汇报的 `timelineItems`、`chartSuggestions`、`achievementHighlights` 只能从事实表派生；没有数量事实时使用 `needs_evidence`，不能生成虚构数值。

## 成功案例使用边界

脱敏成功案例只能用于结构、措辞和亮点组织方式参考，不能迁移其中的成果、数据、经费或团队经历。
