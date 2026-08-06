"""S6：对缺口候选进行趋势预测以评估方向潜力。

提供两类可替代实现方式（可单选或组合）：
  - 时间序列热度预测：由实体/关系出现频次随时间构造 Hot(t)，拟合趋势斜率。
  - 动态图关系演化预测：对结构洞缺口的缺失连接做链路概率占位估计。
信号不足/数据稀疏/不可用时执行回退策略，输出占位式趋势结论 + 不确定性提示。
"""
import math
from collections import defaultdict


def _year(ts):
    if not ts:
        return None
    return str(ts)[:4]


def _collect_signals(gap, dkg):
    """从 DKG 及演化信息收集与缺口相关的时间信号（出现年份频次）。"""
    nodes = dkg["nodes"]
    counts = defaultdict(float)
    points = 0
    for nid in gap["nodes"]:
        for oc in nodes.get(nid, {}).get("occurrences", []):
            y = _year(oc.get("ts"))
            if y:
                counts[y] += 1.0
                points += 1
    nidset = set(gap["nodes"])
    for e in dkg["edges"]:
        if e["source"] in nidset and e["target"] in nidset:
            for oc in e.get("occurrences", []):
                y = _year(oc.get("ts"))
                if y:
                    counts[y] += 1.0
                    points += 1
    return dict(sorted(counts.items())), points


def _slope(series):
    """最小二乘斜率（手算，无第三方依赖）。返回 (slope, n)。"""
    items = sorted(series.items())
    n = len(items)
    if n < 2:
        return 0.0, n
    xs = [int(y) for y, _ in items]
    ys = [v for _, v in items]
    x0 = xs[0]
    xs = [x - x0 for x in xs]
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0, n
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / denom
    return slope, n


def _logistic(x, k=1.5):
    return 1.0 / (1.0 + math.exp(-k * x))


def time_series_heat(gap, dkg, min_points=3):
    series, points = _collect_signals(gap, dkg)
    if points < min_points or len(series) < 2:
        return None   # 触发回退
    slope, n = _slope(series)
    mean_val = sum(series.values()) / len(series)
    norm_slope = slope / mean_val if mean_val else 0.0
    score = round(_logistic(norm_slope), 4)
    conclusion = "上升" if norm_slope > 0.15 else ("下降" if norm_slope < -0.15 else "平稳")
    confidence = round(min(1.0, points / 8.0), 3)
    return {
        "method": "time_series", "trend_score": score, "conclusion": conclusion,
        "hot_series": series, "time_window": f"{min(series)}–{max(series)}",
        "confidence": confidence, "fallback": False, "uncertainty_note": "",
    }


def relation_evolution(gap, dkg):
    """动态图关系演化：对结构洞缺失连接做链路概率占位估计。"""
    link = gap.get("missing_link")
    if not link:
        return None
    u, v = link["source"], link["target"]
    edges = dkg["edges"]
    adj = defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    common = adj[u] & adj[v]
    union = adj[u] | adj[v]
    jaccard = len(common) / len(union) if union else 0.0
    # 优先连接（preferential attachment）占位项 + 共同邻居 → 链路概率占位
    pa = len(adj[u]) * len(adj[v])
    pa_norm = _logistic(math.log1p(pa) - 2.0)
    link_prob = round(0.6 * jaccard + 0.4 * pa_norm, 4)
    score = link_prob
    confidence = round(min(1.0, len(common) / 4.0), 3)
    return {
        "method": "relation_evolution", "trend_score": score,
        "conclusion": "潜在连接概率较高" if link_prob > 0.5 else "潜在连接概率中低",
        "link_probability": link_prob, "common_neighbors": len(common),
        "time_window": "future-1", "confidence": confidence,
        "fallback": False, "uncertainty_note": "",
    }


def _fallback(gap, dkg):
    """回退策略：窗口统计外推占位。输出占位结论 + 不确定性提示。"""
    series, points = _collect_signals(gap, dkg)
    base = 0.45 if points else 0.4
    return {
        "method": "fallback", "trend_score": base,
        "conclusion": "信号不足，趋势不确定（占位结论）",
        "hot_series": series, "time_window": "n/a",
        "confidence": 0.2, "fallback": True,
        "uncertainty_note": "趋势预测因信号不足/数据稀疏触发回退，趋势评分为占位值，"
                            "可靠性边界有限，建议补充近年数据后复核。",
    }


def _fuse(ts, evo, mode="weighted", alpha=0.6, gate=0.4):
    """融合策略：加权 / 置信度门控 / 规则优先级。"""
    if ts and not evo:
        return ts
    if evo and not ts:
        return evo
    if not ts and not evo:
        return None
    if mode == "confidence_gate":
        chosen = ts if ts["confidence"] >= evo["confidence"] else evo
        out = dict(chosen)
        out["method"] = "fusion(confidence_gate)"
        out["fusion"] = {"type": "confidence_gate", "picked": chosen["method"]}
        return out
    if mode == "rule_priority":
        chosen = evo if evo["confidence"] >= gate else ts
        out = dict(chosen)
        out["method"] = "fusion(rule_priority)"
        out["fusion"] = {"type": "rule_priority", "picked": chosen["method"]}
        return out
    # weighted
    score = round(alpha * ts["trend_score"] + (1 - alpha) * evo["trend_score"], 4)
    return {
        "method": "fusion(weighted)", "trend_score": score,
        "conclusion": f"加权融合（ts={ts['conclusion']} / evo={evo['conclusion']}）",
        "time_window": ts.get("time_window"),
        "confidence": round((ts["confidence"] + evo["confidence"]) / 2, 3),
        "fallback": False, "uncertainty_note": "",
        "fusion": {"type": "weighted", "alpha": alpha},
        "hot_series": ts.get("hot_series", {}),
    }


def predict(gap, dkg, methods=("time_series", "relation_evolution"),
            fusion_mode="weighted", alpha=0.6):
    """S6 主入口：返回单条缺口的 TrendEvidence。"""
    ts = time_series_heat(gap, dkg) if "time_series" in methods else None
    evo = relation_evolution(gap, dkg) if "relation_evolution" in methods else None
    fused = _fuse(ts, evo, mode=fusion_mode, alpha=alpha)
    if fused is None:
        fused = _fallback(gap, dkg)
    return fused
