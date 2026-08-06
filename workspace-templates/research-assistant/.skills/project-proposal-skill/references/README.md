# References

本目录保存项目申报助手 Skill 的独立数据契约和规则。该 Skill 可以复用科研线共享对象命名，但运行时不要求读取研究选题、文献阅读或论文写作 Skill 的 references。

统一结构来源：

- `agent_design/improvement/research-line-unified-skill-data-structure.md`

## 独立 references 清单

- `input-output-schema.md`：统一请求/输出信封、`SourceMaterial`、`ProjectFactTable`、`DocumentDraft`、`DocumentSet`、跨文档一致性与成果汇报辅助 schema。
- `project-fact-schema.json`：项目事实表字段、缺失项和冲突检测规则。
- `document-templates.json`：项目申报书、结题报告、成果汇报模板。
- `review-rubrics.json`：评审标准与分值权重。
- `budget-rules.json`：经费预算科目、适用范围和常见错误。
- `consistency-check-rules.md`：跨文档事实一致性、冲突检测和文档生成降级规则。
- `sanitized-case-patterns.json`：脱敏成功案例结构样例，只用于组织方式参考。
- `policy-hotspot-tags.json`：政策热点与资助方向标签。
- `quality-checklist.md`：事实一致性、三文档章节完整性、预算合规、成果汇报展示辅助和不得虚构成果检查。

## 独立性边界

- 可接收用户直接提供的 `input.projectMaterials` 独立抽取项目事实表并生成目标文档。
- 长文生成前必须先形成或校验 `ProjectFactTable`。
- 不得虚构成果、数据、团队经历、经费明细或中标概率。
