---
name: math-reasoning-trace-analyzer
category: 教学辅导
description: >-
  核验中小学数学的学生答案与推理过程，兼容多种正确解法，定位首个关键错误并形成可追溯初始证据；当用户提交计算、推导、应用题、函数、几何、概率统计等作答并要求检查或订正时使用。
---

# 数学推理轨迹分析

目标是验证学生路径本身并找到**首个关键错误**，不是强迫学生复现参考解法。

## 前置输入

优先读取 `math-task-structurer` 形成的任务结构。若尚未结构化，至少取得原题、条件、学生最终答案和按原顺序记录的步骤。学生明确自述的算法规则、理由或口算说明是可核验步骤，必须保留原话和 `student_self_report` 来源，不得改写成“没有过程”。根据题型只读取一个相关领域参考：

- 数与运算：`references/domains/arithmetic.md`
- 代数与方程：`references/domains/algebra.md`
- 函数与图表：`references/domains/functions.md`
- 几何：`references/domains/geometry.md`
- 应用建模：`references/domains/modeling.md`
- 概率统计：`references/domains/probability-statistics.md`

## 核验流程

1. 检查题目条件是否足够、是否存在定义域或隐含约束。条件不足时停止并请求补充。
2. 独立得到至少一条合法解法；学生使用另一条路径时，逐步验证该路径，不以参考路径不同为错误。
3. 按题型检查相邻步骤：
   - 计算与代数：运算、等价变形、定义域和可逆性；
   - 应用题：变量含义、单位、数量关系和结果合理性；
   - 函数：定义域、对应关系、图表和性质；
   - 几何：已知条件、定理前提、辅助构造和结论链；
   - 概率统计：样本空间、重复计数、独立性与指标选择。
4. 找到首个使目标结论不再可靠的步骤后停止新增归因。后续问题标为传播结果。
5. 最多提出两个互斥或可区分的候选错因，类型来自 `references/math-error-taxonomy.md`。单次作答状态只能是 `observation`。
6. 最终答案正确但中间推理无效时，评价推理证据为 `partial` 或 `incorrect`；答案错误但主要方法正确时，区分局部执行错误。
7. 确实只有答案、没有任何自述规则或理由时，可以核验答案，但把 `first_invalid_step` 记为 `unknown`，不得编造过程。若学生已自述错误规则，则首个关键错误可以定位到该自述规则；仍保持 `observation`，是否为稳定误区留给后续探针验证。

评价方式必须与任务一致：可复算的数值、代数、定义域和有限枚举使用 `deterministic`；几何证明、开放证明和需要逐项核对推理充分性的任务默认使用 `rubric`；缺少可靠标准时使用 `model` 或停止，不得把模型判断伪装成确定性验证。

## 证据落盘

1. 先在上下文中按 `templates/attempt-record-template.json` 整理 attempt，并从对应 `references/curriculum/` 文件逐字复制解释首个错误的最小稳定 `concept_id`。禁止把 `math.junior.*` 改写成 `math.geometry.*` 等同义 ID；没有精确细项时使用已有上位 ID，把细节写入 metadata。
2. 调用 `record_learning_evidence`。通常用 `application`，解释或证明可以用 `free_recall`；提示等级、结果和评价方式必须真实。
3. 工具成功返回后再写 `attempts/<attempt-id>.json`，把真实 `evidence_id` 写入 `evidence_ids`；失败时保留空数组并记录失败原因，不得伪造 ID。
4. 更新 `misconception-ledger.md`，引用同一个 attempt 和 evidence ID。写入前必须先检查文件：不存在时按模板创建；存在时先按 concept ID 和可验证错因机制查重。同一机制已存在时把新证据追加到原 MIS 并按状态规则更新，不新建重复条目；机制确实不同才追加唯一的新 MIS。使用 `edit` 或等价追加方式，绝不能用 `write` 覆盖已有条目或复用其他机制的编号。
5. 文件写完后运行 `node scripts/validate-artifacts.mjs`；失败时修复对应产物后再声称落盘成功。

## 学生反馈

依次给出：保留的正确部分、忠实引用首个需要检查的位置、为什么失效、目前只是待验证的候选原因，以及一道不带答案的最小诊断题。不要声称学生没有提供其实际已提供的过程，也不要一次展示整套练习。内部的 Skill 读取、工具调用、文件写入与校验必须静默完成，不写入学生可见回复。

## 停止条件

- 题目、图像或学生步骤无法辨认；
- 题目条件矛盾或不足；
- 开放结论没有可用评分标准；
- 无法以足够可靠的方式核验生成的标准答案。
