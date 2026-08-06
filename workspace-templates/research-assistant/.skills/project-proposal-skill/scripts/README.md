# Scripts

放置项目事实表校验、预算科目检查、Word/PPT 导出等脚本。

## validate_project_proposal.py

校验项目申报助手 JSON 产物，重点覆盖 `ProjectFactTable` 必填事实、`sourceRefs`、缺失/冲突字段、模板必填章节、三文档 `documentSet`、跨文档一致性和预算/成果虚构风险。

```bash
python3 scripts/validate_project_proposal.py generated-outputs/sample-valid.json
```

## render_project_proposal.py

从请求 JSON 先抽取最小 `ProjectFactTable`，再按目标文档模板生成申报、结题、成果汇报或三文档集合，并同步写出同名 Markdown。材料缺失写入 `missingFields`，同一事实冲突写入 `conflicts`，预算金额必须先进入事实表；预算可来自结构化 `budgetInfo` 或用户材料正文中的预算说明；成果汇报的时间线和图表建议只能由事实表派生。

教育专用内容生成统一使用 `InnoSpark-235B` 作为 Generator 约定，配置读取：

- `INNOSPARK_AIECNU_API_KEY`（可回退到 `INNOSPARK_API_KEY`）
- `INNOSPARK_AIECNU_BASE_URL`，默认 `https://innospark-api.aiecnu.net/v1`
- `RESEARCH_EDU_GENERATOR_MODEL`，默认 `InnoSpark-235B`

脚本输出会在 `modelRuntime`、`dataSourceReport` 和 `qualityReport.metrics` 中记录本次 Generator 配置；项目事实、预算金额和成果数据仍必须先进入 `ProjectFactTable`。

```bash
python3 scripts/render_project_proposal.py /tmp/project-proposal-sample \
  --config examples/sample-request.json \
  --validate

python3 scripts/render_project_proposal.py /tmp/project-proposal-document-set \
  --config examples/document-set-request.json \
  --validate
```

`generated-outputs/sample-*.json` 是固定边界样例，只有在明确刷新 fixture 时才覆盖写入。普通试跑优先写到 `/tmp` 或显式指定的临时目录，避免污染 `generated-outputs/`。

## export_project_presentation.mjs

从已通过校验的项目申报 JSON 输出生成成果汇报 PPTX 骨架。PPTX 仅使用 `ProjectFactTable`、`presentationSupport` 和一致性报告中的事实，不补造数值。

```bash
node scripts/export_project_presentation.mjs --input generated-outputs/sample-document-set.json --out generated-outputs/project-achievement-report.pptx
```
