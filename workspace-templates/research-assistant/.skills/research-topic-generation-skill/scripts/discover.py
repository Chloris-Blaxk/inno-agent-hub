"""S2-S9: education research topic discovery runner.

This script connects request parsing, anchor/subgraph extraction, topology gap
detection, trend prediction, scoring, evidence-chain generation, and feedback.
It intentionally uses only the Python standard library and the sibling modules
in this skill package.
"""
import argparse
import json
import re
from collections import deque
from pathlib import Path

import dkg as dkg_mod
import evidence
import scoring
import topology
import trend


DEFAULT_CONFIG = {
    "defaults": {
        "scene": "教育科研选题",
        "preference": {"mode": "planning", "top_k": 5},
        "identity": "教师",
    },
    "runtime": {
        "anchor_threshold": 0.18,
        "k_hops": 2,
        "edge_top_m": 80,
        "top_k": 5,
        "gap_types": ["sparse_region", "structural_hole"],
        "diversity": {"per_community_cap": 2},
    },
    "weights": {"w1": 0.30, "w2": 0.30, "w3": 0.20, "w4": 0.20},
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG, ensure_ascii=False))
    if not path:
        return cfg
    p = Path(path)
    if not p.exists():
        return cfg
    user_cfg = load_json(p)
    for section, vals in user_cfg.items():
        if isinstance(vals, dict) and isinstance(cfg.get(section), dict):
            cfg[section].update(vals)
        else:
            cfg[section] = vals
    return cfg


def _tokens(value):
    if isinstance(value, list):
        value = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        value = " ".join(str(v) for v in value.values())
    return set(re.findall(r"[\w一-鿿]+", str(value or "").lower()))


def _request_keywords(req):
    kws = list(req.get("keywords") or [])
    kws.extend(_tokens(req.get("theme", "")))
    scene_tokens = list(_tokens(req.get("scene", "")))[:5]
    return list(dict.fromkeys([str(k) for k in kws + scene_tokens if str(k).strip()]))


def parse_request(raw, cfg):
    defaults = cfg.get("defaults", {})
    flags = []
    req = dict(raw)
    if not req.get("theme"):
        req["theme"] = req.get("title") or req.get("topic") or ""
        flags.append("missing_theme: 使用 title/topic 作为 theme；若仍为空，结果只能基于场景弱召回。")
    for field in ("scene", "preference", "identity"):
        if not req.get(field):
            req[field] = defaults.get(field)
            flags.append(f"missing_{field}: 使用默认值 {defaults.get(field)!r}。")
    req["keywords"] = _request_keywords(req)
    return req, flags


def _node_text(nd):
    vals = [nd.get("name", ""), nd.get("type", "")]
    vals.extend(nd.get("aliases", []))
    return " ".join(str(v) for v in vals if v)


def _overlap_score(keywords, text):
    kt = set(_tokens(keywords))
    tt = _tokens(text)
    return len(kt & tt) / len(kt) if kt else 0.0


def locate_anchors(dkg, req, cfg):
    nodes = dkg.get("nodes", {})
    threshold = float(cfg.get("runtime", {}).get("anchor_threshold", 0.18))
    theme = req.get("theme", "")
    scene = req.get("scene", "")
    keywords = req.get("keywords", [])
    scored = []
    for nid, nd in nodes.items():
        text = _node_text(nd)
        sim = max(dkg_mod.similarity(theme, text), dkg_mod.similarity(scene, text))
        overlap = _overlap_score(keywords, text)
        score = round(0.65 * sim + 0.35 * overlap, 6)
        scored.append((score, nid))
    scored.sort(reverse=True)
    anchors = [nid for score, nid in scored if score >= threshold][:8]
    flags = []
    if not anchors and scored:
        relaxed = threshold * 0.65
        anchors = [nid for score, nid in scored if score >= relaxed][:5]
        if anchors:
            flags.append(f"anchor_relaxed: 锚点阈值由 {threshold} 放宽到 {relaxed:.3f}。")
    if not anchors and scored:
        anchors = [nid for _, nid in scored[:3]]
        flags.append("anchor_fallback_top: 未达到阈值，采用相似度最高的 3 个节点弱召回。")
    return anchors, flags


def extract_subgraph(dkg, anchor_ids, cfg):
    runtime = cfg.get("runtime", {})
    k_hops = int(runtime.get("k_hops", 2))
    edge_top_m = runtime.get("edge_top_m", 80)
    edge_top_m = int(edge_top_m) if edge_top_m else None
    all_edges = dkg.get("edges", [])
    adj = {}
    for e in all_edges:
        adj.setdefault(e["source"], []).append((e["target"], e))
        adj.setdefault(e["target"], []).append((e["source"], e))
    seen = set(anchor_ids)
    q = deque((nid, 0) for nid in anchor_ids)
    while q:
        nid, depth = q.popleft()
        if depth >= k_hops:
            continue
        for nxt, _ in adj.get(nid, []):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, depth + 1))
    sub_edges = [e for e in all_edges if e["source"] in seen and e["target"] in seen]
    sub_edges.sort(key=lambda e: float(e.get("weight", 0.0)), reverse=True)
    if edge_top_m:
        sub_edges = sub_edges[:edge_top_m]
        seen = set(anchor_ids)
        for e in sub_edges:
            seen.add(e["source"])
            seen.add(e["target"])
    return sorted(seen), sub_edges, k_hops


def _next_materials(req, gap):
    pref = req.get("preference", {})
    mode = pref.get("mode") if isinstance(pref, dict) else str(pref)
    common = ["补充最近 3-5 年相关论文元数据", "补充同类历年立项题或校级课题样本"]
    if mode == "summary":
        return [
            "按时间整理教师已发表论文、上课案例、教学反思和课题成果",
            "为每份材料补充对象、方法、数据、成果和可迁移证据",
        ] + common
    if gap.get("gap_type") == "structural_hole":
        return [
            "补充缺口两侧主题的代表性文献与政策依据",
            "核查两个主题是否已有直接立项或论文覆盖",
        ] + common
    return [
        "补充该稀疏区域的学校实践问题和可获得样本",
        "核查是否存在相近题名，确认差异化表述",
    ] + common


def run_discovery(dkg, raw_request, cfg):
    req, flags = parse_request(raw_request, cfg)
    anchor_ids, anchor_flags = locate_anchors(dkg, req, cfg)
    flags.extend(anchor_flags)
    req["_anchor_ids"] = anchor_ids
    if not anchor_ids:
        return {
            "request": req,
            "rank_list": [],
            "evidence_chains": [],
            "fallback_flags": flags + ["no_anchor: 图谱中未找到可用锚点。"],
        }

    node_ids, edges, k_hops = extract_subgraph(dkg, anchor_ids, cfg)
    node_meta = dkg.get("nodes", {})
    topo, gaps = topology.detect_gaps(
        node_ids,
        edges,
        node_meta,
        anchor_ids,
        req,
        gap_types=tuple(cfg.get("runtime", {}).get("gap_types", ["sparse_region", "structural_hole"])),
    )
    if not gaps:
        return {
            "request": req,
            "anchors": anchor_ids,
            "rank_list": [],
            "evidence_chains": [],
            "fallback_flags": flags + ["no_gap: 局部子图未触发稀疏区域或结构洞规则。"],
        }

    trend_map = {g["gap_id"]: trend.predict(g, dkg) for g in gaps}
    score_map = scoring.compute_scores(gaps, node_meta, anchor_ids, req, trend_map)
    runtime = cfg.get("runtime", {})
    ranked = scoring.composite_and_rank(
        gaps,
        score_map,
        cfg.get("weights", DEFAULT_CONFIG["weights"]),
        diversity=runtime.get("diversity"),
        topo=topo,
        top_k=int(runtime.get("top_k", 5)),
    )
    gap_map = {g["gap_id"]: g for g in gaps}
    enriched_rank = []
    chains = []
    for i, item in enumerate(ranked, 1):
        gap = gap_map[item["gap_id"]]
        title = evidence.render_direction_title(gap, node_meta)
        rank_item = {
            "rank": i,
            "title": title,
            **item,
            "gap_nodes": gap["nodes"],
            "next_materials": _next_materials(req, gap),
        }
        enriched_rank.append(rank_item)
        chains.append(
            evidence.build_evidence_chain(
                item,
                gap,
                topo,
                node_meta,
                trend_map[item["gap_id"]],
                req,
                k_hops,
                dkg.get("ref_date"),
            )
        )
    return {
        "request": {k: v for k, v in req.items() if not k.startswith("_")},
        "anchors": anchor_ids,
        "subgraph_stats": {"nodes": len(node_ids), "edges": len(edges), "k_hops": k_hops},
        "rank_list": enriched_rank,
        "evidence_chains": chains,
        "fallback_flags": flags,
    }


def apply_feedback(dkg, result, feedback):
    rank_map = {r["gap_id"]: r for r in result.get("rank_list", [])}
    positives = set(feedback.get("positive") or feedback.get("selected_gap_ids") or [])
    negatives = set(feedback.get("negative") or feedback.get("rejected_gap_ids") or [])
    for gid in positives:
        if gid in rank_map:
            dkg_mod.feedback_update(dkg, rank_map[gid].get("gap_nodes", []), signal=1.0)
    for gid in negatives:
        if gid in rank_map:
            dkg_mod.feedback_update(dkg, rank_map[gid].get("gap_nodes", []), signal=-1.0)
    dkg.setdefault("feedback_log", []).append(feedback)
    return dkg


def _main():
    ap = argparse.ArgumentParser(description="S2-S9 选题发现、证据链与反馈闭环")
    sub = ap.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="运行选题与研究缺口挖掘")
    run.add_argument("--dkg", required=True)
    run.add_argument("--request", required=True)
    run.add_argument("--config")
    run.add_argument("--out", required=True)

    fb = sub.add_parser("feedback", help="将用户反馈写回 DKG 权重")
    fb.add_argument("--dkg", required=True)
    fb.add_argument("--result", required=True)
    fb.add_argument("--feedback", required=True)
    fb.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "run":
        cfg = load_config(args.config)
        result = run_discovery(load_json(args.dkg), load_json(args.request), cfg)
        save_json(result, args.out)
        print(f"[S2-S9] rank={len(result['rank_list'])} evidence={len(result['evidence_chains'])} -> {args.out}")
    elif args.cmd == "feedback":
        out = apply_feedback(load_json(args.dkg), load_json(args.result), load_json(args.feedback))
        save_json(out, args.out)
        print(f"[S9] feedback applied -> {args.out}")


if __name__ == "__main__":
    _main()
