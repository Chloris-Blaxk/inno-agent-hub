# 教育版课件版式锁

本文件是教育课件生成的硬约束。目标不是给 Agent 更多灵感，而是防止它生成“像 PPT、但不好教”的页面。

## Golden Source

本 Skill 的生成链路固定为：

`课题描述 -> 课型流程 -> ED 登记版式 -> 素材槽位 -> 教师逐字稿 -> HTML 预览 -> PPTX-ready 结构 -> 校验`

正文页只能使用下方登记的 ED01-ED12 版式。新增版式必须同步更新模板、生成器、校验器和 PPTX 导出器。

## 生成前硬规则

1. 开写内容前先生成 `designPlan`：页码、阶段、版式、选用理由、素材槽位、反馈证据。
2. 每页必须有 `layoutId`，HTML `<section>` 必须写 `data-layout="EDxx"`。
3. 每页必须有 `visualSlots`。没有真实图片时也要写 `assetStatus: "placeholder"` 和可生成素材提示词。
4. 先确定素材槽位和比例，再找图或生成图。不要先有图片再硬塞。
5. 学生屏幕只放学生需要看的内容；逐字稿、预设回答、反馈方式放 `teacherScript`、`feedbackEvidence` 或备注。
6. 互动、练习、错误辨析、出门测必须有反馈证据，说明教师如何判断学生是否达成目标。
7. SVG/图示只画几何关系；可见文字放 HTML/PPTX 可编辑文本框。

## 登记版式

| ID | 名称 | 课堂动作 | 必填屏幕字段 | 素材槽位 |
|---|---|---|---|---|
| ED01 | Studio Cover | 建立课题与课堂氛围 | headline, subtitle, outcome | cover_mark |
| ED02 | Lesson Journey | 告诉学生路径和目标 | headline, route | journey_map |
| ED03 | Hook Scene | 情境导入/认知冲突 | headline, question, visualBrief | hook_visual 16:9 |
| ED04 | Inquiry Split | 观察/猜想/同伴讨论 | headline, prompt, comparePoints | inquiry_workspace |
| ED05 | Concept Canvas | 概念建构/规则生成 | headline, keyIdea, bullets, visualBrief | concept_diagram 16:10 |
| ED06 | Board Model | 板书模型/方法框架 | headline, modelSteps | board_model |
| ED07 | Example Flow | 典型例题分步讲解 | headline, example, steps | step_flow |
| ED08 | Practice Lab | 课堂练习/变式迁移 | headline, tasks | practice_grid |
| ED09 | Error Clinic | 错误辨析/易混点 | headline, misconception, correction, checkQuestion | error_pair |
| ED10 | Activity Studio | 小组任务/实验/互动 | headline, activity | activity_workspace |
| ED11 | Summary Board | 方法小结/板书回收 | headline, summary | summary_board |
| ED12 | Exit Ticket | 课末检测/自评 | headline, tickets | exit_ticket |

## 课型节奏

- `new_concept`：ED01 -> ED02 -> ED03 -> ED04 -> ED05 -> ED07 -> ED08 -> ED09 -> ED11 -> ED12
- `review`：ED01 -> ED02 -> ED08 -> ED06 -> ED09 -> ED08 -> ED11 -> ED12
- `practice`：ED01 -> ED02 -> ED09 -> ED06 -> ED08 -> ED11 -> ED12
- `inquiry`：ED01 -> ED03 -> ED02 -> ED04 -> ED10 -> ED05 -> ED08 -> ED11 -> ED12
- `experiment`：ED01 -> ED03 -> ED02 -> ED04 -> ED10 -> ED05 -> ED08 -> ED11 -> ED12

## 槽位规则

- `cover_mark`：几何主题标记或学科符号，不放照片。
- `journey_map`：3-5 个课堂节点，适合横向路线图。
- `hook_visual`：16:9 情境图、实验现象图、问题图，主体在中央安全区。
- `inquiry_workspace`：左右比较、预测记录或同伴讨论产物。
- `concept_diagram`：16:10 可编辑概念图，公式、标签、步骤文字不要做进图片。
- `board_model`：板书式三步/四步模型，适合教师保留到课堂结束。
- `step_flow`：3-5 步，每步必须有 `teacherCue`。
- `practice_grid`：1-3 题，每题必须有 `target` 和 `feedback`。
- `error_pair`：错误、修正、检查题三件套。
- `activity_workspace`：学生动作、教师收集证据、反馈后推进策略。
- `summary_board`：3-5 条短句，回扣目标。
- `exit_ticket`：1-2 道短测或 1 个自评问题，必须给教师下一步决策依据。

## 禁止清单

- 禁止未登记版式。
- 禁止连续 3 页同一种主体结构。
- 禁止把教师逐字稿放到学生屏幕。
- 禁止练习页只有题目、没有目标和反馈。
- 禁止互动页只有“讨论一下”、没有可收集证据。
- 禁止错误辨析页没有检查题。
- 禁止 PPTX 把整页导出为不可编辑图片。
