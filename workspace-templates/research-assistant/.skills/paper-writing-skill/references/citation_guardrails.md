# 引用真实性与支撑性约束

## 双校验

引用建议必须同时满足：

1. 文献真实存在：在 `literature_whitelist` 或 `evidence_cards` 中存在 `paperId`。
2. 证据真正支撑：证据文本与当前论点存在明确支撑关系。

只满足文献真实但证据不命中时，不建议插入引用，只提示需要补证据。

## 证据级别

- `metadata_only`：仅题录，不能支撑论点。
- `abstract_only`：摘要线索，谨慎使用，不能替代全文证据。
- `fulltext`：可作为支撑证据，需标注页码/段落。
- `uploaded_text`：用户上传原文证据，需标注上传段落或页码。

## GB/T 7714 期刊格式

```text
作者.题名[J].刊名,年,卷(期):起止页码.
```

字段缺失时不得补全；在输出中标注缺失字段。

## 拦截规则

必须拦截：

- 不在白名单中的文献。
- 证据级别为 `metadata_only` 的支撑性引用。
- 只有摘要但用户要求强支撑。
- 论点与证据主题不匹配。
- 缺少 `paperId` 或证据位置。

## 输出决策

- `suggest_insert`：文献真实且证据命中。
- `need_more_evidence`：文献真实但证据不足。
- `blocked_fake_reference`：文献不在白名单。
- `blocked_unsupported`：证据不支撑论点。
