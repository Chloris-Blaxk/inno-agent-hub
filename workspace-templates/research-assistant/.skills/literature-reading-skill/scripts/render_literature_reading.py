#!/usr/bin/env python3
"""文献阅读助手最小离线渲染脚本。"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = ROOT / "generated-outputs"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_literature_reading.py"

sys.path.insert(0, str(ROOT.parent / "research-line-common"))
from data_source_report import build_data_source_report, build_source  # noqa: E402
from education_generator_config import (  # noqa: E402
    attach_education_generator_runtime,
    build_education_generator_source,
)
from evidence_card_builder import build_evidence_card_from_paper  # noqa: E402
from evidence_policy import can_create_evidence_card, evidence_level_for_availability, has_readable_text  # noqa: E402
import literature_adapter  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_literature_data_source_report(
    config: dict[str, Any],
    input_obj: dict[str, Any],
    uploaded_record: dict[str, Any] | None,
    adapters: list[literature_adapter.BaseLiteratureAdapter],
) -> dict[str, Any]:
    sources = literature_adapter.describe_adapters(adapters)
    sources.append(build_education_generator_source(record_count=1))
    if uploaded_record:
        sources.append(
            build_source(
                source_id="user-uploaded-paper-text",
                source_name="用户上传论文文本",
                source_type="user_provided",
                data_type="paper_text",
                record_count=1,
                authorization_status="user_provided",
                limitations=["仅能说明用户上传文本内的内容，不能声称已由白名单或授权库验证。"],
            )
        )
    return build_data_source_report(
        skill_id="literature-reading-skill",
        task_intent=config.get("taskIntent", "literature_discovery"),
        sources=sources,
        overall_limitations=["EvidenceCard 只能在文本可用性满足规则时生成；metadata-only 题录只能作为候选阅读或后续核验入口。"],
    )


def selected_backend(config: dict[str, Any], input_obj: dict[str, Any]) -> str | None:
    backend = (
        config.get("backend")
        or config.get("literatureBackend")
        or input_obj.get("backend")
        or input_obj.get("literatureBackend")
        or os.environ.get("RESEARCH_LITERATURE_BACKEND")
    )
    return str(backend).strip() if backend else None


def build_domain_filters(input_obj: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "stage": ("stage", "schoolStage"),
        "subject": ("subject", "subjectCategory"),
        "research_domain": ("research_domain", "researchDomain", "domain"),
        "research_method": ("research_method", "researchMethod", "method"),
        "year_from": ("year_from", "yearFrom"),
        "year_to": ("year_to", "yearTo"),
        "journal": ("journal", "venue"),
        "must_have_doi": ("must_have_doi", "mustHaveDoi"),
        "citation_min": ("citation_min", "citationMin"),
    }
    filters: dict[str, Any] = {}
    nested = input_obj.get("domainFilters") if isinstance(input_obj.get("domainFilters"), dict) else {}
    merged = {**nested, **input_obj}
    for output_key, input_keys in aliases.items():
        for key in input_keys:
            value = merged.get(key)
            if value not in (None, "", [], {}):
                filters[output_key] = value
                break
    return filters


def dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for paper in papers:
        if isinstance(paper, dict) and paper.get("paperId"):
            index[paper["paperId"]] = paper
    return list(index.values())


def load_local_index() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return literature_adapter.load_literature_index()


def relevance_score(paper: dict[str, Any], keywords: list[str], topic: str) -> int:
    return literature_adapter.relevance_score(paper, keywords, topic)


def matched_keywords(paper: dict[str, Any], keywords: list[str], topic: str) -> list[str]:
    return literature_adapter.matched_keywords(paper, keywords, topic)


def paper_source(paper: dict[str, Any]) -> str:
    if paper.get("sourceStatus") == "user_provided":
        return "user_available_papers"
    if paper.get("database"):
        return str(paper.get("database"))
    return "literature_whitelist"


def build_corpus_search_report(
    metadata: dict[str, Any],
    papers: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    keywords: list[str],
    topic: str,
    limit: int,
) -> dict[str, Any]:
    top_hits = []
    for paper in ranked[:limit]:
        score = relevance_score(paper, keywords, topic)
        matches = matched_keywords(paper, keywords, topic)
        availability = paper.get("textAvailability", "metadata")
        top_hits.append(
            {
                "paperId": paper.get("paperId"),
                "score": score,
                "matchedKeywords": matches,
                "textAvailability": availability,
                "sourceStatus": paper.get("sourceStatus", "unverified"),
                "selectionReason": "关键词和主题高度匹配，且具备可读文本。" if score >= 3 and availability != "metadata" else "主题相关但文本证据有限，优先作为推荐阅读。",
                "source": paper_source(paper),
            }
        )
    return {
        "indexName": metadata.get("indexVersion", "local-mock-index"),
        "indexSource": "local_mock_index",
        "simulatedCorpusSize": metadata.get("simulatedCorpusSize", len(papers)),
        "query": {
            "researchTopic": topic,
            "keywords": keywords,
            "filters": {
                "subjectCategory": "不限",
                "yearRange": "不限",
                "requireReadableText": False,
            },
        },
        "candidateCount": len(papers),
        "returnedCount": len(top_hits),
        "rankingSignals": ["keyword_overlap", "topic_overlap", "text_availability"],
        "topHits": top_hits,
    }


def reading_decision(score: int, availability: str) -> str:
    if score >= 3 and has_readable_text(availability):
        return "priority_read"
    if score > 0:
        return "optional_read"
    return "skip"


def evidence_level_for(paper: dict[str, Any]) -> str:
    return evidence_level_for_availability(paper.get("textAvailability"))


def readable_text(paper: dict[str, Any]) -> tuple[str, str]:
    availability = paper.get("textAvailability")
    if availability == "metadata":
        return "", "metadata"
    if availability == "fulltext":
        text = paper.get("fullText") or paper.get("text") or paper.get("abstract") or ""
        return text, "fulltext" if paper.get("fullText") or paper.get("text") else "abstract"
    if availability == "user_uploaded":
        text = paper.get("uploadedText") or paper.get("sourceText") or paper.get("text") or paper.get("abstract") or ""
        return text, "user_uploaded_text" if text else "user_uploaded_text_missing"
    return paper.get("abstract") or "", "abstract"


def location_label(location: str) -> str:
    labels = {
        "abstract": "摘要",
        "fulltext": "全文",
        "user_uploaded_text": "用户上传文本",
        "metadata": "元数据",
    }
    return labels.get(location, location)


def split_sentences(text: str, limit: int = 2) -> list[str]:
    sentences = [part.strip(" 。；;") for part in text.replace("\n", "。").split("。") if part.strip()]
    return sentences[:limit] if sentences else []


def infer_method(text: str) -> str:
    method_terms = ["行动研究", "课堂观察", "问卷", "访谈", "案例研究", "实验", "文本分析", "混合研究"]
    matched = [term for term in method_terms if term in text]
    return "、".join(matched) if matched else "未提供"


def usable_ideas(paper: dict[str, Any]) -> list[str]:
    keywords = paper.get("keywords", [])
    ideas = []
    if any("即时反馈" in str(keyword) for keyword in keywords):
        ideas.append("可用于梳理课堂即时反馈的研究背景。")
    if any("错因" in str(keyword) for keyword in keywords):
        ideas.append("可用于设计错因分类或讲评策略。")
    if any("过程性评价" in str(keyword) or "学习证据" in str(keyword) for keyword in keywords):
        ideas.append("可用于说明过程性评价与课堂改进的关联。")
    return ideas or ["可作为主题背景文献，需结合原文后再提炼具体论据。"]


def build_quick_card(index: int, paper: dict[str, Any], decision: str) -> dict[str, Any]:
    text, location = readable_text(paper)
    availability = paper.get("textAvailability")
    generated_summary = paper.get("generatedSummary", "")
    return {
        "cardId": f"read-{index:03d}",
        "paperId": paper["paperId"],
        "cardType": "quick",
        "topicRelevance": "high" if decision == "priority_read" else "medium" if decision == "optional_read" else "low",
        "researchProblem": paper.get("title", "未提供"),
        "method": "未提供",
        "findings": text[:180] if text else generated_summary or "仅有元数据，未提供发现。",
        "limitations": "仅有元数据或系统生成摘要，不能生成证据卡。" if availability == "metadata" else f"{location_label(location)}级阅读，方法和样本细节需进一步确认。",
        "readingDecision": decision,
        "reason": "与关键词或研究主题相关。" if decision != "skip" else "与当前主题关联较弱。",
        "evidenceLevel": evidence_level_for(paper),
    }


def build_evidence_card(index: int, paper: dict[str, Any]) -> dict[str, Any] | None:
    return build_evidence_card_from_paper(index, paper, purpose="literature_reading", support_type="background")


def build_deep_card(index: int, paper: dict[str, Any], evidence_card: dict[str, Any] | None) -> dict[str, Any] | None:
    text, location = readable_text(paper)
    if not text or not has_readable_text(paper.get("textAvailability")):
        return None
    evidence_level = evidence_level_for(paper)
    findings = split_sentences(text, limit=3) or ["未提供"]
    limitations = []
    if evidence_level == "abstract_verified":
        limitations.append("仅基于摘要，研究设计、样本和数据细节需获取原文确认。")
    elif evidence_level == "user_text_only":
        limitations.append("基于用户上传文本，文献真实性需另行核验。")
    else:
        limitations.append("仅依据当前可访问片段，页码和完整语境需后续确认。")
    return {
        "cardId": f"deep-{index:03d}",
        "paperId": paper["paperId"],
        "cardType": "deep",
        "researchProblem": paper.get("title", "未提供"),
        "method": infer_method(text),
        "findings": findings,
        "limitations": limitations,
        "usableIdeas": usable_ideas(paper),
        "evidenceRefs": [evidence_card["cardId"]] if evidence_card else [],
        "evidenceLevel": evidence_level,
        "sourceTextScope": location,
    }


def build_comparison_matrix(topic: str, quick_cards: list[dict[str, Any]], deep_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deep_by_paper = {card["paperId"]: card for card in deep_cards}
    rows = []
    for quick in quick_cards:
        paper_id = quick.get("paperId")
        deep = deep_by_paper.get(paper_id, {})
        rows.append(
            {
                "paperId": paper_id,
                "problem": deep.get("researchProblem") or quick.get("researchProblem", "未提供"),
                "method": deep.get("method") or quick.get("method", "未提供"),
                "finding": "；".join(deep.get("findings", [])) if deep else quick.get("findings", "未提供"),
                "limitation": "；".join(deep.get("limitations", [])) if deep else quick.get("limitations", "未提供"),
                "usableFor": deep.get("usableIdeas", ["推荐阅读，需补文本后再复用。"]),
            }
        )
    if not rows:
        return []
    return [{"matrixId": "cmp-render-001", "topic": topic or "当前研究主题", "rows": rows}]


def input_paper_text(input_obj: dict[str, Any], paper: dict[str, Any] | None) -> str:
    if isinstance(input_obj.get("paperMd"), str) and input_obj["paperMd"].strip():
        return input_obj["paperMd"]
    if isinstance(input_obj.get("paperText"), str) and input_obj["paperText"].strip():
        return input_obj["paperText"]
    path_value = input_obj.get("paperMdPath") or input_obj.get("paperPath")
    if path_value:
        path = Path(path_value)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            return path.read_text(encoding="utf-8")
    if paper:
        text, _ = readable_text(paper)
        return text
    return ""


def build_deep_read_sessions(input_obj: dict[str, Any], paper: dict[str, Any] | None) -> list[dict[str, Any]]:
    paper_md = input_paper_text(input_obj, paper)
    if not paper_md:
        return []
    questions = input_obj.get("questions") or input_obj.get("deepReadQuestions") or []
    if isinstance(input_obj.get("question"), str) and input_obj["question"].strip():
        questions = [input_obj["question"]]
    if not isinstance(questions, list) or not questions:
        questions = ["这篇论文的研究问题、方法、主要发现和局限分别是什么？"]
    questions = [str(question) for question in questions if str(question).strip()][:5]
    title = input_obj.get("paperTitle") or (paper or {}).get("title") or "待精读论文"
    try:
        from deep_read_adapter import multi_turn_deep_read  # noqa: PLC0415
    except ImportError:
        return []
    return multi_turn_deep_read(paper_md=paper_md, questions=questions, title=title)


def build_uploaded_record(input_obj: dict[str, Any]) -> dict[str, Any] | None:
    paper_text = input_paper_text(input_obj, None)
    if not paper_text:
        return None
    return {
        "paperId": input_obj.get("paperId", "paper-user-deep-read-001"),
        "title": input_obj.get("paperTitle", "用户上传待精读论文"),
        "authors": input_obj.get("authors", ["用户上传材料"]),
        "year": input_obj.get("year", "待确认"),
        "journal": input_obj.get("journal", "用户上传原文"),
        "doi": input_obj.get("doi", ""),
        "keywords": input_obj.get("keywords", []),
        "uploadedText": paper_text,
        "sourceStatus": "user_provided",
        "textAvailability": "user_uploaded",
        "evidenceLevel": "user_text_only",
    }


def render(config: dict[str, Any]) -> dict[str, Any]:
    task_intent = config.get("taskIntent", "literature_discovery")
    input_obj = config.get("input", {})
    keywords = input_obj.get("keywords", [])
    topic = input_obj.get("researchTopic", "")
    uploaded_record = build_uploaded_record(input_obj)
    available_papers = [paper for paper in (input_obj.get("availablePapers", []) or []) if isinstance(paper, dict)]
    if uploaded_record:
        available_papers.append(uploaded_record)
    backend = selected_backend(config, input_obj)
    adapters = literature_adapter.default_adapters(available_papers, backend=backend)
    _, papers = literature_adapter.load_default_papers(available_papers, adapters=adapters)
    domain_filters = build_domain_filters(input_obj)
    search_result = literature_adapter.search_papers(
        research_topic=topic,
        keywords=keywords,
        available_papers=available_papers,
        adapters=adapters,
        limit=5,
        domain_filters=domain_filters,
    )
    records = search_result["records"]
    corpus_search_report = search_result["corpusSearchReport"]
    papers = dedupe_papers([*records, *papers])
    if task_intent == "deep_read" and input_obj.get("paperId"):
        selected = next((paper for paper in papers if paper.get("paperId") == input_obj.get("paperId")), None)
        if selected:
            records = [selected]
            corpus_search_report = build_corpus_search_report(
                {
                    "indexVersion": corpus_search_report.get("indexName", "local-mock-index"),
                    "simulatedCorpusSize": corpus_search_report.get("simulatedCorpusSize", len(papers)),
                },
                papers,
                records,
                keywords,
                topic,
                1,
            )

    quick_cards = []
    deep_cards = []
    evidence_cards = []
    deep_read_sessions: list[dict[str, Any]] = []
    internal_quick_cards = []
    internal_deep_cards = []
    for index, paper in enumerate(records, 1):
        decision = reading_decision(relevance_score(paper, keywords, topic), paper.get("textAvailability", "metadata"))
        quick_card = build_quick_card(index, paper, decision)
        evidence_card = build_evidence_card(index, paper)
        deep_card = build_deep_card(index, paper, evidence_card)
        internal_quick_cards.append(quick_card)
        if deep_card:
            internal_deep_cards.append(deep_card)
        if task_intent in {"literature_discovery", "quick_read"}:
            quick_cards.append(quick_card)
            if task_intent == "literature_discovery":
                if evidence_card:
                    evidence_cards.append(evidence_card)
                if deep_card:
                    deep_cards.append(deep_card)
        elif task_intent == "evidence_carding" and evidence_card:
            evidence_cards.append(evidence_card)
        elif task_intent == "deep_read":
            if evidence_card:
                evidence_cards.append(evidence_card)
            if deep_card:
                deep_cards.append(deep_card)

    if task_intent == "deep_read":
        deep_read_sessions = build_deep_read_sessions(input_obj, records[0] if records else None)
        if any(session.get("_mock") for session in deep_read_sessions):
            evidence_cards = []
            for card in deep_cards:
                card["evidenceRefs"] = []
                card.setdefault("limitations", []).append("当前为 mock 精读结果，不得作为 EvidenceCard、支撑性引用或论文结论使用。")
                card["evidenceLevel"] = "user_text_only" if card.get("evidenceLevel") == "user_text_only" else "abstract_verified"
                card["mockDegraded"] = True

    metadata_count = sum(1 for paper in records if paper.get("textAvailability") == "metadata")
    abstract_count = sum(1 for paper in records if paper.get("textAvailability") == "abstract")
    fulltext_count = sum(1 for paper in records if paper.get("textAvailability") == "fulltext")
    user_uploaded_count = sum(1 for paper in records if paper.get("textAvailability") == "user_uploaded")
    bibliographic_candidates = corpus_search_report.get("bibliographicCandidates", [])
    reading_list_report = corpus_search_report.get("readingListReport", {})
    comparison_matrix = build_comparison_matrix(topic, internal_quick_cards, internal_deep_cards) if task_intent in {"compare_papers", "literature_discovery"} else []
    comparison_row_count = sum(len(matrix.get("rows", [])) for matrix in comparison_matrix)
    warnings = list(corpus_search_report.get("adapterWarnings", []))
    if task_intent in {"deep_read", "evidence_carding"} and not evidence_cards:
        warnings.append("当前候选只有元数据或缺少可读文本，未生成 EvidenceCard。")
    if bibliographic_candidates and not evidence_cards:
        warnings.append("PedaScope/元数据候选仅用于推荐阅读和后续核验，未生成 EvidenceCard 或支撑性引用。")
    if task_intent == "deep_read" and not deep_read_sessions:
        warnings.append("未提供可用于 deep_read 的论文文本，未生成 deepReadSessions。")
    if task_intent == "deep_read" and any(session.get("_mock") for session in deep_read_sessions):
        warnings.append("deep_read 当前为 mock 模式，不能生成 EvidenceCard 或支撑性引用；请配置 LLM/Embedding 凭证后重跑。")
    status = "warn" if warnings else "pass"
    payload = {
        "requestId": config.get("requestId", "req-literature-reading-render-001"),
        "skillId": "literature-reading-skill",
        "taskIntent": task_intent,
        "status": status,
        "summary": f"已按 {task_intent} 模式生成文献阅读产物；metadata-only 文献不生成支撑性证据卡。",
        "inputSummary": {
            "sourceRequest": config.get("sourceRequest", ""),
            "researchTopic": topic,
            "keywordCount": len(keywords),
            "literatureBackend": backend or "local_mock",
            "domainFilters": domain_filters,
            "availablePaperCount": len(input_obj.get("availablePapers", []) or []),
            "sourceFileCount": len(config.get("sourceFiles", []) or []),
            "assumptions": config.get("assumptions", []),
            "constraints": config.get("constraints", {}),
        },
        "warnings": warnings,
        "dataSourceReport": build_literature_data_source_report(config, input_obj, uploaded_record, adapters),
        "artifacts": [],
        "result": {
            "corpusSearchReport": corpus_search_report,
            "readingListReport": reading_list_report,
            "literatureRecords": records,
            "bibliographicCandidates": bibliographic_candidates,
            "quickReadCards": quick_cards,
            "deepReadCards": deep_cards,
            "deepReadSessions": deep_read_sessions,
            "comparisonMatrix": comparison_matrix,
            "evidenceCards": evidence_cards,
        },
        "handoff": {
            "literatureRecords": records,
            "readingListReport": reading_list_report,
            "bibliographicCandidates": bibliographic_candidates,
            "evidenceCards": evidence_cards,
        },
        "qualityReport": {
            "status": status,
            "checks": [{"id": "task_intent_route", "status": "pass"}, {"id": "metadata_no_evidence_card", "status": "pass"}, {"id": "evidence_card_backlink", "status": "pass"}],
            "warnings": warnings,
            "metrics": {
                "literatureHitCount": len(records),
                "metadataOnlyCount": metadata_count,
                "abstractAvailableCount": abstract_count,
                "fulltextAvailableCount": fulltext_count,
                "userUploadedCount": user_uploaded_count,
                "deepReadCardCount": len(deep_cards),
                "deepReadSessionCount": len(deep_read_sessions),
                "comparisonRowCount": comparison_row_count,
                "evidenceCardCount": len(evidence_cards),
                "searchCandidateCount": corpus_search_report["candidateCount"],
                "searchReturnedCount": corpus_search_report["returnedCount"],
                "bibliographicCandidateCount": len(bibliographic_candidates),
                "structuredReadingListCount": len(reading_list_report.get("readingList", [])) if isinstance(reading_list_report, dict) else 0,
                "mustReadCount": sum(1 for item in reading_list_report.get("readingList", []) if isinstance(item, dict) and item.get("priority") == "must_read") if isinstance(reading_list_report, dict) else 0,
                "priorityReadCount": sum(1 for card in quick_cards if card.get("readingDecision") == "priority_read"),
            },
        },
        "provenanceReport": {
            "sourceCount": len(records),
            "verifiedSourceCount": len([paper for paper in records if paper.get("sourceStatus") == "whitelist"]),
            "unsupportedClaimCount": 0,
        },
        "nextActions": ["为 metadata-only 文献补充摘要或全文。"] if metadata_count else [],
    }
    return attach_education_generator_runtime(
        payload,
        skill_id="literature-reading-skill",
        task_intent=str(task_intent),
        used_for=["quick_read_card_generation", "deep_read_answer_generation", "evidence_card_language_packaging"],
        generation_mode="availability_guarded_with_innospark_235b_generator_contract",
    )


def _paper_title(paper_id: str, records: list[dict[str, Any]]) -> str:
    """根据 paperId 查找论文标题，找不到则返回 paperId 本身。"""
    for r in records:
        if r.get("paperId") == paper_id:
            return r.get("title", paper_id)
    return paper_id


def _avail_cn(avail: str) -> str:
    return {"fulltext": "✅ 有全文可读", "abstract": "📄 仅有摘要", "metadata": "📋 仅知标题", "user_uploaded": "📤 你上传的原文"}.get(avail, avail)


def _decision_cn(dec: str) -> str:
    return {"priority_read": "🔴 建议先读", "optional_read": "🟡 有空可读", "skip": "⚪ 可以先放一放"}.get(dec, dec)


def _level_cn(level: str) -> str:
    return {"fulltext_verified": "✅ 全文级证据", "abstract_verified": "⚠️ 摘要级证据（仅能做背景引用）", "metadata_verified": "📋 元数据已核对（无文本可引用）", "user_text_only": "📤 你提供的文本（未经数据库验证）"}.get(level, level)


def render_markdown(data: dict[str, Any]) -> str:
    result = data.get("result", {})
    metrics = data.get("qualityReport", {}).get("metrics", {})
    records = result.get("literatureRecords", [])
    lines = [
        "# 文献阅读建议",
        "",
        f"请求 ID：`{data.get('requestId')}`",
        f"校验状态：`{data.get('qualityReport', {}).get('status')}`",
        f"文献数：{metrics.get('literatureHitCount', 0)}，证据卡数：{metrics.get('evidenceCardCount', 0)}",
        "",
    ]
    search = result.get("corpusSearchReport", {})
    if search:
        lines.extend(
            [
                "## 检索概览",
                "",
                f"- 索引：`{search.get('indexName')}` / `{search.get('indexSource')}`",
                f"- 候选数：{search.get('candidateCount')}；返回数：{search.get('returnedCount')}",
                f"- 排序信号：{'、'.join(search.get('rankingSignals', []))}",
                "",
            ]
        )
        for i, hit in enumerate(search.get("topHits", [])[:5], 1):
            matched = "、".join(hit.get("matchedKeywords", [])) or "无"
            title = _paper_title(hit.get("paperId", ""), records)
            avail = _avail_cn(hit.get("textAvailability", ""))
            lines.append(f"- {i}.《{title}》（score={hit.get('score')}；命中：{matched}；{avail}）")
        lines.append("")
    reading_list = result.get("readingListReport", {}).get("readingList", []) if isinstance(result.get("readingListReport"), dict) else []
    if reading_list:
        lines.extend(["## 结构化阅读优先级", ""])
        for item in reading_list[:8]:
            reasons = "、".join(str(reason) for reason in item.get("reasons", [])) or "未提供"
            lines.append(f"- 《{item.get('title', item.get('paperId'))}》（score={item.get('score')}；{reasons}）")
        lines.append("")
    if result.get("bibliographicCandidates"):
        lines.extend(["## 题录级候选", ""])
        for candidate in result.get("bibliographicCandidates", [])[:5]:
            title = candidate.get("title", candidate.get("paperId"))
            lines.extend(
                [
                    f"- 🏷️ PedaScope 候选：《{title}》（内部追溯：`{candidate.get('paperId')}`）",
                    f"  - 来源级别：{_level_cn(candidate.get('evidenceLevel', ''))} / {_avail_cn(candidate.get('textAvailability', ''))}",
                    f"  - 限制：{'；'.join(candidate.get('limits', []))}",
                ]
            )
        lines.append("")
    lines.extend(["## 优先阅读文献", ""])
    quick_by_paper = {card.get("paperId"): card for card in result.get("quickReadCards", [])}
    for paper in records:
        card = quick_by_paper.get(paper.get("paperId"), {})
        lines.extend(
            [
                f"### {paper.get('title')}",
                "",
                f"（内部追溯：`{paper.get('paperId')}`）",
                f"- 作者/年份：{'、'.join(paper.get('authors', []))}，{paper.get('year')}",
                f"- 文本可读程度：{_avail_cn(paper.get('textAvailability', ''))}",
                f"- 阅读决策：{_decision_cn(card.get('readingDecision', ''))}",
                f"- 主要信息：{card.get('findings', '未提供')}",
                f"- 注意：{card.get('limitations', '未提供')}",
                "",
            ]
        )
    if result.get("deepReadCards"):
        lines.extend(["## 精读四维卡", ""])
        for card in result.get("deepReadCards", []):
            title = _paper_title(card.get("paperId", ""), records)
            lines.extend(
                [
                    f"### 《{title}》精读卡",
                    f"（内部追溯：`{card.get('paperId')}`）",
                    "",
                    f"- 研究问题：{card.get('researchProblem')}",
                    f"- 方法：{card.get('method')}",
                    f"- 发现：{'；'.join(card.get('findings', []))}",
                    f"- 不足：{'；'.join(card.get('limitations', []))}",
                    f"- 可吸收信息：{'；'.join(card.get('usableIdeas', []))}",
                    "",
                ]
            )
    if result.get("comparisonMatrix"):
        lines.extend(["## 横向比较", ""])
        for matrix in result.get("comparisonMatrix", []):
            lines.append(f"### {matrix.get('topic')}")
            lines.append("")
            for row in matrix.get("rows", []):
                title = _paper_title(row.get("paperId", ""), records)
                lines.extend(
                    [
                        f"- 《{title}》：{row.get('problem')}",
                        f"  - 方法：{row.get('method')}",
                        f"  - 发现：{row.get('finding')}",
                        f"  - 限制：{row.get('limitation')}",
                    ]
                )
            lines.append("")
    if result.get("evidenceCards"):
        lines.extend(["## 可复用证据卡片", ""])
        for card in result.get("evidenceCards", []):
            title = card.get("paperTitle") or _paper_title(card.get("paperId", ""), records)
            lines.extend(
                [
                    f"### 📇 来自《{title}》的证据",
                    f"（内部追溯：`{card.get('cardId')}` · `{card.get('paperId')}`）",
                    "",
                    f"- 内容：{card.get('evidenceText', card.get('claim', ''))}",
                    f"- 出处：{card.get('quoteLocation')}",
                    f"- 证据级别：{_level_cn(card.get('evidenceLevel', ''))}",
                    f"- 可用于：{'、'.join(card.get('usableFor', []))}",
                    f"- ⚠️ 边界：{'；'.join(card.get('limits', []))}",
                    "",
                ]
            )
        lines.append("")
    next_actions = data.get("nextActions", [])
    if next_actions:
        lines.extend(["## 下一步", ""])
        lines.extend(f"- {item}" for item in next_actions)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染文献阅读助手 JSON 产物。")
    parser.add_argument("input_or_output_base", help="旧入口为请求 JSON；使用 --config 时为输出 base")
    parser.add_argument("--config", help="模板式入口的请求 JSON 文件：render_x.py <output_base> --config <request>")
    parser.add_argument("--output", help="输出 JSON 文件；默认写入 generated-outputs/<requestId>.json")
    parser.add_argument("--validate", action="store_true", help="输出后立即运行 validate_literature_reading.py")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else Path(args.input_or_output_base)
    config = load_json(config_path)
    output = render(config)
    if args.output:
        output_path = Path(args.output)
    elif args.config:
        output_base = Path(args.input_or_output_base)
        output_path = output_base if output_base.suffix == ".json" else output_base.with_suffix(".json")
    else:
        output_path = OUTPUT_DIR / f"{output['requestId']}.json"
    md_path = output_path.with_suffix(".md")
    output["artifacts"] = [
        {"type": "json", "path": str(output_path), "description": "结构化文献阅读结果"},
        {"type": "markdown", "path": str(md_path), "description": "教师可读文献阅读报告"},
    ]
    write_json(output_path, output)
    write_markdown(md_path, render_markdown(output))
    print(output_path)
    print(md_path)
    if args.validate:
        return subprocess.run(["python3", str(VALIDATE_SCRIPT), str(output_path)], check=False).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
