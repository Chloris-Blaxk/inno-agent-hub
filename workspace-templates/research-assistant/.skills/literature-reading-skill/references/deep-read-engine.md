# deep_read 精读引擎详细说明

> 📖 本文件仅在 `taskIntent=deep_read` 时加载。其他模式可跳过。

## Python API

```python
# deep_read 模式的核心调用
from paper_qa_runtime import PaperQARuntime, RuntimeConfig

runtime = PaperQARuntime(RuntimeConfig(
    llm_base_url="https://innospark-api.aiecnu.net/v1",
    llm_api_key="...",  # INNOSPARK_AIECNU_API_KEY
    llm_model="InnoSpark-235B",
    embedding_base_url="...", embedding_api_key="...",
    embedding_model="Qwen/Qwen3-Embedding-8B",
    embedding_dimensions=4096,
))

result = runtime.answer(
    paper_md=paper_md,
    history=deep_read_history,
    question=user_question,
    title=paper_title,
)
```

## 执行流程（10 步）

1. 确认 `paperId` 和 `paperMd`（论文 Markdown 文本）。paperMd 来源优先级：用户上传原文 > 系统全文 > 系统摘要 > 仅元数据（仅元数据时拒绝 deep_read）。
2. 调用 `scripts/paper_qa_runtime` 进行分块索引 → 章节路由 → Query Rewrite → 混合检索 → 上下文裁剪 → 生成回答。
3. **章节路由**：根据用户问题自动路由到对应 Agent：
   - `review_agent`：引言、背景、文献综述、研究问题
   - `method_agent`：方法、样本、数据、实验设计（三步进阶：看懂→批判→设计思维）
   - `result_agent`：结果、发现、统计分析
   - `discussion_agent`：讨论、结论、局限、启示
   - `general_agent`：跨章节或宽泛问题
4. **回答框架**：简答（直接回应）+ 分析（解释 why）+ 拓展（引导性追问）。
5. **多轮对话**：支持追问，自动 Query Rewrite 保持上下文连贯。
6. **引用标注**：每个观点标注 citations（chunkIndex / 章节 / 原文片段预览）。
7. 汇总为 `DeepReadCard`（四维卡：researchProblem / method / findings / limitations / usableIdeas）+ `deepReadSessions[]`（逐轮 QA 记录）。
8. 有摘要/全文/用户上传原文时，同步生成 `EvidenceCard`。每张 EvidenceCard 必须标注 evidenceLevel、supportType、quoteLocation、limits。
9. 全文级精读使用本地索引缓存（`.paper_qa_index/`），同一论文重复调用不重新 embedding。
10. deep_read 的 Agent Prompt 内置在 `scripts/paper_qa_runtime/prompts/agents/normal/`。

## 引擎模块

`scripts/paper_qa_runtime/` 内部模块分工：

| 模块 | 职责 |
|------|------|
| `runtime.py` | PaperQARuntime 主入口，编排完整流水线 |
| `routing.py` | 章节路由（review/method/result/discussion/general） |
| `retrieval.py` | 混合检索（Vector + Keyword + Structure Boost） |
| `query_rewrite.py` | 多轮对话 Query 改写 |
| `generation.py` | 带引用的回答生成 |
| `indexing.py` | 论文分块 + Embedding 索引 |
| `storage.py` | 本地索引缓存（`.paper_qa_index/`） |
| `chunking.py` | Markdown 按标题分块（~700 token/chunk） |
| `embeddings.py` | Embedding 客户端（ModelScope / OpenAI / TEI） |
| `llm.py` | LLM 客户端抽象（chat completions + retry） |
| `context_builder.py` | 上下文预算裁剪（默认 6000 token） |
| `prompts.py` / `prompts/` | Prompt 管理与模板 |
| `config.py` | 配置加载 |
| `schemas.py` | 数据模型 |
| `text_utils.py` | 文本工具（CJK-aware token 估算等） |

## CLI 调试

### 单篇论文精读

```bash
cd agent_cases/literature-reading-skill
PYTHONPATH=scripts python -m adapters.cli answer \
  --config runtime_config.json \
  --paper examples/sample-paper-for-deep-read.md \
  --question "这篇论文采用了什么研究方法？"
```

加 `--json` 查看 citations、retrieval traces 和缓存状态。

## HTTP Adapter（服务化部署）

```bash
cd agent_cases/literature-reading-skill
PAPER_QA_CONFIG=runtime_config.json \
  PYTHONPATH=scripts uvicorn adapters.http_server:app --host 127.0.0.1 --port 18082
```

接口：`POST /v1/paper-qa/answer`

## 操作注意

- 本地索引缓存目录为 `.paper_qa_index`。缓存 key = 论文内容 hash + chunk 配置 + embedding 配置。同一论文重复调用不重新 embedding。
- API key 不放入请求体或提交到代码仓库。服务部署时通过配置文件、环境变量或宿主系统的配置机制注入。
- deep_read 默认 LLM 为 `InnoSpark-235B`，通过 `INNOSPARK_AIECNU_API_KEY` / `INNOSPARK_AIECNU_BASE_URL` 注入；`PAPER_QA_LLM_*` 显式配置优先。
- LLM 响应无 `choices` 时视为 provider/model/channel 故障，不静默降级。
- Embedding 响应 `data: null` 时检查 provider 兼容性、模型可用性和 token 有效性。
- 不要重新实现 chunking、retrieval、routing、query rewrite、prompt selection 或 context construction——直接调用 paper_qa_runtime。
