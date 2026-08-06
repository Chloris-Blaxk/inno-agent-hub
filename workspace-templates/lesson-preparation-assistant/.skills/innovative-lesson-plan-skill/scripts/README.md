# Scripts

## render_lesson_plan.py

调用生成模型生成创新教案 JSON 和 Word-ready Markdown。脚本会先做请求预检，再调用模型，随后重建 `export.markdown` 并运行本地校验。

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/render_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving \
  --config agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json \
  --thinking \
  --model qwen3.5-122b-a10b
```

环境变量：

- `DASHSCOPE_API_KEY`：必填，和 `agent_design/script/test_connection/test_qwen.py` 一致。
- `DASHSCOPE_BASE_URL`：可选，默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- `GENERATOR_MODEL` 或 `QWEN_MODEL`：可选，默认 `qwen3.5-122b-a10b`，也可用 `--model` 覆盖。
- `LESSON_PLAN_DEBUG_DIR`：可选，默认 `/tmp/lesson_plan_debug`，保存模型原始响应和 JSON 解析调试信息。

说明：

- `--thinking` 会向 Qwen 传入 `extra_body={"enable_thinking": true}`。
- `--reasoning-effort` 仅为兼容旧命令保留，Qwen 生成链路不使用该值。
- 默认导出 `.docx`（需系统安装 pandoc：`brew install pandoc` 或 `apt install pandoc`）；加 `--no-docx` 可跳过。

输出：

- `<output>.json`
- `<output>.md`
- `<output>.docx`（默认导出，`--no-docx` 时跳过）

## validate_lesson_plan.py

校验生成结果的根字段、活动总时长、行为动词层级、活动/目标/评价量规 ID 引用和创新类型专属结构。若请求中包含 `confirmedContext`，校验器会检查这些阶段一确认信息是否在输出设计中有体现；默认只给警告，可用 `--strict-context` 将警告提升为失败。

```bash
python3 agent_cases/innovative-lesson-plan-skill/scripts/validate_lesson_plan.py \
  agent_cases/innovative-lesson-plan-skill/generated-outputs/pbl-campus-water-saving.json \
  --request agent_cases/innovative-lesson-plan-skill/examples/pbl-campus-water-saving.json
```
