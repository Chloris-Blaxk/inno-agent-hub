---
name: adaptive-math-practice
category: 教学辅导
description: >-
  根据中小学数学的目标概念、已验证错因、表征方式和当前表现生成并自检递进练习；当学生需要针对训练、举一反三、错题巩固或延迟复测时使用，不用于证据不足时盲目刷题。
---

# 自适应数学练习

练习必须服务于一个明确的目标概念或待澄清错因。生成前读取 `references/practice-generation-rules.md`、`references/problem-quality-checklist.md` 和相关领域参考。

## 入口

允许以下入口：

- 已 `confirmed` 或 `improving` 的错因；
- `inconclusive` 状态下用于区分识别与应用差异的一道任务；
- 学生明确指定的知识点和难度；
- 复习计划中到期的概念。

证据不足且用户未指定目标时，先交给 `math-task-structurer` 或 `math-misconception-verifier`，不要生成泛化题海。

## 练习阶梯

按需要选择，不必机械走完：

1. 概念恢复：只检查一个定义或关系；
2. 最小规则：去掉无关计算负担；
3. 同构应用：改变数字或背景，保留核心结构；
4. 近邻反例：表面相似但规则或条件不同；
5. 多表征任务：改变文字、符号、图像或表格；
6. 综合迁移：与新知识或真实情境结合；
7. 延迟复测：至少间隔 24 小时的无提示任务。

每次只展示当前一题，先等待学生回答。连续正确时提高结构或表征差异；错误时回到首个失效规则，不只是换数字重复。

## 题目质量门

展示前独立求解并按 `references/problem-quality-checklist.md` 检查：条件完整、答案存在、结论无歧义、学段合适、目标纯净、数据合理、解析一致。未通过则内部修订或放弃，不把有缺陷的题交给学生。

将通过检查的题按 `templates/practice-item-template.json` 写入 `practice/<practice-id>.json`。写完后重新读取，确认 ID 与文件名一致、目标 concept ID 稳定、答案与解析一致且五项质量检查全部通过；有问题先修复，再向学生展示。学生作答后调用 `record_learning_evidence`，并回填 evidence ID；只听完讲解只能记 `exposure`。

## 复习计划

即时训练完成只能标为 `improving`。更新 `review-plan.md` 前先读取现有计划；文件不存在时按 `templates/review-plan-template.md` 创建。相同概念合并更新，不同概念保留原行，不得覆盖无关计划。只有用户明确同意后才调用 `create_scheduled_job`，使用 `taskType: spaced_review`；站内任务可以不指定 channel，用户明确要求外部推送时才确认并填写已启用渠道。
