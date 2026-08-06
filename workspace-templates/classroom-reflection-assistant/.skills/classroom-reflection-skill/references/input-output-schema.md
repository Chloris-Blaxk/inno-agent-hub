# 输入输出约定

本文档只描述当前真实流程。`classroom-reflection-skill` 不再生成结构化 `reflection-report.json`，最终面向教师的产物均为 Markdown。

## 输入 Request JSON

`scripts/run_reflection.py prepare` 接受 JSON 对象、JSON 转写数组、纯文本逐字稿或 stdin。推荐输入为 JSON 对象：

```json
{
  "subject": "语文",
  "grade": "七年级",
  "topic": "紫藤萝瀑布",
  "lessonDurationMin": 45,
  "lessonContext": {
    "objectives": [
      "把握托物言志写法",
      "体会作者情感变化"
    ],
    "stages": [
      {"name": "导入", "startSec": 0, "endSec": 300},
      {"name": "文本研读", "startSec": 300, "endSec": 1800}
    ]
  },
  "customRubric": null,
  "requirements": "重点关注问题链、学生表达和形成性评价。",
  "transcription": [
    {
      "id": 1,
      "speaker": "教师",
      "start": 0.0,
      "end": 8.2,
      "content": "同学们，今天我们学习《紫藤萝瀑布》。"
    },
    {
      "id": 2,
      "speaker": "学生",
      "start": 8.5,
      "end": 12.0,
      "content": "这是一篇散文。"
    }
  ]
}
```

### 必填字段

| 字段 | 说明 |
|---|---|
| `transcription[]` | 课堂逐字稿数组，至少 1 条有效发言。 |
| `transcription[].content` | 发言文本，不能为空。 |
| `transcription[].speaker` | 推荐为 `教师`、`学生` 或 `其他`。脚本会兼容常见别名。 |
| `transcription[].start` | 开始时间，单位为秒；缺失时脚本会按前一条推断并写入 warning。 |
| `transcription[].end` | 结束时间，单位为秒；缺失或无效时脚本会推断并写入 warning。 |

### 推荐字段

| 字段 | 说明 |
|---|---|
| `subject` | 学科。缺失时脚本会按课题、目标和逐字稿关键词保守推断；无法可靠识别时使用通用评价量规。 |
| `grade` | 年级或学段，用于报告表述和后续核心素养目标匹配。 |
| `topic` | 课题，用于生成 `lessonSlug` 和报告元信息。 |
| `lessonDurationMin` | 课时长度，缺省时按转写最后一条 `end` 推断。 |
| `lessonContext.objectives[]` | 原教学目标，供报告和后续教案优化参考。 |
| `lessonContext.stages[]` | 已知课堂环节时间窗；缺失时脚本会生成初步环节。 |
| `requirements` | 用户补充的分析重点。 |
| `customRubric` | 用户自定义评价量规；提供后优先于内置学科评价量规。 |

### Speaker 标准化

脚本会把常见说话人写法标准化为：

| 标准值 | 常见输入 |
|---|---|
| `教师` | `教师`、`老师`、`teacher`、`T` |
| `学生` | `学生`、`生`、`student`、`S` |
| `其他` | `其他`、`other`，以及无法识别的 speaker |

如果所有有效发言都被识别为 `其他`，脚本会报错，因为没有足够课堂数据可分析。

## Prepare 输出

运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare <request.json>
```

会创建：

```text
generated-outputs/<lesson-slug>/<conversation-id>/
  run-state.json
  .internal/
    normalized-input.json
    prompt-payload.md
```

### `run-state.json`

`run-state.json` 是后续流程的唯一连续性锚点。典型字段：

```json
{
  "skill": "classroom-reflection-skill",
  "createdAt": "2026-06-08T10:00:00",
  "lessonSlug": "zitengluo-pubush",
  "conversationId": "case-zitengluo-pubush-001",
  "inputFile": "/path/to/request.json",
  "generatedRoot": ".../generated-outputs",
  "outputDir": ".../generated-outputs/zitengluo-pubush/case-zitengluo-pubush-001",
  "rubricSource": "匹配评价量规 `01_语文.md`",
  "matchedSubject": "语文",
  "matchedRubric": "01_语文.md",
  "rubricPath": ".../assets/rubric/01_语文.md",
  "reportPath": ".../reflection-report.md",
  "lessonPlanPath": ".../optimized-lesson-plan.md",
  "teacherTranscriptPath": ".../teacher-transcript.md",
  "internalDir": ".../.internal",
  "promptPayloadPath": ".../.internal/prompt-payload.md",
  "normalizedInputPath": ".../.internal/normalized-input.json",
  "validationReportPath": ".../.internal/validation-report.json",
  "warnings": []
}
```

注意：没有 `reportJsonPath`。本 skill 不再生成 `reflection-report.json`。

### `.internal/normalized-input.json`

内部复现文件，包含：

- 规范化后的 request。
- 脚本统计信息。
- 初步课堂环节。
- 学科推断结果。
- 本次实际使用的评价量规内容。

默认不要在后续教案优化和教师逐字稿生成时重新读入该文件，除非需要核对原始证据。

### `.internal/prompt-payload.md`

报告生成材料包，包含：

- 报告生成提示词。
- 报告模板。
- 本次评价量规。
- 统计和初步环节。
- 用户请求元数据。
- 逐字稿。
- 固定落盘路径。

首次生成课堂反思报告时，LLM 应读取该文件，并把最终 Markdown 写入 `run-state.json` 的 `reportPath`。

## 面向用户的 Markdown 产物

输出目录根部只保留面向用户的 Markdown 产物和 `run-state.json`：

```text
generated-outputs/<lesson-slug>/<conversation-id>/
  run-state.json
  reflection-report.md
  optimized-lesson-plan.md
  teacher-transcript.md
  .internal/
```

### `reflection-report.md`

课堂教学反思与公开课点评报告。必需章节：

1. `## 一、基本判断`
2. `## 二、课堂流程复盘`
3. `## 三、定性评价结果`
4. `## 四、主要优点`
5. `## 五、关键问题`
6. `## 六、具体修改建议`
7. `## 七、可直接替换的课堂语言`

报告正文开头必须包含生成时间。课堂流程复盘中的时间格式应同时包含分钟描述和秒数描述：

```text
0分00秒-5分25秒（0-325 秒）
```

不单独输出“评价依据”章节；学科识别和量规来源只在“基本判断”中用一句“学科与量规”简要说明。

### `optimized-lesson-plan.md`

仅当用户继续要求“优化成新教案”时生成。必须复用同一目录的 `run-state.json` 和 `reflection-report.md`，不得重新运行 `prepare` 创建新目录。

教案目标使用核心素养导向写法，不使用“三维目标”。核心素养应按学段和学科查 `references/core-literacy-map.json`，只直接使用 `verificationStatus: "standard_declared"` 的条目。

### `teacher-transcript.md`

仅当用户继续要求“基于教案生成上课逐字稿 / 试讲稿 / 教师话术”时生成。必须复用同一目录的 `run-state.json` 和 `optimized-lesson-plan.md`。

该文件是“拟用”教师课堂语言，不是真实课堂实录。输出为教师易读 Markdown，不输出 JSON，不使用秒级时间轴，只按教学环节标注大致时长。

## 校验输出

写入 `reflection-report.md` 后必须运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py validate \
  --state <outputDir>/run-state.json
```

或使用：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py save-report \
  --state <outputDir>/run-state.json \
  --report <draft.md>
```

校验结果写入：

```text
generated-outputs/<lesson-slug>/<conversation-id>/.internal/validation-report.json
```

`validation-report.json` 是内部校验文件，不是给教师阅读的报告。

## 失败与降级

| 情况 | 行为 |
|---|---|
| `transcription` 缺失或为空 | 报错，要求补充逐字稿。 |
| 某条发言 `content` 为空 | 跳过该条并写入 warning。 |
| `start` 缺失或不是数字 | 脚本按前一条结束时间推断并写入 warning。 |
| `end` 缺失或不大于 `start` | 脚本按文本长度估算并写入 warning。 |
| speaker 无法识别 | 标准化为 `其他` 并写入 warning。 |
| 全部有效发言都是 `其他` | 报错，停止流程。 |
| 学科无法可靠识别 | 回退到 `00_通用.md`。 |
| 用户提供 `customRubric` | 优先使用自定义评价量规，但仍执行完整课堂反思流程和落盘；如原量规含数字权重，只作内部参考，不在报告中输出。 |
