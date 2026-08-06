"""Deterministic guardrails for the academic paper writing assistant.

Commands:
  audit       Check IMRaD sections, abstract elements, citations, and risky claims.
  claim       Match a claim against evidence cards and decide whether citation insertion is allowed.
  chapter-key Extract a stable chapter key from a chapter draft.
  refs        Render GB/T 7714 journal references from evidence records.
"""
import argparse
import json
import re
import sys
from pathlib import Path

COMMON_DIR = Path(__file__).resolve().parents[2] / "research-line-common"
sys.path.insert(0, str(COMMON_DIR))
from evidence_policy import canonicalize_evidence_card, normalize_evidence_level  # noqa: E402


SECTION_PATTERNS = {
    "引言": r"(?:^|\n)\s*(?:一、|1[\.、]?|第一章)?\s*引言|问题提出",
    "文献综述": r"(?:^|\n)\s*(?:二、|2[\.、]?|第二章)?\s*文献综述|已有研究",
    "研究方法": r"(?:^|\n)\s*(?:三、|3[\.、]?|第三章)?\s*研究方法|研究设计",
    "结果": r"(?:^|\n)\s*(?:四、|4[\.、]?|第四章)?\s*结果|研究结果",
    "讨论": r"(?:^|\n)\s*(?:五、|5[\.、]?|第五章)?\s*讨论",
    "结论": r"(?:^|\n)\s*(?:六、|6[\.、]?|第六章)?\s*结论|结论与建议",
}

ABSTRACT_CUES = {
    "研究问题/目的": ["目的", "旨在", "聚焦", "探讨", "研究"],
    "方法/数据": ["采用", "方法", "数据", "样本", "访谈", "问卷", "课堂观察"],
    "核心发现": ["发现", "结果", "显示", "表明"],
    "结论/意义": ["建议", "意义", "启示", "结论", "有助于"],
}

RISKY_FACT_CUES = ["显著", "证明", "提高", "降低", "影响", "预测", "相关", "差异", "p<", "β=", "R²"]


def load_text(path):
    return Path(path).read_text(encoding="utf-8")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_evidence(path):
    """加载证据文件，自动提取 evidenceCards 数组（兼容顶层 object 或纯数组）。"""
    data = load_json(path)
    if isinstance(data, dict) and "evidenceCards" in data:
        return data["evidenceCards"]
    if isinstance(data, list):
        return data
    raise ValueError(f"无法从 {path} 提取 evidenceCards 数组")


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _tokens(value):
    if isinstance(value, list):
        value = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        value = " ".join(str(v) for v in value.values())
    text = str(value or "").lower()
    toks = set(re.findall(r"[\w一-鿿]+", text))
    cjk = re.findall(r"[一-鿿]", text)
    toks.update("".join(cjk[i:i + 2]) for i in range(max(0, len(cjk) - 1)))
    return {t for t in toks if t}


def extract_abstract(article):
    m = re.search(r"(?:^|\n)\s*摘要[:：]?\s*(.+?)(?=\n\s*(?:关键词|一、|1[\.、]|引言|问题提出)|\Z)", article, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def check_structure(article):
    return {
        name: bool(re.search(pattern, article, re.I))
        for name, pattern in SECTION_PATTERNS.items()
    }


def check_abstract(article):
    abstract = extract_abstract(article)
    return {
        "present": bool(abstract),
        "length": len(abstract),
        "elements": {
            key: any(cue in abstract for cue in cues)
            for key, cues in ABSTRACT_CUES.items()
        },
        "text": abstract,
    }


def extract_paper_ids(article):
    return sorted(set(re.findall(r"\b[A-Z]{2,}[-A-Z0-9]*-\d{4}-\d{3}\b|\bEDU-[A-Z0-9-]+\b", article)))


def gbt7714(record):
    # 支持两种字段命名：paper-prefixed (证据卡新规范) 和 unprefixed (旧兼容)
    authors = record.get("paperAuthors") or record.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in re.split(r"[,，;；]", authors) if a.strip()]
    author_text = ",".join(authors[:3])
    if len(authors) > 3:
        author_text += ",等"
    fields_missing = []
    for plain_key, paper_key in [("title", "paperTitle"), ("journal", "paperJournal"), ("year", "paperYear")]:
        if not record.get(paper_key) and not record.get(plain_key):
            fields_missing.append(plain_key)
    title = record.get("paperTitle") or record.get("title") or "[题名缺失]"
    journal = record.get("paperJournal") or record.get("journal") or "[刊名缺失]"
    year = record.get("paperYear") or record.get("year") or "[年份缺失]"
    volume = record.get("volume")
    issue = record.get("issue")
    pages = record.get("pages")
    vol_issue = ""
    if volume and issue:
        vol_issue = f",{volume}({issue})"
    elif issue:
        vol_issue = f"({issue})"
    page_text = f":{pages}" if pages else ""
    ref = f"{author_text or '[作者缺失]'}.{title}[J].{journal},{year}{vol_issue}{page_text}."
    return {"reference": ref, "missing_fields": fields_missing}


def _evidence_text(card):
    return " ".join(str(v) for v in [
        card.get("title", ""),
        " ".join(card.get("keywords") or []),
        card.get("claim", ""),
        card.get("evidenceText", ""),
        card.get("evidence", ""),
        card.get("abstract", ""),
    ])


def match_claim(claim, evidence_cards, top_k=5):
    claim_tokens = _tokens(claim)
    rows = []
    for raw_card in evidence_cards:
        card = canonicalize_evidence_card(raw_card)
        text_tokens = _tokens(_evidence_text(card))
        overlap = len(claim_tokens & text_tokens) / len(claim_tokens) if claim_tokens else 0.0
        level = normalize_evidence_level(card.get("evidenceLevel"))
        if level == "metadata_verified":
            decision = "blocked_unsupported"
        elif overlap < 0.15:
            decision = "blocked_unsupported"
        elif level == "abstract_verified":
            decision = "need_more_evidence"
        else:
            decision = "suggest_insert"
        support_status = "supports" if decision == "suggest_insert" else "related_only" if decision == "need_more_evidence" else "not_support"
        snippet = card.get("evidenceText", "")
        ref_info = gbt7714(card)
        rows.append({
            "paperId": card.get("paperId"),
            "cardId": card.get("cardId"),
            "evidenceCardId": card.get("cardId"),
            "locator": card.get("quoteLocation"),
            "quoteLocation": card.get("quoteLocation"),
            "sourceLocator": card.get("sourceLocator", {"locationType": card.get("quoteLocation", "unknown"), "locator": card.get("quoteLocation", "unknown"), "confidence": "medium"}),
            "evidence_level": level,
            "evidenceLevel": level,
            "support_score": round(overlap, 4),
            "support_relation": "关键词/证据文本命中" if overlap >= 0.15 else "证据与论点弱相关",
            "matchType": "evidence_card",
            "matchSnippet": snippet,
            "supportStatus": support_status,
            "confidence": "high" if decision == "suggest_insert" else "medium" if decision == "need_more_evidence" else "low",
            "gbt7714": ref_info["reference"],
            "missing_reference_fields": ref_info["missing_fields"],
            "decision": decision,
        })
    rows.sort(key=lambda r: (r["decision"] != "suggest_insert", -r["support_score"]))
    top_rows = rows[:top_k]
    decision = "suggest_insert" if any(row["decision"] == "suggest_insert" for row in top_rows) else "need_more_evidence" if any(row["decision"] == "need_more_evidence" for row in top_rows) else "blocked_unsupported"
    return {"claim": claim, "decision": decision, "matches": top_rows}


def sentence_split(text):
    return [s.strip() for s in re.split(r"(?<=[。！？.!?])\s*", text) if s.strip()]


def unsupported_claims(article, evidence_cards):
    known_ids = {c.get("paperId") for c in evidence_cards}
    risky = []
    for sent in sentence_split(article):
        if not any(cue in sent for cue in RISKY_FACT_CUES):
            continue
        cited = set(extract_paper_ids(sent))
        if not cited:
            risky.append({"sentence": sent, "risk": "事实性/因果性表述缺少证据标注"})
        elif not cited <= known_ids:
            risky.append({"sentence": sent, "risk": "引用 paperId 不在证据白名单中", "unknown_ids": sorted(cited - known_ids)})
    return risky


def audit(article, evidence_cards):
    paper_ids = extract_paper_ids(article)
    evidence_ids = {c.get("paperId") for c in evidence_cards}
    structure = check_structure(article)
    abstract = check_abstract(article)
    return {
        "structure_check": {
            "sections": structure,
            "missing_sections": [k for k, ok in structure.items() if not ok],
        },
        "abstract_check": {
            **abstract,
            "missing_elements": [k for k, ok in abstract["elements"].items() if not ok],
        },
        "citation_check": {
            "paper_ids_in_article": paper_ids,
            "unknown_paper_ids": sorted(set(paper_ids) - evidence_ids),
            "known_paper_ids": sorted(set(paper_ids) & evidence_ids),
        },
        "unsupported_claims": unsupported_claims(article, evidence_cards),
    }


def chapter_key(chapter_text):
    first = next((line.strip() for line in chapter_text.splitlines() if line.strip()), "")
    patterns = [
        r"^(第[一二三四五六七八九十\d]+章)",
        r"^(\d+)\s*[\.、]\s*",
    ]
    for pattern in patterns:
        m = re.search(pattern, first)
        if m:
            return {"chapter_key": m.group(1) if "第" in m.group(1) else f"第{m.group(1)}章", "title_line": first}
    return {"chapter_key": "", "title_line": first, "warning": "未能从第一行抽取章序号"}


def _main():
    ap = argparse.ArgumentParser(description="写作助手结构、引用与章节守卫脚本")
    sub = ap.add_subparsers(dest="cmd", required=True)

    audit_cmd = sub.add_parser("audit", help="检查文章结构、摘要、引用和事实风险")
    audit_cmd.add_argument("--article", required=True)
    audit_cmd.add_argument("--evidence", required=True)
    audit_cmd.add_argument("--out", required=True)

    claim_cmd = sub.add_parser("claim", help="为单个论点匹配证据卡")
    claim_cmd.add_argument("--claim", required=True)
    claim_cmd.add_argument("--evidence", required=True)
    claim_cmd.add_argument("--out", required=True)

    key_cmd = sub.add_parser("chapter-key", help="从章节草稿第一行提取章节 key")
    key_cmd.add_argument("--chapter", required=True)
    key_cmd.add_argument("--out", required=True)

    refs_cmd = sub.add_parser("refs", help="输出 GB/T 7714 参考文献")
    refs_cmd.add_argument("--evidence", required=True)
    refs_cmd.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "audit":
        result = audit(load_text(args.article), load_evidence(args.evidence))
    elif args.cmd == "claim":
        result = match_claim(args.claim, load_evidence(args.evidence))
    elif args.cmd == "chapter-key":
        result = chapter_key(load_text(args.chapter))
    else:
        result = [gbt7714(card) for card in load_evidence(args.evidence)]
    save_json(result, args.out)
    print(f"[writing-guardrails] {args.cmd} -> {args.out}")


if __name__ == "__main__":
    _main()
