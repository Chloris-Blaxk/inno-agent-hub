#!/usr/bin/env python3
"""Shared EvidenceCard construction helpers for research-line Skills."""
from __future__ import annotations

from typing import Any

from evidence_policy import can_create_evidence_card, evidence_level_for_availability


def readable_text(record: dict[str, Any]) -> tuple[str, str]:
    """Return the safest available text and its locator kind."""
    availability = record.get("textAvailability")
    if availability == "metadata":
        return "", "metadata"
    if availability == "fulltext":
        text = record.get("fullText") or record.get("text") or record.get("abstract") or ""
        return str(text), "fulltext" if record.get("fullText") or record.get("text") else "abstract"
    if availability == "user_uploaded":
        text = record.get("uploadedText") or record.get("sourceText") or record.get("text") or record.get("abstract") or ""
        return str(text), "user_uploaded_text" if text else "user_uploaded_text_missing"
    text = record.get("abstract") or ""
    return str(text), "abstract"


def split_text_units(text: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """Split text into small reusable units with deterministic locators."""
    units: list[dict[str, Any]] = []
    for index, part in enumerate(text.replace("\n", "。").split("。"), 1):
        clean = part.strip(" 。；;")
        if not clean:
            continue
        units.append({"unitId": f"unit-{index:03d}", "text": clean, "locator": f"句段 {index}"})
        if len(units) >= limit:
            break
    return units


def limits_for_level(evidence_level: str, source_status: str | None) -> list[str]:
    if evidence_level == "abstract_verified":
        return ["摘要级信息，不能支撑强因果、统计显著性或样本细节结论。"]
    if evidence_level == "user_text_only":
        return ["基于用户上传文本，文献真实性需另行通过白名单或题录库核验。"]
    if evidence_level == "fulltext_verified":
        return ["仅可在当前授权全文或可访问片段范围内复用。"]
    if source_status == "synthetic":
        return ["synthetic fixture 不得作为真实证据。"]
    return ["metadata-only 不得生成 EvidenceCard。"]


def build_evidence_cards_from_text(
    paper: dict[str, Any],
    text_units: list[dict[str, Any]],
    *,
    purpose: str = "literature_reading",
    start_index: int = 1,
    support_type: str = "background",
) -> list[dict[str, Any]]:
    """Build EvidenceCards only from readable text units.

    Metadata-only records return an empty list. The caller may request direct or
    partial support only after a separate support check; the default stays
    background to avoid overclaiming from reading workflows.
    """
    availability = paper.get("textAvailability")
    evidence_level = paper.get("evidenceLevel") or evidence_level_for_availability(availability)
    if evidence_level == "metadata_verified" and availability != "metadata":
        evidence_level = evidence_level_for_availability(availability)
    if not can_create_evidence_card(availability, evidence_level):
        return []

    cards: list[dict[str, Any]] = []
    source_status = paper.get("sourceStatus")
    for offset, unit in enumerate(text_units, start_index):
        text = str(unit.get("text") or "").strip()
        if not text:
            continue
        locator = str(unit.get("locator") or unit.get("unitId") or "text")
        location_type = str(unit.get("locationType") or unit.get("sourceScope") or paper.get("textAvailability") or "text")
        cards.append(
            {
                "cardId": f"ec-render-{offset:03d}",
                "claim": unit.get("claim") or f"{paper.get('title', '该文献')}可为相关研究提供背景线索",
                "evidenceText": text[:500],
                "paperId": paper.get("paperId", ""),
                "quoteLocation": locator,
                "sourceLocator": {
                    "locationType": location_type,
                    "locator": locator,
                    "confidence": "medium" if evidence_level == "abstract_verified" else "high",
                },
                "supportType": unit.get("supportType") or support_type,
                "evidenceLevel": evidence_level,
                "usableFor": unit.get("usableFor") or ["论文引言", "项目研究背景"],
                "purpose": purpose,
                "limits": list(dict.fromkeys((unit.get("limits") or []) + limits_for_level(evidence_level, source_status))),
            }
        )
    return cards


def build_evidence_card_from_paper(
    index: int,
    paper: dict[str, Any],
    *,
    purpose: str = "literature_reading",
    support_type: str = "background",
) -> dict[str, Any] | None:
    """Build the first conservative EvidenceCard from a paper-like record."""
    text, location = readable_text(paper)
    if not text:
        return None
    units = split_text_units(text, limit=1)
    for unit in units:
        unit["locator"] = location
        unit["locationType"] = location
    cards = build_evidence_cards_from_text(
        paper,
        units,
        purpose=purpose,
        start_index=index,
        support_type=support_type,
    )
    return cards[0] if cards else None
