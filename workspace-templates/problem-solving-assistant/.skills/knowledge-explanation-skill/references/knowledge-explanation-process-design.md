# 知识点讲解过程设计说明（引用版）

更新时间：2026-06-05

## 1. 设计问题

本 Skill 要解决的不是“生成一段更详细的解释”，而是“如何在多轮对话中讲清一个具体知识点”。这里的“讲清”不是学生听完觉得顺耳，而是学生能：

1. 知道这个知识点解决什么问题。
2. 说出核心规则或关键属性。
3. 区分适用和不适用的例子。
4. 在题目中完成至少一个关键步骤。
5. 通过一个小回应暴露当前理解，方便系统继续诊断。

因此，知识点讲解应被设计为一个弹性微教学判断过程，而不是单轮讲义输出或固定工作流。

## 2. 知识点讲解的本体要求

知识点讲解至少包含四个对象：

| 对象 | 说明 | 设计含义 |
|---|---|---|
| 知识对象 | 概念、规则/原理、过程步骤、例题或错误过程 | 先判断知识类型，不能所有问题都套同一讲法 |
| 学生状态 | 前置掌握、当前卡点、情绪和需求 | 缺前置时只补最小前置 |
| 教学表示 | 直觉、定义、规则、符号、正例/反例、worked example | 解释必须连接多种表示，而不是只给抽象定义 |
| 可观察回应 | 判断、补一步、解释一句或选择下一步 | 讲解后必须留下一个检查点，供下一轮反馈回流 |

这意味着：一个好的知识点讲解，不是把“定义、例题、易错点、练习”一次全倒出来，而是在学生当前可处理的范围内，先建立可理解的入口，再通过例子和反馈逐步压实。

## 3. 理论依据

### 3.1 显性教学：小步呈现与检查理解

Rosenshine (2012) 总结有效教学原则时强调，教师应先复习相关旧知，再以小步呈现新材料，并在每一步之后安排学生练习和检查理解。文章还强调 worked examples、提问、示范和脚手架对初学者的重要性。

对本 Skill 的转化：

- 每轮只讲一小步。
- 不一口气讲完概念、例题、易错点和练习。
- 每轮末尾留下一个可检查的学生回应。
- 例题带做时先示范关键一步，再让学生接下一步。

参考：Rosenshine, B. (2012). *Principles of Instruction: Research-Based Strategies That All Teachers Should Know*. American Educator, 36(1), 12-39. https://files.eric.ed.gov/fulltext/EJ971753.pdf

### 3.2 教学事件：从前置激活到反馈回流

Gagné 的教学事件理论把教学组织为一组事件，包括引起注意、告知目标、激活旧知、呈现内容、提供学习指导、引出表现、提供反馈、评价表现和促进迁移保持（Gagné, 1985；Gagné, Briggs, & Wager, 1992）。

对本 Skill 的转化：

- 入口检查对应“目标与注意”。
- 前置检查对应“激活旧知”。
- 直觉入口和规则具体化对应“呈现内容”和“提供指导”。
- 结尾一个问题对应“引出表现”。
- 下一轮判断和修正对应“反馈”和“回流”。

参考：Gagné, R. M. (1985). *The Conditions of Learning and Theory of Instruction* (4th ed.). Holt, Rinehart and Winston. 另见 Northern Illinois University 对九大教学事件的说明：https://www.niu.edu/citl/resources/guides/instructional-guide/gagnes-nine-events-of-instruction.shtml

### 3.3 首要教学原理：激活、示范、应用、整合

Merrill (2002) 提出的 First Principles of Instruction 指出，学习在以下情况下更容易发生：学习者解决真实问题，已有知识被激活，新知识被示范，学习者应用新知识，并把新知识整合进自己的世界。

对本 Skill 的转化：

- 不只讲定义，要把知识点放到一个小问题、小例子或题目步骤里。
- 讲新知识前先看是否需要激活前置。
- 解释后要让学生做一个小应用，而不是只听。

参考：Merrill, M. D. (2002). *First Principles of Instruction*. Educational Technology Research and Development, 50(3), 43-59. https://doi.org/10.1007/BF02505024

### 3.4 知识类型匹配：概念、规则、过程不能同讲

Merrill 的 Component Display Theory 把学习内容区分为事实、概念、过程和原则，并把呈现形式区分为规则、例子、回忆和练习。这个理论说明：教学材料应根据内容类型和表现目标组合呈现形式，而不是固定套一个模板。

对本 Skill 的转化：

- 先判断知识类型，再决定讲法。
- 概念类要突出关键属性、正例和反例。
- 规则类要讲适用条件和边界。
- 过程类要用 worked example 带关键步骤。

参考：Merrill, M. D. (1983). *Component Display Theory*. In C. M. Reigeluth (Ed.), *Instructional-design theories and models: An overview of their current status*. Lawrence Erlbaum. 另见概述：https://www.instructionaldesign.org/theories/component-display/

### 3.5 概念教学：关键属性、正例、反例和变式

Tennyson and Cocchiarella (1986) 专门提出概念教学的设计理论，将概念学习看成概念性知识形成和程序性知识发展两个阶段，并强调内容结构变量与教学设计变量的结合。

对本 Skill 的转化：

- 对“同类项”“函数”“等式性质”等概念，不能只给定义。
- 要用最小正例和反例帮助学生辨别关键属性。
- 讲解目标应从“听懂定义”转为“能判断一个例子是不是这个概念”。

参考：Tennyson, R. D., & Cocchiarella, M. J. (1986). *An Empirically Based Instructional Design Theory for Teaching Concepts*. Review of Educational Research, 56(1), 40-71. https://doi.org/10.3102/00346543056001040

### 3.6 教学解释：解释要围绕问题和表示连接

Leinhardt (2001) 把 instructional explanations 视为教学中的关键场所。教学解释不是抽象说明，而是要围绕学生的问题、学科原则、例子、表示和隐含前提建立连接。

对本 Skill 的转化：

- 先判断学生到底问什么，不要直接铺讲义。
- 解释时要把直觉、规则、符号和例子连接起来。
- 不要只给术语定义，也不要只给生活类比；类比最后必须回到准确规则。

参考：Leinhardt, G. (2001). *Instructional Explanations: A Commonplace for Teaching and Location for Contrast*. In V. Richardson (Ed.), *Handbook of Research on Teaching* (4th ed., pp. 333-357). American Educational Research Association.

### 3.7 例题学习：worked example 和自我解释

Atkinson, Derry, Renkl, and Wortham (2000) 总结 worked examples 研究，指出例题能为初学者提供专家解题步骤，降低新手在问题解决中的负荷。Wittwer and Renkl (2010) 进一步指出，教学解释与例题结合时，并不是解释越多越好；解释的效果会受到学习者前置知识和自我解释活动影响。

对本 Skill 的转化：

- 用户给题时，先带一个关键步骤，不直接把整题讲完。
- 解释例题时要让学生注意“为什么这一步这样做”。
- 下一步交给学生补，促成自我解释。

参考：Atkinson, R. K., Derry, S. J., Renkl, A., & Wortham, D. (2000). *Learning from Examples: Instructional Principles from the Worked Examples Research*. Review of Educational Research, 70(2), 181-214. https://doi.org/10.3102/00346543070002181

参考：Wittwer, J., & Renkl, A. (2010). *How Effective Are Instructional Explanations in Example-Based Learning? A Meta-Analytic Review*. Educational Psychology Review, 22, 393-409. https://doi.org/10.1007/s10648-010-9136-5

### 3.8 自我解释和形成性反馈

Chi et al. (1994) 的研究说明，引出学习者的自我解释有助于理解。Shute (2008) 的形成性反馈综述指出，反馈应具体、及时、支持性、非评价性，并服务于改变学习者后续思考或行为。

对本 Skill 的转化：

- 结尾问题不是闲聊，而是 self-explanation prompt 或 formative check。
- 学生答错后，不评价学生能力，不重讲整章；只指出当前错误和下一步。
- 反馈要低威胁、具体、可执行。

参考：Chi, M. T. H., de Leeuw, N., Chiu, M. H., & LaVancher, C. (1994). *Eliciting Self-Explanations Improves Understanding*. Cognitive Science, 18(3), 439-477. https://doi.org/10.1016/0364-0213(94)90016-7

参考：Shute, V. J. (2008). *Focus on Formative Feedback*. Review of Educational Research, 78(1), 153-189. https://doi.org/10.3102/0034654307313795

## 4. 综合后的弹性判断框架

以上文献没有直接给出“生成式 AI 知识点讲解智能体”的固定完整流程。因此，本项目采用理论整合方式，把它们转化为适合多轮对话的弹性教学判断框架。框架提供每轮应考虑的要素和优先级，但不要求每轮按顺序完整执行。

```text
1. 明确本轮讲解对象
   判断用户问的是概念、规则/原理、步骤、例题、错误过程还是总结。

2. 激活或检查最小前置
   如果前置缺失会导致讲偏，先补一个最小前置或问一个短诊断。

3. 给一个直觉入口
   用类比、画面或问题情境建立方向感。

4. 压成准确规则
   用一句话说清关键属性、适用条件或操作原则。

5. 配一个最小例子
   概念用正例/反例；规则用边界例子；步骤用 worked example。

6. 让学生做一个小回应
   只问一个判断、补一步、解释一句或选择下一步。

7. 根据回应反馈回流
   对了就推进或总结；错了就定位第一处关键错误并修正这一小步。
```

这不是单轮输出模板，也不是固定流水线，而是跨多轮推进的教学判断框架。每轮只执行当前最必要的一个动作。

## 5. 与原 Skill 的关系

原 Skill 中的“直觉引导、规则具体化、例题带做、错因修正、快速总结”可以保留，但它们应被理解为框架中的教学动作，而不是固定流程本身。

新的设计优先级是：

1. 先判断知识类型。
2. 再判断学生卡点和前置。
3. 再选择一个教学动作。
4. 最后套用语言风格。

风格层只影响表达方式，不影响知识类型判断、教学动作选择、数学准确性和反馈边界。

## 6. 无知识库时的落地方式

这个教学判断框架不要求知识库必须存在。当前无知识库模式下，Skill 只依赖用户输入、对话上下文和 AI 的通用学科知识完成本轮判断。知识图谱、详解库、题库、教材库和学生画像都只是未来增强项。

无知识库时要额外遵守：

1. 不声称已经检索知识图谱、题库、教材或课标。
2. 不编造教材版本、课标条目、题库来源、知识点 ID 或学生长期画像。
3. 微例、正例/反例和检查题可以临时生成，但不能说成真实来源。
4. 前置关系和难度边界只能保守判断；不确定时问一个短问题。

## 7. 推荐写法

对外说明本 Skill 时，可以这样写：

> 本 Skill 的知识点讲解框架主要参考显性教学、教学事件、首要教学原理、概念教学、教学解释、例题学习、自我解释和形成性反馈研究。由于现有教育理论并未直接给出面向生成式 AI 智能体的固定多轮知识点讲解流程，本项目采用理论整合方式，将知识点讲解组织为一个弹性微教学判断框架：每轮先判断知识类型与学生卡点，再视情况检查最小前置、建立直觉入口、压成准确规则、配置正例/反例或 worked example、引出学生小回应，并基于回应反馈回流。
