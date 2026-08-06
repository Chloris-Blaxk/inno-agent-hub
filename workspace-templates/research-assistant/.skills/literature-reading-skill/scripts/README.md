# Scripts

本目录存放文献阅读助手的可执行脚本和精读引擎。

## render_literature_reading.py

全流程离线渲染脚本——从请求 JSON、本地 mock 文献索引、白名单样例和用户提供文献生成文献筛选结果、检索报告、速读卡、精读卡、横向比较矩阵和证据卡，并同步写出同名 Markdown。

教育专用内容生成统一使用 `InnoSpark-235B` 作为 Generator 约定，配置读取：

- `INNOSPARK_AIECNU_API_KEY`（可回退到 `INNOSPARK_API_KEY`）
- `INNOSPARK_AIECNU_BASE_URL`，默认 `https://innospark-api.aiecnu.net/v1`
- `RESEARCH_EDU_GENERATOR_MODEL`，默认 `InnoSpark-235B`

脚本输出会在 `modelRuntime`、`dataSourceReport` 和 `qualityReport.metrics` 中记录本次 Generator 配置；metadata-only 文献仍不得生成 EvidenceCard 或支撑性引用。

```bash
cd agent_cases/literature-reading-skill
PYTHONPATH=scripts python scripts/render_literature_reading.py examples/sample-request.json --validate
PYTHONPATH=scripts python scripts/render_literature_reading.py generated-outputs/sample --config examples/sample-request.json --validate
```

## validate_literature_reading.py

校验 JSON 产物，覆盖 `CorpusSearchReport`、`LiteratureRecord`、`textAvailability` 降级、精读卡/横向比较回链和 `EvidenceCard` 字段完整性。

```bash
python3 scripts/validate_literature_reading.py generated-outputs/sample-valid.json
```

## ../research-line-common/literature_adapter.py

科研线共享文献适配器。默认读取本地样例池，也支持通过 CLI 组合授权库离线索引、外部元数据索引、用户提供文献和用户证据卡。

```bash
python3 ../research-line-common/literature_adapter.py search \
  --topic "小学数学即时反馈" \
  --keywords "即时反馈,错因诊断" \
  --no-local-mock \
  --authorized-index-json /path/to/authorized-index.json
```

## ../research-line-common/docx_export.py

从已通过校验的文献阅读 JSON 输出导出教师可读 DOCX，包含检索报告、推荐阅读、速读卡、精读卡、横向比较、证据卡和数据源限制。

```bash
python3 ../research-line-common/docx_export.py generated-outputs/sample-valid.json --output-dir generated-outputs/docx
```

## deep_read_adapter.py

deep_read 模式适配器——调用 paper_qa_runtime 进行单篇论文多轮精读。无 LLM 凭证时自动回退为 mock 模式。

默认 LLM 已改为 `InnoSpark-235B`；显式传入 `PAPER_QA_LLM_BASE_URL`、`PAPER_QA_LLM_API_KEY`、`PAPER_QA_LLM_MODEL` 时会覆盖默认值。

```bash
PYTHONPATH=scripts python scripts/deep_read_adapter.py \
  --paper examples/sample-paper-for-deep-read.md \
  --question "这篇论文采用了什么研究方法？" \
  --question "有哪些局限性？"
```

## paper_qa_runtime/ 🆕

单篇论文精读引擎（从 ra-skill 融合），负责：
- Markdown 分块 + Embedding 索引
- 章节路由（review/method/result/discussion/general）
- Query Rewrite + 混合检索（Vector + Keyword）
- 上下文裁剪 + 带引用的回答生成
- 本地索引缓存（`.paper_qa_index/`）

Agent Prompt 在 `paper_qa_runtime/prompts/` 中。

## adapters/ 🆕

- `cli.py` — 命令行调试入口（`python -m adapters.cli answer`）
- `http_server.py` — HTTP 服务适配器（需 `fastapi` 和 `uvicorn`）
