# Generated Outputs

本目录用于保存本地生成的创新教案 JSON 和 Word-ready Markdown。

`sample-valid.json` 是当前 schema 下的最小可校验样例，用于验证 `scripts/validate_lesson_plan.py` 与 `references/quality-checklist.md` 的目标结构。其他历史生成产物可能来自旧 schema，复用前应重新运行 render 或 validate。

生成示例：

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/render_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving \
  --config agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json \
  --thinking \
  --model qwen3.5-122b-a10b
```

生成产物默认不提交。
