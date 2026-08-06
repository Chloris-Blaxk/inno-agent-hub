# 科研线公共底座

`research-line-common` 是四个科研线 Skill 的公共运行时与契约层，负责统一输出信封、证据策略、文献适配、模型输出门禁、跨 Skill workspace 摘要和教师可读 DOCX 导出。

## 统一入口

优先使用 `research_line_cli.py` 执行公共动作：

```bash
python3 agent_cases/research-line-common/research_line_cli.py guard \
  agent_cases/research-topic-generation-skill/generated-outputs/sample-valid.json \
  agent_cases/literature-reading-skill/generated-outputs/sample-valid.json
```

```bash
python3 agent_cases/research-line-common/research_line_cli.py workspace \
  agent_cases/research-topic-generation-skill/generated-outputs/sample-valid.json \
  agent_cases/literature-reading-skill/generated-outputs/sample-valid.json \
  --output /tmp/research-workspace.json
```

```bash
python3 agent_cases/research-line-common/research_line_cli.py docx \
  agent_cases/research-topic-generation-skill/generated-outputs/sample-valid.json \
  --output-dir /tmp/research-docx
```

说明：

- `guard` 会调用四个业务 Skill 的 validator，并输出 `ready_for_render`、`needs_review` 或 `rejected`。
- `workspace` 会把多个 Skill 输出压缩为可进入下游上下文的 `ResearchWorkspace` 摘要，不保留全文和完整 `sourceRefs`。
- `docx` 会从已通过校验的科研线 JSON 输出导出教师可读 DOCX。该命令需要运行环境安装 `python-docx`。

## 文献适配器

`literature_adapter.py` 提供五类后端：

- `LocalMockLiteratureAdapter`：默认本地样例池，读取文献阅读索引、文献阅读白名单和论文写作白名单。
- `PedaScopeMcpAdapter`：通过 `pedascope-kb-mcp-bundle/kb_mcp.py` 调用 PedaScope KB 150w 教育文献题录库，只返回题录候选、系统生成的非逐字摘要、结构化阅读清单、题录真实性验证、文献态势信号、候选查源和引用草案；不能直接生成 EvidenceCard。
- `AuthorizedDatabaseAdapter`：授权文献库离线索引占位实现，真实接入时应保留授权范围和文本可用性。
- `UserUploadAdapter`：用户提供文献记录和 EvidenceCard，来源状态保持 `user_provided`。
- `ExternalMetadataAdapter`：外部题录/元数据索引，只能用于推荐和相关性提示，不能直接生成支撑性证据。

后端选择：

- 默认：`RESEARCH_LITERATURE_BACKEND=local_mock`
- PedaScope：`RESEARCH_LITERATURE_BACKEND=pedascope`
- PedaScope 优先、本地样例兜底：`RESEARCH_LITERATURE_BACKEND=hybrid`

```bash
python3 agent_cases/research-line-common/literature_adapter.py search \
  --topic "小学数学即时反馈" \
  --keywords "即时反馈,错因诊断" \
  --no-local-mock \
  --authorized-index-json /path/to/authorized-index.json
```

```bash
python3 agent_cases/research-line-common/literature_adapter.py search \
  --backend pedascope \
  --topic "小学数学即时反馈" \
  --keywords "即时反馈,错因诊断"
```

```bash
python3 agent_cases/research-line-common/literature_adapter.py trace \
  --backend pedascope \
  --query "课堂即时反馈有助于教师调整教学决策"
```

```bash
python3 agent_cases/research-line-common/literature_adapter.py reading-list \
  --backend pedascope \
  --topic "小学数学即时反馈支持错因诊断"
```

```bash
python3 agent_cases/research-line-common/literature_adapter.py verify-citation \
  --backend pedascope \
  --title "人工智能助推教师专业发展的若干思考" \
  --year 2022 \
  --journal "中国远程教育"
```

```bash
python3 agent_cases/research-line-common/literature_adapter.py gaps \
  --backend pedascope \
  --keywords "即时反馈,错因诊断" \
  --domain "小学数学"
```

## 直接脚本

保留以下直接脚本，便于调试和向后兼容：

```bash
python3 agent_cases/research-line-common/model_output_guard.py <output.json>
python3 agent_cases/research-line-common/workspace_summary.py <output-a.json> <output-b.json> --output <workspace.json>
python3 agent_cases/research-line-common/docx_export.py <output.json> --output-dir <dir>
```
