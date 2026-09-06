---
name: tavily-search
category: 研究检索
subject: 跨学科
kind: 通用工具
description: >-
  通过 Tavily API 进行实时联网搜索，获取模型训练截止日期之后的最新信息。
  当用户询问近期事件、实时数据、当前状态、价格、版本号等容易过时的事实，
  或明确要求「搜一下 / 查一下 / 帮我搜索」时使用；纯概念解释、闲聊、
  基于已有上下文即可完成的推理不要调用。
---

## 执行步骤

### 1. 发起搜索

把 `<QUERY>` 换成检索词（保留用户原始语言，中英文均可）后执行：

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"YOUR_TAVILY_API_KEY","query":"<QUERY>","max_results":5,"include_answer":true,"search_depth":"basic"}'
```

可调参数：
- `max_results`：返回结果数，默认 5；问题宽泛或需多方求证时调到 8–10。
- `search_depth`：`basic`（快，默认）或 `advanced`（更深，耗时更长，重要查询用）。
- `topic`：默认 `general`；查新闻时可加 `"topic":"news"`。

### 2. 解析响应

响应是 JSON，使用这些字段：

| 字段 | 用途 |
|---|---|
| `answer` | Tavily 合成的直接答案，作为回答主体 |
| `results[].title` | 来源标题 |
| `results[].url` | 来源链接 |
| `results[].content` | 来源摘要，引用时取前 ~300 字 |
| `results[].score` | 相关度 0–1，低于 0.5 的来源丢弃不引用 |

### 3. 组织回答

1. 用 `answer` 给出结论；若 `answer` 为空，则综合高分 `results` 自行归纳。
2. 在结论下方列 2–3 条高分来源，格式 `[标题](url)`。
3. 结尾标注「来源：Tavily 实时搜索」，让用户知道这是联网结果而非模型记忆。

### 错误处理

- HTTP 401 / `Unauthorized`：API Key 无效或未替换，提示用户检查 `YOUR_TAVILY_API_KEY`。
- HTTP 432 / 配额用尽：告知用户当月免费额度（1000 次）已用完。
- 网络超时或空结果：如实说明搜索失败，不要编造内容。
