---
name: math-task-structurer
category: 教学辅导
description: >-
  将小学至高中数学题、图片题和学生作答整理为统一任务结构，识别学段、题型、条件、目标、表征、概念与评价方式；当开始讲题、诊断或生成练习且输入尚未结构化时使用。
---

# 数学任务结构化

本 Skill 负责把输入整理清楚并决定后续路由，不负责提前给出完整答案。

## 输入收集

尽量取得：原题、全部条件、图形或表格信息、求解目标、学生答案、学生原始步骤、已使用提示和可用参考答案。学生用“我写的是……”“我是这样想的……”“因为……所以……”给出的规则、理由、口算说明或草稿描述，也必须作为原始步骤逐字保留，并标记来源为 `student_self_report`；不能因缺少规范竖式或逐行算式就判成“只有最终答案”。图片无法由模型可靠读取时使用 `ocr_image`；OCR 公式或图形关系不清时让用户确认，不静默修正。

## 结构化

按 `references/problem-schema.md` 形成任务对象：

- `grade_band`：primary/junior/senior/unknown；
- `question_type`：objective/calculation/derivation/modeling/function/geometry/proof/probability-statistics/inquiry；
- `representations`：verbal/symbolic/diagram/graph/table/manipulative；
- 条件、目标、学生答案和原始步骤；
- 最小目标 `concept_ids`：必须从对应 `references/curriculum/` 文件逐字复制匹配 ID，不能改写命名空间或同义造词；没有精确细项时使用最接近的已有上位 ID，并把更细主题写入 `topic` 或后续 evidence metadata；
- `evaluation_method`：deterministic/rubric/model/unknown。

学段未说明时可根据内容作临时估计，但必须标记为 inferred；难度与教学措辞依赖年级时再询问。

## 路由与前置

按学段读取一份课程路由：小学使用 `references/curriculum/primary-math.md`，初中使用 `references/curriculum/junior-math.md`，高中使用 `references/curriculum/senior-math.md`；再只读取与题目相关的一个领域参考。目标概念已经原子化或本题不依赖前置时直接继续；确有必要时调用 `assess_learning_prerequisites`，最多提交 3 个直接相关、低置信的 `model_inferred` 候选，并严格遵守工具返回协议。

## 完整性检查

- 缺少关键条件：列出缺失项并停止求解；
- 确实只有最终答案且没有任何规则、理由或过程描述：允许核验答案，但不能推断具体错误步骤；
- 多问题混在一起：按用户优先级逐题处理；
- 超出中小学数学：说明模板边界并征询是否按一般学习助手处理；
- 开放探究题：明确采用的评价量表和不确定性。

完成后将结构传给 `math-reasoning-trace-analyzer`、`multi-representation-repair` 或 `adaptive-math-practice`。
