# 数学任务结构

结构化结果可保留在上下文中，复杂任务或需要跨轮复用时写入 attempt。字段含义如下：

```json
{
  "grade_band": "primary | junior | senior | unknown",
  "grade_source": "user | inferred | unknown",
  "topic": "章节或主题",
  "question_type": "objective | calculation | derivation | modeling | function | geometry | proof | probability-statistics | inquiry",
  "prompt": "完整题目原文",
  "conditions": ["逐条条件"],
  "target": "要求得到或证明的目标",
  "representations": ["verbal | symbolic | diagram | graph | table | manipulative"],
  "student_answer": "学生最终答案",
  "student_steps": ["保持原始顺序"],
  "reasoning_source": "written_steps | student_self_report | mixed | none",
  "verbatim_reasoning": ["学生关于规则、理由或步骤的原话"],
  "hint_level": 0,
  "reference_answer": null,
  "concept_ids": ["最小稳定概念 ID"],
  "evaluation_method": "deterministic | rubric | model | unknown",
  "completeness": "complete | missing-condition | unreadable | missing-work",
  "missing_items": []
}
```

`student_self_report` 是有效的过程来源。例如“我把分子相加、分母相加”必须进入 `student_steps` 和 `verbatim_reasoning`；它可以支持定位本次关键错误，但单次自述不等于稳定误区。只有 `reasoning_source: none` 才能称为“只有最终答案”。

## 评价方式

- `deterministic`：数值结果、代数恒等、定义域、可枚举概率等可以独立复算；
- `rubric`：几何证明、开放证明、建模表达和探究题有明确条件清单或评分规则；证明题默认使用本方式，不因结论显然就改成 deterministic；
- `model`：只能进行保守的结构评价，必须降低置信度并说明依据；
- `unknown`：无法可靠评价，应请求补充而不是继续诊断。

图像题要把可见关系转写进 `conditions`，并标明来自题干还是仅由图形外观推测。未经题干说明，不得把“看起来垂直、等长、平行”当作已知条件。

`concept_ids` 必须保留学段命名空间：`math.primary.*`、`math.junior.*` 或 `math.senior.*`。课程参考已有匹配项时逐字复用；没有精确项时使用最近的已有上位 ID，不创建只换命名方式的同义 ID。
