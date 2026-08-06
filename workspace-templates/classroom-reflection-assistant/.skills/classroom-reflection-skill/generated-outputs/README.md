# Generated Outputs

本目录用于保存本地生成的课堂反思报告、行为统计和改进片段。生成产物默认不提交。

产出路径约定：

```text
generated-outputs/<lesson-slug>/<conversation-id>/reflection-report.md
generated-outputs/<lesson-slug>/<conversation-id>/optimized-lesson-plan.md
generated-outputs/<lesson-slug>/<conversation-id>/teacher-transcript.md
generated-outputs/<lesson-slug>/<conversation-id>/run-state.json
generated-outputs/<lesson-slug>/<conversation-id>/.internal/
```

`<conversation-id>` 由 `scripts/run_reflection.py prepare` 为每次新的独立分析分配；如果默认案例目录已存在，脚本会自动追加下一个编号。只有明确继续某个既有案例时，后续教案和逐字稿才复用该案例的 `run-state.json`。生成时间只写在各 Markdown 正文开头，不用于区分目录。

写入前必须先创建或确认完整目录：

```text
generated-outputs/<lesson-slug>/<conversation-id>/
```

不要把产物直接写到 `generated-outputs/<lesson-slug>/` 根目录。

`.internal/` 用于保存中间流程文件，例如 `normalized-input.json`、`prompt-payload.md` 和 `validation-report.json`。这些文件用于复现、校验和必要时核对证据。首次课堂分析通过 `prompt-payload.md` 覆盖完整课堂材料；后续优化教案优先读取 `reflection-report.md`，生成教师逐字稿优先读取 `optimized-lesson-plan.md`，不要默认重新读入内部大文件。

`teacher-transcript.md` 是基于优化教案生成的拟用教师上课逐字稿，不代表真实课堂实录。

## 视音频转换中间产物
统一放在/.internal/中
  - tingwu-direct-raw.json：通义听悟 WebSocket 直接返回的原始事件列表，最原始。
  - tingwu-raw/tingwu-realtime-events.json：同样是原始事件列表，作为 raw-dir 归档。
  - tingwu-raw/tingwu-realtime-transcription-normalized.json：把实时事件整理成 Sentences 后的中间文本结构。
  - media-transcription-request.json：最终给 classroom-reflection-skill 使用的标准 request JSON。