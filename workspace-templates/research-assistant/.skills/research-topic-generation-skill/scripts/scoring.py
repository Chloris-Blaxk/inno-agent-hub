"""S7：综合评分与排序，形成候选研究方向优先级列表 RankList。

综合评分 = 匹配评分 MatchScore + 缺口评分 GapScore + 趋势评分 TrendScore
          + 可行性评分 FeasibilityScore，按权重方案加权组合或规则组合。
权重方案、筛选与多样性约束由偏好字段/身份字段触发选择（由 discover.py 传入）。
"""
import re
from collections import defaultdict


def _tokens(s):
    return set(re.findall(r"[\w一-鿿]+", (s or "").lower()))


def match_score(gap, node_meta, anchor_ids, req):
    """匹配评分：主题语义相关性 + 研究场景约束满足。"""
    theme_tok = _tokens(req.get("theme", "")) | {
        t for kw in req.get("keywords", []) for t in _tokens(kw)}
    names = " ".join(node_meta.get(n, {}).get("name", "") for n in gap["nodes"])
    name_tok = _tokens(names)
    overlap = len(theme_tok & name_tok) / len(theme_tok) if theme_tok else 0.0
    anchor_bonus = 0.35 if gap.get("anchor_linked") else 0.0
    scene_tok = _tokens(req.get("scene", ""))
    scene_hit = 0.15 if (scene_tok & name_tok) else 0.0
    return round(min(1.0, 0.5 * overlap + anchor_bonus + scene_hit + 0.1), 4)


def gap_score(gap, hole_minmax):
    if gap["gap_type"] == "sparse_region":
        ind = len(gap["trigger_metrics"])
        return round(min(1.0, 0.4 + 0.2 * (ind - 1)), 4)   # 2 指标→0.6, 4→1.0
    bs = gap["trigger_metrics"].get("bridge_score", 0.0)
    lo, hi = hole_minmax
    norm = (bs - lo) / (hi - lo) if hi > lo else 0.5
    return round(0.5 + 0.5 * norm, 4)


def feasibility_score(gap, node_meta, req):
    """可行性评分：数据充分性 + 来源覆盖 - 争议惩罚 - 资源/阶段约束。"""
    occ = sum(len(node_meta.get(n, {}).get("occurrences", [])) for n in gap["nodes"])
    src = set()
    for n in gap["nodes"]:
        src.update(node_meta.get(n, {}).get("sources", []))
    data_suff = min(1.0, occ / 8.0)
    source_cov = min(1.0, len(src) / 4.0)
    disputed = any(node_meta.get(n, {}).get("disputed") for n in gap["nodes"])
    penalty = 0.2 if disputed else 0.0
    # 身份字段：资源/阶段受限 → 对涉及节点多（高资源需求）的候选降权
    identity = _flatten_text(req.get("identity")).lower()
    size = len(gap["nodes"])
    resource_pen = 0.0
    if any(k in identity for k in ("研究生", "新手", "资源有限", "起步", "student")):
        resource_pen = min(0.25, 0.04 * max(0, size - 4))
    return round(max(0.0, 0.5 * data_suff + 0.4 * source_cov + 0.1
                     - penalty - resource_pen), 4)


def _flatten_text(value):
    """把教师画像对象/列表归一化为可检索文本。"""
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return str(value or "")


def compute_scores(gaps, node_meta, anchor_ids, req, trend_map):
    hole_bs = [g["trigger_metrics"].get("bridge_score", 0.0)
               for g in gaps if g["gap_type"] == "structural_hole"]
    hole_minmax = (min(hole_bs), max(hole_bs)) if hole_bs else (0.0, 1.0)
    scores = {}
    for g in gaps:
        te = trend_map.get(g["gap_id"], {})
        scores[g["gap_id"]] = {
            "MatchScore": match_score(g, node_meta, anchor_ids, req),
            "GapScore": gap_score(g, hole_minmax),
            "TrendScore": round(float(te.get("trend_score", 0.4)), 4),
            "FeasibilityScore": feasibility_score(g, node_meta, req),
        }
    return scores


def composite_and_rank(gaps, scores, weights, strategy="weighted",
                       gate=0.35, diversity=None, topo=None, top_k=None):
    """综合评分 + 排序 + 多样性约束。"""
    gmap = {g["gap_id"]: g for g in gaps}
    ranked = []
    for gid, s in scores.items():
        if strategy == "rule":
            # 规则组合：先可行性门控，再按缺口+趋势优先级
            if s["FeasibilityScore"] < gate:
                composite = 0.0
                gated = True
            else:
                composite = round(0.6 * s["GapScore"] + 0.4 * s["TrendScore"], 4)
                gated = False
            synth = f"规则组合：可行性门控(>={gate}) {'未通过' if gated else '通过'}，" \
                    f"通过后按 0.6*缺口+0.4*趋势排序"
        else:
            w = weights
            composite = round(w["w1"] * s["MatchScore"] + w["w2"] * s["GapScore"]
                              + w["w3"] * s["TrendScore"] + w["w4"] * s["FeasibilityScore"], 4)
            synth = (f"加权组合：{w['w1']}*匹配 + {w['w2']}*缺口 + "
                     f"{w['w3']}*趋势 + {w['w4']}*可行性")
        ranked.append({
            "gap_id": gid, "gap_type": gmap[gid]["gap_type"],
            "composite_score": composite, "score_breakdown": s,
            "synthesis": synth,
        })
    ranked.sort(key=lambda r: -r["composite_score"])

    # 多样性约束：限制同一社团/同一类型的占比
    if diversity and topo and topo.get("community"):
        comm = topo["community"]
        per_comm_cap = diversity.get("per_community_cap")
        if per_comm_cap:
            seen = defaultdict(int)
            kept, deferred = [], []
            for r in ranked:
                head = gmap[r["gap_id"]]["nodes"][0]
                c = comm.get(head)
                if seen[c] < per_comm_cap:
                    seen[c] += 1
                    kept.append(r)
                else:
                    r["diversity_note"] = f"社团 {c} 已达多样性上限，降序保留"
                    deferred.append(r)
            ranked = kept + deferred
    if top_k:
        ranked = ranked[:top_k]
    return ranked
