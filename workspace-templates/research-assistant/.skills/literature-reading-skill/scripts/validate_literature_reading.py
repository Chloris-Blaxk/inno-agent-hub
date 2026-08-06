#!/usr/bin/env python3
"""校验文献阅读助手 Skill 的 JSON 产物。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

COMMON_ROOT = Path(__file__).resolve().parents[1].parent / "research-line-common"
sys.path.insert(0, str(COMMON_ROOT))
from data_source_report import validate_data_source_report  # noqa: E402
from evidence_policy import (  # noqa: E402
    EVIDENCE_LEVELS,
    SOURCE_STATUSES,
    SUPPORT_TYPES,
    TEXT_AVAILABILITY,
    can_create_evidence_card,
    evidence_level_matches_availability,
    requires_limits_for_abstract_support,
)


SKILL_ID = "literature-reading-skill"
ALLOWED_INTENTS = {"literature_discovery", "quick_read", "deep_read", "compare_papers", "evidence_carding"}
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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

    records = result.get("literatureRecords", [])
    corpus_search_report = result.get("corpusSearchReport", {})
    evidence_cards = result.get("evidenceCards", [])
    handoff_evidence_cards = data.get("handoff", {}).get("evidenceCards", []) if isinstance(data.get("handoff"), dict) else []
    quick_cards = result.get("quickReadCards", [])
    deep_cards = result.get("deepReadCards", [])
    deep_read_sessions = result.get("deepReadSessions", [])
    comparison_matrix = result.get("comparisonMatrix", [])
    bibliographic_candidates = result.get("bibliographicCandidates", [])
    if not isinstance(records, list) or not records:
        errors.append("result.literatureRecords 必须是非空数组。")
        records = []
    if not isinstance(corpus_search_report, dict) or not corpus_search_report:
        errors.append("result.corpusSearchReport 必须是对象。")
        corpus_search_report = {}
    if not isinstance(evidence_cards, list):
        errors.append("result.evidenceCards 必须是数组。")
        evidence_cards = []
    if not isinstance(handoff_evidence_cards, list):
        errors.append("handoff.evidenceCards 必须是数组。")
        handoff_evidence_cards = []
    if not isinstance(comparison_matrix, list):
        errors.append("result.comparisonMatrix 必须是数组。")
        comparison_matrix = []
    if not isinstance(deep_read_sessions, list):
        errors.append("result.deepReadSessions 必须是数组。")
        deep_read_sessions = []
    has_mock_deep_read = any(isinstance(session, dict) and session.get("_mock") for session in deep_read_sessions)

    record_index: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            errors.append(f"literatureRecords[{index}] 必须是对象。")
            continue
        require_fields(record, ["paperId", "title", "authors", "year", "sourceStatus", "textAvailability", "evidenceLevel"], f"literatureRecords[{index}]", errors)
        if record.get("sourceStatus") not in SOURCE_STATUSES:
            errors.append(f"literatureRecords[{index}] sourceStatus 不合法：{record.get('sourceStatus')}")
        if record.get("textAvailability") not in TEXT_AVAILABILITY:
            errors.append(f"literatureRecords[{index}] textAvailability 不合法：{record.get('textAvailability')}")
        if record.get("evidenceLevel") not in EVIDENCE_LEVELS:
            errors.append(f"literatureRecords[{index}] evidenceLevel 不合法：{record.get('evidenceLevel')}")
        record_index[record.get("paperId")] = record

    if corpus_search_report:
        require_fields(corpus_search_report, ["indexName", "indexSource", "simulatedCorpusSize", "query", "candidateCount", "returnedCount", "rankingSignals", "topHits"], "corpusSearchReport", errors)
        if corpus_search_report.get("indexSource") not in {"local_mock_index", "multi_backend", "authorized_database", "external_metadata", "pedascope_kb"}:
            errors.append(f"corpusSearchReport.indexSource 不合法：{corpus_search_report.get('indexSource')}")
        if corpus_search_report.get("indexSource") == "multi_backend":
            source_backends = corpus_search_report.get("sourceBackends", [])
            data_sources = corpus_search_report.get("dataSources", [])
            if not isinstance(source_backends, list) or len(source_backends) < 2:
                errors.append("corpusSearchReport.indexSource=multi_backend 时必须包含至少 2 个 sourceBackends。")
            if not isinstance(data_sources, list) or len(data_sources) < 2:
                errors.append("corpusSearchReport.indexSource=multi_backend 时必须包含至少 2 个 dataSources。")
        if not isinstance(corpus_search_report.get("simulatedCorpusSize"), int) or corpus_search_report.get("simulatedCorpusSize") < len(records):
            errors.append("corpusSearchReport.simulatedCorpusSize 必须不小于返回文献数。")
        if not isinstance(corpus_search_report.get("candidateCount"), int) or corpus_search_report.get("candidateCount") < len(records):
            errors.append("corpusSearchReport.candidateCount 必须不小于返回文献数。")
        top_hits = corpus_search_report.get("topHits", [])
        if not isinstance(top_hits, list) or not top_hits:
            errors.append("corpusSearchReport.topHits 必须是非空数组。")
            top_hits = []
        if corpus_search_report.get("returnedCount") != len(top_hits):
            errors.append("corpusSearchReport.returnedCount 与 topHits 数量不一致。")
        if corpus_search_report.get("returnedCount") != len(records):
            errors.append("corpusSearchReport.returnedCount 应与 literatureRecords 数量一致。")
        for index, hit in enumerate(top_hits, 1):
            label = f"corpusSearchReport.topHits[{index}]"
            if not isinstance(hit, dict):
                errors.append(f"{label} 必须是对象。")
                continue
            require_fields(hit, ["paperId", "score", "textAvailability", "sourceStatus", "selectionReason", "source"], label, errors)
            require_keys(hit, ["matchedKeywords"], label, errors)
            if hit.get("paperId") not in record_index:
                errors.append(f"{label} 引用了不在 literatureRecords 中的 paperId：{hit.get('paperId')}")
            if not isinstance(hit.get("score"), (int, float)) or hit.get("score") < 0:
                errors.append(f"{label}.score 必须是非负数。")
            if hit.get("textAvailability") not in TEXT_AVAILABILITY:
                errors.append(f"{label}.textAvailability 不合法：{hit.get('textAvailability')}")
            if hit.get("sourceStatus") not in SOURCE_STATUSES:
                errors.append(f"{label}.sourceStatus 不合法：{hit.get('sourceStatus')}")
            if not isinstance(hit.get("matchedKeywords", []), list):
                errors.append(f"{label}.matchedKeywords 必须是数组。")

    if not isinstance(bibliographic_candidates, list):
        errors.append("result.bibliographicCandidates 必须是数组。")
        bibliographic_candidates = []
    for index, candidate in enumerate(bibliographic_candidates, 1):
        if not isinstance(candidate, dict):
            errors.append(f"bibliographicCandidates[{index}] 必须是对象。")
            continue
        require_fields(candidate, ["candidateId", "paperId", "title", "relation", "sourceStatus", "textAvailability", "evidenceLevel", "limits"], f"bibliographicCandidates[{index}]", errors)
        if candidate.get("textAvailability") != "metadata":
            errors.append(f"bibliographicCandidates[{index}] 必须保持 textAvailability=metadata。")
        if candidate.get("evidenceLevel") != "metadata_verified":
            errors.append(f"bibliographicCandidates[{index}] 必须保持 evidenceLevel=metadata_verified。")
        if candidate.get("paperId") not in record_index:
            errors.append(f"bibliographicCandidates[{index}] 引用了不存在的 paperId：{candidate.get('paperId')}")
        if not isinstance(candidate.get("limits", []), list) or not candidate.get("limits"):
            errors.append(f"bibliographicCandidates[{index}].limits 必须说明不能直接作为支撑性引用。")

    deep_evidence_refs: list[tuple[str, str]] = []
    for collection_name, cards in [("quickReadCards", quick_cards), ("deepReadCards", deep_cards)]:
        if not isinstance(cards, list):
            errors.append(f"result.{collection_name} 必须是数组。")
            continue
        for index, card in enumerate(cards, 1):
            if not isinstance(card, dict):
                errors.append(f"{collection_name}[{index}] 必须是对象。")
                continue
            require_fields(card, ["cardId", "paperId", "cardType", "evidenceLevel"], f"{collection_name}[{index}]", errors)
            if card.get("paperId") not in record_index:
                errors.append(f"{collection_name}[{index}] 引用了不存在的 paperId：{card.get('paperId')}")
            if collection_name == "deepReadCards":
                require_fields(card, ["researchProblem", "method", "findings", "limitations"], f"{collection_name}[{index}]", errors)
                require_keys(card, ["usableIdeas", "evidenceRefs"], f"{collection_name}[{index}]", errors)
                if card.get("cardType") != "deep":
                    errors.append(f"{collection_name}[{index}] cardType 必须是 deep。")
                record = record_index.get(card.get("paperId"))
                if record and record.get("textAvailability") == "metadata":
                    errors.append(f"{collection_name}[{index}] 不能由 metadata-only 文献生成。")
                if card.get("evidenceLevel") == "metadata_verified":
                    errors.append(f"{collection_name}[{index}] 不能使用 metadata_verified 作为精读证据级别。")
                if not isinstance(card.get("findings"), list) or not card.get("findings"):
                    errors.append(f"{collection_name}[{index}].findings 必须是非空数组。")
                if not isinstance(card.get("limitations"), list) or not card.get("limitations"):
                    errors.append(f"{collection_name}[{index}].limitations 必须是非空数组。")
                evidence_refs = card.get("evidenceRefs", [])
                if not isinstance(evidence_refs, list):
                    errors.append(f"{collection_name}[{index}].evidenceRefs 必须是数组。")
                    evidence_refs = []
                if card.get("mockDegraded") is True:
                    if evidence_refs:
                        errors.append(f"{collection_name}[{index}] mockDegraded=true 时不得包含 evidenceRefs。")
                    limitations_text = "；".join(str(item) for item in card.get("limitations", []))
                    if "mock" not in limitations_text:
                        errors.append(f"{collection_name}[{index}] mockDegraded=true 时 limitations 必须说明 mock 降级风险。")
                for ref in evidence_refs:
                    deep_evidence_refs.append((card.get("cardId", f"deep-{index}"), ref))

    seen_cards: set[str] = set()
    all_evidence_cards = evidence_cards + [card for card in handoff_evidence_cards if isinstance(card, dict) and card.get("cardId") not in {item.get("cardId") for item in evidence_cards if isinstance(item, dict)}]
    for index, card in enumerate(all_evidence_cards, 1):
        if not isinstance(card, dict):
            errors.append(f"evidenceCards[{index}] 必须是对象。")
            continue
        if card.get("cardId") in seen_cards:
            errors.append(f"evidenceCards[{index}] cardId 重复：{card.get('cardId')}")
        seen_cards.add(card.get("cardId"))
        require_fields(card, ["cardId", "claim", "evidenceText", "paperId", "quoteLocation", "supportType", "evidenceLevel"], f"evidenceCards[{index}]", errors)
        paper_id = card.get("paperId")
        record = record_index.get(paper_id)
        if not record:
            errors.append(f"evidenceCards[{index}] 引用了不存在的 paperId：{paper_id}")
            continue
        if not can_create_evidence_card(record.get("textAvailability"), card.get("evidenceLevel")):
            if record.get("textAvailability") == "metadata":
                errors.append(f"evidenceCards[{index}] 不能由 metadata-only 文献生成。")
            else:
                errors.append(f"evidenceCards[{index}] 证据卡不能使用 metadata_verified 作为支撑证据。")
        if card.get("evidenceLevel") in EVIDENCE_LEVELS and not evidence_level_matches_availability(card.get("evidenceLevel"), record.get("textAvailability")):
            errors.append(f"evidenceCards[{index}] evidenceLevel 与文献 textAvailability 不一致。")
        if card.get("supportType") not in SUPPORT_TYPES:
            errors.append(f"evidenceCards[{index}] supportType 不合法：{card.get('supportType')}")
        if card.get("evidenceLevel") not in EVIDENCE_LEVELS:
            errors.append(f"evidenceCards[{index}] evidenceLevel 不合法：{card.get('evidenceLevel')}")
        if requires_limits_for_abstract_support(card.get("evidenceLevel"), card.get("supportType"), record.get("textAvailability")):
            if not non_empty(card.get("limits")):
                errors.append(f"evidenceCards[{index}] 摘要级支撑必须填写 limits。")

    for card_id, evidence_ref in deep_evidence_refs:
        if evidence_ref not in seen_cards:
            errors.append(f"deepReadCards[{card_id}] 引用了不存在的 evidenceRef：{evidence_ref}")

    for index, session in enumerate(deep_read_sessions, 1):
        if not isinstance(session, dict):
            errors.append(f"deepReadSessions[{index}] 必须是对象。")
            continue
        require_fields(session, ["question", "answer", "agent"], f"deepReadSessions[{index}]", errors)
        require_keys(session, ["citations"], f"deepReadSessions[{index}]", errors)
        if not isinstance(session.get("citations", []), list):
            errors.append(f"deepReadSessions[{index}].citations 必须是数组。")
    if has_mock_deep_read:
        if evidence_cards or handoff_evidence_cards:
            errors.append("deepReadSessions 包含 mock 结果时不得生成 result/handoff EvidenceCard。")
        for index, card in enumerate(deep_cards, 1):
            if isinstance(card, dict) and card.get("mockDegraded") is not True:
                errors.append(f"deepReadCards[{index}] 来自 mock deep_read 时必须标注 mockDegraded=true。")

    comparison_row_count = 0
    for matrix_index, matrix in enumerate(comparison_matrix, 1):
        if not isinstance(matrix, dict):
            errors.append(f"comparisonMatrix[{matrix_index}] 必须是对象。")
            continue
        require_fields(matrix, ["matrixId", "topic", "rows"], f"comparisonMatrix[{matrix_index}]", errors)
        rows = matrix.get("rows", [])
        if not isinstance(rows, list) or not rows:
            errors.append(f"comparisonMatrix[{matrix_index}].rows 必须是非空数组。")
            rows = []
        comparison_row_count += len(rows)
        for row_index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                errors.append(f"comparisonMatrix[{matrix_index}].rows[{row_index}] 必须是对象。")
                continue
            require_fields(row, ["paperId", "problem", "method", "finding", "limitation", "usableFor"], f"comparisonMatrix[{matrix_index}].rows[{row_index}]", errors)
            if row.get("paperId") not in record_index:
                errors.append(f"comparisonMatrix[{matrix_index}].rows[{row_index}] 引用了不存在的 paperId：{row.get('paperId')}")
            if not isinstance(row.get("usableFor"), list):
                errors.append(f"comparisonMatrix[{matrix_index}].rows[{row_index}].usableFor 必须是数组。")

    priority_read_count = sum(1 for card in quick_cards if isinstance(card, dict) and card.get("readingDecision") == "priority_read")
    metadata_count = sum(1 for record in records if isinstance(record, dict) and record.get("textAvailability") == "metadata")
    abstract_count = sum(1 for record in records if isinstance(record, dict) and record.get("textAvailability") == "abstract")
    fulltext_count = sum(1 for record in records if isinstance(record, dict) and record.get("textAvailability") == "fulltext")
    user_uploaded_count = sum(1 for record in records if isinstance(record, dict) and record.get("textAvailability") == "user_uploaded")
    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict) and metrics.get("literatureHitCount") not in (None, len(records)):
        errors.append("qualityReport.metrics.literatureHitCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("metadataOnlyCount") not in (None, metadata_count):
        errors.append("qualityReport.metrics.metadataOnlyCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("abstractAvailableCount") not in (None, abstract_count):
        errors.append("qualityReport.metrics.abstractAvailableCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("fulltextAvailableCount") not in (None, fulltext_count):
        errors.append("qualityReport.metrics.fulltextAvailableCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("userUploadedCount") not in (None, user_uploaded_count):
        errors.append("qualityReport.metrics.userUploadedCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("evidenceCardCount") not in (None, len(evidence_cards)):
        errors.append("qualityReport.metrics.evidenceCardCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("deepReadCardCount") not in (None, len(deep_cards)):
        errors.append("qualityReport.metrics.deepReadCardCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("deepReadSessionCount") not in (None, len(deep_read_sessions)):
        errors.append("qualityReport.metrics.deepReadSessionCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("comparisonRowCount") not in (None, comparison_row_count):
        errors.append("qualityReport.metrics.comparisonRowCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("searchCandidateCount") not in (None, corpus_search_report.get("candidateCount")):
        errors.append("qualityReport.metrics.searchCandidateCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("searchReturnedCount") not in (None, corpus_search_report.get("returnedCount")):
        errors.append("qualityReport.metrics.searchReturnedCount 与实际不一致。")
    if isinstance(metrics, dict) and metrics.get("priorityReadCount") not in (None, priority_read_count):
        errors.append("qualityReport.metrics.priorityReadCount 与实际不一致。")

    task_intent = data.get("taskIntent")
    if task_intent == "quick_read" and not quick_cards:
        errors.append("taskIntent=quick_read 时必须输出 result.quickReadCards。")
    if task_intent == "deep_read":
        if not deep_cards:
            errors.append("taskIntent=deep_read 时必须输出 result.deepReadCards。")
        if not deep_read_sessions:
            errors.append("taskIntent=deep_read 时必须输出 result.deepReadSessions。")
    if task_intent == "compare_papers" and not comparison_matrix:
        errors.append("taskIntent=compare_papers 时必须输出 result.comparisonMatrix。")
    if task_intent == "evidence_carding" and not evidence_cards:
        errors.append("taskIntent=evidence_carding 时必须输出 result.evidenceCards。")

    quality = data.get("qualityReport", {})
    failed = [item.get("id") for item in quality.get("checks", []) if item.get("status") == "fail"] if isinstance(quality, dict) else []
    if failed:
        errors.append(f"qualityReport 存在失败检查：{failed}")
    if isinstance(quality, dict) and quality.get("status") in {"fail", "failed"}:
        errors.append(f"qualityReport.status 为 {quality.get('status')}。")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验文献阅读助手 JSON 产物。")
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
    print(f"- 文献数：{len(data.get('result', {}).get('literatureRecords', []))}")
    print(f"- 证据卡数：{len(data.get('result', {}).get('evidenceCards', []))}")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
