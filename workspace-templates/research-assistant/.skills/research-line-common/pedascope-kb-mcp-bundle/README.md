# PedaScope KB MCP

版本：`0.2.2`

本目录提供一个 Python stdio MCP server，用于把 PedaScope 文献库检索接口接入
SKILL 或其他 MCP client。服务只返回题录、检索信号和二次生成摘要，不返回论文原文。

## 文件

```text
kb_mcp.py                         MCP server
settings.example.yaml             OpenAgentHarness 配置示例
smoke_test.sh                     基本 stdio 调用检查
examples/call_pedascope_mcp.py    Python 调用示例
docs/API_USAGE.md                 接口说明
```

## 运行

```bash
export PEDASCOPE_KB_BASE_URL="https://pedascope.ecnu.edu.cn/kb_search_api"
export PEDASCOPE_KB_TIMEOUT_SECONDS=30
python3 kb_mcp.py
```

可选环境变量：

- `PEDASCOPE_KB_BASE_URL`：上游检索接口地址。
- `PEDASCOPE_KB_TIMEOUT_SECONDS`：HTTP 超时秒数，默认 `30`。
- `PEDASCOPE_PAPER_CACHE_TTL_SECONDS`：`paper_id` 缓存时间，默认 `86400`。

客户端不能触发全文可用性探测。

## 可请求工具

- `search_by_keywords`：按关键词检索文献。
- `search_by_topic`：按自然语言选题或研究问题检索文献。
- `search_by_domain`：按学段、学科、领域、方法、年份、期刊、DOI、引用量等条件检索。
- `get_paper`：根据搜索返回的 `paper_id` 获取安全题录。
- `trace_claim`：根据一句 claim 返回候选来源。
- `get_citation`：根据 `paper_id` 生成 GB/T 7714-2015 引用草案。
- `health`：返回本地配置和内容策略。

不暴露全文或兼容入口。

## 内容限制

所有公开工具遵循同一返回策略：

- `raw_text_exposed_chars` 固定为 `0`。
- `full_text_exposed` 固定为 `false`。
- 不返回完整论文、原文段落、原始 snippet、embedding、上游 `original_doc_id`。
- `abstract` 是根据题录和检索信号生成的非逐字摘要。
- `paper_id` 是 MCP 进程内临时句柄，不是长期数据库主键。
- `get_paper` 的 `text_availability.status` 固定为 `not_probed`。
- `filter_expr` 自由表达式不接受；需要过滤时使用 `search_by_domain` 的结构化字段。
- 成功响应同时包含 `content[0].text` 和 `structuredContent`。
- `tools/list` 中每个工具都声明 `outputSchema`。

## 调用示例

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_by_keywords",
    "arguments": {
      "keywords": ["machine learning", "education"],
      "top_k": 3,
      "page_size": 1
    }
  }
}
```

返回内容读取顺序：

1. 新客户端读取 `structuredContent`。
2. 旧客户端解析 `content[0].text` 中的 JSON 字符串。

## 配置示例

```yaml
pedascope-kb:
  command: python3 /ABSOLUTE/PATH/TO/pedascope-kb-mcp/kb_mcp.py
  enabled: true
  environment:
    PEDASCOPE_KB_BASE_URL: https://pedascope.ecnu.edu.cn/kb_search_api
    PEDASCOPE_KB_TIMEOUT_SECONDS: "30"
  timeout: 30000
  expose:
    tool_prefix: mcp.pedascope
```

## 检查

```bash
python -m py_compile kb_mcp.py examples/call_pedascope_mcp.py
PEDASCOPE_KB_BASE_URL="https://pedascope.ecnu.edu.cn/kb_search_api" ./smoke_test.sh
```

更完整的调用样例：

```bash
python examples/call_pedascope_mcp.py \
  --server ./kb_mcp.py \
  --base-url https://pedascope.ecnu.edu.cn/kb_search_api
```

## 接口文档

本地文档见 `docs/API_USAGE.md`。
