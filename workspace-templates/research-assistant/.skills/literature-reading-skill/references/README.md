# Literature Reading Skill - References

本目录存放文献阅读助手 Skill 的领域知识库，按需由 SKILL.md 引用加载。

## 文件索引

| 文件 | 用途 | 被哪些模式引用 |
|------|------|---------------|
| `input-output-schema.md` | 统一请求/响应信封 + LiteratureRecord / ReadingCard / EvidenceCard 等对象定义 | 全部模式 |
| `literature-selection-rules.md` | 文献候选排序规则、readingDecision 规则、速读卡四要素 | `literature_discovery`, `quick_read` |
| `reading-card-templates.md` | 速读卡 / 精读卡 / 横向比较矩阵的 JSON Schema 模板 | `quick_read`, `deep_read`, `compare_papers` |
| `evidence-card-rules.md` | 证据卡字段定义、supportType 含义、质量规则 | `evidence_carding`, `deep_read` |
| `availability-levels.md` | textAvailability 四级标记 + evidenceLevel 四级 + 降级规则 | 全部模式 |
| `quality-checklist.md` | P0/P1 质量检查清单 + 降级策略 | 全部模式 |
| `literature-whitelist-sample.json` | 文献白名单样例数据 | `literature_discovery` |
| `literature-index-sample.json` | 文献索引样例数据 | `literature_discovery` |

> **精读 Agent Prompt**（method_agent / result_agent / discussion_agent / review_agent / general_agent / control_agent / query_rewrite）已内置在 `scripts/paper_qa_runtime/prompts/` 中，由 paper_qa_runtime 运行时直接读取。

## 加载原则

- 仅在被 SKILL.md 的步骤明确引用时才加载。
- 不要一次性全部读入上下文。
- 先读 `input-output-schema.md` 了解数据结构，再按当前 `taskIntent` 加载对应规则文件。
