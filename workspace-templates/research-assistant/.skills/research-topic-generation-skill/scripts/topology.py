"""S4 拓扑结构分析 + S5 缺口识别。

S4：对局部子图 G 计算密度类、连通性类指标（必算），并计算聚类、核心层级、
社团结构、中心性、结构约束等多维拓扑特征，形成拓扑证据集合 TopoEvidence。
S5：基于 TopoEvidence 识别稀疏区域型缺口（≥2 指标组合）与结构洞型缺口
（社团边界 + 介数中心性/结构约束），并生成缺口成因描述要素 CauseSet。

阈值策略：默认采用分位阈值（占位式"处于后 x% 分位"），可切换为固定阈值。
"""
import graphlib as gl


def _quantile(values, q):
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return 0.0
    idx = max(0, min(len(xs) - 1, int(q * (len(xs) - 1))))
    return xs[idx]


def topology_analysis(node_ids, edges, enable=None):
    """计算多维拓扑特征。enable 控制可选特征开关。"""
    enable = enable or {"cluster": True, "core": True, "community": True,
                        "centrality": True, "constraint": True}
    adj, wadj = gl.build_adjacency(node_ids, edges)
    nodes = list(node_ids)

    density = {v: round(gl.neighborhood_density(adj, v), 4) for v in nodes}
    wdensity = {v: round(gl.weighted_density(wadj, v), 4) for v in nodes}
    degree = {v: gl.degree(adj, v) for v in nodes}
    conn = gl.connectivity_stats(adj, nodes)
    conn["avg_path_normalized"] = round(gl.avg_shortest_path_normalized(adj, nodes), 4)

    topo = {
        "density": density, "weighted_density": wdensity, "degree": degree,
        "connectivity": conn,
    }
    if enable.get("cluster"):
        topo["clustering"] = {v: round(gl.clustering_coefficient(adj, v), 4) for v in nodes}
    if enable.get("core"):
        topo["core"] = gl.k_core_numbers(adj)
    if enable.get("community"):
        topo["community"] = gl.communities_label_propagation(adj, nodes)
    if enable.get("centrality"):
        topo["betweenness"] = {v: round(b, 6)
                               for v, b in gl.betweenness_centrality(adj, nodes).items()}
    if enable.get("constraint"):
        topo["constraint"] = {v: (round(c, 4) if (c := gl.burt_constraint(wadj, v)) is not None
                                  else None) for v in nodes}
    topo["_adj"] = {v: list(adj[v]) for v in nodes}
    return topo


# ---------- S5 缺口识别 ----------
def _node_brief(node_meta, nid):
    nd = node_meta.get(nid, {})
    return {"id": nid, "name": nd.get("name", nid), "type": nd.get("type", "?"),
            "disputed": nd.get("disputed", False)}


def detect_sparse_gaps(node_ids, topo, node_meta, anchor_ids, req, thresholds):
    """稀疏区域型缺口：≥2 指标组合判定（密度/带权密度/聚类/核心层级/度分位）。"""
    nodes = list(node_ids)
    den_t = thresholds.get("density_q", _quantile(topo["density"].values(), 0.3))
    deg_vals = list(topo["degree"].values())
    deg_t = thresholds.get("degree_q", _quantile(deg_vals, 0.3))
    core = topo.get("core", {})
    core_t = thresholds.get("core_q", _quantile(core.values(), 0.3)) if core else 0
    clus = topo.get("clustering", {})
    clus_t = thresholds.get("cluster_q", _quantile(clus.values(), 0.3)) if clus else 0

    gaps = []
    for v in nodes:
        hits = []
        if topo["density"][v] <= den_t:
            hits.append(("邻域密度", topo["density"][v], "处于低密度分位区间"))
        if topo["degree"][v] <= deg_t:
            hits.append(("节点度", topo["degree"][v], "处于低度分位区间"))
        if core and core.get(v, 0) <= core_t:
            hits.append(("核心层级", core.get(v), "处于低核心层级"))
        if clus and clus.get(v, 0) <= clus_t:
            hits.append(("聚类系数", clus.get(v), "聚类不足"))
        if len(hits) >= 2:   # ≥2 指标组合才判定为稀疏区域
            adj = topo["_adj"]
            involved = [v] + adj.get(v, [])
            related = bool(set(involved) & set(anchor_ids))
            gaps.append({
                "gap_id": f"sparse::{v}",
                "gap_type": "sparse_region",
                "trigger_metrics": {name: val for name, val, _ in hits},
                "nodes": involved,
                "missing_link": None,
                "anchor_linked": related,
                "weight_sum": round(sum(node_meta.get(n, {}).get("weight", 0.0)
                                        for n in involved), 4),
                "cause": {
                    "trigger_basis": "；".join(d for _, _, d in hits),
                    "both_sides": [_node_brief(node_meta, n) for n in involved[:6]],
                    "relation_to_request": _relation_text(req, related),
                },
            })
    return gaps


def detect_structural_holes(node_ids, topo, node_meta, anchor_ids, req, thresholds, top_m=10):
    """结构洞型缺口：社团边界 + 介数中心性/结构约束识别潜在桥接位置。"""
    comm = topo.get("community")
    if not comm:
        return []
    adj = {v: set(topo["_adj"].get(v, [])) for v in node_ids}
    bc = topo.get("betweenness", {})
    constraint = topo.get("constraint", {})
    bc_t = thresholds.get("bc_q", _quantile(bc.values(), 0.6)) if bc else 0

    candidates = {}
    nodes = list(node_ids)
    for i, u in enumerate(nodes):
        for w in nodes[i + 1:]:
            if comm.get(u) == comm.get(w):
                continue                 # 同社团跳过
            if w in adj[u]:
                continue                 # 已直接连接则非缺口
            common = adj[u] & adj[w]
            if not common:
                continue                 # 仅保留 2 跳可达的潜在桥接（跨社团连接稀缺）
            # 桥接吸引力：端点介数高 或 结构约束低
            cons = [constraint.get(u), constraint.get(w)]
            cons = [c for c in cons if c is not None]
            cons_score = (1 - min(cons)) if cons else 0.0
            bc_score = (bc.get(u, 0) + bc.get(w, 0)) / 2
            high_bc = bc.get(u, 0) >= bc_t or bc.get(w, 0) >= bc_t
            score = round(0.6 * bc_score + 0.4 * cons_score + 0.1 * len(common), 6)
            if high_bc or cons_score > 0:
                key = tuple(sorted((u, w)))
                if key not in candidates or candidates[key]["score"] < score:
                    candidates[key] = {"u": u, "w": w, "score": score,
                                       "bridges": list(common)}
    ranked = sorted(candidates.values(), key=lambda c: -c["score"])[:top_m]
    gaps = []
    for c in ranked:
        u, w = c["u"], c["w"]
        related = bool({u, w} & set(anchor_ids))
        gaps.append({
            "gap_id": f"hole::{u}|{w}",
            "gap_type": "structural_hole",
            "trigger_metrics": {
                "介数中心性_u": bc.get(u), "介数中心性_w": bc.get(w),
                "结构约束_u": constraint.get(u), "结构约束_w": constraint.get(w),
                "社团_u": comm.get(u), "社团_w": comm.get(w),
                "bridge_score": c["score"],
            },
            "nodes": [u, w] + c["bridges"],
            "missing_link": {"source": u, "target": w},
            "anchor_linked": related,
            "weight_sum": round(node_meta.get(u, {}).get("weight", 0.0)
                                + node_meta.get(w, {}).get("weight", 0.0), 4),
            "cause": {
                "trigger_basis": f"跨社团（{comm.get(u)}↔{comm.get(w)}）连接稀缺，"
                                 f"端点介数中心性偏高/结构约束偏低，存在潜在桥接机会",
                "both_sides": [_node_brief(node_meta, u), _node_brief(node_meta, w)],
                "relation_to_request": _relation_text(req, related),
            },
        })
    return gaps


def _relation_text(req, related):
    theme = req.get("theme", "")
    scene = req.get("scene", "")
    anchor = "与锚点主题直接相关" if related else "为锚点主题的外围延伸方向"
    return f"该缺口围绕主题「{theme}」、研究场景「{scene}」，{anchor}。"


def detect_gaps(node_ids, edges, node_meta, anchor_ids, req,
                thresholds=None, gap_types=("sparse_region", "structural_hole")):
    """S5 主入口：返回 (TopoEvidence, Gaps)。"""
    thresholds = thresholds or {}
    topo = topology_analysis(node_ids, edges)
    gaps = []
    if "sparse_region" in gap_types:
        gaps += detect_sparse_gaps(node_ids, topo, node_meta, anchor_ids, req, thresholds)
    if "structural_hole" in gap_types:
        gaps += detect_structural_holes(node_ids, topo, node_meta, anchor_ids, req, thresholds)
    # 争议/来源覆盖不足提示要素（S5-5）
    for g in gaps:
        disputed = [n for n in g["nodes"] if node_meta.get(n, {}).get("disputed")]
        if disputed:
            g["cause"]["dispute_note"] = "涉及争议标记对象：" + "、".join(
                node_meta.get(n, {}).get("name", n) for n in disputed[:5])
    return topo, gaps
