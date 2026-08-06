#!/usr/bin/env python3
"""Build a compact ResearchWorkspace summary from research-line outputs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOPIC_LIMIT = 5
LITERATURE_LIMIT = 20
EVIDENCE_LIMIT = 10
CLAIM_LIMIT = 20
QUALITY_REPORT_TOKEN_LIMIT = 1200
FORBIDDEN_LITERATURE_FIELDS = {"abstract", "fullText", "uploadedText", "sourceText", "text"}
FORBIDDEN_ROOT_FIELDS = {"result", "documentDraft", "documentSet", "markdown", "fullText", "uploadedText"}


class WorkspaceError(AssertionError):
    """Workspace summary validation failed."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def estimate_tokens(value: Any) -> int:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return max(1, round(len(text) / 4))


def short_text(value: Any, limit: int = 180) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def unique_by(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        value = item.get(key)
        if not value or value in seen:
            continue
        seen.add(str(value))
        output.append(item)
    return output


def compact_topic(topic: dict[str, Any]) -> dict[str, Any]:
    existing_basis = []
    for item in topic.get("existingBasis", [])[:3]:
        if isinstance(item, dict):
            existing_basis.append(
                {
                    "materialId": item.get("materialId"),
                    "basis": short_text(item.get("basis"), 120),
                }
            )
        elif item:
            existing_basis.append({"basis": short_text(item, 120)})
    feasibility = topic.get("feasibility", {}) if isinstance(topic.get("feasibility"), dict) else {}
    basis_gap = topic.get("basisGap", {}) if isinstance(topic.get("basisGap"), dict) else {}
    differentiation = topic.get("differentiation", {}) if isinstance(topic.get("differentiation"), dict) else {}
    return {
        "topicId": topic.get("topicId"),
        "topicTitle": short_text(topic.get("topicTitle"), 120),
        "topicType": topic.get("topicType"),
        "researchQuestion": short_text(topic.get("researchQuestion"), 160),
        "keywords": topic.get("keywords", [])[:8],
        "existingBasis": existing_basis,
        "feasibility": {
            "score": feasibility.get("score"),
            "risks": [short_text(item, 100) for item in feasibility.get("risks", [])[:3]],
            "neededMaterials": [short_text(item, 80) for item in feasibility.get("neededMaterials", [])[:5]],
        },
        "basisGap": {
            "gapCount": len(basis_gap.get("gaps", [])) if isinstance(basis_gap.get("gaps"), list) else 0,
            "upgradePath": [short_text(item, 100) for item in basis_gap.get("upgradePath", [])[:3]],
        },
        "differentiation": {
            "nearestGrantId": differentiation.get("nearestGrantId"),
            "similarityScore": differentiation.get("similarityScore"),
            "riskLevel": differentiation.get("riskLevel"),
            "differenceStrategy": short_text(differentiation.get("differenceStrategy"), 140),
        },
    }


def compact_material_digest(digest: dict[str, Any]) -> dict[str, Any]:
    key_facts = []
    for item in digest.get("keyFacts", [])[:2]:
        if isinstance(item, dict):
            key_facts.append({"fact": short_text(item.get("fact"), 120), "confidence": item.get("confidence")})
        elif item:
            key_facts.append({"fact": short_text(item, 120)})
    return {
        "digestId": digest.get("digestId"),
        "materialId": digest.get("materialId"),
        "materialType": digest.get("materialType"),
        "title": short_text(digest.get("title"), 100),
        "keyFacts": key_facts,
        "topicSignals": digest.get("topicSignals", [])[:8],
        "usableFor": digest.get("usableFor", [])[:5],
        "limitations": [short_text(item, 100) for item in digest.get("limitations", [])[:3]],
    }


def compact_literature(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "paperId": record.get("paperId"),
        "title": short_text(record.get("title"), 160),
        "authors": record.get("authors", [])[:5],
        "year": record.get("year"),
        "journal": short_text(record.get("journal"), 80),
        "doi": record.get("doi", ""),
        "keywords": record.get("keywords", [])[:8],
        "sourceStatus": record.get("sourceStatus"),
        "textAvailability": record.get("textAvailability"),
        "evidenceLevel": record.get("evidenceLevel"),
        "subjectCategory": record.get("subjectCategory"),
        "journalTier": record.get("journalTier"),
    }


def compact_evidence(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "cardId": card.get("cardId") or card.get("evidenceCardId"),
        "claim": short_text(card.get("claim"), 160),
        "evidenceText": short_text(card.get("evidenceText"), 260),
        "paperId": card.get("paperId"),
        "quoteLocation": card.get("quoteLocation"),
        "supportType": card.get("supportType"),
        "evidenceLevel": card.get("evidenceLevel"),
        "usableFor": card.get("usableFor", [])[:5],
        "limits": [short_text(item, 120) for item in card.get("limits", [])[:3]],
    }


def compact_claim_check(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claimId": claim.get("claimId"),
        "claimText": short_text(claim.get("claimText"), 180),
        "status": claim.get("status"),
        "matchedEvidenceCards": claim.get("matchedEvidenceCards", [])[:8],
        "riskNotes": [short_text(item, 120) for item in claim.get("riskNotes", [])[:4]],
        "recommendedRewrite": short_text(claim.get("recommendedRewrite"), 180),
    }


def compact_project_fact_table(output: dict[str, Any]) -> dict[str, Any] | None:
    result = output.get("result", {})
    fact_table = result.get("projectFactTable", {})
    if not isinstance(fact_table, dict) or not fact_table:
        return None
    facts = []
    for fact in fact_table.get("facts", [])[:30]:
        facts.append(
            {
                "factId": fact.get("factId"),
                "field": fact.get("field"),
                "value": short_text(fact.get("value"), 180),
                "confidence": fact.get("confidence"),
                "status": fact.get("status"),
                "sourceRefCount": len(fact.get("sourceRefs", [])) if isinstance(fact.get("sourceRefs"), list) else 0,
            }
        )
    return {
        "projectId": fact_table.get("projectId"),
        "factCount": len(fact_table.get("facts", [])),
        "conflictCount": len(fact_table.get("conflicts", [])),
        "confirmedFactCount": len([fact for fact in fact_table.get("facts", []) if isinstance(fact, dict) and fact.get("status") == "confirmed"]),
        "needsConfirmationCount": len([fact for fact in fact_table.get("facts", []) if isinstance(fact, dict) and fact.get("status") == "needs_user_confirmation"]),
        "missingFields": [item.get("field") for item in fact_table.get("missingFields", []) if isinstance(item, dict)],
        "conflictFields": [item.get("field") for item in fact_table.get("conflicts", []) if isinstance(item, dict)],
        "facts": facts,
    }


def compact_quality_report(output: dict[str, Any]) -> dict[str, Any]:
    quality = output.get("qualityReport", {}) if isinstance(output.get("qualityReport"), dict) else {}
    return {
        "skillId": output.get("skillId"),
        "taskIntent": output.get("taskIntent"),
        "status": quality.get("status"),
        "warnings": [short_text(item, 140) for item in quality.get("warnings", [])[:8]],
        "metrics": quality.get("metrics", {}),
        "summary": short_text(output.get("summary"), 180),
    }


def collect_workspace(outputs: list[dict[str, Any]], workspace_id: str) -> dict[str, Any]:
    topics: list[dict[str, Any]] = []
    material_digests: list[dict[str, Any]] = []
    literature: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    claim_checks: list[dict[str, Any]] = []
    project_tables: list[dict[str, Any]] = []
    quality_reports: list[dict[str, Any]] = []
    paper_revision_summary: dict[str, Any] = {}

    for output in outputs:
        result = output.get("result", {}) if isinstance(output.get("result"), dict) else {}
        handoff = output.get("handoff", {}) if isinstance(output.get("handoff"), dict) else {}
        quality_reports.append(compact_quality_report(output))

        material_digests.extend(compact_material_digest(item) for item in result.get("materialDigests", []) if isinstance(item, dict))
        topics.extend(compact_topic(item) for item in result.get("topicCandidates", []) if isinstance(item, dict))

        literature_source = handoff.get("literatureRecords") or result.get("literatureRecords", [])
        evidence_source = handoff.get("evidenceCards") or handoff.get("usableEvidenceCards") or result.get("evidenceCards", [])
        literature.extend(compact_literature(item) for item in literature_source if isinstance(item, dict))
        evidence.extend(compact_evidence(item) for item in evidence_source if isinstance(item, dict))

        claim_checks.extend(compact_claim_check(item) for item in result.get("claimChecks", []) if isinstance(item, dict))
        if handoff.get("paperRevisionSummary"):
            summary = dict(handoff.get("paperRevisionSummary", {}))
            summary["skillId"] = output.get("skillId")
            paper_revision_summary = summary

        project_table = compact_project_fact_table(output)
        if project_table:
            project_tables.append(project_table)

    workspace = {
        "schemaVersion": 1,
        "workspaceId": workspace_id,
        "owner": "user-local",
        "sourceOutputCount": len(outputs),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "objectLimits": {
            "topicCandidates": TOPIC_LIMIT,
            "literatureRecords": LITERATURE_LIMIT,
            "evidenceCards": EVIDENCE_LIMIT,
            "claimChecks": CLAIM_LIMIT,
            "qualityReportTokens": QUALITY_REPORT_TOKEN_LIMIT,
        },
        "topicCandidates": unique_by(topics, "topicId")[:TOPIC_LIMIT],
        "materialDigests": unique_by(material_digests, "materialId")[:20],
        "literatureRecords": unique_by(literature, "paperId")[:LITERATURE_LIMIT],
        "evidenceCards": unique_by(evidence, "cardId")[:EVIDENCE_LIMIT],
        "claimChecks": unique_by(claim_checks, "claimId")[:CLAIM_LIMIT],
        "paperRevisionSummary": paper_revision_summary,
        "projectFactTables": project_tables[:5],
        "qualityReports": quality_reports,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    workspace["contextBudget"] = {
        "estimatedTokens": estimate_tokens(workspace),
        "qualityReportTokens": estimate_tokens(workspace["qualityReports"]),
        "status": "ok",
    }
    validate_workspace(workspace)
    return workspace


def validate_workspace(workspace: dict[str, Any]) -> None:
    for field in FORBIDDEN_ROOT_FIELDS:
        if field in workspace:
            raise WorkspaceError(f"workspace summary 不能包含完整字段：{field}")
    if len(workspace.get("topicCandidates", [])) > TOPIC_LIMIT:
        raise WorkspaceError("topicCandidates 超过上限。")
    if len(workspace.get("literatureRecords", [])) > LITERATURE_LIMIT:
        raise WorkspaceError("literatureRecords 超过上限。")
    if len(workspace.get("evidenceCards", [])) > EVIDENCE_LIMIT:
        raise WorkspaceError("evidenceCards 超过上限。")
    if len(workspace.get("claimChecks", [])) > CLAIM_LIMIT:
        raise WorkspaceError("claimChecks 超过上限。")
    if estimate_tokens(workspace.get("qualityReports", [])) > QUALITY_REPORT_TOKEN_LIMIT:
        raise WorkspaceError("qualityReports 超过上下文预算上限。")

    for index, record in enumerate(workspace.get("literatureRecords", []), 1):
        forbidden = FORBIDDEN_LITERATURE_FIELDS.intersection(record.keys())
        if forbidden:
            raise WorkspaceError(f"literatureRecords[{index}] 包含不应进入摘要的全文字段：{sorted(forbidden)}")
        for required in ("paperId", "title", "year", "journal", "textAvailability", "evidenceLevel"):
            if not record.get(required):
                raise WorkspaceError(f"literatureRecords[{index}] 缺少 {required}")
    for table_index, table in enumerate(workspace.get("projectFactTables", []), 1):
        for fact_index, fact in enumerate(table.get("facts", []), 1):
            if "sourceRefs" in fact:
                raise WorkspaceError(f"projectFactTables[{table_index}].facts[{fact_index}] 不能携带完整 sourceRefs，只能携带 sourceRefCount。")
            for required in ("field", "status", "sourceRefCount"):
                if fact.get(required) in (None, ""):
                    raise WorkspaceError(f"projectFactTables[{table_index}].facts[{fact_index}] 缺少 {required}")

    for index, card in enumerate(workspace.get("evidenceCards", []), 1):
        for required in ("cardId", "paperId", "quoteLocation", "supportType", "evidenceLevel"):
            if not card.get(required):
                raise WorkspaceError(f"evidenceCards[{index}] 缺少 {required}")
        if estimate_tokens(card) > 220:
            raise WorkspaceError(f"evidenceCards[{index}] 超过单卡 220 token 上限。")

    for index, topic in enumerate(workspace.get("topicCandidates", []), 1):
        if not topic.get("topicId") or not topic.get("topicTitle"):
            raise WorkspaceError(f"topicCandidates[{index}] 缺少 topicId/topicTitle")
        if estimate_tokens(topic) > 300:
            raise WorkspaceError(f"topicCandidates[{index}] 超过单个 300 token 上限。")

    for index, table in enumerate(workspace.get("projectFactTables", []), 1):
        for fact in table.get("facts", []):
            if "sourceRefs" in fact:
                raise WorkspaceError(f"projectFactTables[{index}] 不能携带完整 sourceRefs，只保留 sourceRefCount。")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成科研线 ResearchWorkspace 压缩摘要。")
    parser.add_argument("outputs", nargs="+", help="四个科研线 Skill 输出 JSON，可传多个。")
    parser.add_argument("--output", required=True, help="写入 workspace summary JSON 的路径。")
    parser.add_argument("--workspace-id", default="rw-local-research-001")
    parser.add_argument("--validate-only", action="store_true", help="只校验已有 summary，不重新生成。")
    args = parser.parse_args()

    output_path = Path(args.output)
    if args.validate_only:
        validate_workspace(load_json(output_path))
        print(output_path)
        print("通过")
        return 0

    outputs = [load_json(Path(path)) for path in args.outputs]
    workspace = collect_workspace(outputs, args.workspace_id)
    write_json(output_path, workspace)
    print(output_path)
    print(f"estimatedTokens={workspace['contextBudget']['estimatedTokens']}")
    print(f"topicCandidates={len(workspace['topicCandidates'])}")
    print(f"literatureRecords={len(workspace['literatureRecords'])}")
    print(f"evidenceCards={len(workspace['evidenceCards'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
