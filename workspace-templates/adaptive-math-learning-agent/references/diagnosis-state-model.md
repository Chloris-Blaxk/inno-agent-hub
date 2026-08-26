# 数学错因诊断状态模型

状态描述的是一个可验证的错因假设，不是学生的固定能力标签，也不等于平台计算的知识掌握状态。

| 状态 | 含义 | 典型下一状态 |
| --- | --- | --- |
| `observation` | 一次真实作答出现目标错误 | `suspected`、`inconclusive`、`dismissed` |
| `suspected` | 原始作答与至少一道探针方向一致 | `confirmed`、`inconclusive`、`dismissed` |
| `inconclusive` | 证据不足、层级不一致或相互矛盾 | `suspected`、`dismissed` |
| `confirmed` | 原始作答和至少两道一致探针支持同一机制，至少一道无提示 | `improving`、`reopened` |
| `improving` | 已连续完成至少两道即时修复题，但缺少延迟迁移 | `resolved`、`reopened` |
| `resolved` | 间隔至少 24 小时后无提示完成迁移任务 | `reopened` |
| `dismissed` | 足够反证表明原候选不是稳定错因 | `reopened` |
| `reopened` | 已改善、解决或排除的同类错误再次出现 | `suspected`、`confirmed`、`improving` |

## 不变量

1. 单次错误最多形成 `observation`。
2. 一道正确的规则识别题不能证明独立应用稳定，只能形成反证或要求应用层探针。
3. 确认需要原始作答加至少两道方向一致的探针，且至少一道 `hint_level=0`。
4. 即时正确最多说明 `improving`；`resolved` 必须包含至少 24 小时后的无提示迁移。
5. 如果后续证据否定原候选，进入 `dismissed`，不得改写或删除原始错误。
6. 状态变化必须附 attempt_id、evidence_id、探针原文、学生原话、结果、提示等级、评价方式和理由。
7. 没有工具返回时不得编造 evidence_id；写入失败应显式记录。

诊断置信度只能用低、中、高并注明证据数量和评价方式。不要把它转换为掌握率百分比。
