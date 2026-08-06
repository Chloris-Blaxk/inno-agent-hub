# Scripts

放置引用格式检查、证据支撑性校验、摘要四要素检查等脚本。

## validate_paper_writing.py

校验论文写作助手 JSON 产物，重点覆盖 `source_trace` 决策、候选文献支撑状态、出处位置、证据卡 `paperId` 回链、GB/T 7714 引用检查、待教师确认插入建议、IMRaD 结构诊断、摘要四要素、保守润色不新增事实和质量指标一致性。

```bash
python3 scripts/validate_paper_writing.py generated-outputs/sample-valid.json
```

## render_paper_writing.py

从请求 JSON 生成最小 `source_trace`、`structure_diagnosis` 或 `conservative_polish` 结果并同步写出同名 Markdown。查源只在原句或关键术语被证据片段支撑时输出可用证据卡、引用检查和待确认插入建议，否则诚实降级为相关文献或未找到来源；结构和润色任务可仅凭 `input.draftText` 独立运行。

教育专用内容生成统一使用 `InnoSpark-235B` 作为 Generator 约定，配置读取：

- `INNOSPARK_AIECNU_API_KEY`（可回退到 `INNOSPARK_API_KEY`）
- `INNOSPARK_AIECNU_BASE_URL`，默认 `https://innospark-api.aiecnu.net/v1`
- `RESEARCH_EDU_GENERATOR_MODEL`，默认 `InnoSpark-235B`

脚本输出会在 `modelRuntime`、`dataSourceReport` 和 `qualityReport.metrics` 中记录本次 Generator 配置；引用和事实支撑仍必须来自 EvidenceCard、白名单或用户提供材料。

```bash
python3 scripts/render_paper_writing.py examples/sample-request.json --validate
python3 scripts/render_paper_writing.py generated-outputs/sample --config examples/sample-request.json --validate
```

## ../research-line-common/literature_adapter.py

共享查源适配器，支持本地样例池、授权库离线索引、外部元数据索引、用户提供文献和用户证据卡。`source_trace` 只能把通过支撑性判断的 EvidenceCard 作为可用证据。

```bash
python3 ../research-line-common/literature_adapter.py trace \
  --query "即时反馈有助于教师调整教学决策" \
  --authorized-index-json /path/to/authorized-index.json
```

## ../research-line-common/docx_export.py

从已通过校验的论文写作 JSON 输出导出教师可读 DOCX，包含查源结论、候选文献、论点检查、结构诊断、保守润色建议和待确认插入建议。

```bash
python3 ../research-line-common/docx_export.py generated-outputs/sample-citation-ready.json --output-dir generated-outputs/docx
```
