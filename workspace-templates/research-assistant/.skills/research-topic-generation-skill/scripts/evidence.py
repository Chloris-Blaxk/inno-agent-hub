"""S8：生成结构化证据链 EC，与排序靠前的候选缺口一一对应。

EC 字段（8 项，见 references/scoring_and_evidence.md）：
  gap_type / gap_cause / topo_evidence / trend_evidence /
  source_coverage / path / score_breakdown / uncertainty_note
EC 为结构化数据对象，不限定前端实现与数据格式，可追溯到 DKG 与计算过程。
"""
from collections import deque


def _bfs_path(adj, src, dst, max_hops):
    """锚点到缺口的路径序列（受跳数 K 限制）。"""
    if src == dst:
        return [src]
    prev = {src: None}
    q = deque([(src, 0)])
    while q:
        u, d = q.popleft()
        if d >= max_hops:
            continue
        for w in adj.get(u, []):
            if w not in prev:
                prev[w] = u
                if w == dst:
                    path = [w]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                q.append((w, d + 1))
    return None


def _path_desc(gap, topo, node_meta, anchor_ids, k):
    adj = topo["_adj"]
    name = lambda n: node_meta.get(n, {}).get("name", n)
    if gap["gap_type"] == "structural_hole":
        u, w = gap["missing_link"]["source"], gap["missing_link"]["target"]
        bridges = [b for b in gap["nodes"] if b not in (u, w)]
        bd = "、".join(name(b) for b in bridges[:3]) or "无显式桥接"
        return (f"跨社团连接带：{name(u)} ⟂ {name(w)}（缺失直接连接），"
                f"经共同邻居 [{bd}] 间接相连；路径长度受跳数范围 K={k} 限制。")
    # 稀疏区域：给出锚点到缺口核心节点的路径
    core = gap["nodes"][0]
    for a in anchor_ids:
        p = _bfs_path(adj, a, core, k)
        if p:
            return "锚点路径：" + " → ".join(name(n) for n in p) + f"（≤K={k} 跳）。"
    return f"稀疏区域核心：{name(core)} 及其邻域 {len(gap['nodes'])} 节点，局部连接稀疏。"


def _topo_summary(gap, topo):
    tm = gap["trigger_metrics"]
    if gap["gap_type"] == "sparse_region":
        return {
            "indicator_types": list(tm.keys()),
            "threshold_strategy": "分位阈值（后 30% 分位）",
            "conclusion": "；".join(f"{k}={v}" for k, v in tm.items())
                          + "→ 满足稀疏区域多指标组合判定",
        }
    return {
        "indicator_types": ["介数中心性", "结构约束系数", "社团结构"],
        "threshold_strategy": "社团边界 + 介数分位阈值",
        "conclusion": f"跨社团连接稀缺（社团 {tm.get('社团_u')}↔{tm.get('社团_w')}），"
                      f"bridge_score={tm.get('bridge_score')}",
    }


def _trend_summary(te):
    out = {
        "method": te.get("method"), "time_window": te.get("time_window"),
        "conclusion": te.get("conclusion"), "confidence": te.get("confidence"),
        "fallback": te.get("fallback", False),
    }
    if "fusion" in te:
        out["fusion"] = te["fusion"]
    if te.get("hot_series"):
        out["hot_series"] = te["hot_series"]
    if "link_probability" in te:
        out["link_probability"] = te["link_probability"]
    return out


def _source_coverage(gap, node_meta, ref_date, time_window):
    src_types = {}
    sources = set()
    disputed = []
    for n in gap["nodes"]:
        nd = node_meta.get(n, {})
        for s in nd.get("sources", []):
            sources.add(s)
            t = s.split(":")[0] if ":" in s else "未知"
            src_types[t] = src_types.get(t, 0) + 1
        if nd.get("disputed"):
            disputed.append(nd.get("name", n))
    cov = {
        "source_count": len(sources),
        "source_type_distribution": src_types,
        "temporal_window": time_window or "n/a",
        "ref_date": ref_date,
    }
    if disputed:
        cov["dispute_note"] = "争议对象：" + "、".join(disputed[:5])
    if len(sources) < 2:
        cov["coverage_note"] = "来源覆盖不足（<2 来源），结论可靠性受限。"
    return cov


def build_evidence_chain(rank_item, gap, topo, node_meta, trend_evidence,
                         req, k_hops, ref_date):
    """生成单条候选缺口的结构化证据链 EC。"""
    anchor_ids = req.get("_anchor_ids", [])
    src_cov = _source_coverage(gap, node_meta, ref_date,
                               trend_evidence.get("time_window"))
    notes = []
    if trend_evidence.get("uncertainty_note"):
        notes.append(trend_evidence["uncertainty_note"])
    if "coverage_note" in src_cov:
        notes.append(src_cov["coverage_note"])
    if "dispute_note" in src_cov:
        notes.append("存在争议标记，需人工复核相关事实。")
    if gap.get("anchor_linked") is False:
        notes.append("该方向为外围延伸，与锚点主题为弱关联，属规划性探索方向。")

    return {
        "gap_id": gap["gap_id"],
        "rank_score": rank_item["composite_score"],
        "gap_type": "稀疏区域型" if gap["gap_type"] == "sparse_region" else "结构洞型",
        "gap_cause": gap["cause"],
        "topo_evidence": _topo_summary(gap, topo),
        "trend_evidence": _trend_summary(trend_evidence),
        "source_coverage": src_cov,
        "path": _path_desc(gap, topo, node_meta, anchor_ids, k_hops),
        "score_breakdown": {
            **rank_item["score_breakdown"],
            "composite": rank_item["composite_score"],
            "synthesis": rank_item["synthesis"],
        },
        "uncertainty_note": notes or ["无显著不确定性提示。"],
    }


def render_direction_title(gap, node_meta):
    """把缺口翻译为人类可读的候选研究方向标题。"""
    name = lambda n: node_meta.get(n, {}).get("name", n)
    if gap["gap_type"] == "structural_hole":
        u, w = gap["missing_link"]["source"], gap["missing_link"]["target"]
        return f"探索「{name(u)}」与「{name(w)}」的交叉/桥接研究"
    core = gap["nodes"][0]
    return f"深化「{name(core)}」方向上证据稀疏区域的实证研究"
