# Scripts

放置教师画像校验、材料解析、选题重复度检查等脚本。

## validate_research_topic.py

校验研究选题生成 JSON 产物，重点覆盖总结性选题材料回链、材料主题聚类、研究轨迹归纳、教师已有成果反幻觉、选题具体性、已有基础差距、差异化检查、可行性风险和补资料清单。

```bash
python3 scripts/validate_research_topic.py generated-outputs/sample-valid.json
```

## render_research_topic.py

从请求 JSON 生成最小可运行的研究选题 JSON，并同步写出同名 Markdown，支持材料摘要、主题聚类、研究轨迹、总结性选题、规划性选题、基础差距、立项题差异化检查和 handoff 关键词。

教育专用内容生成统一使用 `InnoSpark-235B` 作为 Generator 约定，配置读取：

- `INNOSPARK_AIECNU_API_KEY`（可回退到 `INNOSPARK_API_KEY`）
- `INNOSPARK_AIECNU_BASE_URL`，默认 `https://innospark-api.aiecnu.net/v1`
- `RESEARCH_EDU_GENERATOR_MODEL`，默认 `InnoSpark-235B`

脚本输出会在 `modelRuntime`、`dataSourceReport` 和 `qualityReport.metrics` 中记录本次 Generator 配置；事实依据仍只来自用户材料、授权文献或本地样例。

```bash
python3 scripts/render_research_topic.py examples/sample-request.json --validate
python3 scripts/render_research_topic.py generated-outputs/sample --config examples/sample-request.json --validate
```

## ../research-line-common/docx_export.py

从已通过校验的研究选题 JSON 输出导出教师可读 DOCX，包含候选选题、材料聚类、研究轨迹、数据源和下一步补资料建议。

```bash
python3 ../research-line-common/docx_export.py generated-outputs/sample-valid.json --output-dir generated-outputs/docx
```
