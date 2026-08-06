# 质量检查清单

## P0 必须通过（查源完整性 + 学术诚信 + 教师可读性）

### 查源完整性（PedaScope 优先）

- [ ] `source_trace` 和 `claim_support_check` 必须按 4 级顺序执行查源，不可跳过 PedaScope。
- [ ] `dataSourceReport` 必须逐级记录执行状态（已查询 / 未配置 / 超时）和命中数。
- [ ] 不能笼统写「受限于 mock 数据范围」而不说明 PedaScope 的查询状态。
- [ ] `source_trace` 输出必须区分 `verified_source_found`、`candidate_source_found`、`related_sources_only`、`no_source_found`。

### 学术诚信

- 引用建议必须同时满足文献真实和证据支撑。
- supports 候选必须包含 `evidenceCardId`、`quoteLocation`、`sourceLocator` 和 `evidenceLevel`。
- `citationChecks` 必须校验 GB/T 7714 基础字段，缺卷期页码时进入 `citationWarnings`。
- `insertionSuggestions` 必须为 `pending_teacher_confirmation`，且 `requiresTeacherConfirmation=true`。
- 只有元数据或主题相关时，不得断言"这句话出自该文"。
- 润色不得新增样本量、统计结论、研究发现或不存在的引用。
- `structure_diagnosis` 必须输出 IMRaD 覆盖、摘要四要素和修改优先级。
- `revisionSuggestions` 必须声明 `changedFacts=false` 且 `addedFacts=[]`。
- 输出必须包含 `qualityReport` 和 `provenanceReport`。

### 教师可读性

- [ ] 文献以论文标题为主标签，paperId 在括号中。
- [ ] 引用决策用中文 + emoji（✅ 可以引用 / ⚠️ 证据不足 / ❌ 未找到来源）。
- [ ] 每级查源结果附带来源说明（如「PedaScope KB（150 万篇题录）已查询，命中 3 条」）。
- [ ] 全文用「你」称呼教师，不用「用户」。

## P1 建议通过

- IMRaD 诊断应指出缺失要素和修改优先级。
- 引用格式缺字段时应进入 `citationWarnings`。
- 强论断应给出保守改写建议。
- 存在结构缺口或仍需证据支撑的润色建议时，`qualityReport.status` 应为 `warn`。

## 降级策略

- **PedaScope MCP 不可用**：在 dataSourceReport 中记录「❌ 当前会话未配置 MCP 连接」，然后继续第 2、3 级查源。不能跳过 PedaScope 就宣布 no_source_found 而不说明原因。
- **全部 4 级未命中**：输出 `no_source_found`，如实说明每级查询状态，建议教师补充关键词或上传原文。
- **只命中相关主题**：输出 `related_sources_only`（或 `candidate_source_found` 如果来自 PedaScope），不可作为支撑引用。
- **证据只部分支持**：输出 `partially_supported` 和保守改写建议。
- **PedaScope 命中但无全文**：输出 `candidate_source_found`，附带候选题录和引用草案，标注「正式引用前需人工获取全文确认」。
