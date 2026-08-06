# References

本目录保存研究选题生成 Skill 的独立数据契约和规则。该 Skill 可以复用科研线共享对象命名，但运行时不要求读取文献阅读、论文写作或项目申报 Skill 的 references。

统一结构来源：

- `agent_design/improvement/research-line-unified-skill-data-structure.md`

## 独立 references 清单

- `input-output-schema.md`：统一请求/输出信封、`TeacherProfile`、`SourceMaterial`、`MaterialDigest`、`ResearchTopicCandidate` schema。
- `material-parsing-rules.md`：论文、案例、反思、成果材料解析规范。
- `teacher-profile-schema.json`：最小教师画像字段和可选约束。
- `topic-evaluation-rubric.json`：创新性、已有基础、可行性和差异化量规。
- `policy-hotspot-tags.json`：政策热点与资助方向标签。
- `grant-title-samples.json`：历年立项题目样本，用于重复度和差异化判断。
- `practice-problem-bank.json`：学校/区域实践问题样例，用于规划性选题角度、风险和补资料清单。
- `quality-checklist.md`：材料依据、选题类型、可行性和不得虚构已有成果检查。

## 独立性边界

- 可接收用户直接提供的 `teacherProfile` 和 `input.materials` 独立生成选题。
- 文献元数据索引只能作为增强数据；没有文献索引时仍可输出保守选题。
- 不得虚构教师已有成果、论文、课题、获奖或学校条件。
