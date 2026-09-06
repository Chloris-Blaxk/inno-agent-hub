#!/usr/bin/env python3
"""从 skill-library 生成技能库展示站(docs/)。

单一真源:
  - 每个 skill-library/<id>/SKILL.md 的 frontmatter -> name / category / description
  - skill-library/README.md 的目录表 -> 类型 / 通过验证 / 一句话 / 引用 / 效果 / 分组
  - skill-library/assets/<id>/*.gif|png -> demo 素材
  - scripts/skill_scenarios.py -> 星图的场景归属与示例输入

产出:
  - docs/index.html   星图首页(场景星系 + 程序化 riso 图块 + 点击看详情)
  - docs/all.html     全部技能(卡片网格 + 搜索 + 分类筛选)
  - docs/skills.json  结构化数据,供本站与平台复用

用法: python3 scripts/build_skills_site.py
"""
from __future__ import annotations
import json
import math
import os
import re
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import riso_art  # noqa: E402
from skill_scenarios import FALLBACK, SCENARIOS, SKILLS as SCENARIO_MAP  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "skill-library")
DOCS = os.path.join(ROOT, "docs")
HERE = os.path.dirname(os.path.abspath(__file__))
GRID_TEMPLATE = os.path.join(HERE, "site_template.html")
MAP_TEMPLATE = os.path.join(HERE, "map_template.html")
STATIC_DIR = os.path.join(HERE, "static")          # 404 / favicon / og 图,原样拷到 docs/
REPO_URL = "https://github.com/Chloris-Blaxk/inno-agent-hub"
# 站点根 URL(带末尾 /),给 og:url / canonical 用;CI 里按仓库算,本地可用 SITE_URL 环境变量覆盖
SITE_URL = os.environ.get("SITE_URL", "https://chloris-blaxk.github.io/inno-agent-hub/").rstrip("/") + "/"

# category -> 莫兰迪配色(卡片网格页用)
PALETTE = {
    "教学辅导": {"bg": "#cdd9ce", "fg": "#3f5c48"},
    "内容创作": {"bg": "#e8d6ca", "fg": "#9a5c40"},
    "文档处理": {"bg": "#cddae3", "fg": "#3d627e"},
    "研究检索": {"bg": "#e6e0cd", "fg": "#736846"},
    "开发工具": {"bg": "#d7d0de", "fg": "#5b4b73"},
}
DEFAULT_COLOR = {"bg": "#dcdcdc", "fg": "#555555"}

FEATURED_HINT = ["k12-lesson-planning", "comment-on-docx", "frontend-slides", "algorithmic-art"]

MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# ── 星图画布 ────────────────────────────────────────────────
WORLD_W, WORLD_H = 1980, 1180
CLUSTER_POS = {
    "备课": (452, 556),
    "讲课": (898, 248),
    "自学": (772, 906),
    "研究": (1352, 798),
    "创造": (1566, 412),
}
LABEL_HALF_W, LABEL_HALF_H = 188, 96   # 标题+说明文字的占位框,图块须避开
# 角落大字(Inno / Agent)的占位框。字号 168px、Georgia 下宽约 2.0~2.5 倍字号,
# 放大后必须让图块避开,否则会被压住。
CORNER_FONT = 168
CORNER_BOXES = [
    (34, 56, 34 + int(CORNER_FONT * 2.05), 56 + CORNER_FONT),                       # 左上 Inno
    (WORLD_W - 34 - int(CORNER_FONT * 2.55), WORLD_H - 64 - CORNER_FONT,
     WORLD_W - 34, WORLD_H - 64),                                                   # 右下 Agent
]
GOLDEN = math.pi * (3 - math.sqrt(5))


def read_frontmatter(path: str) -> dict:
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        return {}
    out, key = {}, None
    for line in m.group(1).split("\n"):
        if re.match(r"^[a-zA-Z_-]+:", line):
            key, _, val = line.partition(":")
            key = key.strip()
            out[key] = val.strip()
        elif key and line.startswith("  ") and out.get(key) in (">-", ">", "|", "|-", ""):
            out[key] = (out.get(key, "") if out.get(key) not in (">-", ">", "|", "|-") else "") + line.strip()
        elif key and line.startswith("  ") and key in out:
            out[key] = (out[key] + " " + line.strip()).strip()
    for k, v in list(out.items()):
        if isinstance(v, str):
            out[k] = v.strip().strip('"').strip("'")
    return out


def parse_readme(path: str) -> dict:
    rows: dict[str, dict] = {}
    group, cols = None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("### "):
            group, cols = line[4:].strip(), None
            continue
        if line.startswith("| Skill |"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            continue
        if not cols or not line.startswith("|"):
            continue
        if set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(cols):
            continue
        rec = dict(zip(cols, cells))
        m = MD_LINK.search(rec.get("Skill", ""))
        if not m:
            continue
        sid = m.group(2).strip("./").strip("/")
        ref_t = ref_u = ""
        rm = MD_LINK.search(rec.get("引用", ""))
        if rm:
            ref_t, ref_u = rm.group(1), rm.group(2)
        demo = ""
        dm = MD_LINK.search(rec.get("效果", ""))
        if dm:
            demo = dm.group(2).lstrip("./")
        rows[sid] = {
            "group": group, "type": rec.get("类型", "") or "收集",
            "verified": bool(rec.get("通过验证", "").strip()),
            "tagline": rec.get("一句话", "").strip(),
            "ref_text": ref_t, "ref_url": ref_u, "demo": demo,
        }
    return rows


def find_demo(sid: str) -> str:
    d = os.path.join(LIB, "assets", sid)
    if not os.path.isdir(d):
        return ""
    for f in sorted(os.listdir(d)):
        if f.lower().endswith((".gif", ".png", ".jpg", ".webp")):
            return f"assets/{sid}/{f}"
    return ""


def layout_map(skills: list[dict]) -> list[dict]:
    """把每个 skill 摆到它所属星系周围,再做一轮松弛避免重叠。"""
    by_sc: dict[str, list[dict]] = {}
    for s in skills:
        by_sc.setdefault(s["scenario"], []).append(s)

    for key, members in by_sc.items():
        cx, cy = CLUSTER_POS.get(key, (WORLD_W / 2, WORLD_H / 2))
        n = len(members)
        radius = max(232, 122 + 34 * math.sqrt(n))  # 小星系也要撑开,免得贴住标题
        for i, s in enumerate(members):
            r = riso_art.Rand(riso_art.seed_of(s["id"] + key))
            rr = radius * math.sqrt((i + 0.75) / n)
            th = i * GOLDEN + r.rng(-0.34, 0.34)
            s["x"] = cx + rr * math.cos(th) + r.rng(-20, 20)
            s["y"] = cy + rr * math.sin(th) * 0.86 + r.rng(-20, 20)

    label_rects = [
        (cx - LABEL_HALF_W, cy - LABEL_HALF_H, cx + LABEL_HALF_W, cy + LABEL_HALF_H)
        for cx, cy in CLUSTER_POS.values()
    ] + [(x0 - 14, y0 - 14, x1 + 14, y1 + 14) for (x0, y0, x1, y1) in CORNER_BOXES]

    # 矩形分离:沿重叠最小的轴推开,竖版/横版图块都能正确避让
    gap = 52   # 要容得下 ±24px 的漂浮,否则相邻图块会漂到互相压住
    for _ in range(140):
        for i, a in enumerate(skills):
            for b in skills[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                ox = (a["w"] + b["w"]) / 2 + gap - abs(dx)
                oy = (a["h"] + b["h"]) / 2 + gap - abs(dy)
                if ox <= 0 or oy <= 0:
                    continue
                if ox < oy:
                    push = ox / 2 * (1 if dx >= 0 else -1)
                    a["x"] -= push; b["x"] += push
                else:
                    push = oy / 2 * (1 if dy >= 0 else -1)
                    a["y"] -= push; b["y"] += push
        for s in skills:
            hw, hh = s["w"] / 2, s["h"] / 2
            for (lx0, ly0, lx1, ly1) in label_rects:
                lcx, lcy = (lx0 + lx1) / 2, (ly0 + ly1) / 2
                dx, dy = s["x"] - lcx, s["y"] - lcy
                ox = (lx1 - lx0) / 2 + hw - abs(dx)
                oy = (ly1 - ly0) / 2 + hh - abs(dy)
                if ox <= 0 or oy <= 0:
                    continue
                if ox < oy:
                    s["x"] += ox * (1 if dx >= 0 else -1)
                else:
                    s["y"] += oy * (1 if dy >= 0 else -1)
            s["x"] = min(max(s["x"], hw + 34), WORLD_W - hw - 34)
            s["y"] = min(max(s["y"], hh + 34), WORLD_H - hh - 34)

    # 收尾:标题避让可能把图块又推回彼此身上,再纯分离几轮
    for _ in range(40):
        for i, a in enumerate(skills):
            for b in skills[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                ox = (a["w"] + b["w"]) / 2 + gap - abs(dx)
                oy = (a["h"] + b["h"]) / 2 + gap - abs(dy)
                if ox <= 0 or oy <= 0:
                    continue
                if ox < oy:
                    push = ox / 2 * (1 if dx >= 0 else -1)
                    a["x"] -= push; b["x"] += push
                else:
                    push = oy / 2 * (1 if dy >= 0 else -1)
                    a["y"] -= push; b["y"] += push
        for s in skills:
            hw, hh = s["w"] / 2, s["h"] / 2
            s["x"] = min(max(s["x"], hw + 34), WORLD_W - hw - 34)
            s["y"] = min(max(s["y"], hh + 34), WORLD_H - hh - 34)

    for s in skills:
        s["x"], s["y"] = round(s["x"], 1), round(s["y"], 1)
    return skills


def main() -> int:
    readme = parse_readme(os.path.join(LIB, "README.md"))
    valid_sc = {s["key"] for s in SCENARIOS}
    skills, unmapped = [], []

    for sid in sorted(os.listdir(LIB)):
        d = os.path.join(LIB, sid)
        sk = os.path.join(d, "SKILL.md")
        if not os.path.isdir(d) or sid == "assets" or not os.path.isfile(sk):
            continue
        fm = read_frontmatter(sk)
        r = readme.get(sid, {})
        cat = fm.get("category", "") or "未分类"
        demo = r.get("demo") or find_demo(sid)
        tagline = r.get("tagline") or (fm.get("description", "")[:60] + "…")

        meta = SCENARIO_MAP.get(sid)
        if not meta:
            unmapped.append(sid)
            meta = {"scenario": FALLBACK, "also": [], "example": f"用 {sid} 来帮我……"}
        scenario = meta["scenario"] if meta["scenario"] in valid_sc else FALLBACK
        art = riso_art.make_tile(sid, scenario)
        # 漂浮参数:幅度保底 11px,否则看起来跟静止没区别
        fr = riso_art.Rand(riso_art.seed_of(sid + "float"))
        fx, fy = fr.rng(-24, 24), fr.rng(-24, 24)
        if abs(fx) < 11: fx = 11 if fx >= 0 else -11
        if abs(fy) < 11: fy = 11 if fy >= 0 else -11

        skills.append({
            "id": sid, "name": fm.get("name", sid), "category": cat,
            "color": PALETTE.get(cat, DEFAULT_COLOR), "tagline": tagline,
            "description": fm.get("description", ""),
            "type": r.get("type", "收集"), "verified": r.get("verified", False),
            "group": r.get("group", ""), "refText": r.get("ref_text", ""),
            "refUrl": r.get("ref_url", ""), "demo": demo, "hasDemo": bool(demo),
            "scenario": scenario,
            "also": [a for a in meta.get("also", []) if a in valid_sc and a != scenario],
            "example": meta["example"],
            "svg": art["svg"], "w": art["w"], "h": art["h"], "pattern": art["pattern"],
            "fx": round(fx, 1), "fy": round(fy, 1),
            "dur": round(fr.rng(6, 13), 1), "delay": round(fr.rng(0, 7), 1),
            "rot": round(fr.rng(-1.6, 1.6), 2),   # 轻微旋转,比纯平移更"活"
        })

    featured = [s["id"] for s in skills if s["hasDemo"]]
    order = {s["id"] for s in skills}
    for fid in FEATURED_HINT:
        if fid in order and fid not in featured:
            featured.append(fid)
    featured = featured[:4]
    for i, s in enumerate(skills, 1):
        s["num"] = f"{i:02d}"
        s["featured"] = s["id"] in featured

    layout_map(skills)

    cats: dict[str, int] = {}
    for s in skills:
        cats[s["category"]] = cats.get(s["category"], 0) + 1
    sc_counts: dict[str, int] = {}
    for s in skills:
        sc_counts[s["scenario"]] = sc_counts.get(s["scenario"], 0) + 1

    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "count": len(skills),
        "repo": REPO_URL,
        "site": SITE_URL,
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "scenarios": [
            {**sc, "count": sc_counts.get(sc["key"], 0),
             "x": CLUSTER_POS.get(sc["key"], (0, 0))[0], "y": CLUSTER_POS.get(sc["key"], (0, 0))[1]}
            for sc in SCENARIOS
        ],
        "world": {"w": WORLD_W, "h": WORLD_H},
        "skills": skills,
    }

    os.makedirs(DOCS, exist_ok=True)
    copied = 0
    for s in skills:
        if not s["demo"]:
            continue
        src, dst = os.path.join(LIB, s["demo"]), os.path.join(DOCS, s["demo"])
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        else:
            print(f"   ⚠️ demo 源缺失,已忽略: {s['id']} -> {s['demo']}")
            s["demo"], s["hasDemo"] = "", False

    with open(os.path.join(DOCS, "skills.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 静态附件:404 页、favicon、og 分享图
    if os.path.isdir(STATIC_DIR):
        for f in sorted(os.listdir(STATIC_DIR)):
            shutil.copy2(os.path.join(STATIC_DIR, f), os.path.join(DOCS, f))
    open(os.path.join(DOCS, ".nojekyll"), "a").close()

    payload = json.dumps(data, ensure_ascii=False)
    for tpl, out in ((MAP_TEMPLATE, "index.html"), (GRID_TEMPLATE, "all.html")):
        if not os.path.isfile(tpl):
            print(f"❌ 缺少模板 {tpl}", file=sys.stderr)
            return 1
        html = (open(tpl, encoding="utf-8").read()
                .replace("/*__DATA__*/null", payload)
                .replace("{{SITE_URL}}", SITE_URL)
                .replace("{{PAGE}}", out)
                .replace("{{COUNT}}", str(len(skills))))
        with open(os.path.join(DOCS, out), "w", encoding="utf-8") as f:
            f.write(html)

    print(f"✅ {len(skills)} 个 skill -> docs/index.html(星图)+ docs/all.html(网格)")
    print("   星系: " + " · ".join(f"{k}({v})" for k, v in sc_counts.items()))
    print("   分类: " + " · ".join(f"{c['name']}({c['count']})" for c in data["categories"]))
    print(f"   demo {copied} 个 | 已验证 {sum(1 for s in skills if s['verified'])} 个 | 图块 {len(skills)} 张")
    if unmapped:
        print(f"   ⚠️ 未配场景/示例(已兜底,建议补 scripts/skill_scenarios.py): {', '.join(unmapped)}")
    miss = [s["id"] for s in skills if not s["refUrl"] and s["type"] == "收集"]
    if miss:
        print(f"   ⚠️ 收集类但缺引用: {', '.join(miss)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
