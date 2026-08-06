# ED 课堂页面版式

页面版式服务课堂动作。`layoutId`、HTML `data-layout`、PPTX 侧栏和校验器均使用 `ED01-ED12`。不要临时发明版式；新增版式必须同步更新模板、生成器、校验器和 PPTX 导出器。

## 版式清单

| ID | 视觉骨架 | 适用阶段 | 屏幕内容原则 |
|---|---|---|---|
| ED01 | 左大标题 + 右学科标记 + 目标条 | cover | 第一眼看到课题和本课产出 |
| ED02 | 路线图 + 时间徽标 | objective_map / knowledge_map | 3-5 个节点，不写教案式目标 |
| ED03 | 大问题 + 右侧情境图卡 | lead_in / driving_question / prediction | 不直接给结论 |
| ED04 | 左右对比/同伴讨论工作区 | explore / hypothesis | 让学生产生可观察表达 |
| ED05 | 概念短句 + 图示画布 | concept_build / explanation | 短句 + 图示，定义不超过两行 |
| ED06 | 板书模型 + 方法步骤 | key_methods / method_rebuild | 适合教师保留板书 |
| ED07 | 例题 + 纵向步骤流 | example | 3-5 步，每步有教师追问 |
| ED08 | 练习实验台 + 题目卡 | guided_practice / retry_practice / integrated_practice | 1-3 题，学生屏幕只放题目 |
| ED09 | 错误诊所 + 修正 + 检查题 | misconception_check / error_clinic / typical_error | 错误不羞辱，强调方法边界 |
| ED10 | 活动工作室 + 小组任务 | interaction / group_explore / demonstration | 明确学生做什么和教师收集什么 |
| ED11 | 总结板 + 关键句 | summary / reflection | 回扣目标，形成可复述方法 |
| ED12 | 出门测 + 教学决策 | exit_ticket | 1-2 道短测，支撑下一课决策 |

## 版式多样性

- 8 页及以下至少使用 6 个不同 ED 版式。
- 9 页及以上至少使用 8 个不同 ED 版式。
- 不允许连续 3 页使用相同 layout family：
  - `scene`：ED03 / ED04 / ED10
  - `model`：ED05 / ED06 / ED11
  - `assessment`：ED08 / ED09 / ED12

## 屏幕密度

- 每页只承载一个教学动作。
- headline 不超过 18 个中文字符。
- bullets / summary / route 每页 3-5 条。
- 练习题最多 3 道；更多题放到备注或附件。
- 教师话术、反馈方式、预设回答不出现在学生屏幕。
