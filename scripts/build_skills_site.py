#!/usr/bin/env python3
"""从 skill-library 生成技能库展示站(docs/)。

单一真源:
  - 每个 skill-library/<id>/SKILL.md 的 frontmatter -> name / category / description
  - skill-library/README.md 的目录表 -> 类型 / 通过验证 / 一句话 / 引用 / 效果 / 分组
  - skill-library/assets/<id>/*.gif|png -> demo 素材

产出:
  - docs/skills.json  (数据,供本站与平台复用)
  - docs/index.html   (自包含单页,数据内联,可直接双击打开)

用法: python3 scripts/build_skills_site.py
"""
from __future__ import annotations
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "skill-library")
DOCS = os.path.join(ROOT, "docs")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_template.html")

# category -> 莫兰迪配色
PALETTE = {
    "教学辅导": {"bg": "#cdd9ce", "fg": "#3f5c48"},
    "内容创作": {"bg": "#e8d6ca", "fg": "#9a5c40"},
    "文档处理": {"bg": "#cddae3", "fg": "#3d627e"},
    "研究检索": {"bg": "#e6e0cd", "fg": "#736846"},
    "开发工具": {"bg": "#d7d0de", "fg": "#5b4b73"},
}
DEFAULT_COLOR = {"bg": "#dcdcdc", "fg": "#555555"}

# 精选(START HERE):优先有 demo 的,再补这些旗舰
FEATURED_HINT = [
    "k12-lesson-planning",
    "comment-on-docx",
    "frontend-slides",
    "algorithmic-art",
]

MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


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
    """返回 {skill_id: {group, 类型, 通过验证, 一句话, 引用_text, 引用_url, 效果}}"""
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
            "group": group,
            "type": rec.get("类型", "") or "收集",
            "verified": bool(rec.get("通过验证", "").strip()),
            "tagline": rec.get("一句话", "").strip(),
            "ref_text": ref_t,
            "ref_url": ref_u,
            "demo": demo,
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


def main() -> int:
    readme = parse_readme(os.path.join(LIB, "README.md"))
    skills = []
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
        skills.append({
            "id": sid,
            "name": fm.get("name", sid),
            "category": cat,
            "color": PALETTE.get(cat, DEFAULT_COLOR),
            "tagline": tagline,
            "description": fm.get("description", ""),
            "type": r.get("type", "收集"),
            "verified": r.get("verified", False),
            "group": r.get("group", ""),
            "refText": r.get("ref_text", ""),
            "refUrl": r.get("ref_url", ""),
            "demo": demo,
            "hasDemo": bool(demo),
        })

    # 编号 + 精选
    order = {s["id"]: i for i, s in enumerate(skills)}
    featured = [s["id"] for s in skills if s["hasDemo"]]
    for fid in FEATURED_HINT:
        if fid in order and fid not in featured:
            featured.append(fid)
    featured = featured[:4]
    for i, s in enumerate(skills, 1):
        s["num"] = f"{i:02d}"
        s["featured"] = s["id"] in featured

    cats: dict[str, int] = {}
    for s in skills:
        cats[s["category"]] = cats.get(s["category"], 0) + 1
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "count": len(skills),
        "repo": "https://github.com/Chloris-Blaxk/inno-agent-hub",
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "skills": skills,
    }

    os.makedirs(DOCS, exist_ok=True)
    # demo 素材拷进 docs/,否则 Pages 只服务 docs/ 会 404
    copied = 0
    for s in skills:
        if not s["demo"]:
            continue
        src = os.path.join(LIB, s["demo"])
        dst = os.path.join(DOCS, s["demo"])
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        else:
            print(f"   ⚠️ demo 源缺失,已忽略: {s['id']} -> {s['demo']}")
            s["demo"], s["hasDemo"] = "", False

    with open(os.path.join(DOCS, "skills.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not os.path.isfile(TEMPLATE):
        print(f"❌ 缺少模板 {TEMPLATE}", file=sys.stderr)
        return 1
    html = open(TEMPLATE, encoding="utf-8").read()
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ {len(skills)} 个 skill -> docs/skills.json + docs/index.html (demo 素材 {copied} 个已拷入 docs/)")
    print(f"   分类: " + " · ".join(f"{c['name']}({c['count']})" for c in data["categories"]))
    print(f"   有 demo: {sum(1 for s in skills if s['hasDemo'])} | 已验证: {sum(1 for s in skills if s['verified'])}")
    miss = [s["id"] for s in skills if not s["refUrl"] and s["type"] == "收集"]
    if miss:
        print(f"   ⚠️ 收集类但缺引用: {', '.join(miss)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
