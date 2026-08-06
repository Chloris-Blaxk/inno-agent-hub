"""S1：构建并维护教育科研动态知识图谱 DKG。

实现多源融合、增量更新、对齐消歧（字符串 + 语义相似融合）、冲突消解、
动态权重更新（时间衰减 → 来源增益）、演化记录 EvoLog 与版本化维护。

DKG 文件格式（JSON）：
{
  "version": 3,
  "params": {"decay_lambda":0.35, "source_gain":0.5, "align_threshold":0.82},
  "nodes": { "<id>": {id,name,type,aliases,sources,occurrences,
                       latest_ts,weight,disputed,dispute_info} },
  "edges": [ {id,source,target,type,sources,occurrences,latest_ts,
              weight,disputed,dispute_info} ],
  "evolog": [ {obj_id,change_type,timestamp,sources,weight_dir,
               conflict_decision,dispute_flag} ]
}

输入源记录格式见 references/workflow.md#S1 与 examples/sample_sources.json。
"""
import argparse
import json
import math
import re
from datetime import date, datetime
from difflib import SequenceMatcher

DEFAULT_PARAMS = {"decay_lambda": 0.35, "source_gain": 0.5, "align_threshold": 0.82}


# ---------- 工具 ----------
def _slug(name, etype):
    s = re.sub(r"\s+", "", f"{etype}::{name}".lower())
    return re.sub(r"[^\w:一-鿿]", "", s)


def _parse_ts(ts):
    if not ts:
        return None
    ts = str(ts).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(ts, fmt).date()
        except ValueError:
            continue
    return None


def _years_between(a, b):
    return abs((a - b).days) / 365.25


def _tokens(s):
    return set(re.findall(r"[\w一-鿿]+", s.lower()))


def similarity(a, b):
    """字符串匹配 + token 语义相似的融合策略（离线近似）。

    部署时可由模型服务组件替换为向量语义相似度。
    """
    str_sim = SequenceMatcher(None, a, b).ratio()
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return 0.5 * str_sim + 0.5 * jac


# ---------- 建图 ----------
def empty_dkg(params=None):
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    return {"version": 0, "params": p, "nodes": {}, "edges": [], "evolog": []}


def _log(dkg, obj_id, change_type, sources, weight_dir="", conflict="", dispute=False):
    dkg["evolog"].append({
        "obj_id": obj_id, "change_type": change_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "sources": sources, "weight_dir": weight_dir,
        "conflict_decision": conflict, "dispute_flag": dispute,
    })


def _find_alias_match(dkg, name, etype, threshold):
    """对齐消歧：在同类型节点中找字符串+语义相似 >= 阈值的已有节点。"""
    best, best_sim = None, 0.0
    for nid, nd in dkg["nodes"].items():
        if nd["type"] != etype:
            continue
        cands = [nd["name"]] + nd.get("aliases", [])
        sim = max(similarity(name, c) for c in cands)
        if sim > best_sim:
            best, best_sim = nid, sim
    if best is not None and best_sim >= threshold:
        return best
    return None


def _upsert_entity(dkg, name, etype, aliases, source_id, ts, threshold):
    sid = _slug(name, etype)
    if sid in dkg["nodes"]:
        nid = sid
        merged = False
    else:
        nid = _find_alias_match(dkg, name, etype, threshold)
        merged = nid is not None
        if nid is None:
            nid = sid
            dkg["nodes"][nid] = {
                "id": nid, "name": name, "type": etype, "aliases": [],
                "sources": [], "occurrences": [], "latest_ts": None,
                "weight": 0.0, "disputed": False, "dispute_info": [],
            }
            _log(dkg, nid, "add_entity", [source_id])
    nd = dkg["nodes"][nid]
    for al in [name] + list(aliases or []):
        if al != nd["name"] and al not in nd["aliases"]:
            nd["aliases"].append(al)
    if source_id not in nd["sources"]:
        nd["sources"].append(source_id)
    nd["occurrences"].append({"source": source_id, "ts": ts})
    if merged:
        _log(dkg, nid, "merge_entity", [source_id], conflict=f"align<-{sid}")
    return nid


def _upsert_relation(dkg, sid, tid, rtype, source_id, ts):
    for e in dkg["edges"]:
        if {e["source"], e["target"]} == {sid, tid}:
            if e["type"] != rtype:
                # 关系冲突：同一对实体存在不同关系类型
                e["disputed"] = True
                e["dispute_info"].append({"source": source_id, "candidate_type": rtype})
                _log(dkg, e["id"], "relation_conflict", [source_id],
                     conflict=f"{e['type']}|{rtype}", dispute=True)
            if source_id not in e["sources"]:
                e["sources"].append(source_id)
            e["occurrences"].append({"source": source_id, "ts": ts})
            return e["id"]
    eid = f"e{len(dkg['edges'])}:{sid}->{tid}"
    dkg["edges"].append({
        "id": eid, "source": sid, "target": tid, "type": rtype,
        "sources": [source_id], "occurrences": [{"source": source_id, "ts": ts}],
        "latest_ts": ts, "weight": 0.0, "disputed": False, "dispute_info": [],
    })
    _log(dkg, eid, "add_relation", [source_id])
    return eid


def _trust_of(source_map, source_id):
    return source_map.get(source_id, {}).get("trust", 0.6)


def _update_weights(dkg, source_map, ref_date):
    """动态权重：先时间衰减得中间权重，再来源增益得最终权重。"""
    lam = dkg["params"]["decay_lambda"]
    gamma = dkg["params"]["source_gain"]

    def compute(occs, sources):
        base = 0.0           # 时间衰减后的中间权重
        latest = None
        for oc in occs:
            d = _parse_ts(oc.get("ts"))
            if d is None:
                base += 1.0
                continue
            dt = _years_between(ref_date, d)
            base += math.exp(-lam * dt)
            latest = d if latest is None or d > latest else latest
        trusts = [_trust_of(source_map, s) for s in sources] or [0.6]
        gain = 1.0 + gamma * (sum(trusts) / len(trusts))   # 来源增益
        return round(base * gain, 6), (latest.isoformat() if latest else None)

    for nd in dkg["nodes"].values():
        old = nd["weight"]
        nd["weight"], nd["latest_ts"] = compute(nd["occurrences"], nd["sources"])
        _log(dkg, nd["id"], "weight_update", nd["sources"],
             weight_dir="+" if nd["weight"] >= old else "-")
    for e in dkg["edges"]:
        e["weight"], e["latest_ts"] = compute(e["occurrences"], e["sources"])


def build(sources, base=None, params=None, ref_date=None):
    dkg = base if base else empty_dkg(params)
    if params:
        dkg["params"].update(params)
    threshold = dkg["params"]["align_threshold"]
    source_map = {}
    all_ts = []
    for rec in sources:
        sid_src = rec["source_id"]
        source_map[sid_src] = {"trust": float(rec.get("source_trust", 0.6)),
                               "type": rec.get("source_type", "未知")}
        ts = rec.get("timestamp")
        d = _parse_ts(ts)
        if d:
            all_ts.append(d)
        name_to_id = {}
        for ent in rec.get("entities", []):
            nid = _upsert_entity(dkg, ent["name"], ent.get("type", "研究主题"),
                                 ent.get("aliases"), sid_src, ts, threshold)
            name_to_id[ent["name"]] = nid
        for rel in rec.get("relations", []):
            s = name_to_id.get(rel["source"]) or _upsert_entity(
                dkg, rel["source"], rel.get("source_type", "研究主题"), [], sid_src, ts, threshold)
            t = name_to_id.get(rel["target"]) or _upsert_entity(
                dkg, rel["target"], rel.get("target_type", "研究主题"), [], sid_src, ts, threshold)
            _upsert_relation(dkg, s, t, rel.get("type", "关联"), sid_src, ts)
    rd = _parse_ts(ref_date) or (max(all_ts) if all_ts else date.today())
    # 合并历史 source_map（增量更新时旧来源可信度未知则用默认）
    dkg.setdefault("_source_map", {})
    dkg["_source_map"].update({k: v for k, v in source_map.items()})
    full_map = dkg["_source_map"]
    _update_weights(dkg, full_map, rd)
    # 标记争议实体（来自含 dispute 的关系两端 + 类型冲突）
    for e in dkg["edges"]:
        if e["disputed"]:
            for nid in (e["source"], e["target"]):
                if nid in dkg["nodes"]:
                    dkg["nodes"][nid]["disputed"] = True
    dkg["version"] += 1
    dkg["ref_date"] = rd.isoformat()
    return dkg


def feedback_update(dkg, gap_node_ids, signal, beta=0.3):
    """S9：反馈映射为权重增强/衰减。signal>0 增强，<0 衰减。"""
    direction = "+" if signal >= 0 else "-"
    factor = 1.0 + beta * signal
    for nid in gap_node_ids:
        if nid in dkg["nodes"]:
            dkg["nodes"][nid]["weight"] = round(dkg["nodes"][nid]["weight"] * factor, 6)
            _log(dkg, nid, "feedback", dkg["nodes"][nid]["sources"], weight_dir=direction)
    for e in dkg["edges"]:
        if e["source"] in gap_node_ids and e["target"] in gap_node_ids:
            e["weight"] = round(e["weight"] * factor, 6)
            _log(dkg, e["id"], "feedback", e["sources"], weight_dir=direction)
    dkg["version"] += 1
    return dkg


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(dkg, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dkg, f, ensure_ascii=False, indent=2)


def _main():
    ap = argparse.ArgumentParser(description="S1 动态知识图谱构建/维护")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="构建或增量更新 DKG")
    b.add_argument("--sources", required=True)
    b.add_argument("--base", help="已有 DKG（增量更新）")
    b.add_argument("--out", required=True)
    b.add_argument("--ref-date", help="参考日期 YYYY-MM-DD，默认取数据最新时间")
    s = sub.add_parser("stats", help="查看 DKG 统计")
    s.add_argument("--dkg", required=True)
    args = ap.parse_args()

    if args.cmd == "build":
        with open(args.sources, encoding="utf-8") as f:
            sources = json.load(f)
        base = load(args.base) if args.base else None
        dkg = build(sources, base=base, ref_date=args.ref_date)
        save(dkg, args.out)
        print(f"[S1] DKG v{dkg['version']}：{len(dkg['nodes'])} 实体 / "
              f"{len(dkg['edges'])} 关系 / {len(dkg['evolog'])} 演化记录 → {args.out}")
    elif args.cmd == "stats":
        dkg = load(args.dkg)
        disp = sum(1 for n in dkg["nodes"].values() if n["disputed"])
        print(f"version={dkg['version']} ref_date={dkg.get('ref_date')}")
        print(f"nodes={len(dkg['nodes'])} edges={len(dkg['edges'])} disputed_nodes={disp}")


if __name__ == "__main__":
    _main()
