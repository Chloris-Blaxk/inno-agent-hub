#!/usr/bin/env python3
"""校验论文写作助手 Skill 的 JSON 产物。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

COMMON_ROOT = Path(__file__).resolve().parents[1].parent / "research-line-common"
sys.path.insert(0, str(COMMON_ROOT))
from data_source_report import validate_data_source_report  # noqa: E402
from evidence_policy import EVIDENCE_LEVELS, SUPPORT_TYPES, can_create_evidence_card  # noqa: E402


SKILL_ID = "paper-writing-skill"
ALLOWED_INTENTS = {
    "source_trace",
    "claim_support_check",
    "structure_diagnosis",
    "conservative_polish",
    "citation_format",
    "outline_generation",
    "chapter_drafting",
    "local_rewrite",
}
ROOT_REQUIRED = [
    "requestId",
    "skillId",
    "taskIntent",
    "status",
    "summary",
    "warnings",
    "dataSourceReport",
    "result",
    "handoff",
    "qualityReport",
    "provenanceReport",
    "nextActions",
]
DECISIONS = {"verified_source_found", "candidate_source_found", "related_sources_only", "no_source_found"}
MATCH_TYPES = {"title", "metadata", "abstract", "evidence_card", "fulltext", "pedascope_claim_candidate"}
SUPPORT_STATUSES = {"supports", "related_only", "not_support"}
CONFIDENCES = {"high", "medium", "low"}
CLAIM_STATUSES = {"supported", "partially_supported", "needs_evidence", "unsupported"}
CRITICAL_SUPPORT_TERMS = ["即时反馈", "错因", "典型错因", "成绩", "显著", "讲评", "教学调整", "学习投入"]
STRUCTURE_STATUSES = {"present", "missing", "weak"}
REVISION_EDIT_TYPES = {"conservative_polish", "claim_softening", "structure_prompt"}
FABRICATED_MARKERS = ["作者", "DOI", "doi", "页码", "样本量", "显著性", "p<", "P<", "p =", "P ="]
CITATION_FORMAT_STATUSES = {"pass", "warn", "fail"}
INSERTION_STATUSES = {"pending_teacher_confirmation", "rejected", "inserted"}
DRAFT_STATUSES = {"draft_reference", "needs_evidence", "needs_user_confirmation"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_paper_ids() -> set[str]:
    reference_path = Path(__file__).resolve().parents[1] / "references" / "literature-whitelist-sample.json"
    try:
        data = load_json(reference_path)
    except FileNotFoundError:
        return set()
    return {paper.get("paperId") for paper in data.get("papers", []) if paper.get("paperId")}


def non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def require_fields(obj: dict[str, Any], fields: list[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj or not non_empty(obj[field]):
            errors.append(f"{label} 缺少或为空：{field}")


def require_keys(obj: dict[str, Any], fields: list[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj:
            errors.append(f"{label} 缺少字段：{field}")


def critical_terms(text: str) -> set[str]:
    return {term for term in CRITICAL_SUPPORT_TERMS if term in text}


def collect_literature_records(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = data.get("result", {})
    handoff = data.get("handoff", {})
    records: list[Any] = []
    if isinstance(result, dict):
        records.extend(result.get("literatureRecords", []))
    if isinstance(handoff, dict):
        records.extend(handoff.get("literatureRecords", []))

    index: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and record.get("paperId"):
            index[record["paperId"]] = record
    for paper_id in load_reference_paper_ids():
        index.setdefault(paper_id, {"paperId": paper_id, "textAvailability": "abstract", "sourceStatus": "whitelist"})
    return index


def validate_evidence_cards(
    cards: list[Any],
    known_papers: dict[str, dict[str, Any]],
    candidate_paper_ids: set[str],
    errors: list[str],
) -> set[str]:
    valid_card_ids: set[str] = set()
    for index, card in enumerate(cards, 1):
        if not isinstance(card, dict):
            errors.append(f"usableEvidenceCards[{index}] 必须是对象。")
            continue
        require_fields(card, ["cardId", "claim", "evidenceText", "paperId", "quoteLocation", "supportType", "evidenceLevel"], f"usableEvidenceCards[{index}]", errors)
        paper_id = card.get("paperId")
        if paper_id not in known_papers and paper_id not in candidate_paper_ids:
            errors.append(f"usableEvidenceCards[{index}] 不能回链到真实 paperId：{paper_id}")
        if card.get("supportType") not in SUPPORT_TYPES:
            errors.append(f"usableEvidenceCards[{index}] supportType 不合法：{card.get('supportType')}")
        if card.get("evidenceLevel") not in EVIDENCE_LEVELS:
            errors.append(f"usableEvidenceCards[{index}] evidenceLevel 不合法：{card.get('evidenceLevel')}")
        known_paper = known_papers.get(paper_id, {})
        if card.get("evidenceLevel") == "metadata_verified" or (
            known_paper and not can_create_evidence_card(known_paper.get("textAvailability"), card.get("evidenceLevel"))
        ):
            errors.append(f"usableEvidenceCards[{index}] 不能把 metadata_verified 当作支撑证据。")
        if card.get("cardId"):
            valid_card_ids.add(card["cardId"])
    return valid_card_ids


def validate_quality_report(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    quality = data.get("qualityReport", {})
    if not isinstance(quality, dict):
        errors.append("qualityReport 必须是对象。")
        return
    checks = quality.get("checks", [])
    if isinstance(checks, list):
        failed = [item.get("id") for item in checks if isinstance(item, dict) and item.get("status") == "fail"]
        if failed:
            errors.append(f"qualityReport 存在失败检查：{failed}")
    if quality.get("status") in {"fail", "failed"}:
        errors.append(f"qualityReport.status 为 {quality.get('status')}。")
    if quality.get("status") == "warn":
        warnings.append("qualityReport.status 为 warn，请查看 warnings。")


def collect_number_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", text or ""))


def collect_fabricated_markers(text: str) -> set[str]:
    markers = {marker for marker in FABRICATED_MARKERS if marker in (text or "")}
    markers.update(re.findall(r"(?:19|20)\d{2}", text or ""))
    return markers


def validate_structure_diagnosis(structure: Any, errors: list[str]) -> tuple[int, int]:
    if not structure:
        return 0, 0
    if not isinstance(structure, dict):
        errors.append("result.structureDiagnosis 必须是对象。")
        return 0, 0

    require_keys(structure, ["documentType", "sectionCoverage", "abstractChecklist", "revisionPriorities"], "structureDiagnosis", errors)
    section_coverage = structure.get("sectionCoverage", [])
    abstract_checklist = structure.get("abstractChecklist", [])
    revision_priorities = structure.get("revisionPriorities", [])
    if not isinstance(section_coverage, list) or not section_coverage:
        errors.append("structureDiagnosis.sectionCoverage 必须是非空数组。")
        section_coverage = []
    if not isinstance(abstract_checklist, list) or not abstract_checklist:
        errors.append("structureDiagnosis.abstractChecklist 必须是非空数组。")
        abstract_checklist = []
    if not isinstance(revision_priorities, list):
        errors.append("structureDiagnosis.revisionPriorities 必须是数组。")

    structure_issue_count = 0
    for index, item in enumerate(section_coverage, 1):
        label = f"structureDiagnosis.sectionCoverage[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(item, ["sectionId", "label", "status"], label, errors)
        require_keys(item, ["missingElements", "weakElements"], label, errors)
        if item.get("status") not in STRUCTURE_STATUSES:
            errors.append(f"{label} status 不合法：{item.get('status')}")
        if not isinstance(item.get("missingElements", []), list):
            errors.append(f"{label}.missingElements 必须是数组。")
        if not isinstance(item.get("weakElements", []), list):
            errors.append(f"{label}.weakElements 必须是数组。")
        if item.get("status") != "present":
            structure_issue_count += 1

    missing_abstract_count = 0
    for index, item in enumerate(abstract_checklist, 1):
        label = f"structureDiagnosis.abstractChecklist[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(item, ["element", "label", "status"], label, errors)
        require_keys(item, ["evidenceSnippet"], label, errors)
        if item.get("status") not in STRUCTURE_STATUSES:
            errors.append(f"{label} status 不合法：{item.get('status')}")
        if item.get("status") != "present":
            structure_issue_count += 1
            missing_abstract_count += 1
    return structure_issue_count, missing_abstract_count


def validate_revision_suggestions(suggestions: Any, errors: list[str]) -> tuple[int, int, int]:
    if suggestions is None:
        return 0, 0, 0
    if not isinstance(suggestions, list):
        errors.append("result.revisionSuggestions 必须是数组。")
        return 0, 0, 0

    added_fact_count = 0
    needs_evidence_count = 0
    for index, item in enumerate(suggestions, 1):
        label = f"revisionSuggestions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(item, ["suggestionId", "revisedText", "editType"], label, errors)
        require_keys(item, ["originalText", "changedFacts", "addedFacts", "needsEvidence", "riskNotes"], label, errors)
        if item.get("editType") not in REVISION_EDIT_TYPES:
            errors.append(f"{label} editType 不合法：{item.get('editType')}")
        if item.get("changedFacts") is not False:
            errors.append(f"{label} changedFacts 必须为 false。")
        if not isinstance(item.get("addedFacts", []), list):
            errors.append(f"{label}.addedFacts 必须是数组。")
        elif item.get("addedFacts"):
            errors.append(f"{label} 不得新增事实：{item.get('addedFacts')}")
            added_fact_count += len(item.get("addedFacts", []))
        if item.get("needsEvidence") is True:
            needs_evidence_count += 1
        if not isinstance(item.get("riskNotes", []), list):
            errors.append(f"{label}.riskNotes 必须是数组。")

        original = str(item.get("originalText", ""))
        revised = str(item.get("revisedText", ""))
        new_numbers = collect_number_tokens(revised) - collect_number_tokens(original)
        if new_numbers:
            errors.append(f"{label} 润色后新增数字或比例，存在虚构事实风险：{sorted(new_numbers)}")
        new_markers = collect_fabricated_markers(revised) - collect_fabricated_markers(original)
        if new_markers:
            errors.append(f"{label} 润色后新增引用、年份或统计标记：{sorted(new_markers)}")
    return len(suggestions), added_fact_count, needs_evidence_count


def validate_citation_checks(checks: Any, known_papers: dict[str, dict[str, Any]], valid_card_ids: set[str], errors: list[str]) -> tuple[int, int, int]:
    if checks is None:
        errors.append("result.citationChecks 必须是数组。")
        return 0, 0, 0
    if not isinstance(checks, list):
        errors.append("result.citationChecks 必须是数组。")
        return 0, 0, 0

    ready_count = 0
    warning_count = 0
    for index, item in enumerate(checks, 1):
        label = f"citationChecks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(item, ["citationId", "paperId", "citationStyle", "formattedCitation", "formatStatus", "sourceLocator"], label, errors)
        require_keys(item, ["evidenceCardId", "requiredFieldsPresent", "missingFields", "warnings"], label, errors)
        paper_id = item.get("paperId")
        if paper_id not in known_papers:
            errors.append(f"{label} 引用了不存在的 paperId：{paper_id}")
        evidence_card_id = item.get("evidenceCardId")
        if evidence_card_id and evidence_card_id not in valid_card_ids:
            errors.append(f"{label} 引用了不可用 evidenceCard：{evidence_card_id}")
        if item.get("citationStyle") != "GB/T 7714":
            errors.append(f"{label}.citationStyle 当前必须为 GB/T 7714。")
        if item.get("formatStatus") not in CITATION_FORMAT_STATUSES:
            errors.append(f"{label}.formatStatus 不合法：{item.get('formatStatus')}")
        if item.get("formatStatus") == "pass":
            ready_count += 1
        if item.get("formatStatus") == "warn":
            warning_count += 1
        if item.get("formatStatus") == "fail":
            errors.append(f"{label}.formatStatus 为 fail。")
        if "[J]" not in str(item.get("formattedCitation", "")):
            errors.append(f"{label}.formattedCitation 缺少期刊文献标识 [J]。")
        paper = known_papers.get(paper_id, {})
        for field in ["title", "journal", "year"]:
            value = str(paper.get(field, ""))
            if value and value not in str(item.get("formattedCitation", "")):
                errors.append(f"{label}.formattedCitation 未包含文献字段 {field}。")
        if not isinstance(item.get("missingFields", []), list):
            errors.append(f"{label}.missingFields 必须是数组。")
        if not isinstance(item.get("warnings", []), list):
            errors.append(f"{label}.warnings 必须是数组。")
        locator = item.get("sourceLocator", {})
        if not isinstance(locator, dict):
            errors.append(f"{label}.sourceLocator 必须是对象。")
        else:
            require_fields(locator, ["locationType", "locator", "confidence"], f"{label}.sourceLocator", errors)
            if locator.get("locationType") == "metadata":
                errors.append(f"{label}.sourceLocator 不能是 metadata。")
    return len(checks), ready_count, warning_count


def validate_insertion_suggestions(
    suggestions: Any,
    claim_checks: list[Any],
    citation_checks: list[Any],
    valid_card_ids: set[str],
    verified_trace_count: int,
    errors: list[str],
) -> tuple[int, int]:
    if suggestions is None:
        errors.append("result.insertionSuggestions 必须是数组。")
        return 0, 0
    if not isinstance(suggestions, list):
        errors.append("result.insertionSuggestions 必须是数组。")
        return 0, 0
    if verified_trace_count == 0 and suggestions:
        errors.append("没有 verified_source_found 时不得输出 insertionSuggestions。")

    claim_ids = {item.get("claimId") for item in claim_checks if isinstance(item, dict)}
    citation_card_ids = {item.get("evidenceCardId") for item in citation_checks if isinstance(item, dict) and item.get("formatStatus") != "fail"}
    pending_count = 0
    for index, item in enumerate(suggestions, 1):
        label = f"insertionSuggestions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(item, ["insertionId", "claimId", "paperId", "evidenceCardId", "inTextMarker", "formattedCitation", "sourceLocator", "status"], label, errors)
        require_keys(item, ["requiresTeacherConfirmation", "riskNotes"], label, errors)
        if item.get("claimId") not in claim_ids:
            errors.append(f"{label} 引用了不存在的 claimId：{item.get('claimId')}")
        if item.get("evidenceCardId") not in valid_card_ids:
            errors.append(f"{label} 引用了不可用 evidenceCard：{item.get('evidenceCardId')}")
        if item.get("evidenceCardId") not in citation_card_ids:
            errors.append(f"{label} 没有对应可用 citationCheck：{item.get('evidenceCardId')}")
        if item.get("requiresTeacherConfirmation") is not True:
            errors.append(f"{label}.requiresTeacherConfirmation 必须为 true。")
        if item.get("status") not in INSERTION_STATUSES:
            errors.append(f"{label}.status 不合法：{item.get('status')}")
        if item.get("status") == "pending_teacher_confirmation":
            pending_count += 1
        if not str(item.get("inTextMarker", "")).startswith("["):
            errors.append(f"{label}.inTextMarker 应为待插入编号标记。")
        if not isinstance(item.get("riskNotes", []), list) or not item.get("riskNotes"):
            errors.append(f"{label}.riskNotes 必须是非空数组。")
        locator = item.get("sourceLocator", {})
        if not isinstance(locator, dict):
            errors.append(f"{label}.sourceLocator 必须是对象。")
        else:
            require_fields(locator, ["locationType", "locator", "confidence"], f"{label}.sourceLocator", errors)
    return len(suggestions), pending_count


def validate_outline(outline: Any, errors: list[str]) -> int:
    if not outline:
        return 0
    if not isinstance(outline, dict):
        errors.append("result.outline 必须是对象。")
        return 0
    require_fields(outline, ["outlineId", "title", "documentType", "sections"], "outline", errors)
    sections = outline.get("sections", [])
    if not isinstance(sections, list) or not sections:
        errors.append("outline.sections 必须是非空数组。")
        return 0
    for index, section in enumerate(sections, 1):
        label = f"outline.sections[{index}]"
        if not isinstance(section, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(section, ["sectionId", "title", "coreFunction", "suggestedLength", "evidenceNeed"], label, errors)
    return len(sections)


def validate_document_draft(draft: Any, errors: list[str]) -> int:
    if not draft:
        return 0
    if not isinstance(draft, dict):
        errors.append("result.documentDraft 必须是对象。")
        return 0
    require_fields(draft, ["documentId", "documentType", "title", "draftStatus", "sections"], "documentDraft", errors)
    require_keys(draft, ["requiresTeacherConfirmation"], "documentDraft", errors)
    if draft.get("draftStatus") != "draft_reference":
        errors.append("documentDraft.draftStatus 必须为 draft_reference。")
    if draft.get("requiresTeacherConfirmation") is not True:
        errors.append("documentDraft.requiresTeacherConfirmation 必须为 true。")
    sections = draft.get("sections", [])
    if not isinstance(sections, list) or not sections:
        errors.append("documentDraft.sections 必须是非空数组。")
        return 0
    for index, section in enumerate(sections, 1):
        label = f"documentDraft.sections[{index}]"
        if not isinstance(section, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(section, ["sectionId", "title", "content", "status"], label, errors)
        require_keys(section, ["factRefs", "evidenceRefs", "riskNotes"], label, errors)
        if section.get("status") not in DRAFT_STATUSES:
            errors.append(f"{label}.status 不合法：{section.get('status')}")
        if section.get("status") == "draft_reference" and section.get("requiresTeacherConfirmation") is not True:
            errors.append(f"{label}.requiresTeacherConfirmation 必须为 true。")
        if section.get("status") == "draft_reference" and "参考草稿" not in "；".join(str(item) for item in section.get("riskNotes", [])):
            errors.append(f"{label}.riskNotes 必须说明参考草稿不得直接作为定稿。")
        if not isinstance(section.get("factRefs", []), list):
            errors.append(f"{label}.factRefs 必须是数组。")
        if not isinstance(section.get("evidenceRefs", []), list):
            errors.append(f"{label}.evidenceRefs 必须是数组。")
        if not isinstance(section.get("riskNotes", []), list) or not section.get("riskNotes"):
            errors.append(f"{label}.riskNotes 必须是非空数组。")
    return len(sections)


def validate_local_rewrite(rewrite: Any, errors: list[str]) -> int:
    if not rewrite:
        return 0
    if not isinstance(rewrite, dict):
        errors.append("result.localRewrite 必须是对象。")
        return 0
    require_fields(rewrite, ["rewriteId", "rewriteMode", "originalText", "revisedText", "scope"], "localRewrite", errors)
    require_keys(rewrite, ["changedFacts", "addedFacts", "riskNotes"], "localRewrite", errors)
    if rewrite.get("changedFacts") is not False:
        errors.append("localRewrite.changedFacts 必须为 false。")
    if rewrite.get("addedFacts"):
        errors.append("localRewrite.addedFacts 必须为空。")
    if rewrite.get("scope") != "selected_text_only":
        errors.append("localRewrite.scope 必须为 selected_text_only。")
    return 1


def validate(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    require_keys(data, ROOT_REQUIRED, "根对象", errors)
    require_fields(data, [field for field in ROOT_REQUIRED if field not in {"nextActions", "warnings"}], "根对象", errors)
    if errors:
        return errors, warnings

    if data.get("skillId") != SKILL_ID:
        errors.append(f"skillId 不一致：期望 {SKILL_ID}，实际 {data.get('skillId')}")
    if data.get("taskIntent") not in ALLOWED_INTENTS:
        errors.append(f"未知 taskIntent：{data.get('taskIntent')}")
    if data.get("status") not in {"pass", "warn", "failed"}:
        errors.append(f"根对象 status 不合法：{data.get('status')}")
    if data.get("status") != data.get("qualityReport", {}).get("status"):
        errors.append("根对象 status 必须与 qualityReport.status 一致。")
    if not isinstance(data.get("warnings"), list):
        errors.append("根对象 warnings 必须是数组。")
    elif data.get("warnings") != data.get("qualityReport", {}).get("warnings", []):
        errors.append("根对象 warnings 必须与 qualityReport.warnings 一致。")
    errors.extend(validate_data_source_report(data.get("dataSourceReport")))

    result = data.get("result", {})
    handoff = data.get("handoff", {})
    if not isinstance(result, dict):
        errors.append("result 必须是对象。")
        return errors, warnings
    if not isinstance(handoff, dict):
        errors.append("handoff 必须是对象。")
        return errors, warnings

    source_trace_results = result.get("sourceTraceResults", [])
    claim_checks = result.get("claimChecks", [])
    citation_warnings = result.get("citationWarnings", [])
    structure_diagnosis = result.get("structureDiagnosis", {})
    revision_suggestions = result.get("revisionSuggestions", [])
    citation_checks = result.get("citationChecks")
    insertion_suggestions = result.get("insertionSuggestions")
    bibliographic_candidates = result.get("bibliographicCandidates", [])
    outline = result.get("outline", {})
    document_draft = result.get("documentDraft", {})
    local_rewrite = result.get("localRewrite", {})
    if not isinstance(source_trace_results, list):
        errors.append("result.sourceTraceResults 必须是数组。")
        source_trace_results = []
    if not isinstance(claim_checks, list):
        errors.append("result.claimChecks 必须是数组。")
        claim_checks = []
    if not isinstance(citation_warnings, list):
        errors.append("result.citationWarnings 必须是数组。")
        citation_warnings = []
    if not isinstance(bibliographic_candidates, list):
        errors.append("result.bibliographicCandidates 必须是数组。")
        bibliographic_candidates = []

    known_papers = collect_literature_records(data)
    candidate_paper_ids: set[str] = set()
    verified_trace_count = 0
    for trace_index, trace in enumerate(source_trace_results, 1):
        if not isinstance(trace, dict):
            errors.append(f"sourceTraceResults[{trace_index}] 必须是对象。")
            continue
        require_fields(trace, ["queryText", "candidates", "decision"], f"sourceTraceResults[{trace_index}]", errors)
        decision = trace.get("decision")
        if decision not in DECISIONS:
            errors.append(f"sourceTraceResults[{trace_index}] decision 不合法：{decision}")
        candidates = trace.get("candidates", [])
        if not isinstance(candidates, list):
            errors.append(f"sourceTraceResults[{trace_index}].candidates 必须是数组。")
            candidates = []

        supporting_candidates = 0
        related_candidates = 0
        for candidate_index, candidate in enumerate(candidates, 1):
            label = f"sourceTraceResults[{trace_index}].candidates[{candidate_index}]"
            if not isinstance(candidate, dict):
                errors.append(f"{label} 必须是对象。")
                continue
            require_fields(candidate, ["paperId", "matchType", "matchSnippet", "supportStatus", "confidence"], label, errors)
            require_keys(candidate, ["quoteLocation", "sourceLocator", "evidenceLevel"], label, errors)
            paper_id = candidate.get("paperId")
            if paper_id:
                candidate_paper_ids.add(paper_id)
            if candidate.get("matchType") not in MATCH_TYPES:
                errors.append(f"{label} matchType 不合法：{candidate.get('matchType')}")
            if candidate.get("supportStatus") not in SUPPORT_STATUSES:
                errors.append(f"{label} supportStatus 不合法：{candidate.get('supportStatus')}")
            if candidate.get("confidence") not in CONFIDENCES:
                errors.append(f"{label} confidence 不合法：{candidate.get('confidence')}")
            if candidate.get("evidenceLevel") not in EVIDENCE_LEVELS:
                errors.append(f"{label} evidenceLevel 不合法：{candidate.get('evidenceLevel')}")
            locator = candidate.get("sourceLocator", {})
            if not isinstance(locator, dict):
                errors.append(f"{label}.sourceLocator 必须是对象。")
            else:
                require_fields(locator, ["locationType", "locator", "confidence"], f"{label}.sourceLocator", errors)
            if candidate.get("supportStatus") == "supports":
                supporting_candidates += 1
                require_fields(candidate, ["evidenceCardId", "quoteLocation"], label, errors)
                if candidate.get("matchType") in {"title", "metadata"}:
                    errors.append(f"{label} 不能仅凭 title/metadata 判定 supports。")
                if paper_id not in known_papers and not non_empty(candidate.get("citation")):
                    errors.append(f"{label} supports 候选缺少真实文献锚点：{paper_id}")
                query_terms = critical_terms(str(trace.get("queryText", "")))
                snippet_terms = critical_terms(str(candidate.get("matchSnippet", "")))
                if not query_terms.issubset(snippet_terms):
                    missing = sorted(query_terms - snippet_terms)
                    errors.append(f"{label} supports 缺少查询关键术语证据：{missing}")
            elif candidate.get("supportStatus") == "related_only":
                related_candidates += 1

        if decision == "verified_source_found":
            verified_trace_count += 1
            if supporting_candidates == 0:
                errors.append(f"sourceTraceResults[{trace_index}] 判定 verified_source_found 但没有 supports 候选。")
        if decision in {"candidate_source_found", "related_sources_only"} and supporting_candidates > 0:
            errors.append(f"sourceTraceResults[{trace_index}] {decision} 不能包含 supports 候选。")
        if decision in {"candidate_source_found", "related_sources_only"} and related_candidates == 0:
            errors.append(f"sourceTraceResults[{trace_index}] {decision} 至少需要一个 related_only 候选。")
        if decision == "no_source_found" and candidates:
            warnings.append(f"sourceTraceResults[{trace_index}] no_source_found 通常不应保留候选，请确认是否应为 related_sources_only。")
        for candidate in candidates:
            if not isinstance(candidate, dict) or candidate.get("matchType") != "pedascope_claim_candidate":
                continue
            if candidate.get("evidenceLevel") != "metadata_verified" or candidate.get("quoteLocation") != "metadata":
                errors.append(f"sourceTraceResults[{trace_index}] PedaScope 候选必须保持 metadata_verified/metadata。")
            if candidate.get("rawEvidenceReturned") is not False:
                errors.append(f"sourceTraceResults[{trace_index}] PedaScope 候选不得声称返回原文证据。")

    usable_evidence_cards = handoff.get("usableEvidenceCards", [])
    if not isinstance(usable_evidence_cards, list):
        errors.append("handoff.usableEvidenceCards 必须是数组。")
        usable_evidence_cards = []
    valid_card_ids = validate_evidence_cards(usable_evidence_cards, known_papers, candidate_paper_ids, errors)

    for index, candidate in enumerate(bibliographic_candidates, 1):
        if not isinstance(candidate, dict):
            errors.append(f"bibliographicCandidates[{index}] 必须是对象。")
            continue
        require_fields(candidate, ["paperId", "title", "textAvailability", "evidenceLevel", "limits"], f"bibliographicCandidates[{index}]", errors)
        if candidate.get("textAvailability") != "metadata":
            errors.append(f"bibliographicCandidates[{index}] 必须保持 textAvailability=metadata。")
        if candidate.get("evidenceLevel") != "metadata_verified":
            errors.append(f"bibliographicCandidates[{index}] 必须保持 evidenceLevel=metadata_verified。")
        if candidate.get("paperId") not in candidate_paper_ids and candidate.get("paperId") not in known_papers:
            errors.append(f"bibliographicCandidates[{index}] 未出现在查源候选或文献记录中：{candidate.get('paperId')}")

    if any(trace.get("decision") in {"candidate_source_found", "related_sources_only", "no_source_found"} for trace in source_trace_results if isinstance(trace, dict)):
        if not any(trace.get("decision") == "verified_source_found" for trace in source_trace_results if isinstance(trace, dict)) and usable_evidence_cards:
            errors.append("未找到 verified_source_found 时不得输出 usableEvidenceCards。")

    supported_claim_count = 0
    needs_evidence_count = 0
    for index, check in enumerate(claim_checks, 1):
        if not isinstance(check, dict):
            errors.append(f"claimChecks[{index}] 必须是对象。")
            continue
        require_fields(check, ["claimId", "claimText", "status", "recommendedRewrite"], f"claimChecks[{index}]", errors)
        require_keys(check, ["matchedEvidenceCards", "riskNotes"], f"claimChecks[{index}]", errors)
        status = check.get("status")
        if status not in CLAIM_STATUSES:
            errors.append(f"claimChecks[{index}] status 不合法：{status}")
        if status == "supported":
            supported_claim_count += 1
        if status in {"needs_evidence", "unsupported"}:
            needs_evidence_count += 1
        matched = check.get("matchedEvidenceCards", [])
        if not isinstance(matched, list):
            errors.append(f"claimChecks[{index}].matchedEvidenceCards 必须是数组。")
            matched = []
        if status in {"supported", "partially_supported"} and not matched:
            errors.append(f"claimChecks[{index}] {status} 必须引用 matchedEvidenceCards。")
        for card_id in matched:
            if card_id not in valid_card_ids:
                errors.append(f"claimChecks[{index}] 引用了不存在或不可用的 evidenceCard：{card_id}")

    structure_issue_count, missing_abstract_count = validate_structure_diagnosis(structure_diagnosis, errors)
    revision_count, added_fact_count, needs_evidence_revision_count = validate_revision_suggestions(revision_suggestions, errors)
    citation_check_count, citation_ready_count, citation_warning_count = validate_citation_checks(citation_checks, known_papers, valid_card_ids, errors)
    insertion_count, pending_confirmation_count = validate_insertion_suggestions(insertion_suggestions, claim_checks, citation_checks if isinstance(citation_checks, list) else [], valid_card_ids, verified_trace_count, errors)
    outline_section_count = validate_outline(outline, errors)
    draft_section_count = validate_document_draft(document_draft, errors)
    local_rewrite_count = validate_local_rewrite(local_rewrite, errors)
    revision_summary = handoff.get("paperRevisionSummary", {})
    if isinstance(revision_summary, dict):
        if revision_summary.get("addedFacts") not in (None, added_fact_count):
            errors.append("handoff.paperRevisionSummary.addedFacts 与实际不一致。")
        if revision_summary.get("revisionSuggestionCount") not in (None, revision_count):
            errors.append("handoff.paperRevisionSummary.revisionSuggestionCount 与实际不一致。")
        if revision_summary.get("needsEvidenceRevisionCount") not in (None, needs_evidence_revision_count):
            errors.append("handoff.paperRevisionSummary.needsEvidenceRevisionCount 与实际不一致。")
        if revision_summary.get("citationCheckCount") not in (None, citation_check_count):
            errors.append("handoff.paperRevisionSummary.citationCheckCount 与实际不一致。")
        if revision_summary.get("insertionSuggestionCount") not in (None, insertion_count):
            errors.append("handoff.paperRevisionSummary.insertionSuggestionCount 与实际不一致。")
        if revision_summary.get("draftSectionCount") not in (None, draft_section_count):
            errors.append("handoff.paperRevisionSummary.draftSectionCount 与实际不一致。")
    else:
        errors.append("handoff.paperRevisionSummary 必须是对象。")

    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict):
        if metrics.get("claimCount") not in (None, len(claim_checks)):
            errors.append("qualityReport.metrics.claimCount 与实际不一致。")
        if metrics.get("supportedClaimCount") not in (None, supported_claim_count):
            errors.append("qualityReport.metrics.supportedClaimCount 与实际不一致。")
        if metrics.get("needsEvidenceCount") not in (None, needs_evidence_count):
            errors.append("qualityReport.metrics.needsEvidenceCount 与实际不一致。")
        if metrics.get("sourceTraceHitCount") not in (None, verified_trace_count):
            errors.append("qualityReport.metrics.sourceTraceHitCount 与实际不一致。")
        if metrics.get("citationFormatWarnings") not in (None, len(citation_warnings)):
            errors.append("qualityReport.metrics.citationFormatWarnings 与实际不一致。")
        if metrics.get("structureIssueCount") not in (None, structure_issue_count):
            errors.append("qualityReport.metrics.structureIssueCount 与实际不一致。")
        if metrics.get("missingAbstractElementCount") not in (None, missing_abstract_count):
            errors.append("qualityReport.metrics.missingAbstractElementCount 与实际不一致。")
        if metrics.get("revisionSuggestionCount") not in (None, revision_count):
            errors.append("qualityReport.metrics.revisionSuggestionCount 与实际不一致。")
        if metrics.get("addedFactCount") not in (None, added_fact_count):
            errors.append("qualityReport.metrics.addedFactCount 与实际不一致。")
        if metrics.get("needsEvidenceRevisionCount") not in (None, needs_evidence_revision_count):
            errors.append("qualityReport.metrics.needsEvidenceRevisionCount 与实际不一致。")
        if metrics.get("citationCheckCount") not in (None, citation_check_count):
            errors.append("qualityReport.metrics.citationCheckCount 与实际不一致。")
        if metrics.get("citationReadyCount") not in (None, citation_ready_count):
            errors.append("qualityReport.metrics.citationReadyCount 与实际不一致。")
        if metrics.get("insertionSuggestionCount") not in (None, insertion_count):
            errors.append("qualityReport.metrics.insertionSuggestionCount 与实际不一致。")
        if metrics.get("pendingTeacherConfirmationCount") not in (None, pending_confirmation_count):
            errors.append("qualityReport.metrics.pendingTeacherConfirmationCount 与实际不一致。")
        if metrics.get("outlineSectionCount") not in (None, outline_section_count):
            errors.append("qualityReport.metrics.outlineSectionCount 与实际不一致。")
        if metrics.get("draftSectionCount") not in (None, draft_section_count):
            errors.append("qualityReport.metrics.draftSectionCount 与实际不一致。")
        if metrics.get("localRewriteCount") not in (None, local_rewrite_count):
            errors.append("qualityReport.metrics.localRewriteCount 与实际不一致。")
        if metrics.get("addedFactCount", 0) > 0:
            errors.append("qualityReport.metrics.addedFactCount 必须为 0。")

    task_intent = data.get("taskIntent")
    if task_intent == "outline_generation" and not outline:
        errors.append("taskIntent=outline_generation 时必须输出 result.outline。")
    if task_intent == "chapter_drafting" and not document_draft:
        errors.append("taskIntent=chapter_drafting 时必须输出 result.documentDraft。")
    if task_intent == "local_rewrite" and not local_rewrite:
        errors.append("taskIntent=local_rewrite 时必须输出 result.localRewrite。")

    if data.get("qualityReport", {}).get("status") == "pass" and (structure_issue_count > 0 or needs_evidence_revision_count > 0):
        errors.append("存在结构缺口或需补证据润色建议时，qualityReport.status 不能为 pass。")

    validate_quality_report(data, errors, warnings)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验论文写作助手 JSON 产物。")
    parser.add_argument("output_json", help="待校验 JSON 文件")
    args = parser.parse_args()

    data = load_json(Path(args.output_json))
    errors, warnings = validate(data)
    if errors:
        print("不通过")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"- 警告：{warning}")
        return 1

    print("通过")
    print(f"- 已检查 {args.output_json}")
    print(f"- source_trace 结果数：{len(data.get('result', {}).get('sourceTraceResults', []))}")
    print(f"- 可用证据卡数：{len(data.get('handoff', {}).get('usableEvidenceCards', []))}")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
