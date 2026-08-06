# Scripts

## render_exercise_set.py

根据请求 JSON 和 `references/` 中的内部示例数据生成结构化练习/作业/测验。

```bash
python3 agent_cases/exercise-generation-skill/scripts/render_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/math-g5-fraction-layered-homework \
  --config agent_cases/exercise-generation-skill/examples/math-g5-fraction-layered-homework.json
```

输出：

- `<output>.json`：结构化练习/作业数据。
- `<output>.md`：教师可读题目、答案解析和讲评建议。

支持：

- `layerMix`、`questionTypeMix`、`difficultyMix` 蓝图目标。
- `strictBlueprint` 严格蓝图模式。
- `replacementSuggestions` 换题建议。

默认生成后会调用 `validate_exercise_set.py` 校验。可通过 `--no-validate` 跳过。

## validate_exercise_set.py

校验已有 JSON 产物：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_exercise_set.py \
  agent_cases/exercise-generation-skill/generated-outputs/math-g5-fraction-layered-homework.json
```

检查项：

- 根字段完整性。
- 题量与题目 ID。
- 题干重复。
- 答案、分步解析、知识点、题型、难度、错因和评分点。
- 分层作业 A/B/C 层题量。
- 知识点覆盖。
- 超纲风险。
- 题型比例和难度比例。
- 换题建议字段。

## validate_reference_data.py

校验 `references/` 中的基础数据：

```bash
python3 agent_cases/exercise-generation-skill/scripts/validate_reference_data.py
```

检查项：

- 课标、知识点、教材课时、错因、相似题组和题库之间的 ID 引用。
- 每道题的题干、答案、解析、评分点、知识点和错因完整性。
- 题目 `sourceId` 是否重复。
- 是否残留异常分隔符。
- 每个知识点题量是否达到默认 30 道。
