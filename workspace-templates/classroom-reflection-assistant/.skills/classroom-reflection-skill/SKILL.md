---
name: classroom-reflection-skill
description: 基于课堂逐字稿或课堂视音频进行证据化课堂教学反思、公开课点评与定性评价，输出结构化分析报告和可执行修改建议。即使用户提供自定义评价量规或说“用以下评价量规评价”，也必须执行完整分析流程并落盘，除非用户明确要求只评价。当用户继续交互时，可将分析结果优化为新的公开课教案，并基于优化教案生成教师上课逐字稿。
entryName: 课堂教学反思
entryToken: "@课堂教学反思"
displayName: 课堂教学反思
status: runnable_prototype
---

# 课堂教学反思智能体 Skill

## 场景定位

面向教师课后反思和公开课磨课，解决"评课凭感觉、建议不可操作"的问题。Agent 扮演**公开课点评专家、教研员与教学设计顾问**，基于课堂逐字稿进行证据化分析、量规定性评价和可执行修改建议；如果用户提供课堂视音频文件，先由脚本转写成逐字稿，再进入同一分析流程。用户需要时可继续优化为新教案，或基于优化后的教案生成教师上课逐字稿。

## 首批闭环

1. 识别用户提供的材料：逐字稿、学段、学科、课题、教学目标、原教案、自定义评价量规；若用户未提供学科，则先根据课题、教材内容、课堂关键词、活动类型和教学目标推断学科。
2. 课堂结构切分：根据逐字稿切分导入、新知建构、学生活动、教师讲解、评价反馈、结束等环节。
3. 证据化课堂分析：每个关键判断对应逐字稿中的具体课堂片段（判断→证据→影响→建议）。
4. 量规定性评价：优先使用用户自定义量表；否则按 `assets/rubric/rubric-map.json` 依据显式学科或推断学科匹配学科评价量规，无法识别或置信度低时使用通用量规。
5. 输出优点、关键问题和具体修改建议（具体到环节、原表现、怎么改、为什么改）。
6. 给出可直接替换的课堂语言（导入语、过渡语、提问语、追问语、评价语、总结语）。
7. 支持继续优化为新教案（用户表达意图时进入教案重构模式）。
8. 支持基于优化后的教案生成教师上课逐字稿（用户表达意图时进入逐字稿生成模式）。

## 触发与不可降级规则

只要用户调用本 skill，并提供课堂逐字稿、课堂转写文件、可读取的课堂记录或课堂视音频文件，就必须执行完整课堂反思闭环。用户提供自定义评价量规、说“用这个评价量规评价”“按以下量表评价”“重点评价”等，只表示**替换评价工具**，不表示只输出评价量规。

除非用户明确说“只评价、不需要分析报告、不需要落盘”，否则不得把任务降级为 TUI 中的即时评价回答。完整闭环必须包括：

1. 读取并理解逐字稿；如果输入是视音频，先调用 `classroom-reflection-media-tool` 转写为逐字稿。
2. 识别学科或推断学科。
3. 课堂结构切分。
4. 证据化课堂分析。
5. 使用用户自定义量规或匹配到的内置量规进行定性评价。
6. 输出主要优点、关键问题、具体修改建议和可替换课堂语言。
7. 按 `outputDir` 规则写入 Markdown 文件。

如果用户提供自定义评价量规，报告中必须注明“量规来源：用户自定义评价量规”，并保留自定义评价量规的维度和观察点；如原表含数字分值或权重，只作为内部理解维度重要性的参考，不在报告中输出数字分值、得分或总分。报告结构仍按本 skill 的完整报告结构输出。

## 当前数据闭环

当前已具备完整的 Prompt + 量规 + 输出模板闭环，并通过独立工具接入课堂视音频转写：

- 量规：学科公开课定性评价量规索引与量规文件（`assets/rubric/rubric-map.json`、`assets/rubric/*.md`）。
- Prompt：课堂点评 Prompt + 教案重构 Prompt + 教师逐字稿 Prompt（`assets/prompts/`）。
- 输出模板：课堂点评报告 + 优化版教案 + 教师上课逐字稿（`assets/output-templates/`）。
- 示例：内置数学课样例与初中语文《背影》输入样例。
- 真实数据：六年级语文「盼」公开课 205 条 ASR 转写。
- 执行方式：**脚本负责流程与文件，LLM 负责判断与写作**。必须优先使用 `scripts/run_reflection.py` 完成输入规范化、评价量规选择、输出目录创建、`run-state.json` 写入、精简 Prompt Payload 生成和输出校验。
- 视音频入口：`scripts/run_reflection.py prepare <media-file>` 会自动识别 `.mp4`、`.mov`、`.m4a`、`.mp3`、`.wav`、`.webm` 等本地媒体文件，调用 `agent_cases/classroom-reflection-media-tool/transcribe_media.py transcribe-realtime` 生成逐字稿 request，再继续原有课堂反思流程。若用户提供公网可访问媒体 URL（包括临时公网隧道 URL 或以后固定公网存储 URL），使用 `scripts/run_reflection.py prepare --media-url <url>` 走通义听悟离线转写。

## 脚本优先执行规则

报告生成模式下，不要直接手工决定输出目录、评价量规和 state。先运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare <input>
```

`<input>` 可以是 JSON / 纯文本逐字稿，也可以是本地课堂视音频文件。若输入后缀是 `.mp4`、`.mov`、`.m4a`、`.mp3`、`.wav`、`.webm` 等媒体类型，`prepare` 会先调用 `classroom-reflection-media-tool` 完成通义听悟转写，并把媒体转写 request、阿里云原始事件/产物和 raw 目录归档到本次输出目录的 `.internal/` 下，然后继续执行逐字稿规范化、评价量规选择和 prompt 生成。若用户提供的是公网媒体 URL，不要把 URL 当作本地 Path 传入，应运行 `prepare --media-url <url>`。LLM 不要直接读取或分析音视频内容。

每次新的独立课堂分析都必须让 `prepare` 分配新的可用案例目录；不要手写或复用上一次的目录名。如果用户显式指定案例 id，可添加 `--conversation-id <case-id>`；若该目录已存在，脚本仍会自动分配下一个编号。只有在用户明确要求回到某个既有案例，且你已经确认该案例 id，就是要复用的目录时，才允许同时使用 `--conversation-id <case-id> --reuse-existing`。同一案例后续优化教案和教师逐字稿不要重新运行 `prepare`，必须复用已生成的 `run-state.json`。

`prepare` 会强制完成：

1. 读取 JSON、纯文本逐字稿或 stdin。
2. 校验并规范化 `transcription[]`、`speaker/start/end/content`。
3. 生成 `lessonSlug` 与新的可用 `conversationId`。
4. 创建 `generated-outputs/<lesson-slug>/<conversation-id>/`。
5. 按自定义评价量规优先、学科/别名匹配、通用表回退的顺序选择评价量规。
6. 在输出目录根部写入小型 `run-state.json`，并在 `.internal/` 写入 `normalized-input.json` 和 `prompt-payload.md`。
7. 输出报告、教案、逐字稿的固定落盘路径。

然后读取 `run-state.json` 中 `promptPayloadPath` 指向的 `.internal/prompt-payload.md`，由 LLM 完成课堂判断、证据化分析、定性评价理由和 Markdown 报告写作。首次课堂分析默认必须覆盖完整逐字稿；只有在用户明确要求压缩材料或输入过长无法处理时，才允许使用逐字稿节选，并且必须读取 `normalized-input.json` 补足截断范围外的证据。写入报告后必须运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py validate --state <outputDir>/run-state.json
```

也可用脚本将草稿写入固定报告路径并校验：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py save-report --state <outputDir>/run-state.json --report <draft.md>
```

校验失败时继续修改报告，不要把失败报告当作最终产物。

校验返回 `{"status": "ok"}` 是报告生成模式的终止态。收到 `ok` 后不要再次运行同一个 `validate` 命令，不要继续轮询已经结束的后台任务，也不要重复读取同一份 state；直接向用户报告 `reportPath`、基本判断和整体表现。只有在校验返回 `fail` / `warn` 且你修改了报告内容之后，才允许再次运行 `validate`。

## 输入模式

```json
{
  "subject": "语文",
  "grade": "六年级",
  "topic": "《盼》",
  "lessonDurationMin": 45,
  "lessonType": "校内公开课",
  "objectives": ["理解围绕中心意思选材的方法"],
  "customRubric": null,
  "transcription": [
    {"id": 1, "content": "同学们，今天我们学习……", "start": 20.54, "end": 74.512, "speaker": "教师"},
    {"id": 2, "content": "怕不怕？怕。", "start": 74.512, "end": 75.82, "speaker": "学生"}
  ],
  "requirements": "重点关注问题设计与学生参与质量。"
}
```

### 必需输入

- `transcription[]`：课堂逐字稿，每条含 `id`、`content`、`start`（秒）、`end`（秒）、`speaker`（`"教师"` / `"学生"` / `"其他"`）。

### 媒体输入

如果用户提供本地课堂视音频文件路径，仍然只调用：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare <media-file>
```

不要手动先跑媒体工具。`prepare` 会自动判断输入类型：逐字稿按原流程读取；视音频先转写为逐字稿 request，再进入原流程。媒体转写中间文件会写入 `.internal/media-transcription-request.json`、`.internal/tingwu-direct-raw.json` 和 `.internal/tingwu-raw/`。

如果用户提供的是临时公网隧道 URL 或其他公网存储 URL，调用：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare --media-url <url>
```

这条路径走通义听悟离线转写，不需要本地实时推流；后续如果从临时隧道切换为学校服务器、NAS 反代或其他公网存储，只需要替换 URL 来源，skill 后续流程不变。

### 推荐输入

| 字段 | 说明 |
|------|------|
| `subject` / `grade` / `topic` | 学段、学科、课题名称 |
| `lessonDurationMin` | 课时长度 |
| `objectives` | 教学目标列表 |
| `lessonType` | 公开课类型：校内公开课 / 优质课 / 赛课 / 教研课 / 新教师汇报课 |
| `customRubric` | 用户自定义评价量规（提供时优先使用；只替换评价量规，不改变完整分析与落盘流程） |
| `requirements` | 用户自定义评价重点 |

### 信息缺失处理

如果用户只提供逐字稿，不反复追问。先完成初步分析，并在报告开头说明：

> 由于未提供学段、学科、教学目标和原教案，以下评价主要基于逐字稿中的课堂语言、互动结构、问题设计、任务组织、学生口头回应和教学推进进行判断。

## 输出模式

输出为 Markdown 报告，直接呈现给教师；如需结构化数据，可在末尾附 JSON 块。

### 输出落盘约定

完成报告生成前，**必须**先通过 `scripts/run_reflection.py prepare` 确定本次独立分析的 `<conversation-id>`，再将 Markdown 报告落盘到 `run-state.json` 中的 `reportPath`。`<conversation-id>` 用于绑定同一个案例中的报告、优化教案和教师逐字稿，不能在该案例的后续步骤中重新生成。

`<conversation-id>` 取值规则：

1. 新的独立报告生成默认不复用已有目录；如果默认案例目录已存在，脚本自动追加下一个编号。
2. 如果用户明确指定输出目录名或案例 id，使用用户指定值；若已存在且这是一次新的独立分析，脚本自动分配下一个编号。
3. 如果运行环境无法提供对话 id，则首次生成报告时从 `case-<lesson-slug>-001` 开始；若已存在则创建 `case-<lesson-slug>-002`、`case-<lesson-slug>-003` 等。
4. 只有明确继续某个已生成案例时，后续教案优化和逐字稿生成才不重新运行 `prepare`，直接读取原 `run-state.json` 复用目录。

生成时间只写在正文中，不再用时间戳作为目录名。同一节课的多次独立分析应使用不同 `<conversation-id>` / 案例 id；同一案例内的后续优化产物必须写入同一目录。

写入前必须先得到并使用脚本创建的完整输出目录：

```text
outputDir = agent_cases/classroom-reflection-skill/generated-outputs/<lesson-slug>/<conversation-id>/
```

如果 `outputDir` 不存在，先运行 `prepare` 创建该目录，再写入文件。**禁止**把报告、教案、逐字稿或分析结果直接写到 `generated-outputs/<lesson-slug>/` 根目录。

```
agent_cases/classroom-reflection-skill/generated-outputs/<lesson-slug>/<conversation-id>/reflection-report.md
```

`<lesson-slug>` 命名规则（按优先级）：

1. 如果用户在请求中明确指定了输出目录名，使用用户指定的。
2. 否则，由 `topic` 字段转换：去引号、空格转 `-`、保留中英文与数字。
3. 如 `topic` 缺失，则用输入文件名（去扩展名）作为 slug。

如用户继续要求"优化为新教案"，必须先读取同一 `<lesson-slug>/<conversation-id>/run-state.json`；如果已有 `reflection-report.md`，落盘到 state 指定的 `optimized-lesson-plan.md`，不得新建目录。只有用户明确要求重新分析、另开一版或指定新的案例 id 时，才创建新的 `<conversation-id>` 目录。

如用户继续要求"基于教案生成上课逐字稿 / 课堂逐字稿 / 试讲稿 / 教师话术"，必须优先读取同一 `<lesson-slug>/<conversation-id>/run-state.json` 和 `optimized-lesson-plan.md`，并落盘到 state 指定的 `teacher-transcript.md`。该文件必须标注为“拟用”，必须是教师易读的 Markdown 文档，不输出 JSON，不使用秒级时间轴，不得写成真实课堂实录。

报告、教案和逐字稿正文开头都应标注生成时间，例如 `生成时间：2026-05-28 15:30:12`。落盘完成后，在对话中用一行说明告知用户文件路径，并简要呈现报告关键结论（基本判断 + 整体表现），不必把整份 Markdown 重复贴出。

### 内部文件

输出目录根部只放面向用户的 Markdown 产物和 `run-state.json`。中间流程文件统一放入：

```text
generated-outputs/<lesson-slug>/<conversation-id>/.internal/
```

内部文件包括：

- `normalized-input.json`：完整规范化输入、统计、初步环节和评价量规内容；主要用于复现、校验和必要时核对证据。
- `prompt-payload.md`：报告生成材料包；首次课堂分析默认包含完整逐字稿，只有显式压缩时才保留节选。
- `validation-report.json`：校验结果。

节省 token 的原则：首次课堂分析不能牺牲完整证据；后续教案优化只读 `run-state.json` 与 `reflection-report.md`；教师逐字稿只读 `run-state.json` 与 `optimized-lesson-plan.md`。不要在后续步骤默认读取 `.internal/normalized-input.json` 或 `.internal/prompt-payload.md`。

### 报告结构

```markdown
# 课堂教学反思与公开课点评报告

## 一、基本判断
本节课整体属于：优秀 / 良好 / 合格 / 待改进。
一句话诊断：……
学科与量规：识别/推断学科为……；量规来源为……。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
| 一级指标 | 二级观察点 | 表现判断 | 判断依据 |
整体表现：优秀 / 良好 / 合格 / 待改进

## 四、主要优点
1. ……（附证据）

## 五、关键问题
### 问题 N：……
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语 / 提问语 / 追问语 / 评价语 / 总结语优化
```

其中“课堂流程复盘”的时间统一写成“分钟描述 + 秒数描述”：

- 单个时长：`5分25秒（325 秒）`
- 起止区间：`0分00秒-5分25秒（0-325 秒）`

保留原秒数，新增分钟表达，便于教师快速感知环节长度。

### 教案重构模式

当用户表达"继续优化成新教案"意图时，输出优化版公开课教案，包含：核心素养导向教学目标、重点难点、教学过程、关键问题链、课堂评价设计、板书设计、公开课亮点、相较原课堂的改进说明。

### 教师逐字稿生成模式

当用户表达"基于教案生成上课逐字稿""生成试讲稿""生成教师话术""写课堂逐字稿"等意图时，基于优化版公开课教案输出教师上课逐字稿，包含：生成时间、使用说明、按教学环节展开的教师话术、关键提问与追问、形成性评价语言、过渡语与应急话术、板书与课件提示、试讲前检查。

教师逐字稿必须服务于优化后的教案，不得另起炉灶改变教学目标、环节顺序和关键问题链。主体按环节组织，只写环节级大致时长（如"约5分钟"），不写秒级起止时间。学生发言只能写成"预设学生回应"或"可能回应"，避免将拟用稿误写成真实课堂实录。

## 默认评价量规

当用户没有提供自定义评价量规时，由 `scripts/run_reflection.py prepare` 读取 `assets/rubric/rubric-map.json`。如果输入中有明确 `subject`，脚本按 `subject` 与 `aliases` 匹配学科评价量规；如果没有明确 `subject`，LLM 可先推断候选学科并通过 `--inferred-subject` 交给脚本映射，或由脚本根据课题、逐字稿内容、教学目标和关键词做保守推断。无法识别、只能粗略判断或置信度低时，使用 `00_通用.md`。所有内置量规均为音频/逐字稿定性评价量规，只评价课堂语言、互动结构、任务组织、学生口头回应和反馈证据，表头统一为“一级指标 / 二级观察点 / 评价要点 / 表现判断”。

匹配顺序：

1. 用户提供自定义评价量规时，使用用户评价量规。
2. `subject` 与某个 `rubrics[].subject` 完全一致时，使用该学科文件。
3. `subject` 命中某个 `rubrics[].aliases` 时，使用该学科文件。
4. `subject` 缺失时，先推断 `inferredSubject`，并用同样规则匹配 `rubrics[].subject` 或 `rubrics[].aliases`。
5. 推断结果不明确、多个学科并列、置信度低或仍未命中时，使用 `default` 指定的 `00_通用.md`。

学科识别、评价量规匹配、课堂材料和评价量规确认必须在内部完成，并记录在 `run-state.json` 和 `prompt-payload.md` 中。面向教师的报告不要单独输出“评价依据”章节；只在“基本判断”末尾用一句话简要呈现“学科与量规”，说明识别/推断学科和量规来源。不要展开内部路由字段、匹配规则或证据限制说明。

定性评价结果只列音频/逐字稿可证实的观察点。即使用户自定义量规包含只能通过现场或画面判断的观察点，也不要把这些观察点展开到评价表、主要优点、关键问题或修改建议中；可以把相近内容转化为可听证据维度，例如任务说明是否清楚、学生是否能口头说明方法、教师反馈是否具体。

整体表现只使用定性描述：优秀 / 良好 / 合格 / 待改进。不得输出百分制总分、单项得分或排名百分位。

## 资源加载顺序

1. 先读本文件，确认任务是课堂教学反思 / 公开课点评。
2. 报告生成模式先运行 `scripts/run_reflection.py prepare ...`，不要跳过。
3. 读脚本生成的 `.internal/prompt-payload.md`；它已内嵌课堂点评提示词、报告模板、匹配评价量规、逐字稿、基础统计、初步环节和固定落盘路径。
4. 如用户提供自定义评价量规，`prompt-payload.md` 中的量规来源必须是“用户自定义评价量规”；不得再用内置评价量规覆盖它。
5. 输出报告后运行一次 `scripts/run_reflection.py validate --state <outputDir>/run-state.json`，按校验结果修正报告；若返回 `status: ok`，立即进入最终回复，不要重复校验。
6. 仅在用户要求"优化为新教案"时，再读 `references/core-literacy-map.json`、`assets/prompts/lesson_rewrite_prompt.md` 与 `assets/output-templates/lesson_plan_template.md`；教学目标按学段和学科匹配，只使用 `verificationStatus: "standard_declared"` 的学科核心素养条目，并参考匹配条目的 `objectiveWritingHints` 组织目标表述。
7. 仅在用户要求"基于教案生成上课逐字稿"时，再读 `assets/prompts/teacher_transcript_prompt.md` 与 `assets/output-templates/teacher_transcript_template.md`；优先基于同一 `<conversation-id>` 目录中的 `optimized-lesson-plan.md` 生成。
8. 输出前对照 `references/quality-checklist.md` 自检。

## 调用方式

用户可以用自然语言调用本 skill，例如：

```text
@agent_cases/classroom-reflection-skill/ 使用该 skill 对 /path/to/lesson.mp4 这个视频进行分析
```

或：

```text
@课堂教学反思 使用该 skill 对 /path/to/lesson.mp4 这个视频进行分析
```

执行时不要要求用户改成命令行。Agent 必须从用户话语中提取本地文件路径或公网媒体 URL，判断输入是逐字稿、本地视音频还是公网视音频 URL。

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare <extracted-input-path>
```

若提取到的是 `http://` 或 `https://` 媒体 URL，改用：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py prepare --media-url <extracted-url>
```

后续步骤：

1. 用户上传逐字稿（JSON / 纯文本）或课堂视音频文件，或在自然语言里指定文件路径。
2. 从用户话语中提取文件路径或公网 URL；如果有多个候选，优先使用明确被“这个视频 / 这个音频 / 逐字稿”修饰的输入。
3. 本地路径运行 `scripts/run_reflection.py prepare <extracted-input-path>`；公网媒体 URL 运行 `scripts/run_reflection.py prepare --media-url <extracted-url>`。脚本先判断输入类型，逐字稿直接规范化，视音频先调用 media tool 转写成逐字稿 request，再创建 `outputDir`、`run-state.json` 和 `.internal/` 中的中间文件。
4. LLM 读取 `run-state.json` 中 `promptPayloadPath` 指向的 `.internal/prompt-payload.md`，按 prompt 流程做分析、定性评价、生成 Markdown 报告，并写入 `run-state.json` 的 `reportPath`。
5. 运行一次 `scripts/run_reflection.py validate --state <outputDir>/run-state.json`；如果返回 `status: ok`，不要再检查状态，直接告知用户报告路径和关键结论。
6. 用户继续说"优化成新教案"时，LLM 读取同一目录的 `run-state.json` 与 `reflection-report.md`，进入教案重构模式，并写入 state 指定的 `optimized-lesson-plan.md`。
7. 用户继续说"基于教案生成上课逐字稿"时，LLM 读取同一目录的 `run-state.json` 与 `optimized-lesson-plan.md`，进入教师逐字稿生成模式，并写入 state 指定的 `teacher-transcript.md`。

样例输入：

- `examples/math-g5-fraction-reflection.json` — 内置数学课样例（24 条转写）

## 边界

- 媒体输入只用于语音转写；不承诺视频动作识别、语调分析或表情识别。
- 评价报告只评价逐字稿可支持的课堂语言、互动结构、任务组织、学生口头回应和反馈证据；逐字稿无法判断的现场细节不要进入定性评价表或评价结论。
- 不替教师做主观负评；语气专业、建设性。
- 不输出百分制分数、单项得分或排名百分位；定性表现判断必须与证据匹配。
- 用户提供自定义评价量规时优先使用用户评价量规。
- 用户提供自定义评价量规时，只替换评价维度和观察点；如原表含分值或权重，只作内部参考，不在报告中呈现；其中无法由逐字稿判断的观察点不进入评价结果。仍必须完成课堂结构切分、证据化分析、具体建议、可替换语言和 Markdown 落盘。
- 教案重构时保留原课堂中有价值的部分，修改应服务于真实课堂可实施性。
- 教师逐字稿是拟用课堂语言，不冒充真实课堂实录。

## 质量标准

- 所有关键评价都基于逐字稿证据，不脱离文本泛泛而谈。
- 只把逐字稿可判断内容写入评价结论；无法由音频/逐字稿判断的现场细节不进入定性评价表。
- 给出分维度定性评价，每个维度有判断依据。
- 每个关键问题有证据、影响和修改方向。
- 建议具体到课堂环节和教师语言，不说"加强互动""突出学生主体"等空话。
- 可替换课堂语言自然，适合真实课堂，不过度书面化。
- 教案重构时，教学目标必须使用核心素养导向写法，不使用三维目标；核心素养本身必须来自对应学段、对应学科课程标准。
- 教师逐字稿必须与优化教案一致，语言自然可说，普通教师容易读懂和试讲；不输出 JSON，不写秒级时间轴，关键问题、追问、评价语和板书提示完整。
- 输出对照 `references/quality-checklist.md` 自检通过。
