# References

本目录保存论文写作助手 Skill 的独立数据契约和规则。该 Skill 可以复用科研线共享对象命名，但运行时不要求文献阅读助手先生成证据卡。

统一结构来源：

- `agent_design/improvement/research-line-unified-skill-data-structure.md`

## 独立 references 清单

- `input-output-schema.md`：统一请求/输出信封、`LiteratureRecord`、`EvidenceCard`、`ClaimCheck`、`DocumentDraft` schema。
- `literature-whitelist-sample.json`：真实文献白名单样例，用于 `source_trace` 查出处。
- `evidence-card-index.json`：证据卡索引样例，用于论点支撑性判断。
- `imrad-checklist.md`：IMRaD 结构和摘要四要素检查表。
- `citation-rules.md`：GB/T 7714 引用格式和支撑性校验规则。
- `academic-expression-rules.md`：教学经验表达到学术表达的保守改写规则。
- `conservative-editing-rules.md`：不新增事实的保守润色边界。
- `quality-checklist.md`：引用真实性、证据支撑和事实一致性检查。

## 独立性边界

- `source_trace` 必须能直接处理 `input.queryText`，不能把文献阅读助手作为前置依赖。
- 只命中文献主题但没有证据片段时，只能输出 `related_sources_only`，不能断言“这句话出自该文”。
- 不得编造文献、作者、年份、期刊、DOI、页码、样本量、显著性或研究发现。
