# 引用格式与支撑性校验规则

当前规则用于跑通 GB/T 7714 风格的基础引用格式和支撑性校验。真实期刊格式可后续补充。

## 证据级别

| 内部值 | 向教师展示时怎么说 | 含义 | 是否可支撑论点 |
|---|---|---|---|
| `metadata_only` | 📋 只知标题和作者 | 仅题录，无摘要或全文 | ❌ 只能列为相关文献 |
| `abstract_only` | 📄 仅有摘要 | 仅有摘要，无全文 | ⚠️ 谨慎使用，不能替代全文证据，不支撑强因果或"显著提升"结论 |
| `fulltext` | ✅ 有全文可定位 | 有全文可定位 | ✅ 可作为支撑证据，需标注页码/段落 |
| `uploaded_text` | 📤 你上传的原文 | 你上传的原文证据 | ✅ 需标注上传段落或页码，标记为 `user_text_only` |

## GB/T 7714 基础格式

### 期刊论文

```text
作者. 题名[J]. 期刊名, 年份, 卷(期): 起止页码.
```

字段不足时：

- 无卷期页码：可以暂缺，但必须在 `citationWarnings` 中提示。
- 无 DOI：不影响基础引用。
- 作者未知：不得编造，输出"作者待确认"并标记警告。
- 任何必填字段缺失都必须在输出中显式标注，不得静默补全。

## 支撑性校验

### 双重验证原则

引用建议必须同时满足：

1. **文献真实存在**：在 `literature_whitelist` 或 `evidence_cards` 中存在 `paperId`。
2. **证据真正支撑**：证据文本与当前论点存在明确支撑关系。

只满足文献真实但证据不命中时，不建议插入引用，只提示需要补证据。

### 支撑性条件表

| 条件 | 允许动作 |
|---|---|
| 文献存在 + 摘要/全文证据直接支持 | 可推荐引用，并标明证据级别 |
| 文献存在 + 证据只部分支持 | 可推荐保守改写，不可支撑原强论断 |
| 只有元数据无文本证据 | 只能列为相关文献，不可作为支撑引用 |
| 未命中文献 | 输出需要补证据，不得编造引用 |

## 输出决策（四级）

| 内部决策值 | 向教师展示时怎么说 | 条件 | 含义 |
|---|---|---|---|
| `suggest_insert` | ✅ **可以引用（需你确认）** | 文献真实 + 证据命中 | 可建议插入引用，仍需教师确认 |
| `need_more_evidence` | ⚠️ **文献真实但证据不足** | 文献真实但证据不足 | 只提示补证据（如"建议先找到这篇的全文再引用"），不生成引用建议 |
| `blocked_fake_reference` | ❌ **未找到可靠来源，不能引用** | 文献不在白名单中 | 拦截，不得生成任何引用 |
| `blocked_unsupported` | ❌ **文献内容不支撑你的论点** | 证据不支撑该论点 | 拦截，证据与论点不匹配 |

## 拦截规则

必须拦截以下情况：

- 不在白名单中的文献。
- 证据级别为 `metadata_only` 的支撑性引用。
- 只有摘要但用户要求强支撑（如统计结论、因果关系、显著提升）。
- 论点与证据主题不匹配。
- 缺少 `paperId` 或证据位置。

## source_trace 决策与多级查源

### 查源优先级（必须按顺序执行，不可跳过）

```
第 1 级：PedaScope KB MCP（trace_claim / search_by_keywords / search_by_topic）
   ↓ 命中 → candidate_source_found，继续第 2 级补证据
   ↓ 未命中 / 不可用 → 记录原因，进入第 2 级
第 2 级：文献阅读助手共享证据卡 + 索引（跨 Skill 复用）
   ↓ 命中 fulltext → verified_source_found
   ↓ 命中 abstract → related_sources_only
   ↓ 未命中 → 进入第 3 级
第 3 级：论文写作助手本地白名单 + 证据卡索引
   ↓ 命中 → 按支撑性规则判定
   ↓ 未命中 → 进入第 4 级
第 4 级：全部未命中 → no_source_found
```

### 查源结果类型

| 决策 | 含义 | 典型场景 |
|---|---|---|
| `verified_source_found` | 文献真实，且证据片段能确认原句或直接支撑 | 全文命中，原文段落可直接定位 → 对应 `suggest_insert` |
| `candidate_source_found` | PedaScope 等题录库找到了候选来源，但未返回原文证据 | 只能输出候选题录和引用草案 → 对应 `need_more_evidence`，不得自动插入引用 |
| `related_sources_only` | 找到相关文献，但不能确认该句来源 | 摘要级匹配或主题相似 → 对应 `need_more_evidence` 或 `blocked_unsupported` |
| `no_source_found` | 全部 4 级查源均未找到 | 对应 `blocked_fake_reference`，必须如实汇报每级查询状态 |

### 禁止行为

- ❌ 跳过 PedaScope 直接宣称「受限于 mock 数据范围」
- ❌ 只在第 3 级（本地 JSON）找不到就输出 `no_source_found`
- ❌ 把 PedaScope 的 `candidate_source_found` 直接当作 `verified_source_found`
- ❌ dataSourceReport 中笼统写「mock 数据」而不逐级说明查询状态

## 插入前确认

- 可插入引用必须同时具备 `paperId`、`evidenceCardId`、`sourceLocator`、`evidenceLevel` 和 `formattedCitation`。
- 摘要级证据可以作为背景引用，但不能伪装成页码级直接引文。
- `insertionSuggestions` 只能是待教师确认对象，状态为 `pending_teacher_confirmation`；教师确认前不得自动写入正文或参考文献表。
