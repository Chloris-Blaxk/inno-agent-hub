# 评分与证据链规范

## 排序字段

`rank_list` 中每条候选至少包含：

- `rank`
- `title`
- `gap_id`
- `gap_type`
- `composite_score`
- `score_breakdown`
- `synthesis`
- `gap_nodes`
- `next_materials`

## 评分解释

默认综合分：

```text
Composite = w1*MatchScore + w2*GapScore + w3*TrendScore + w4*FeasibilityScore
```

默认权重：

- `w1=0.30` 匹配
- `w2=0.30` 缺口
- `w3=0.20` 趋势
- `w4=0.20` 可行性

当身份字段显示“新手、研究生、资源有限、起步”等资源约束时，对节点跨度较大的候选降低可行性评分。

## 证据链 EC 字段

每条候选方向必须对应一个结构化证据链对象：

- `gap_type`：稀疏区域型或结构洞型。
- `gap_cause`：触发依据、缺口两侧实体、与请求关系、争议提示。
- `topo_evidence`：拓扑指标摘要和阈值策略。
- `trend_evidence`：趋势方法、时间窗、结论、置信度、融合方式或回退状态。
- `source_coverage`：来源数量、来源类型分布、时效窗口、争议对象、覆盖不足提示。
- `path`：锚点到缺口的路径，或跨社团缺失连接描述。
- `score_breakdown`：四项分数、综合分、合成方式。
- `uncertainty_note`：趋势回退、来源不足、争议对象、外围弱关联等风险提示。

## 禁止输出

- 不得把回退趋势写成确定增长。
- 不得删除来源覆盖不足提示。
- 不得将“结构上存在潜在桥接机会”表述为“已证明创新”。
- 不得根据候选分数预测申报成功率。
