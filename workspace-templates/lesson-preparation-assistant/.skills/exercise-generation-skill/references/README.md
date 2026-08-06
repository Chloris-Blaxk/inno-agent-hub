# References

本目录用于沉淀出题智能体的规则与内部示例数据。当前已支持五年级数学「分数的加法和减法」单元的出题闭环。

当前题库覆盖 3 个连续知识点：

- `math-g5-fraction-same-denominator-add`：同分母分数加减法，30 题。
- `math-g5-fraction-add`：异分母分数加减法，30 题。
- `math-g5-fraction-application`：分数加减法应用，30 题。

## 文件说明

- `input-output-schema.md`：出题请求、题目对象、练习对象、覆盖报告 schema。
- `blueprint-rules.md`：课堂练习、分层作业、阶段测验、专题练习的蓝图规则。
- `quality-checklist.md`：超纲、答案、解析、题型比例和知识点覆盖检查表。
- `curriculum-standards.json`：内部示例课标条目与超纲边界。
- `knowledge-graph.json`：内部示例知识点、前置知识、常见错因和课标映射。
- `textbook-map.json`：内部示例教材版本、单元、课时和教学边界。
- `seed-question-bank.json`：结构化种子题库。
- `difficulty-rules.json`：A/B/C 分层、难度和 taskType 默认题量规则。
- `misconception-tags.json`：高频错因、症状、原因和补救建议。
- `similar-question-groups.json`：相似题组、换题规则和变式替换依据。

## 数据校验

基础数据改动后先运行：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_reference_data.py
```

## 扩展建议

1. 先把一个学科连续 2-3 个单元补成真实授权数据。
2. 每个知识点至少准备 30-60 道结构化种子题，覆盖 A/B/C 三层和常见题型。
3. 每道题都保留答案、分步解析、评分点和错因标签，方便后续复用到拍题答疑和知识点讲解。
