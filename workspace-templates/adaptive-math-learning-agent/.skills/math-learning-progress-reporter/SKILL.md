---
name: math-learning-progress-reporter
category: 教学辅导
description: >-
  汇总中小学数学 attempt、学习证据、错因状态、练习与复测计划，生成可追溯的学生版或教师版报告；当用户要求学习总结、错题报告、阶段复盘或教学建议时使用。
---

# 数学学习进展报告

报告只重组已有证据，不在报告阶段重新猜测错因或生成掌握率。

## 数据读取

依次读取：最新 L1 学习者上下文、`attempts/`、`misconception-ledger.md`、`practice/` 和 `review-plan.md`。时间段、章节或报告对象不明确且会改变内容时，一次性确认。没有证据的项目写“暂无可核验证据”。

上述读取、目录检查、模板读取和写文件都在后台静默完成。学生或教师可见回复不得出现“我先读取”“正在查看目录”“目录尚不存在”等工具执行旁白；只需说明报告结果、保存位置和必要摘要。

## 学生版

突出：本阶段练习内容、已经做对并能解释的部分、仍待验证的一个重点、下一次具体行动和建议复测时间。语气清楚、鼓励但不夸大。

## 教师版

包含：题目与学生原始步骤、首个关键错误、候选错因及状态、探针及提示等级、同构与迁移表现、评价方式与置信度、未解决风险、建议教学干预。每个关键结论附 attempt_id/evidence_id。

## 文件与边界

按 `templates/report-template.md` 的证据结构写入 `reports/<date>-<HHmm>-math-progress-<student|teacher>.md`。写入前检查同名文件，冲突时增加序号；除非用户明确要求更新原报告，不覆盖已有报告。报告应包含证据索引和数据截止时间。`observation`、`suspected`、`inconclusive`、`confirmed`、`improving`、`resolved`、`dismissed`、`reopened` 必须分开呈现；即时正确不得写成长期掌握。
