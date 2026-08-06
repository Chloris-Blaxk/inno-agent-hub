#!/usr/bin/env python3
"""校验项目申报助手 Skill 的 JSON 产物。"""
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


SKILL_ID = "project-proposal-skill"
ALLOWED_INTENTS = {"fact_extraction", "project_application", "closing_report", "achievement_report", "budget_check", "document_set"}
DOCUMENT_TYPES = {"project_application", "closing_report", "achievement_report"}
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
FACT_STATUSES = {"confirmed", "inferred", "missing", "conflict", "needs_user_confirmation"}
CONFIDENCES = {"high", "medium", "low"}
SECTION_STATUSES = {"draft", "needs_evidence", "needs_user_confirmation"}
PRESENTATION_STATUSES = {"derived_from_fact", "needs_evidence", "draft"}
AMOUNT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(万元|元)")
FORBIDDEN_ASSURANCE_PATTERN = re.compile(r"(保证|确保|预计|大概率).{0,8}(立项|中标|获批|通过)")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_json(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "references" / name
    return load_json(path)


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


def template_for(document_type: str) -> dict[str, Any] | None:
    templates = load_reference_json("document-templates.json").get("templates", [])
    for template in templates:
        if template.get("documentType") == document_type:
            return template
    return None


def required_fact_fields() -> set[str]:
    return set(load_reference_json("project-fact-schema.json").get("requiredFields", []))


def text_from_document(document: dict[str, Any]) -> str:
    parts: list[str] = []
    for section in document.get("sections", []):
        if isinstance(section, dict):
            parts.append(str(section.get("title", "")))
            parts.append(str(section.get("content", "")))
    return "\n".join(parts)


def contains_amount(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(AMOUNT_PATTERN.search(value))
    if isinstance(value, list):
        return any(contains_amount(item) for item in value)
    if isinstance(value, dict):
        return any(contains_amount(item) for item in value.values())
    return False


def required_section_coverage(document: dict[str, Any]) -> float:
    template = template_for(str(document.get("documentType", "")))
    expected_required = {section.get("sectionId") for section in template.get("sections", []) if section.get("required")}
    if not expected_required:
        return 1.0
    actual_section_ids = {section.get("sectionId") for section in document.get("sections", []) if isinstance(section, dict)}
    return round(len(expected_required.intersection(actual_section_ids)) / len(expected_required), 2)


def validate_document(
    document: dict[str, Any],
    fact_ids: set[str],
    budget_fact_has_amount: bool,
    errors: list[str],
    *,
    label: str = "documentDraft",
) -> float | None:
    require_fields(document, ["documentId", "documentType", "title", "sections"], label, errors)
    document_type = document.get("documentType")
    sections = document.get("sections", [])
    if document_type not in DOCUMENT_TYPES:
        errors.append(f"{label}.documentType 不合法：{document_type}")
    if not isinstance(sections, list):
        errors.append(f"{label}.sections 必须是数组。")
        sections = []
    template = template_for(str(document_type))
    if not template:
        errors.append(f"未找到 documentType 对应模板：{document_type}")
    else:
        actual_section_ids = {section.get("sectionId") for section in sections if isinstance(section, dict)}
        actual_titles = {section.get("title") for section in sections if isinstance(section, dict)}
        missing_sections = []
        for section in template.get("sections", []):
            if section.get("required") and section.get("sectionId") not in actual_section_ids and section.get("title") not in actual_titles:
                missing_sections.append(section.get("title"))
        if missing_sections:
            errors.append(f"{label} 缺少模板必填章节：{missing_sections}")

    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict):
            errors.append(f"{label}.sections[{index}] 必须是对象。")
            continue
        require_fields(section, ["sectionId", "title", "required", "content", "status"], f"{label}.sections[{index}]", errors)
        require_keys(section, ["factRefs"], f"{label}.sections[{index}]", errors)
        if section.get("status") not in SECTION_STATUSES:
            errors.append(f"{label}.sections[{index}] status 不合法：{section.get('status')}")
        fact_refs = section.get("factRefs", [])
        if not isinstance(fact_refs, list):
            errors.append(f"{label}.sections[{index}].factRefs 必须是数组。")
            fact_refs = []
        for fact_ref in fact_refs:
            if fact_ref not in fact_ids:
                errors.append(f"{label}.sections[{index}] 引用了不存在的 factId：{fact_ref}")
        if section.get("required") is True and section.get("status") == "draft" and not fact_refs:
            errors.append(f"{label}.sections[{index}] 必填章节处于 draft 时必须引用 factRefs。")

    document_text = text_from_document(document)
    if FORBIDDEN_ASSURANCE_PATTERN.search(document_text):
        errors.append(f"{label} 中出现立项/中标/获批概率承诺，项目申报助手不得预测或保证结果。")
    if contains_amount(document_text) and not budget_fact_has_amount:
        errors.append(f"{label} 出现具体金额，但 ProjectFactTable 没有对应预算金额事实。")
    return required_section_coverage(document)


def validate_document_set(
    result: dict[str, Any],
    fact_ids: set[str],
    budget_fact_has_amount: bool,
    data: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> list[dict[str, Any]]:
    document_set = result.get("documentSet", {})
    if not isinstance(document_set, dict) or not document_set:
        return []
    require_fields(document_set, ["setId", "generationMode", "documents"], "documentSet", errors)
    documents = document_set.get("documents", [])
    if not isinstance(documents, list) or not documents:
        errors.append("documentSet.documents 必须是非空数组。")
        return []
    doc_types: list[str] = []
    coverages: list[float] = []
    document_ids: set[str] = set()
    for index, document in enumerate(documents, 1):
        if not isinstance(document, dict):
            errors.append(f"documentSet.documents[{index}] 必须是对象。")
            continue
        doc_id = document.get("documentId")
        if doc_id in document_ids:
            errors.append(f"documentSet.documents[{index}] documentId 重复：{doc_id}")
        if doc_id:
            document_ids.add(doc_id)
        doc_type = document.get("documentType")
        if isinstance(doc_type, str):
            doc_types.append(doc_type)
        coverage = validate_document(document, fact_ids, budget_fact_has_amount, errors, label=f"documentSet.documents[{index}]")
        if coverage is not None:
            coverages.append(coverage)
    if len(set(doc_types)) != len(doc_types):
        errors.append("documentSet 中 documentType 不能重复。")
    if data.get("taskIntent") == "document_set" and set(doc_types) != DOCUMENT_TYPES:
        errors.append(f"document_set 必须同时包含三类文档：{sorted(DOCUMENT_TYPES)}")
    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict):
        if metrics.get("documentCount") not in (None, len(documents)):
            errors.append("qualityReport.metrics.documentCount 与 documentSet.documents 数量不一致。")
        average_coverage = round(sum(coverages) / len(coverages), 2) if coverages else 1.0
        if metrics.get("templateSectionCoverage") not in (None, average_coverage, int(average_coverage * 100)):
            errors.append("qualityReport.metrics.templateSectionCoverage 与文档集必填章节覆盖率不一致。")
    if document_set.get("generationMode") != "three_format_document_set":
        warnings.append("documentSet.generationMode 建议标记为 three_format_document_set。")
    return documents


def validate_cross_document_report(
    data: dict[str, Any],
    documents: list[dict[str, Any]],
    fact_by_id: dict[str, dict[str, Any]],
    fact_by_field: dict[str, list[Any]],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not documents:
        return
    result = data.get("result", {})
    report = result.get("crossDocumentConsistencyReport")
    if not isinstance(report, dict) or not report:
        if len(documents) > 1:
            errors.append("存在多文档输出时，必须包含 crossDocumentConsistencyReport。")
        return
    require_keys(report, ["status", "documentsChecked", "sharedFactFields", "conflicts", "missingSharedFields"], "crossDocumentConsistencyReport", errors)
    require_fields(report, ["status", "documentsChecked", "sharedFactFields"], "crossDocumentConsistencyReport", errors)
    if report.get("status") not in {"pass", "warn"}:
        errors.append(f"crossDocumentConsistencyReport.status 不合法：{report.get('status')}")
    document_types = [document.get("documentType") for document in documents if isinstance(document, dict)]
    if sorted(report.get("documentsChecked", [])) != sorted(document_types):
        errors.append("crossDocumentConsistencyReport.documentsChecked 与实际文档类型不一致。")

    shared_fields = report.get("sharedFactFields", [])
    if not isinstance(shared_fields, list):
        errors.append("crossDocumentConsistencyReport.sharedFactFields 必须是数组。")
        shared_fields = []
    for index, item in enumerate(shared_fields, 1):
        if not isinstance(item, dict):
            errors.append(f"sharedFactFields[{index}] 必须是对象。")
            continue
        require_keys(item, ["field", "value", "sourceRefs", "usedInDocuments", "requiredByDocuments", "status"], f"sharedFactFields[{index}]", errors)
        if item.get("status") not in {"consistent", "needs_user_confirmation"}:
            errors.append(f"sharedFactFields[{index}].status 不合法：{item.get('status')}")
        if item.get("status") == "consistent":
            require_fields(item, ["field", "value", "sourceRefs", "usedInDocuments", "requiredByDocuments"], f"sharedFactFields[{index}]", errors)
        fact_id = item.get("factId")
        if fact_id is not None:
            if fact_id not in fact_by_id:
                errors.append(f"sharedFactFields[{index}] factId 不存在：{fact_id}")
            else:
                fact = fact_by_id[fact_id]
                if fact.get("field") != item.get("field"):
                    errors.append(f"sharedFactFields[{index}] field 与 factId 对应字段不一致。")
                if json.dumps(fact.get("value"), ensure_ascii=False, sort_keys=True) != json.dumps(item.get("value"), ensure_ascii=False, sort_keys=True):
                    errors.append(f"sharedFactFields[{index}] value 与 ProjectFactTable 不一致。")
        for doc_type in item.get("usedInDocuments", []):
            if doc_type not in document_types:
                errors.append(f"sharedFactFields[{index}] usedInDocuments 包含不存在文档：{doc_type}")

    missing_shared = report.get("missingSharedFields", [])
    conflicts = report.get("conflicts", [])
    if not isinstance(missing_shared, list):
        errors.append("crossDocumentConsistencyReport.missingSharedFields 必须是数组。")
        missing_shared = []
    if not isinstance(conflicts, list):
        errors.append("crossDocumentConsistencyReport.conflicts 必须是数组。")
        conflicts = []
    if report.get("status") == "pass" and (missing_shared or conflicts or report.get("sectionWarnings")):
        errors.append("crossDocumentConsistencyReport 存在缺失/冲突/章节警告时 status 不能为 pass。")

    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict):
        if metrics.get("crossDocumentConflictCount") not in (None, len(conflicts)):
            errors.append("qualityReport.metrics.crossDocumentConflictCount 与报告不一致。")
        if metrics.get("crossDocumentMissingSharedFieldCount") not in (None, len(missing_shared)):
            errors.append("qualityReport.metrics.crossDocumentMissingSharedFieldCount 与报告不一致。")
    if len(documents) > 1 and not shared_fields:
        warnings.append("crossDocumentConsistencyReport.sharedFactFields 为空，无法证明三份文档共享事实一致。")


def validate_presentation_support(result: dict[str, Any], documents: list[dict[str, Any]], fact_ids: set[str], errors: list[str]) -> None:
    needs_support = any(document.get("documentType") == "achievement_report" for document in documents if isinstance(document, dict))
    support = result.get("presentationSupport", {})
    if not needs_support:
        return
    if not isinstance(support, dict) or not support:
        errors.append("成果汇报任务必须包含 presentationSupport。")
        return
    require_fields(support, ["timelineItems", "chartSuggestions", "achievementHighlights"], "presentationSupport", errors)
    for group_name in ("timelineItems", "chartSuggestions", "achievementHighlights"):
        items = support.get(group_name, [])
        if not isinstance(items, list):
            errors.append(f"presentationSupport.{group_name} 必须是数组。")
            continue
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                errors.append(f"presentationSupport.{group_name}[{index}] 必须是对象。")
                continue
            status = item.get("status")
            if status not in PRESENTATION_STATUSES:
                errors.append(f"presentationSupport.{group_name}[{index}].status 不合法：{status}")
            fact_refs = item.get("factRefs", [])
            if not isinstance(fact_refs, list):
                errors.append(f"presentationSupport.{group_name}[{index}].factRefs 必须是数组。")
                fact_refs = []
            for fact_ref in fact_refs:
                if fact_ref not in fact_ids:
                    errors.append(f"presentationSupport.{group_name}[{index}] 引用了不存在的 factId：{fact_ref}")
            if status == "derived_from_fact" and not fact_refs:
                errors.append(f"presentationSupport.{group_name}[{index}] derived_from_fact 必须引用 factRefs。")


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
    if not isinstance(result, dict):
        errors.append("result 必须是对象。")
        return errors, warnings

    fact_table = result.get("projectFactTable")
    if not isinstance(fact_table, dict):
        errors.append("result.projectFactTable 必须是对象。")
        return errors, warnings

    require_fields(fact_table, ["projectId", "facts"], "projectFactTable", errors)
    require_keys(fact_table, ["missingFields", "conflicts"], "projectFactTable", errors)
    facts = fact_table.get("facts", [])
    missing_fields = fact_table.get("missingFields", [])
    conflicts = fact_table.get("conflicts", [])
    if not isinstance(facts, list) or not facts:
        errors.append("projectFactTable.facts 必须是非空数组。")
        facts = []
    if not isinstance(missing_fields, list):
        errors.append("projectFactTable.missingFields 必须是数组。")
        missing_fields = []
    if not isinstance(conflicts, list):
        errors.append("projectFactTable.conflicts 必须是数组。")
        conflicts = []

    fact_ids: set[str] = set()
    fact_by_id: dict[str, dict[str, Any]] = {}
    fact_fields: dict[str, list[Any]] = {}
    budget_fact_has_amount = False
    budget_field_has_amount = False
    for index, fact in enumerate(facts, 1):
        if not isinstance(fact, dict):
            errors.append(f"facts[{index}] 必须是对象。")
            continue
        require_fields(fact, ["factId", "field", "value", "sourceRefs", "confidence", "status"], f"facts[{index}]", errors)
        fact_id = fact.get("factId")
        field = fact.get("field")
        status = fact.get("status")
        if fact_id in fact_ids:
            errors.append(f"facts[{index}] factId 重复：{fact_id}")
        if fact_id:
            fact_ids.add(fact_id)
            fact_by_id[fact_id] = fact
        if status not in FACT_STATUSES:
            errors.append(f"facts[{index}] status 不合法：{status}")
        if fact.get("confidence") not in CONFIDENCES:
            errors.append(f"facts[{index}] confidence 不合法：{fact.get('confidence')}")
        source_refs = fact.get("sourceRefs", [])
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"facts[{index}] 必须有非空 sourceRefs，不能无来源写入事实。")
        if isinstance(source_refs, list) and any(str(ref).lower() in {"model", "ai", "generated", "assumption"} for ref in source_refs):
            errors.append(f"facts[{index}] sourceRefs 不能使用模型生成占位来源。")
        if isinstance(source_refs, list) and any("pedascope" in str(ref).lower() or str(ref).startswith("paper_") for ref in source_refs):
            errors.append(f"facts[{index}] 不得把 PedaScope 题录候选写入 ProjectFactTable.facts。")
        if isinstance(field, str):
            fact_fields.setdefault(field, []).append(fact.get("value"))
            if field.startswith("outcomes.actual") and status != "confirmed":
                errors.append(f"facts[{index}] 实际成果必须来自已确认材料，不能标记为 {status}。")
            if field.startswith("budget.") and contains_amount(fact.get("value")):
                budget_fact_has_amount = True
                if field == "budget.total":
                    budget_field_has_amount = True

    background_candidates = result.get("literatureBackgroundCandidates", [])
    if not isinstance(background_candidates, list):
        errors.append("result.literatureBackgroundCandidates 必须是数组。")
        background_candidates = []
    for index, candidate in enumerate(background_candidates, 1):
        if not isinstance(candidate, dict):
            errors.append(f"literatureBackgroundCandidates[{index}] 必须是对象。")
            continue
        require_fields(candidate, ["paperId", "title", "relation", "textAvailability", "evidenceLevel", "limits"], f"literatureBackgroundCandidates[{index}]", errors)
        if candidate.get("relation") != "background_candidate":
            errors.append(f"literatureBackgroundCandidates[{index}].relation 必须为 background_candidate。")
        if candidate.get("textAvailability") != "metadata" or candidate.get("evidenceLevel") != "metadata_verified":
            errors.append(f"literatureBackgroundCandidates[{index}] 必须保持 metadata / metadata_verified。")

    missing_field_set = {item.get("field") if isinstance(item, dict) else item for item in missing_fields}
    conflict_field_set = {item.get("field") for item in conflicts if isinstance(item, dict)}
    for field in sorted(required_fact_fields()):
        if field not in fact_fields and field not in missing_field_set and field not in conflict_field_set:
            errors.append(f"必填事实字段未在 facts、missingFields 或 conflicts 中说明：{field}")

    for field, values in fact_fields.items():
        normalized = {json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values}
        if len(normalized) > 1 and field not in conflict_field_set:
            errors.append(f"字段 {field} 出现多个不同值，但未写入 conflicts。")

    for index, conflict in enumerate(conflicts, 1):
        if not isinstance(conflict, dict):
            errors.append(f"conflicts[{index}] 必须是对象。")
            continue
        require_fields(conflict, ["field", "values", "sourceRefs", "resolution"], f"conflicts[{index}]", errors)
        if conflict.get("resolution") != "needs_user_confirmation":
            warnings.append(f"conflicts[{index}] 建议将 resolution 标记为 needs_user_confirmation。")

    document = result.get("documentDraft", {})
    document_set_documents = validate_document_set(result, fact_ids, budget_fact_has_amount, data, errors, warnings)
    documents: list[dict[str, Any]] = []
    if isinstance(document, dict) and document:
        coverage = validate_document(document, fact_ids, budget_fact_has_amount, errors, label="documentDraft")
        if coverage is not None:
            metrics = data.get("qualityReport", {}).get("metrics", {})
            if not document_set_documents and isinstance(metrics, dict) and metrics.get("templateSectionCoverage") not in (None, coverage, int(coverage * 100)):
                errors.append("qualityReport.metrics.templateSectionCoverage 与模板必填章节覆盖率不一致。")
        documents.append(document)
    documents.extend(document_set_documents)
    if data.get("taskIntent") != "fact_extraction" and not documents:
        errors.append("生成文档类任务必须包含 result.documentDraft 或 result.documentSet。")
    validate_cross_document_report(data, documents, fact_by_id, fact_fields, errors, warnings)
    validate_presentation_support(result, documents, fact_ids, errors)

    budget_report = result.get("budgetReport", {})
    budget_warnings = []
    if isinstance(budget_report, dict) and contains_amount(budget_report) and not budget_fact_has_amount:
        errors.append("budgetReport 出现具体金额，但 ProjectFactTable 没有对应预算金额事实。")
    if isinstance(budget_report, dict):
        budget_warnings = budget_report.get("warnings", [])
        if not isinstance(budget_warnings, list):
            errors.append("budgetReport.warnings 必须是数组。")
            budget_warnings = []
        budget_items = budget_report.get("items", [])
        if not isinstance(budget_items, list):
            errors.append("budgetReport.items 必须是数组。")
            budget_items = []
        if contains_amount(budget_report.get("totalAmount")) and not budget_field_has_amount:
            errors.append("budgetReport.totalAmount 出现金额，但 ProjectFactTable 没有 budget.total 事实。")
        for index, item in enumerate(budget_items, 1):
            if not isinstance(item, dict):
                errors.append(f"budgetReport.items[{index}] 必须是对象。")
                continue
            require_fields(item, ["category", "amount", "purpose", "sourceRefs", "status"], f"budgetReport.items[{index}]", errors)
            if item.get("status") not in {"confirmed", "needs_user_confirmation"}:
                errors.append(f"budgetReport.items[{index}] status 不合法：{item.get('status')}")
            source_refs = item.get("sourceRefs", [])
            if not isinstance(source_refs, list) or not source_refs:
                errors.append(f"budgetReport.items[{index}] sourceRefs 必须是非空数组。")

    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict):
        if metrics.get("factCount") not in (None, len(facts)):
            errors.append("qualityReport.metrics.factCount 与实际不一致。")
        if metrics.get("conflictCount") not in (None, len(conflicts)):
            errors.append("qualityReport.metrics.conflictCount 与实际不一致。")
        if metrics.get("missingFieldCount") not in (None, len(missing_fields)):
            errors.append("qualityReport.metrics.missingFieldCount 与实际不一致。")
        if isinstance(budget_warnings, list) and metrics.get("budgetWarningCount") not in (None, len(budget_warnings)):
            errors.append("qualityReport.metrics.budgetWarningCount 与实际不一致。")

    quality = data.get("qualityReport", {})
    if isinstance(quality, dict) and quality.get("status") == "pass":
        if missing_fields:
            errors.append("存在 missingFields 时 qualityReport.status 不能为 pass。")
        if conflicts:
            errors.append("存在 conflicts 时 qualityReport.status 不能为 pass。")
        if budget_warnings:
            errors.append("存在 budgetReport.warnings 时 qualityReport.status 不能为 pass。")
        cross_report = result.get("crossDocumentConsistencyReport", {})
        if isinstance(cross_report, dict) and cross_report.get("status") == "warn":
            errors.append("跨文档一致性存在 warning 时 qualityReport.status 不能为 pass。")

    validate_quality_report(data, errors, warnings)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验项目申报助手 JSON 产物。")
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
    print(f"- 事实数：{len(data.get('result', {}).get('projectFactTable', {}).get('facts', []))}")
    print(f"- 冲突数：{len(data.get('result', {}).get('projectFactTable', {}).get('conflicts', []))}")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
