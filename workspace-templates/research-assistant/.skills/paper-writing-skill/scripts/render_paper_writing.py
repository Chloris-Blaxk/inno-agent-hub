#!/usr/bin/env python3
"""论文写作助手离线渲染脚本。

支持集成 writing_guardrails.py 做确定性审计和论据索引。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = ROOT / "generated-outputs"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_paper_writing.py"
GUARDRAILS_SCRIPT = ROOT / "scripts" / "writing_guardrails.py"

sys.path.insert(0, str(ROOT.parent / "research-line-common"))
from citation_verifier import verify_citations_batch  # noqa: E402
from data_source_report import build_data_source_report, build_source  # noqa: E402
from education_generator_config import (  # noqa: E402
    attach_education_generator_runtime,
    build_education_generator_source,
)
from evidence_policy import can_support_claim  # noqa: E402
import literature_adapter  # noqa: E402
from support_matcher import cards_supporting_claim as common_cards_supporting_claim  # noqa: E402
from support_matcher import check_claim_support  # noqa: E402


STOP_TERMS = {"这句", "这句话", "出自", "哪篇", "文章", "研究", "有助于", "能够", "可以"}
MAJOR_TERMS = ["即时反馈", "错因", "典型错因", "教学调整", "学习投入", "显著", "成绩", "讲评"]
SOURCE_TRACE_INTENTS = {"source_trace", "claim_support_check", "citation_format"}
OUTLINE_INTENTS = {"outline_generation"}
CHAPTER_DRAFT_INTENTS = {"chapter_drafting"}
LOCAL_REWRITE_INTENTS = {"local_rewrite"}
STRUCTURE_SECTIONS = [
    {
        "sectionId": "introduction",
        "label": "Introduction",
        "headingKeywords": ["引言", "研究背景"],
        "sectionKeywords": ["引言", "背景", "问题", "研究意义", "已有研究", "本文聚焦", "本研究"],
        "elements": {
            "研究背景": ["背景", "现状", "课堂中", "教学实践"],
            "问题提出": ["问题", "困境", "痛点", "不足"],
            "已有研究不足": ["已有研究", "相关研究", "研究不足", "缺口"],
            "本文研究问题": ["研究问题", "本文聚焦", "本研究", "旨在", "目的"],
        },
    },
    {
        "sectionId": "methods",
        "label": "Methods",
        "headingKeywords": ["方法", "研究方法", "研究对象", "数据来源", "研究设计"],
        "sectionKeywords": ["方法", "对象", "样本", "数据来源", "课堂观察", "访谈", "问卷", "分析方法"],
        "elements": {
            "对象/样本": ["对象", "样本", "学生", "班级", "教师", "参与者"],
            "数据来源": ["数据来源", "课堂观察", "访谈", "问卷", "作业", "测试"],
            "研究过程": ["过程", "流程", "干预", "实施", "步骤"],
            "分析方法": ["分析方法", "编码", "统计", "比较", "归纳"],
        },
    },
    {
        "sectionId": "results",
        "label": "Results",
        "headingKeywords": ["结果", "研究结果", "主要发现"],
        "sectionKeywords": ["结果", "发现", "数据显示", "课堂观察显示", "表明", "案例"],
        "elements": {
            "主要发现": ["发现", "结果", "表明", "显示", "观察到"],
            "证据/数据": ["数据", "案例", "记录", "表", "访谈", "作业"],
            "发现边界": ["范围", "边界", "仅", "主要", "可能"],
        },
    },
    {
        "sectionId": "discussion",
        "label": "Discussion",
        "headingKeywords": ["讨论", "研究启示", "局限", "反思", "建议"],
        "sectionKeywords": ["讨论", "启示", "局限", "反思", "建议", "后续研究"],
        "elements": {
            "解释发现": ["说明", "可能由于", "原因", "解释"],
            "实践意义": ["启示", "意义", "建议", "应用"],
            "局限和后续研究": ["局限", "不足", "后续", "进一步"],
        },
    },
]
ABSTRACT_ELEMENTS = [
    ("purpose", "目的", ["目的", "旨在", "聚焦", "解决", "探讨"]),
    ("methods", "方法", ["方法", "采用", "通过", "对象", "样本", "课堂观察", "访谈", "问卷"]),
    ("results", "结果", ["结果", "发现", "显示", "表明", "观察到"]),
    ("conclusion", "结论", ["结论", "启示", "建议", "意义"]),
]
STRONG_REPLACEMENTS = [
    ("能够显著提升", "可能有助于改善"),
    ("能显著提升", "可能有助于改善"),
    ("显著提升", "可能改善"),
    ("显著提高", "可能改善"),
    ("大幅提升", "有助于改善"),
    ("有效提升", "有助于改善"),
    ("明显提升", "可能改善"),
    ("完全解决", "有助于缓解"),
    ("必然导致", "可能影响"),
    ("必然", "可能"),
    ("证明", "提示"),
    ("提高成绩", "改善学习表现"),
]
STRONG_TERMS = ["显著", "证明", "大幅", "必然", "有效提升", "提高成绩", "完全解决"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def selected_backend(config: dict[str, Any], input_obj: dict[str, Any]) -> str | None:
    backend = (
        config.get("backend")
        or config.get("literatureBackend")
        or input_obj.get("backend")
        or input_obj.get("literatureBackend")
        or os.environ.get("RESEARCH_LITERATURE_BACKEND")
    )
    return str(backend).strip() if backend else None


def build_paper_writing_data_source_report(config: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    sources = [source for source in trace.get("dataSources", []) if isinstance(source, dict)]
    if not sources:
        cards = literature_adapter.load_evidence_cards(input_obj.get("availableEvidenceCards", []))
        sources = [
            build_source(
                source_id="shared-literature-pool",
                source_name="科研线共享本地文献池",
                source_type="local_mock",
                data_type="literature_record",
                record_count=len(trace.get("papers", [])),
                authorization_status="mock_sample",
                version=literature_adapter.ADAPTER_VERSION,
                limitations=["由本地 mock 文献索引和样例白名单合并而来，不能替代真实授权检索。"],
            ),
            build_source(
                source_id="paper-writing-evidence-card-index",
                source_name="论文写作证据卡样例库",
                source_type="local_sample",
                data_type="evidence_card",
                record_count=len(cards),
                authorization_status="sample_only",
                limitations=["证据卡为样例数据；进入引用建议前仍需支撑性、定位和教师确认校验。"],
            ),
        ]
    if not any(source.get("sourceId") == "innospark-235b-education-generator" for source in sources):
        sources.append(build_education_generator_source(record_count=1))
    return build_data_source_report(
        skill_id="paper-writing-skill",
        task_intent=config.get("taskIntent", "source_trace"),
        sources=sources,
        overall_limitations=["未验证支撑性的候选不得进入引用或正文事实；PedaScope 题录候选不能直接生成 EvidenceCard 或插入建议。"],
    )


def tokenize(text: str) -> set[str]:
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text)
    terms: set[str] = set()
    for chunk in chunks:
        if len(chunk) <= 1:
            continue
        for size in (4, 3, 2):
            for index in range(0, max(len(chunk) - size + 1, 0)):
                term = chunk[index : index + size]
                if term not in STOP_TERMS:
                    terms.add(term)
    return terms


def citation_for(paper: dict[str, Any]) -> str:
    authors = "，".join(paper.get("authors", [])) or "作者待确认"
    base = f"{authors}. {paper.get('title', '题名待确认')}[J]. {paper.get('journal', '期刊待确认')}, {paper.get('year', '年份待确认')}"
    volume = paper.get("volume")
    issue = paper.get("issue")
    pages = paper.get("pages")
    if volume and issue and pages:
        return f"{base}, {volume}({issue}): {pages}."
    if pages:
        return f"{base}: {pages}."
    return f"{base}."


def source_locator_for(card: dict[str, Any] | None, paper: dict[str, Any] | None = None) -> dict[str, Any]:
    if card and isinstance(card.get("sourceLocator"), dict):
        locator = dict(card["sourceLocator"])
    else:
        quote_location = card.get("quoteLocation") if card else "abstract"
        locator = {
            "locationType": quote_location or "abstract",
            "locator": quote_location or "abstract",
            "page": card.get("page", "") if card else "",
            "paragraph": card.get("paragraph", quote_location or "") if card else "",
        }
    if paper and locator.get("locationType") == "metadata":
        locator["confidence"] = "low"
    else:
        locator["confidence"] = "medium" if locator.get("locationType") == "abstract" else "high"
    return locator


def citation_check_for(index: int, paper: dict[str, Any], card: dict[str, Any] | None, style: str) -> dict[str, Any]:
    required_fields = ["authors", "title", "journal", "year"]
    missing_required = [field for field in required_fields if not paper.get(field)]
    missing_optional = [field for field in ["volume", "issue", "pages"] if not paper.get(field)]
    warnings = []
    if missing_required:
        warnings.append(f"缺少 GB/T 7714 必填字段：{', '.join(missing_required)}。")
    if missing_optional:
        warnings.append(f"缺少卷期页码字段：{', '.join(missing_optional)}；引用可作为基础格式草案，但定稿前需补齐。")
    if card and card.get("evidenceLevel") == "abstract_verified":
        warnings.append("当前证据位置为摘要级，不能支撑页码级直接引文。")
    status = "fail" if missing_required else "warn" if warnings else "pass"
    return {
        "citationId": f"cit-{index:03d}",
        "paperId": paper.get("paperId"),
        "evidenceCardId": card.get("cardId") if card else "",
        "citationStyle": style or "GB/T 7714",
        "formattedCitation": citation_for(paper),
        "formatStatus": status,
        "requiredFieldsPresent": not missing_required,
        "missingFields": missing_required + missing_optional,
        "sourceLocator": source_locator_for(card, paper),
        "warnings": warnings,
    }


def build_citation_artifacts(
    claim_checks: list[dict[str, Any]],
    usable_cards: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    style: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    paper_index = {paper.get("paperId"): paper for paper in papers if paper.get("paperId")}
    citation_checks = []
    insertion_suggestions = []
    warnings: list[str] = []
    card_index = {card.get("cardId"): card for card in usable_cards if card.get("cardId")}
    for citation_index, card in enumerate(usable_cards, 1):
        paper = paper_index.get(card.get("paperId"))
        if not paper:
            warnings.append(f"证据卡 {card.get('cardId')} 缺少可回链文献，未生成引用。")
            continue
        check = citation_check_for(citation_index, paper, card, style)
        citation_checks.append(check)
        warnings.extend(check.get("warnings", []))

    for claim in claim_checks:
        if claim.get("status") not in {"supported", "partially_supported"}:
            continue
        for card_id in claim.get("matchedEvidenceCards", []):
            card = card_index.get(card_id)
            paper = paper_index.get(card.get("paperId")) if card else None
            citation_check = next((item for item in citation_checks if item.get("evidenceCardId") == card_id), None)
            if not card or not paper or not citation_check or citation_check.get("formatStatus") == "fail":
                continue
            insertion_suggestions.append(
                {
                    "insertionId": f"insert-{len(insertion_suggestions) + 1:03d}",
                    "claimId": claim.get("claimId"),
                    "paperId": paper.get("paperId"),
                    "evidenceCardId": card_id,
                    "inTextMarker": f"[{len(insertion_suggestions) + 1}]",
                    "formattedCitation": citation_check.get("formattedCitation"),
                    "sourceLocator": citation_check.get("sourceLocator"),
                    "requiresTeacherConfirmation": True,
                    "status": "pending_teacher_confirmation",
                    "riskNotes": card.get("limits", []) + ["教师确认前不得自动插入正文或参考文献表。"],
                }
            )
    return citation_checks, insertion_suggestions, list(dict.fromkeys(warnings))


def attach_candidate_location(candidate: dict[str, Any], card: dict[str, Any] | None, paper: dict[str, Any]) -> dict[str, Any]:
    candidate["quoteLocation"] = card.get("quoteLocation", "") if card else candidate.get("matchType", "")
    candidate["sourceLocator"] = source_locator_for(card, paper)
    candidate["evidenceLevel"] = card.get("evidenceLevel", "abstract_verified" if candidate.get("matchType") == "abstract" else "metadata_verified") if card else ("abstract_verified" if candidate.get("matchType") == "abstract" else "metadata_verified")
    if card and card.get("cardId"):
        candidate["evidenceCardId"] = card["cardId"]
    return candidate


def load_reference_pool(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    input_obj = config.get("input", {})
    _, papers = literature_adapter.load_default_papers(input_obj.get("availableLiteratureRecords", []))
    cards = literature_adapter.load_evidence_cards(input_obj.get("availableEvidenceCards", []))
    return papers, cards


def score_text(query_terms: set[str], text: str) -> int:
    return len(query_terms.intersection(tokenize(text)))


def major_terms(text: str) -> set[str]:
    return {term for term in MAJOR_TERMS if term in text}


def can_support(query_text: str, candidate_text: str, card: dict[str, Any]) -> bool:
    if query_text and query_text in candidate_text:
        return True
    required = major_terms(query_text)
    if not required:
        return False
    candidate_terms = major_terms(candidate_text)
    return required.issubset(candidate_terms) and can_support_claim(card.get("evidenceLevel"), card.get("supportType"))


def cards_supporting_claim(claim_text: str, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return common_cards_supporting_claim(claim_text, cards)


def build_source_trace(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    query_text = (
        input_obj.get("queryText")
        or " ".join(claim.get("claimText", "") for claim in input_obj.get("claims", []) if isinstance(claim, dict))
        or config.get("sourceRequest", "")
    )
    backend = selected_backend(config, input_obj)
    adapters = literature_adapter.default_adapters(
        input_obj.get("availableLiteratureRecords", []),
        input_obj.get("availableEvidenceCards", []),
        backend=backend,
    )
    trace = literature_adapter.source_trace(
        query_text=query_text,
        available_papers=input_obj.get("availableLiteratureRecords", []),
        available_cards=input_obj.get("availableEvidenceCards", []),
        adapters=adapters,
        limit=5,
    )
    verification_checks = verify_citations_batch(trace.get("candidates", []), adapters=adapters, limit=5)
    trace["dataSources"] = literature_adapter.describe_adapters(adapters)
    trace["literatureBackend"] = backend or "local_mock"
    trace["citationVerificationChecks"] = verification_checks
    return trace


def extract_draft_text(config: dict[str, Any]) -> str:
    input_obj = config.get("input", {})
    draft = input_obj.get("draftText", "")
    if isinstance(draft, str):
        return draft.strip()
    return ""


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[。！？；;!?])\s*|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk and chunk.strip()]


def find_evidence_snippet(text: str, keywords: list[str]) -> str:
    for sentence in split_sentences(text):
        if contains_any(sentence, keywords):
            return sentence[:120]
    return ""


def extract_abstract_text(text: str) -> str:
    if "摘要" not in text:
        return ""
    abstract = re.split(r"摘要[:：]", text, maxsplit=1)
    if len(abstract) < 2:
        return ""
    tail = abstract[1]
    tail = re.split(r"\n\s*(关键词|关键字|引言|一、|1[.、])[:：]?", tail, maxsplit=1)[0]
    return tail.strip()


def extract_section_chunks(text: str) -> dict[str, str]:
    heading_map = [
        ("abstract", ["摘要"]),
        ("introduction", ["引言", "研究背景"]),
        ("methods", ["方法", "研究方法", "研究对象", "数据来源", "研究设计"]),
        ("results", ["结果", "研究结果", "主要发现"]),
        ("discussion", ["讨论", "研究启示", "局限", "反思"]),
    ]
    matches: list[tuple[int, int, str]] = []
    for section_id, headings in heading_map:
        for heading in headings:
            for match in re.finditer(rf"(^|\n)\s*{re.escape(heading)}\s*[:：]", text):
                matches.append((match.start(), match.end(), section_id))
    matches.sort(key=lambda item: item[0])

    chunks: dict[str, str] = {}
    for index, (_, end, section_id) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        chunks[section_id] = text[end:next_start].strip()
    return chunks


def build_structure_diagnosis(config: dict[str, Any]) -> dict[str, Any]:
    draft_text = extract_draft_text(config)
    if not draft_text:
        return {}

    section_chunks = extract_section_chunks(draft_text)
    section_coverage = []
    revision_priorities = []
    for section in STRUCTURE_SECTIONS:
        section_text = section_chunks.get(section["sectionId"], "")
        scan_text = section_text if section_text else (draft_text if not section_chunks else "")
        hit_elements = [label for label, keywords in section["elements"].items() if contains_any(scan_text, keywords)]
        present = bool(section_text) or (not section_chunks and len(hit_elements) >= 2)
        missing_elements = [label for label in section["elements"] if label not in hit_elements]
        weak_elements = [] if not present else missing_elements[:]
        if not present:
            status = "missing"
            revision_priorities.append(f"补充 {section['label']}：需要说明{'、'.join(missing_elements)}。")
        elif missing_elements:
            status = "weak"
            revision_priorities.append(f"加强 {section['label']}：补齐{'、'.join(missing_elements)}。")
        else:
            status = "present"
        section_coverage.append(
            {
                "sectionId": section["sectionId"],
                "label": section["label"],
                "status": status,
                "missingElements": missing_elements if not present else [],
                "weakElements": weak_elements,
            }
        )

    abstract_text = extract_abstract_text(draft_text)
    abstract_checklist = []
    for element_id, label, keywords in ABSTRACT_ELEMENTS:
        snippet = find_evidence_snippet(abstract_text, keywords) if abstract_text else ""
        if not abstract_text:
            status = "missing"
        elif snippet:
            status = "present"
        else:
            status = "missing"
        abstract_checklist.append(
            {
                "element": element_id,
                "label": label,
                "status": status,
                "evidenceSnippet": snippet,
            }
        )
        if status != "present":
            revision_priorities.append(f"摘要补充{label}要素。")

    return {
        "documentType": "research_paper",
        "sectionCoverage": section_coverage,
        "abstractChecklist": abstract_checklist,
        "revisionPriorities": revision_priorities[:8],
    }


def soften_sentence(sentence: str) -> str:
    revised = sentence
    for source, target in STRONG_REPLACEMENTS:
        revised = revised.replace(source, target)
    return revised


def build_revision_suggestions(config: dict[str, Any], structure_diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    draft_text = extract_draft_text(config)
    if not draft_text:
        return []

    suggestions: list[dict[str, Any]] = []
    for sentence in split_sentences(draft_text):
        if not contains_any(sentence, STRONG_TERMS):
            continue
        revised = soften_sentence(sentence)
        if revised == sentence:
            revised = sentence.replace("显著", "可能")
        suggestions.append(
            {
                "suggestionId": f"rev-{len(suggestions) + 1:03d}",
                "originalText": sentence,
                "revisedText": revised,
                "editType": "claim_softening",
                "changedFacts": False,
                "addedFacts": [],
                "needsEvidence": True,
                "riskNotes": ["原句包含强因果或强效果表述，保守改写后仍需文献、数据或课堂材料支撑。"],
            }
        )
        if len(suggestions) >= 5:
            break

    if not suggestions and structure_diagnosis:
        priorities = structure_diagnosis.get("revisionPriorities", [])
        prompt = priorities[0] if priorities else "当前草稿未发现需要弱化的强论断，可继续补充方法、结果和讨论边界。"
        suggestions.append(
            {
                "suggestionId": "rev-001",
                "originalText": "",
                "revisedText": prompt,
                "editType": "structure_prompt",
                "changedFacts": False,
                "addedFacts": [],
                "needsEvidence": False,
                "riskNotes": [],
            }
        )
    return suggestions


def build_outline(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    title = input_obj.get("title") or input_obj.get("paperTitle") or config.get("sourceRequest") or "待定论文题目"
    research_question = input_obj.get("researchQuestion") or input_obj.get("queryText") or "围绕教师已有材料明确研究问题。"
    sections = [
        ("introduction", "问题提出", "阐明实践背景、研究问题、研究意义和已有研究不足。", "800-1200 字"),
        ("literature_review", "文献综述", "梳理核心概念、相关研究脉络和本研究定位。", "1500-2500 字"),
        ("methods", "研究方法", "说明研究对象、数据来源、实施过程和分析方法。", "1000-1500 字"),
        ("results", "研究发现", "按证据链呈现课堂观察、学生作品或访谈中的主要发现。", "2500-3500 字"),
        ("discussion", "讨论与结论", "解释发现、提出教学建议、说明局限和后续研究。", "1200-1800 字"),
    ]
    return {
        "outlineId": "outline-001",
        "title": title,
        "researchQuestion": research_question,
        "documentType": "research_paper",
        "sections": [
            {
                "sectionId": section_id,
                "title": section_title,
                "coreFunction": core_function,
                "suggestedLength": suggested_length,
                "evidenceNeed": "需要用户材料或 EvidenceCard 支撑事实性表述。",
            }
            for section_id, section_title, core_function, suggested_length in sections
        ],
        "riskNotes": ["大纲属于结构建议，不代表正文已具备事实或引用支撑。"],
    }


def build_document_draft(config: dict[str, Any], claim_checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    outline = input_obj.get("outline") if isinstance(input_obj.get("outline"), dict) else build_outline(config)
    target_section = input_obj.get("sectionId") or input_obj.get("chapterId") or "introduction"
    source_materials = input_obj.get("sourceMaterials", []) or input_obj.get("materials", [])
    evidence_refs = [
        card_id
        for check in claim_checks
        if check.get("status") in {"supported", "partially_supported"}
        for card_id in check.get("matchedEvidenceCards", [])
    ]
    material_hint = ""
    if source_materials and isinstance(source_materials[0], dict):
        material_hint = source_materials[0].get("content") or source_materials[0].get("summary") or ""
    paragraph = (
        material_hint[:180]
        if material_hint
        else "本段为 draft_reference：请教师补充课堂材料、研究对象、数据来源和证据卡后，再逐句确认是否纳入正文。"
    )
    return {
        "documentId": "draft-001",
        "documentType": "research_paper",
        "title": outline.get("title", "待定论文题目"),
        "draftStatus": "draft_reference",
        "requiresTeacherConfirmation": True,
        "sections": [
            {
                "sectionId": target_section,
                "title": next((item.get("title") for item in outline.get("sections", []) if item.get("sectionId") == target_section), "章节草稿"),
                "required": True,
                "content": paragraph,
                "factRefs": [],
                "evidenceRefs": evidence_refs,
                "status": "draft_reference",
                "requiresTeacherConfirmation": True,
                "needsEvidence": not bool(evidence_refs),
                "riskNotes": ["参考草稿不得直接作为定稿；事实、数据和引用需教师逐句确认。"],
            }
        ],
    }


def build_local_rewrite(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    selected_text = input_obj.get("selectedText") or input_obj.get("draftText") or ""
    rewrite_mode = input_obj.get("rewriteMode", "conservative_polish")
    revised = soften_sentence(selected_text) if selected_text else ""
    return {
        "rewriteId": "local-rewrite-001",
        "rewriteMode": rewrite_mode,
        "originalText": selected_text,
        "revisedText": revised,
        "changedFacts": False,
        "addedFacts": [],
        "scope": "selected_text_only",
        "riskNotes": ["局部改写只处理用户选中片段；扩写也不得补造研究事实、数据或引用。"],
    }


def count_structure_issues(structure_diagnosis: dict[str, Any]) -> int:
    if not structure_diagnosis:
        return 0
    coverage = structure_diagnosis.get("sectionCoverage", [])
    abstract = structure_diagnosis.get("abstractChecklist", [])
    return sum(1 for item in coverage if item.get("status") != "present") + sum(1 for item in abstract if item.get("status") != "present")


def count_missing_abstract_elements(structure_diagnosis: dict[str, Any]) -> int:
    if not structure_diagnosis:
        return 0
    return sum(1 for item in structure_diagnosis.get("abstractChecklist", []) if item.get("status") != "present")


def should_run_source_trace(config: dict[str, Any]) -> bool:
    input_obj = config.get("input", {})
    return (
        config.get("taskIntent", "source_trace") in SOURCE_TRACE_INTENTS
        or bool(input_obj.get("queryText"))
        or bool(input_obj.get("claims"))
    )


def render(config: dict[str, Any]) -> dict[str, Any]:
    task_intent = config.get("taskIntent", "source_trace")
    input_obj = config.get("input", {}) if isinstance(config.get("input"), dict) else {}
    run_source_trace = should_run_source_trace(config)
    trace = build_source_trace(config) if run_source_trace else {"queryText": "", "candidates": [], "decision": "no_source_found", "usableEvidenceCards": [], "papers": []}
    decision = trace["decision"]
    claims = config.get("input", {}).get("claims", [])
    if not claims and run_source_trace and trace["queryText"]:
        claims = [{"claimId": "claim-001", "claimText": trace["queryText"]}]

    claim_checks = []
    claim_support_checks = []
    for index, claim in enumerate(claims, 1):
        claim_id = claim.get("claimId") if isinstance(claim, dict) else f"claim-{index:03d}"
        claim_text = claim.get("claimText") if isinstance(claim, dict) else str(claim)
        support_check = check_claim_support(
            claim_text,
            trace["usableEvidenceCards"] if decision == "verified_source_found" else [],
            trace.get("candidates", []),
            check_id=f"support-{index:03d}",
        )
        matched_cards = [
            card
            for card in trace["usableEvidenceCards"]
            if card.get("cardId") in {item.get("evidenceCardId") for item in support_check.get("evidenceMatches", [])}
        ] if decision == "verified_source_found" else []
        matched_card_ids = [card.get("cardId") for card in matched_cards if card.get("cardId")]
        supported = bool(matched_card_ids)
        claim_support_checks.append({**support_check, "claimId": claim_id})
        claim_checks.append(
            {
                "claimId": claim_id,
                "claimText": claim_text,
                "status": "supported" if supported else "needs_evidence",
                "matchedEvidenceCards": matched_card_ids if supported else [],
                "riskNotes": [] if supported else ["当前查源命中的证据不能支撑该论点，不能顺带生成引用。"],
                "recommendedRewrite": claim_text if supported else "保留该表述前，请补充原文、摘要证据或更精确关键词。",
            }
        )

    structure_diagnosis = build_structure_diagnosis(config)
    revision_suggestions = build_revision_suggestions(config, structure_diagnosis)
    structure_issue_count = count_structure_issues(structure_diagnosis)
    missing_abstract_count = count_missing_abstract_elements(structure_diagnosis)
    needs_evidence_revision_count = sum(1 for item in revision_suggestions if item.get("needsEvidence"))
    added_fact_count = sum(len(item.get("addedFacts", [])) for item in revision_suggestions)
    citation_style = config.get("constraints", {}).get("citationStyle", "GB/T 7714")
    citation_checks, insertion_suggestions, citation_check_warnings = build_citation_artifacts(
        claim_checks,
        trace["usableEvidenceCards"] if decision == "verified_source_found" else [],
        trace["papers"],
        citation_style,
    )

    source_trace_results = [
        {
            "queryText": trace["queryText"],
            "candidates": trace["candidates"],
            "decision": decision,
        }
    ] if run_source_trace else []
    outline = build_outline(config) if task_intent in OUTLINE_INTENTS | CHAPTER_DRAFT_INTENTS else {}
    document_draft = build_document_draft(config, claim_checks) if task_intent in CHAPTER_DRAFT_INTENTS else {}
    local_rewrite = build_local_rewrite(config) if task_intent in LOCAL_REWRITE_INTENTS else {}
    if local_rewrite and not revision_suggestions and local_rewrite.get("originalText"):
        revision_suggestions.append(
            {
                "suggestionId": "rev-local-001",
                "originalText": local_rewrite.get("originalText", ""),
                "revisedText": local_rewrite.get("revisedText", ""),
                "editType": "conservative_polish",
                "changedFacts": False,
                "addedFacts": [],
                "needsEvidence": False,
                "riskNotes": local_rewrite.get("riskNotes", []),
            }
        )
    citation_warnings = []
    if run_source_trace and decision != "verified_source_found":
        if decision == "candidate_source_found":
            citation_warnings.append("PedaScope 仅返回候选题录和引用草案，未生成支撑性引用。")
        else:
            citation_warnings.append("未生成支撑性引用。")
    citation_warnings.extend(citation_check_warnings)
    citation_warnings = list(dict.fromkeys(citation_warnings))
    warnings = []
    if run_source_trace and decision != "verified_source_found":
        if decision == "candidate_source_found":
            warnings.append("已找到候选题录来源，但未返回原文证据，不能自动插入引用。")
        else:
            warnings.append("未找到可确认为原句出处的证据。")
    if structure_issue_count:
        warnings.append("草稿存在结构或摘要要素缺口。")
    if needs_evidence_revision_count:
        warnings.append("部分润色建议仍需补充文献、数据或课堂材料支撑。")
    if citation_check_warnings:
        warnings.append("引用格式或出处位置存在待补字段。")
    if document_draft and any(section.get("status") == "needs_evidence" for section in document_draft.get("sections", [])):
        warnings.append("章节草稿为 draft_reference，部分段落仍需证据和教师确认。")
    quality_status = "warn" if warnings else "pass"

    checks = []
    if run_source_trace:
        checks.append({"id": "source_trace_decision", "status": "pass"})
    if structure_diagnosis:
        checks.append({"id": "structure_diagnosis", "status": "pass"})
    if revision_suggestions:
        checks.append({"id": "conservative_revision_no_new_facts", "status": "pass" if added_fact_count == 0 else "fail"})
    if citation_checks:
        checks.append({"id": "citation_format_check", "status": "pass" if all(item.get("formatStatus") != "fail" for item in citation_checks) else "fail"})

    next_actions = []
    if run_source_trace and decision != "verified_source_found":
        if decision == "candidate_source_found":
            next_actions.append("获取候选文献原文、摘要或用户上传片段后，再生成 EvidenceCard 和引用插入建议。")
        else:
            next_actions.append("上传原文片段或调用文献阅读助手扩大候选文献池。")
    if structure_issue_count:
        next_actions.append("补充缺失的 IMRaD 章节、摘要要素或研究边界，再进行下一轮润色。")
    if needs_evidence_revision_count:
        next_actions.append("为弱化后的关键论断补充真实文献、课堂数据或用户材料。")

    payload = {
        "requestId": config.get("requestId", "req-paper-writing-render-001"),
        "skillId": "paper-writing-skill",
        "taskIntent": task_intent,
        "status": quality_status,
        "summary": f"已按 {task_intent} 模式完成论文写作辅助；查源、结构诊断和保守润色均遵守未获证据不生成支撑性引用的原则。",
        "inputSummary": {
            "sourceRequest": config.get("sourceRequest", ""),
            "queryText": input_obj.get("queryText", ""),
            "literatureBackend": trace.get("literatureBackend", selected_backend(config, input_obj) or "local_mock"),
            "claimCount": len(input_obj.get("claims", []) or []),
            "draftTextChars": len(input_obj.get("draftText", "") or ""),
            "availableEvidenceCardCount": len(input_obj.get("availableEvidenceCards", []) or []),
            "assumptions": config.get("assumptions", []),
            "constraints": config.get("constraints", {}),
        },
        "warnings": warnings,
        "dataSourceReport": build_paper_writing_data_source_report(config, trace),
        "artifacts": [],
        "result": {
            "literatureRecords": trace["papers"],
            "sourceTraceResults": source_trace_results,
            "bibliographicCandidates": [
                candidate
                for candidate in trace.get("candidates", [])
                if candidate.get("evidenceLevel") == "metadata_verified" and candidate.get("textAvailability") == "metadata"
            ],
            "claimChecks": claim_checks,
            "claimSupportChecks": claim_support_checks,
            "structureDiagnosis": structure_diagnosis,
            "revisionSuggestions": revision_suggestions,
            "outline": outline,
            "documentDraft": document_draft,
            "localRewrite": local_rewrite,
            "citationChecks": citation_checks,
            "citationVerificationChecks": trace.get("citationVerificationChecks", []),
            "insertionSuggestions": insertion_suggestions,
            "citationWarnings": citation_warnings,
        },
        "handoff": {
                "claimChecks": claim_checks,
                "claimSupportChecks": claim_support_checks,
                "bibliographicCandidates": [
                candidate
                for candidate in trace.get("candidates", [])
                if candidate.get("evidenceLevel") == "metadata_verified" and candidate.get("textAvailability") == "metadata"
            ],
            "usableEvidenceCards": trace["usableEvidenceCards"],
            "paperRevisionSummary": {
                "addedFacts": added_fact_count,
                "revisionSuggestionCount": len(revision_suggestions),
                "needsEvidenceRevisionCount": needs_evidence_revision_count,
                "citationCheckCount": len(citation_checks),
                "citationVerificationCheckCount": len(trace.get("citationVerificationChecks", [])),
                "insertionSuggestionCount": len(insertion_suggestions),
                "draftSectionCount": len(document_draft.get("sections", [])) if document_draft else 0,
                "citationPolicy": "only_verified_sources" if decision == "verified_source_found" else "no_supporting_citation_inserted",
            },
        },
        "qualityReport": {
            "status": quality_status,
            "checks": checks,
            "warnings": warnings,
            "metrics": {
                "claimCount": len(claim_checks),
                "claimSupportCheckCount": len(claim_support_checks),
                "supportedClaimCount": sum(1 for item in claim_checks if item["status"] == "supported"),
                "needsEvidenceCount": sum(1 for item in claim_checks if item["status"] == "needs_evidence"),
                "sourceTraceHitCount": 1 if run_source_trace and decision == "verified_source_found" else 0,
                "candidateSourceCount": 1 if run_source_trace and decision == "candidate_source_found" else 0,
                "citationFormatWarnings": len(citation_warnings),
                "structureIssueCount": structure_issue_count,
                "missingAbstractElementCount": missing_abstract_count,
                "revisionSuggestionCount": len(revision_suggestions),
                "addedFactCount": added_fact_count,
                "needsEvidenceRevisionCount": needs_evidence_revision_count,
                "citationCheckCount": len(citation_checks),
                "citationVerificationCheckCount": len(trace.get("citationVerificationChecks", [])),
                "citationReadyCount": sum(1 for item in citation_checks if item.get("formatStatus") == "pass"),
                "insertionSuggestionCount": len(insertion_suggestions),
                "pendingTeacherConfirmationCount": sum(1 for item in insertion_suggestions if item.get("status") == "pending_teacher_confirmation"),
                "outlineSectionCount": len(outline.get("sections", [])) if outline else 0,
                "draftSectionCount": len(document_draft.get("sections", [])) if document_draft else 0,
                "localRewriteCount": 1 if local_rewrite else 0,
            },
        },
        "provenanceReport": {
            "sourceCount": len(trace["papers"]),
            "verifiedSourceCount": len([paper for paper in trace["papers"] if paper.get("sourceStatus") == "whitelist"]),
            "unsupportedClaimCount": sum(1 for item in claim_checks if item["status"] == "needs_evidence"),
        },
        "nextActions": next_actions,
    }
    return attach_education_generator_runtime(
        payload,
        skill_id="paper-writing-skill",
        task_intent=str(task_intent),
        used_for=["outline_generation", "chapter_draft_reference", "conservative_polish"],
        generation_mode="evidence_guarded_with_innospark_235b_generator_contract",
    )


def render_markdown(data: dict[str, Any]) -> str:
    result = data.get("result", {})
    trace = (result.get("sourceTraceResults") or [{}])[0]
    lines = [
        "# 论文写作助手结果",
        "",
        f"请求 ID：`{data.get('requestId')}`",
        f"校验状态：`{data.get('qualityReport', {}).get('status')}`",
        "",
        "## 查源结论",
        "",
        f"- 查询文本：{trace.get('queryText', '')}",
        f"- 判定：`{trace.get('decision', '')}`",
        "",
    ]
    if trace.get("candidates"):
        lines.extend(["## 候选文献", ""])
        for candidate in trace.get("candidates", []):
            lines.extend(
                [
                    f"- `{candidate.get('paperId')}`：`{candidate.get('supportStatus')}` / `{candidate.get('confidence')}`",
                    f"  - 片段：{candidate.get('matchSnippet')}",
                    f"  - 引用：{candidate.get('citation') or '未生成'}",
                ]
            )
        lines.append("")
    outline = result.get("outline", {})
    if outline:
        lines.extend(["## 大纲", ""])
        lines.append(f"- 题目：{outline.get('title')}")
        for section in outline.get("sections", []):
            lines.append(f"- {section.get('title')}：{section.get('coreFunction')}（{section.get('suggestedLength')}）")
        lines.append("")
    draft = result.get("documentDraft", {})
    if draft:
        lines.extend(["## 章节草稿", ""])
        for section in draft.get("sections", []):
            lines.extend(
                [
                    f"### {section.get('title')}",
                    "",
                    section.get("content", ""),
                    "",
                    f"- 状态：`{section.get('status')}`；需教师确认：`{draft.get('requiresTeacherConfirmation')}`",
                    "",
                ]
            )
    local_rewrite = result.get("localRewrite", {})
    if local_rewrite:
        lines.extend(["## 局部改写", ""])
        lines.extend(
            [
                f"- 原文：{local_rewrite.get('originalText')}",
                f"- 建议：{local_rewrite.get('revisedText')}",
                f"- changedFacts：`{local_rewrite.get('changedFacts')}`",
                "",
            ]
        )
    lines.extend(["## 论点检查", ""])
    for check in result.get("claimChecks", []):
        notes = "；".join(check.get("riskNotes", [])) or "暂无"
        lines.extend(
            [
                f"- {check.get('claimText')}",
                f"  - 状态：`{check.get('status')}`",
                f"  - 风险：{notes}",
                f"  - 建议：{check.get('recommendedRewrite')}",
            ]
        )
    lines.append("")
    structure = result.get("structureDiagnosis", {})
    if structure:
        lines.extend(["## 结构诊断", ""])
        for item in structure.get("sectionCoverage", []):
            weak = "、".join(item.get("weakElements", []) or item.get("missingElements", [])) or "暂无"
            lines.append(f"- {item.get('label')}：`{item.get('status')}`；关注：{weak}")
        lines.append("")
    suggestions = result.get("revisionSuggestions", [])
    if suggestions:
        lines.extend(["## 保守润色建议", ""])
        for item in suggestions:
            lines.extend(
                [
                    f"- `{item.get('suggestionId')}` / `{item.get('editType')}`",
                    f"  - 原文：{item.get('originalText') or '结构提示'}",
                    f"  - 建议：{item.get('revisedText')}",
                    f"  - 需补证据：`{item.get('needsEvidence')}`",
                ]
            )
        lines.append("")
    citation_checks = result.get("citationChecks", [])
    if citation_checks:
        lines.extend(["## 引用格式检查", ""])
        for item in citation_checks:
            warnings = "；".join(item.get("warnings", [])) or "暂无"
            lines.extend(
                [
                    f"- `{item.get('citationId')}` / `{item.get('formatStatus')}`",
                    f"  - 文献：`{item.get('paperId')}`；证据卡：`{item.get('evidenceCardId')}`",
                    f"  - 引用：{item.get('formattedCitation')}",
                    f"  - 出处：{item.get('sourceLocator', {}).get('locator', '')}",
                    f"  - 提醒：{warnings}",
                ]
            )
        lines.append("")
    verification_checks = result.get("citationVerificationChecks", [])
    if verification_checks:
        lines.extend(["## 题录真实性验证", ""])
        for item in verification_checks:
            lines.extend(
                [
                    f"- `{item.get('verificationId')}` / `{item.get('verificationStatus')}` / confidence `{item.get('confidence')}`",
                    f"  - 文献：`{item.get('paperId')}` {item.get('title')}",
                    f"  - 说明：{item.get('verificationNote')}",
                    f"  - 边界：{'；'.join(item.get('limits', []))}",
                ]
            )
        lines.append("")
    insertions = result.get("insertionSuggestions", [])
    if insertions:
        lines.extend(["## 待确认插入建议", ""])
        for item in insertions:
            lines.extend(
                [
                    f"- `{item.get('insertionId')}`：claim `{item.get('claimId')}` -> {item.get('inTextMarker')}",
                    f"  - 状态：`{item.get('status')}`；需教师确认：`{item.get('requiresTeacherConfirmation')}`",
                    f"  - 参考文献：{item.get('formattedCitation')}",
                ]
            )
        lines.append("")
    next_actions = data.get("nextActions", [])
    if next_actions:
        lines.extend(["## 下一步", ""])
        lines.extend(f"- {item}" for item in next_actions)
        lines.append("")
    return "\n".join(lines)


def merge_guardrails_audit(output: dict[str, Any], audit_path: Path) -> dict[str, Any]:
    """将 writing_guardrails.py audit 产出合并到 output 中。"""
    audit_data = load_json(audit_path)
    audit = audit_data.get("audit", audit_data)

    result = output.get("result", {})
    # 合并结构诊断
    structure = audit.get("structure", {})
    if structure:
        existing = result.get("structureDiagnosis", {})
        if not existing:
            result["structureDiagnosis"] = structure
        else:
            for key in ("section_coverage", "abstract_checklist", "sectionCoverage", "abstractChecklist"):
                if key in structure and key not in existing:
                    existing[key] = structure[key]
            result["structureDiagnosis"] = existing

    # 合并引用检查
    citation_issues = audit.get("citations", audit.get("citation_issues", []))
    if citation_issues:
        existing_citations = result.get("citationChecks", [])
        for issue in citation_issues:
            if isinstance(issue, dict) and issue.get("paperId") not in {c.get("paperId") for c in existing_citations}:
                existing_citations.append(issue)
        result["citationChecks"] = existing_citations

    # 合并风险点
    risks = audit.get("risky_claims", audit.get("risks", []))
    if risks:
        existing_risks = result.get("citationWarnings", [])
        for risk in risks:
            if isinstance(risk, str) and risk not in existing_risks:
                existing_risks.append(risk)
            elif isinstance(risk, dict):
                existing_risks.append(risk.get("text", str(risk)))
        result["citationWarnings"] = existing_risks

    # 更新质量报告
    qr = output.get("qualityReport", {})
    qr.setdefault("checks", []).append({"id": "guardrails_audit", "status": "pass"})
    metrics = qr.get("metrics", {})
    metrics["guardrailsAuditEnabled"] = True
    metrics["citationIssuesFromAudit"] = len(citation_issues)
    metrics["riskyClaimsFromAudit"] = len(risks)
    output["status"] = qr.get("status", output.get("status", "pass"))

    return output


def merge_guardrails_claim(output: dict[str, Any], claim_path: Path) -> dict[str, Any]:
    """将 writing_guardrails.py claim 产出合并到 output 中。"""
    claim_data = load_json(claim_path)

    result = output.get("result", {})
    # 追加到 sourceTraceResults
    traces = result.get("sourceTraceResults", [])
    raw_decision = claim_data.get("decision", "")
    query_text = claim_data.get("claim", "")
    normalized_candidates = []
    required_terms = major_terms(query_text)
    for candidate in claim_data.get("matches", []):
        if not isinstance(candidate, dict):
            continue
        item = dict(candidate)
        item.setdefault("citation", item.get("gbt7714", ""))
        if item.get("supportStatus") == "supports" and required_terms:
            snippet_terms = major_terms(str(item.get("matchSnippet", "")))
            if not required_terms.issubset(snippet_terms):
                item["supportStatus"] = "related_only"
                item["confidence"] = "low"
        normalized_candidates.append(item)
    has_support = any(item.get("supportStatus") == "supports" for item in normalized_candidates)
    if raw_decision == "suggest_insert" and has_support:
        trace_decision = "verified_source_found"
    elif raw_decision == "need_more_evidence" or normalized_candidates:
        trace_decision = "related_sources_only"
    else:
        trace_decision = "no_source_found"
    claim_result = {
        "queryText": query_text,
        "decision": trace_decision,
        "candidates": normalized_candidates,
    }
    traces.append(claim_result)
    result["sourceTraceResults"] = traces

    # 更新决策级别
    decision = raw_decision
    if decision == "suggest_insert" and output.get("qualityReport", {}).get("status") != "warn":
        pass  # 保持原有状态

    qr = output.get("qualityReport", {})
    qr.setdefault("checks", []).append({"id": "guardrails_claim", "status": "pass"})
    metrics = qr.get("metrics", {})
    metrics["sourceTraceHitCount"] = sum(1 for trace in result.get("sourceTraceResults", []) if isinstance(trace, dict) and trace.get("decision") == "verified_source_found")
    metrics["guardrailsClaimEnabled"] = True
    metrics["guardrailsClaimDecision"] = decision
    metrics["guardrailsClaimMatchCount"] = len(normalized_candidates)
    output["status"] = qr.get("status", output.get("status", "pass"))

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染论文写作助手 JSON 产物（含可选 writing_guardrails 审计/论据索引）。")
    parser.add_argument("input_or_output_base", help="旧入口为请求 JSON；使用 --config 时为输出 base")
    parser.add_argument("--config", help="模板式入口的请求 JSON 文件：render_x.py <output_base> --config <request>")
    parser.add_argument("--output", help="输出 JSON 文件；默认写入 generated-outputs/<requestId>.json")
    parser.add_argument("--validate", action="store_true", help="输出后立即运行 validate_paper_writing.py")
    parser.add_argument(
        "--guardrails-audit",
        help="可选：运行 writing_guardrails.py audit 的文章文件（.md），结果合并到输出",
    )
    parser.add_argument(
        "--guardrails-claim",
        help="可选：运行 writing_guardrails.py claim 的参数 JSON {claim, evidence}",
    )
    parser.add_argument(
        "--guardrails-evidence",
        help="与 --guardrails-audit 或 --guardrails-claim 配合使用的证据卡 JSON",
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else Path(args.input_or_output_base)
    config = load_json(config_path)
    output = render(config)

    # 集成 writing_guardrails
    if args.guardrails_audit:
        audit_out = OUTPUT_DIR / "guardrails_audit.json"
        cmd = [
            "python3", str(GUARDRAILS_SCRIPT), "audit",
            "--article", args.guardrails_audit,
            "--out", str(audit_out),
        ]
        if args.guardrails_evidence:
            cmd.extend(["--evidence", args.guardrails_evidence])
        rc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if rc.returncode == 0 and audit_out.exists():
            print(f"[guardrails] audit: {rc.stdout.strip()}")
            output = merge_guardrails_audit(output, audit_out)
        else:
            print(f"[guardrails] audit failed: {rc.stderr}")

    if args.guardrails_claim:
        claim_config = load_json(Path(args.guardrails_claim))
        if isinstance(claim_config, str):
            claim = claim_config
        elif isinstance(claim_config, list):
            claim = " ".join(str(c.get("claim", "")) for c in claim_config if isinstance(c, dict)) or " ".join(str(c) for c in claim_config if isinstance(c, str))
        elif isinstance(claim_config, dict):
            input_claims = claim_config.get("input", {}).get("claims", []) if isinstance(claim_config.get("input"), dict) else []
            claim = (
                claim_config.get("claim")
                or claim_config.get("input", {}).get("queryText", "")
                or " ".join(item.get("claimText", "") for item in input_claims if isinstance(item, dict))
            )
        else:
            claim = str(claim_config)
        claim_out = OUTPUT_DIR / "guardrails_claim.json"
        cmd = [
            "python3", str(GUARDRAILS_SCRIPT), "claim",
            "--claim", claim,
            "--out", str(claim_out),
        ]
        if args.guardrails_evidence:
            cmd.extend(["--evidence", args.guardrails_evidence])
        rc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if rc.returncode == 0 and claim_out.exists():
            print(f"[guardrails] claim: {rc.stdout.strip()}")
            output = merge_guardrails_claim(output, claim_out)
        else:
            print(f"[guardrails] claim failed: {rc.stderr}")

    if args.output:
        output_path = Path(args.output)
    elif args.config:
        output_base = Path(args.input_or_output_base)
        output_path = output_base if output_base.suffix == ".json" else output_base.with_suffix(".json")
    else:
        output_path = OUTPUT_DIR / f"{output['requestId']}.json"
    md_path = output_path.with_suffix(".md")
    output["artifacts"] = [
        {"type": "json", "path": str(output_path), "description": "结构化论文写作辅助结果"},
        {"type": "markdown", "path": str(md_path), "description": "教师可读论文写作诊断报告"},
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
