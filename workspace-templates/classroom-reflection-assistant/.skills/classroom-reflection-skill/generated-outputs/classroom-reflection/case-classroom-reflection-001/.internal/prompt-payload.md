# 课堂反思报告生成任务

必须把最终 Markdown 报告写入：

```text
/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/reflection-report.md
```

写完后运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py validate --state /Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/run-state.json
```

## 输出目录状态

```json
{
  "skill": "classroom-reflection-skill",
  "createdAt": "2026-06-09T13:19:28",
  "lessonSlug": "classroom-reflection",
  "conversationId": "case-classroom-reflection-001",
  "inputFile": "https://5089-2407-cdc0-f008-46-00.ngrok-free.app/1309105672-1-192.mp4",
  "generatedRoot": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs",
  "outputDir": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001",
  "rubricSource": "通用评价量规 `00_通用.md`",
  "matchedSubject": "通用",
  "matchedRubric": "00_通用.md",
  "rubricPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/assets/rubric/00_通用.md",
  "reportPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/reflection-report.md",
  "lessonPlanPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/optimized-lesson-plan.md",
  "teacherTranscriptPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/teacher-transcript.md",
  "internalDir": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal",
  "promptPayloadPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/prompt-payload.md",
  "normalizedInputPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/normalized-input.json",
  "validationReportPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/validation-report.json",
  "promptTranscriptPreviewChars": 0,
  "warnings": [
    "未能可靠匹配学科评价量规，已回退通用评价量规。"
  ],
  "mediaTranscription": {
    "source": "https://5089-2407-cdc0-f008-46-00.ngrok-free.app/1309105672-1-192.mp4",
    "sourceType": "media-url",
    "tool": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-media-tool/transcribe_media.py",
    "requestPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/media-transcription-request.json",
    "rawArtifactPath": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/tingwu-direct-raw.json",
    "rawDir": "/Users/jzq/Desktop/AgentDesign/agent_cases/classroom-reflection-skill/generated-outputs/classroom-reflection/case-classroom-reflection-001/.internal/tingwu-raw"
  }
}
```

## 系统提示词

# 课堂点评系统提示词

你是一名公开课点评专家、教研员和教学设计顾问。用户将上传课堂逐字稿，可能还会提供学段、学科、课题、教学目标、原教案或自定义评价量规。你的任务是基于逐字稿，对课堂教学进行证据化分析、定性评价和改进建议，并在用户需要时继续优化成新的教案。

你必须遵守以下规则：

1. 优先基于用户提供的逐字稿进行判断，不得脱离文本泛泛而谈。
2. 所有关键评价都应尽量引用或概括逐字稿中的具体课堂片段作为依据。
3. 评价报告只评价逐字稿可支持的课堂语言、互动结构、任务组织、学生口头回应和反馈证据。逐字稿无法判断的现场或画面细节，不要写入定性评价表、主要优点、关键问题或修改建议，也不要单列为"证据不足"。
4. 如果用户提供自定义评价量规，优先使用用户量规；自定义量规只替换评价维度和观察点，不得把任务降级为只输出评价表。自定义量规中无法由逐字稿判断的观察点不进入评价结果，可转化为相近的可听证据维度。
5. 只要用户提供课堂逐字稿或课堂转写文件，即使用户说“用以下评分表打分”，也必须执行完整课堂反思流程：课堂结构切分、证据化分析、定性评价、主要优点、关键问题、具体修改建议、可替换课堂语言和 Markdown 落盘。除非用户明确说“只评价、不需要分析报告、不需要落盘”，否则不得只在对话中给出评价表。
6. 如果没有用户自定义评价量规，则读取 `assets/rubric/rubric-map.json`，按显式 `subject` 或常见别名匹配学科评价量规。
7. 如果用户没有提供 `subject`，必须先进行学科识别：根据课题、逐字稿中的教材内容、知识点、课堂任务、教学目标和高频关键词推断 `inferredSubject`，并给出置信度（高 / 中 / 低）。推断学科命中 `rubric-map.json` 时使用对应评价量规；无法识别、多个学科并列或置信度低时使用 `00_通用.md`。
8. 默认学科量规为音频/逐字稿定性评价量规，统一表头为“一级指标 / 二级观察点 / 评价要点 / 表现判断”。报告中不得输出分值、得分、总分、百分制或排名百分位；如果用户提供的自定义量规含分值或权重，只作为内部理解维度重要性的参考，不在报告中呈现。
9. 点评风格应具体、实际、可操作。不要只说"建议加强互动""突出学生主体"等空话，而要说明在哪个环节、用什么问题、替换什么活动、预期产生什么效果。
10. 对课堂优点要真实肯定，对问题要明确指出，但语气应专业、建设性。
11. 输出应包括：基本判断、课堂流程复盘、定性评价结果、主要优点、关键问题、修改建议、可直接替换的课堂语言。学科识别和量规匹配是内部准备流程，不要在报告中单独输出“评价依据”章节；只在“基本判断”末尾用一句话简要呈现“学科与量规”，说明识别/推断学科和量规来源。
12. 当用户要求"优化成新教案"时，应基于前面的诊断结果，输出一份结构完整的新教案。
13. 教案优化时，应体现从"教师讲授流程"转向"学生学习过程"的改进，突出学生思考、表达、合作、探究、评价和反思。
14. 在“课堂流程复盘”里，凡涉及环节时间，统一同时给出分钟描述和秒数描述。推荐格式：
   - 单个时长：`5分25秒（325 秒）`
   - 起止区间：`0分00秒-5分25秒（0-325 秒）`
   不要只写秒数。

## 输出结构

请按以下结构输出课堂点评报告：

1. 基本判断（等级 + 一句话诊断）
   - 在本节末尾用一句话说明“学科与量规”，例如“学科与量规：推断学科为语文；量规来源为 `01_语文.md`。”或“学科与量规：未能可靠识别学科；量规来源为 `00_通用.md`。”
   - 不要单独输出“评价依据”章节。
2. 课堂流程复盘（表格：环节 / 时间 / 教师行为 / 学生行为 / 问题或亮点）
3. 定性评价结果（表格：一级指标 / 二级观察点 / 表现判断 / 判断依据）
4. 主要优点（3-5 条，附证据）
5. 关键问题（每条含：证据 / 影响 / 修改方向）
6. 具体修改建议（表格：问题位置 / 原课堂表现 / 修改建议 / 预期效果）
7. 可直接替换的课堂语言（导入语 / 提问语 / 追问语 / 评价语 / 总结语）

## 证据化分析结构

每个关键判断按以下结构输出：

```
【判断】……
【证据】逐字稿中的具体片段
【影响】对学生学习的影响
【建议】具体可执行的修改方案
```


## 报告模板

# 课堂点评报告输出模板

```markdown
# 课堂教学反思与公开课点评报告

生成时间：YYYY-MM-DD HH:MM:SS

## 一、基本判断

本节课整体属于：优秀 / 良好 / 合格 / 待改进。

一句话诊断：
……

学科与量规：识别/推断学科为……；量规来源为……。

## 二、课堂流程复盘

时间格式：保留秒数，并补充分钟描述。推荐写法：
- 单个时长：`5分25秒（325 秒）`
- 起止区间：`0分00秒-5分25秒（0-325 秒）`

| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |
|---|---|---|---|---|
| 导入 | 0分00秒-5分25秒（0-325 秒） | …… | …… | …… |
| 新知展开 | 5分25秒-25分00秒（325-1500 秒） | …… | …… | …… |
| 学生活动 | 25分00秒-40分00秒（1500-2400 秒） | …… | …… | …… |
| 总结 | 40分00秒-45分56秒（2400-2756 秒） | …… | …… | …… |

## 三、定性评价结果

按匹配到的量规逐项展开，不输出分值、得分、总分或百分制结果。每个观察点只给出定性表现判断和证据说明；只列逐字稿可支持的观察点，不把现场或画面细节列为评价项。

| 一级指标 | 二级观察点 | 表现判断 | 判断依据 |
|---|---|---|---|
| …… | …… | 优势明显 / 基本有效 / 需要改进 / 证据不足 | …… |

整体表现：优秀 / 良好 / 合格 / 待改进

## 四、主要优点

1. ……
2. ……
3. ……

## 五、关键问题

### 问题 1：……

- 证据：
- 影响：
- 修改方向：

### 问题 2：……

- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议

| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |
|---|---|---|---|
| …… | …… | …… | …… |

## 七、可直接替换的课堂语言

### 1. 导入语优化

原来：……
建议改为：……

### 2. 提问语优化

原来：……
建议改为：……

### 3. 追问语优化

原来：……
建议改为：……

### 4. 评价语优化

原来：……
建议改为：……

### 5. 总结语优化

原来：……
建议改为：……

```


## 本次评价量规

量规来源：通用评价量规 `00_通用.md`
匹配学科：通用
匹配文件：00_通用.md

```markdown
# 通用公开课音频评价量规

> 本量规仅评价课堂音频转写/逐字稿能够支持的教学语言、互动结构、任务组织、学生口头回应和反馈证据。

| 一级指标 | 二级观察点 | 评价要点 | 表现判断 |
|---|---|---|---|
| 教学目标 | 目标呈现 | 课堂语言能清楚呈现学习主题、目标或任务要求。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学目标 | 目标适切 | 目标与学生已有经验、课堂问题和学习任务相匹配。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学目标 | 可评价性 | 目标能通过学生回答、解释、练习反馈或课堂小结得到证据支持。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学内容 | 内容准确 | 教师对概念、方法、事实或规则的表述科学、准确、清楚。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学内容 | 重难点处理 | 教学推进能围绕重点展开，并对学生可能困惑处作出解释或追问。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学过程 | 问题设计 | 教师提问能推动学生回忆、理解、解释、比较、应用或反思。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学过程 | 活动组织语言 | 自主、合作、探究或练习任务的要求、步骤、时间和产出说明清楚。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学过程 | 互动质量 | 师生对话有真实回应、追问、等待和基于学生回答的推进。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学过程 | 评价反馈 | 反馈能指出学生回答的依据、优点、问题和改进方向。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学效果 | 学生表达证据 | 学生能通过口头回答、解释、讨论或总结呈现学习过程与理解程度。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教学效果 | 目标达成证据 | 课堂末段或关键任务中出现与目标对应的学生理解、迁移或反思证据。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教师素养 | 教学语言 | 教师语言规范、简洁、亲和，指令和过渡清楚。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教师素养 | 点拨追问 | 教师能根据学生回答进行解释、追问、纠偏和提升。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |
| 教师素养 | 节奏调控 | 教师能通过语言提示、环节转换和任务收束保持学习节奏。 | 优势明显 / 基本有效 / 需要改进 / 证据不足 |

```

## 脚本统计与初步环节

```json
{
  "stats": {
    "utteranceCount": {
      "total": 16,
      "teacher": 12,
      "student": 4,
      "other": 0
    },
    "speakingDurationSec": {
      "teacher": 486.11,
      "student": 49.12,
      "other": 0.0
    },
    "talkRatio": {
      "teacher": 0.908,
      "student": 0.092,
      "other": 0.0
    },
    "totalDurationSec": 570.78,
    "teacherQuestionMarkCount": 19
  },
  "draftSegments": [
    {
      "name": "导入与目标唤起",
      "startSec": 20.92,
      "endSec": 163.62,
      "timeLabel": "0分21秒-2分44秒（21-164 秒）",
      "utteranceCount": 6,
      "teacherUtteranceCount": 4,
      "studentUtteranceCount": 2
    },
    {
      "name": "新知建构与文本/任务推进",
      "startSec": 163.62,
      "endSec": 306.31,
      "timeLabel": "2分44秒-5分06秒（164-306 秒）",
      "utteranceCount": 4,
      "teacherUtteranceCount": 3,
      "studentUtteranceCount": 1
    },
    {
      "name": "学生练习或探究活动",
      "startSec": 306.31,
      "endSec": 449.01,
      "timeLabel": "5分06秒-7分29秒（306-449 秒）",
      "utteranceCount": 5,
      "teacherUtteranceCount": 4,
      "studentUtteranceCount": 1
    },
    {
      "name": "总结提升与作业布置",
      "startSec": 449.01,
      "endSec": 591.7,
      "timeLabel": "7分29秒-9分52秒（449-592 秒）",
      "utteranceCount": 4,
      "teacherUtteranceCount": 3,
      "studentUtteranceCount": 1
    }
  ],
  "subjectInference": {
    "subject": null,
    "confidence": "低",
    "evidence": [
      "课文",
      "阅读",
      "作者",
      "力",
      "光",
      "声"
    ]
  }
}
```

## 用户请求元数据

```json
{
  "transcriptionProvider": "tongyi-tingwu",
  "mediaUrl": "https://5089-2407-cdc0-f008-46-00.ngrok-free.app/1309105672-1-192.mp4",
  "lessonDurationMin": 9.9
}
```

## 完整逐字稿

```json
[
  {
    "id": 1,
    "content": "各位老师下午好，我是初中语文14号选手，我展示的题目是花铺人的生命赞歌，体悟紫藤萝瀑布中的作者情感。下面我开始我的展示。同学们大家都知道本篇课文的描写对象是紫藤萝花，那么作者为何不直接将紫藤萝作为标题，而是要将核心词落在瀑布二字呢？让我们一起来探究这个问题，藤萝和瀑布有何联系？请大家阅读2到6，发挥联想和想象，并结合生活体验补全我们的表格。",
    "start": 20.92,
    "end": 67.079,
    "speaker": "教师"
  },
  {
    "id": 2,
    "content": "藤萝从空中垂下，好像瀑布飞流直下，我还找到了盛开的花，像河流上的帆船，还找到了点点荧光闪光，好像瀑布白色的水花，还有瀑藤萝欢笑着，好像瀑布的水流声。",
    "start": 71.18,
    "end": 93.375,
    "speaker": "学生"
  },
  {
    "id": 3,
    "content": "真是准确而又全面。通过刚才的表格整理活动，我们可以看出紫藤萝和瀑布组合在一起最直接的原因是什么？他们长得很像，二者真可谓是形似。",
    "start": 93.378,
    "end": 111.02,
    "speaker": "教师"
  },
  {
    "id": 4,
    "content": "品味着眼前这两株形似瀑布的藤萝，作者的心情如何？谁能用原文来回答？老师你来。作者有的只是精神的宁静和生的喜悦。好。",
    "start": 120.18,
    "end": 135.8,
    "speaker": "教师"
  },
  {
    "id": 5,
    "content": "那作者为什么会产生喜悦的心情呢？回头看看我们表格中对藤萝外形的描绘，从哪些词句中你能读出作者的喜悦呢？",
    "start": 141.28,
    "end": 155.594,
    "speaker": "教师"
  },
  {
    "id": 6,
    "content": "从彼此推着挤着，能够体现出花开的很茂盛，那种花香帆船又起航的感觉。欢笑、妖娆这些词是最直接的能够表现喜悦的词语。总之我觉得作者笔下的珍珠唐伯虎特别的有生命力。",
    "start": 156.627,
    "end": 174.315,
    "speaker": "学生"
  },
  {
    "id": 7,
    "content": "你对关键词的抓取能力很棒。是啊，这真是一株生命力旺盛的藤萝，这生机勃发的状态令作者愁思全消，满心欢喜。然而，生命力它直指花的内在精神气质。是什么使作者的双眼能够穿透形色声等一系列外在属性，转而去关注花的内在呢？有同学有想法吗？因为在十年前的时候还有一株，而且他一棒一猪，猪排爬得很高，但花朵从来都稀落伶仃地挂在树梢。后来所幸好可以看出它伶仃而又奚落，毫无生命力。",
    "start": 174.603,
    "end": 232.52,
    "speaker": "教师"
  },
  {
    "id": 8,
    "content": "那既然如此，作者为何还要描绘这十多年前的藤萝呢？成膜它凋谢了，多年后另一个成膜又开发了。这样开发了前后成膜状态的对比更命力。太好了，你真是读懂了作者的心思。那么生命力它不仅体现在当下的时刻，藤萝开的如何茂盛，它更体现在已经逝去的藤萝的生命，在另一株藤萝身上得到了延续。",
    "start": 232.52,
    "end": 271.719,
    "speaker": "教师"
  },
  {
    "id": 9,
    "content": "品味这两株藤萝生命的延续，作者发出了一句人生哲思，谁找到了花和人都会遇到各种各样的不幸，但是生命的长河是无止境的，也正是一朵万花灿烂的流动。你读课文很认真，在这段话中有两个第一句你们发现了吗？第一句将生命比作长河，第二句将生命比作瀑布。你们有没有发现这两个比喻都和水有关。那为什么一定要将生命比作水呢？我们来古诗词中找答案，谁有想法？",
    "start": 275.6,
    "end": 325.26,
    "speaker": "教师"
  },
  {
    "id": 10,
    "content": "千古兴亡和河中弟子都不在了，只有江水在永远的流，生命也是永远向前。没有。",
    "start": 326.94,
    "end": 335.239,
    "speaker": "学生"
  },
  {
    "id": 11,
    "content": "看来大家不仅读懂了宗璞的心，还读懂了古人的心。无论世事万物如何变化，但是水是唯一永恒流淌的事物。",
    "start": 336.05,
    "end": 352.319,
    "speaker": "教师"
  },
  {
    "id": 12,
    "content": "好，那我们讲到这儿，再来回顾一下开头要探究的问题。标题将紫藤萝和瀑布组合在一起，你还能想到其他原因吗？藤萝和瀑布的生命都是没有止境好生藤萝和瀑布的生命都是没有止境的，藤萝的生命得到了延续，而作为水的一种形态，瀑布也在亘古不变的永恒流淌，二者已经超越了形似，达到了神似。在作者的心中，花即是铺铺即是花，二者合而为一，这或许就是作者如此命题的深层原。",
    "start": 360.0,
    "end": 418.873,
    "speaker": "教师"
  },
  {
    "id": 13,
    "content": "品味了花和树的形似和神似神似，让我们再次回头看看这句人生哲思，你觉得作者想表达什么道理呢？生命无止境，我们应该更加积极乐观。是的，万事万物都不可能一直一帆风顺，然而生命向前向善的步伐不会停下，我们应该以坚强昂扬的状态继续前行。那么究竟是怎样的人生经历让作者产生了如此深刻的人生哲思呢？",
    "start": 420.288,
    "end": 460.968,
    "speaker": "教师"
  },
  {
    "id": 14,
    "content": "来看写作背景，十多年前宗璞一家深受文革带来的苦难，十多年后小弟有同样深受病痛的折磨。你们觉得宗璞的经历和谁相似？荷花十多年前花凋零了，十多年后他又重新开开放。那么十多年前的宗璞面对苦难，他的心态如何？悲观、消极又绝望。十多年后，他虽然仍然面临不幸，但是面对着这浅紫色的光辉和浅紫色的芳香，他又不觉怎样加快了脚步，振作了起来。因为他相信生命是无止境的，那么无止境的花，无止境的生命和生命得到延续的藤萝以及永恒流淌的瀑布具有相似性。花和铺不正是作者自身的写照吗？人、花、铺三者合而为一外，外柔内刚。",
    "start": 460.98,
    "end": 542.044,
    "speaker": "教师"
  },
  {
    "id": 15,
    "content": "三者。",
    "start": 542.044,
    "end": 542.984,
    "speaker": "学生"
  },
  {
    "id": 16,
    "content": "共同谱写出一曲永恒有力的生命赞歌。纵观全文，作者清新柔和的文字之下，却蕴藏着一股坚强勇毅的力量，景物、情志和文字三者又相互契合，共同写下这物我交融的名作。最后呢，送给大家一句话，愿大家都能将人生活成瀑布一样的藤萝，为生命的花舱注入最亮丽的底色。我们的作业分为必做和选做，并用评价量表加以参考。以上是我的展示，谢谢各位老师。",
    "start": 542.984,
    "end": 591.7,
    "speaker": "教师"
  }
]
```

