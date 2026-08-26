---
name: math-misconception-verifier
category: 教学辅导
description: >-
  用控制变量式数学探针验证候选错因，区分概念、前置、策略、运算、审题、建模、表征与论证问题；当轨迹分析产生候选原因，或学生询问为何反复出错时使用。
---

# 数学错因验证

每轮只验证一个候选错因。先读取 `references/diagnosis-state-model.md` 和 `references/math-error-taxonomy.md`；具体题型再读取对应领域参考。

## 探针选择

围绕候选机制生成 2–3 个控制变量探针，但每次只呈现一个：

- `conceptual`：改变表面数字，直接辨析概念边界；
- `prerequisite-gap`：检查完成当前步骤所需的最小前置；
- `procedural/calculation`：把目标步骤缩成极简运算；
- `strategy`：给出两个可行入口，让学生选择并解释；
- `condition-reading`：只改变或删除一个条件；
- `modeling`：只要求定义变量或写一个数量关系；
- `representation`：在文字、符号、图像或表格之间转换；
- `reasoning`：提供缺少关键条件的近邻反例。

探针必须可核验、符合学段，并避免同时引入新的知识负担。

## 交互与证据

1. 先呈现探针并停止，等待学生作答；同一消息不泄露答案或强暗示。一个探针只能要求一个判断或一个产出，不能要求“列出多种方法并逐一解释”。
2. 回答后说明评价依据，并调用 `record_learning_evidence`：辨认用 `recognition`，独立解释用 `free_recall`，同构使用 `application`，近邻或新表征使用 `transfer`。
3. 学生说不会时从一级提示开始；每增加一次提示提高 `hint_level`，答案揭示后必须为 3。
4. 工具返回后，把探针、学生原话、结果、提示等级和真实 evidence ID 同步追加到来源 attempt 与 `misconception-ledger.md`。修改账本前先读取现有文件，只编辑对应 MIS 条目，不得重写或删除其他条目。
5. 如果工具失败，不得编造证据或假装已记录。

用户明确限制输出数量或在“反例 / 诊断问题”之间要求二选一时，严格按其限制只提供一个项目；呈现后立即停止，不再追加第二个任务、备选分支或完整练习列表。

## 状态规则

- 单次原始错误：`observation`；
- 原始错误加一条方向一致的探针：`suspected`；
- 原始错误加至少两条一致探针，且至少一条无提示：可为 `confirmed`；
- 正确或矛盾探针：`inconclusive`，不得为了确认而解释成错误；
- 两次连续即时正确：最多 `improving`；
- 间隔至少 24 小时的无提示迁移正确：才可 `resolved`。

只有确认后才用 `record_learning_event` 写入精确、可纠正的误区候选，不提交 `mastery_delta`。如果证据指向普通偶发失误，明确关闭该候选并进入常规应用，不创造永久标签。
