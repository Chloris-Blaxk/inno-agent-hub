#!/usr/bin/env python3
"""Shared evidence-level and EvidenceCard helpers for research-line Skills."""
from __future__ import annotations

from typing import Any


TEXT_AVAILABILITY = {"metadata", "abstract", "fulltext", "user_uploaded"}
EVIDENCE_LEVELS = {"metadata_verified", "abstract_verified", "fulltext_verified", "user_text_only"}
SUPPORT_TYPES = {"direct_support", "partial_support", "background", "not_support"}
SOURCE_STATUSES = {"whitelist", "user_provided", "external_verified", "unverified", "synthetic"}
READABLE_TEXT_AVAILABILITY = {"abstract", "fulltext", "user_uploaded"}
EVIDENCE_CARD_TEXT_AVAILABILITY = READABLE_TEXT_AVAILABILITY
SUPPORTING_EVIDENCE_LEVELS = {"abstract_verified", "fulltext_verified", "user_text_only"}
CONFIRMED_SOURCE_STATUSES = {"whitelist", "external_verified"}
INSERTABLE_SOURCE_STATUSES = {"whitelist", "external_verified"}
CONFIRMATION_STATUSES = {"candidate", "pending_teacher_confirmation", "confirmed", "rejected", "needs_more_evidence"}
SYNTHETIC_ALLOWED_PURPOSES = {"fixture", "validator_test", "workflow_demo", "synthetic_regression"}
SYNTHETIC_FORBIDDEN_PURPOSES = {"real_evidence", "citation_support", "project_fact_without_user_confirmation"}

LEGACY_EVIDENCE_LEVELS = {
    "metadata_only": "metadata_verified",
    "abstract_only": "abstract_verified",
    "fulltext": "fulltext_verified",
    "fulltext_verified": "fulltext_verified",
    "uploaded_text": "user_text_only",
    "user_uploaded": "user_text_only",
    "user_text_only": "user_text_only",
}


def evidence_level_for_availability(text_availability: str | None) -> str:
    if text_availability == "fulltext":
        return "fulltext_verified"
    if text_availability == "user_uploaded":
        return "user_text_only"
    if text_availability == "abstract":
        return "abstract_verified"
    return "metadata_verified"


def normalize_evidence_level(value: Any) -> str:
    text = str(value or "").strip()
    return LEGACY_EVIDENCE_LEVELS.get(text, text if text in EVIDENCE_LEVELS else "metadata_verified")


def legacy_evidence_text(card: dict[str, Any]) -> str:
    return str(card.get("evidenceText") or card.get("evidence") or card.get("abstract") or "")


def legacy_quote_location(card: dict[str, Any]) -> str:
    return str(card.get("quoteLocation") or card.get("locator") or card.get("sourceLocator", {}).get("locator") or "")


def canonicalize_evidence_card(card: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical EvidenceCard while preserving extra source metadata."""
    normalized = dict(card)
    normalized["cardId"] = str(card.get("cardId") or card.get("evidenceCardId") or card.get("paperId") or "")
    normalized["claim"] = str(card.get("claim") or card.get("title") or "")
    normalized["evidenceText"] = legacy_evidence_text(card)
    normalized["paperId"] = str(card.get("paperId") or "")
    normalized["quoteLocation"] = legacy_quote_location(card) or "unknown"
    normalized["supportType"] = card.get("supportType") or card.get("support_type") or "background"
    normalized["evidenceLevel"] = normalize_evidence_level(card.get("evidenceLevel") or card.get("evidence_level"))
    normalized.setdefault("usableFor", card.get("usable_for", []))
    normalized.setdefault("limits", card.get("limits", []))
    return normalized


def can_generate_evidence_card(text_availability: str | None) -> bool:
    return text_availability in EVIDENCE_CARD_TEXT_AVAILABILITY


def has_readable_text(text_availability: str | None) -> bool:
    return text_availability in READABLE_TEXT_AVAILABILITY


def can_create_evidence_card(text_availability: str | None, evidence_level: str | None = None) -> bool:
    """Return whether a source may become an EvidenceCard.

    Metadata-only records can be recommended for reading, but they cannot become
    reusable supporting evidence. User-uploaded text can become a card, while
    still carrying a limitation that source authenticity is not whitelist-verified.
    """
    if evidence_level is not None and normalize_evidence_level(evidence_level) == "metadata_verified":
        return False
    return can_generate_evidence_card(text_availability)


def can_support_claim(evidence_level: str | None, support_type: str | None) -> bool:
    level = normalize_evidence_level(evidence_level)
    return level in SUPPORTING_EVIDENCE_LEVELS and support_type in {"direct_support", "partial_support"}


def evidence_level_matches_availability(evidence_level: str | None, text_availability: str | None) -> bool:
    level = normalize_evidence_level(evidence_level)
    if level == "metadata_verified":
        return text_availability == "metadata"
    if level == "abstract_verified":
        return text_availability in {"abstract", "fulltext", "user_uploaded"}
    if level == "fulltext_verified":
        return text_availability in {"fulltext", "user_uploaded"}
    if level == "user_text_only":
        return text_availability == "user_uploaded"
    return False


def requires_limits_for_abstract_support(evidence_level: str | None, support_type: str | None, text_availability: str | None) -> bool:
    return (
        normalize_evidence_level(evidence_level) == "abstract_verified"
        and support_type in {"direct_support", "partial_support"}
        and text_availability == "abstract"
    )


def is_source_authentic(source_status: str | None) -> bool:
    """Return whether a source status means bibliographic authenticity is confirmed."""
    return source_status in CONFIRMED_SOURCE_STATUSES


def can_insert_citation(
    *,
    evidence_level: str | None,
    support_type: str | None,
    source_status: str | None,
    has_source_locator: bool,
    has_formatted_citation: bool,
) -> bool:
    """Return whether an output may suggest inserting a citation.

    Citation insertion is stricter than claim support: the source must be
    authenticity-checked, the evidence must support the claim, and the output
    must carry both a locator and a formatted citation for teacher review.
    """
    return (
        source_status in INSERTABLE_SOURCE_STATUSES
        and can_support_claim(evidence_level, support_type)
        and has_source_locator
        and has_formatted_citation
    )


def metadata_as_evidence_violations(item: dict[str, Any], label: str = "item") -> list[str]:
    """Return violations when a metadata-only object is used as evidence.

    Bibliographic candidates may carry metadata locators and limits. They cross
    the line only when they are shaped as reusable evidence, supporting claim
    matches, citation insertion, or direct/partial support.
    """
    text_availability = item.get("textAvailability")
    evidence_level = normalize_evidence_level(item.get("evidenceLevel"))
    is_metadata_only = text_availability == "metadata" or evidence_level == "metadata_verified"
    if not is_metadata_only:
        return []

    violations: list[str] = []
    if non_empty_value(item.get("evidenceText")):
        violations.append(f"{label} metadata-only item must not carry evidenceText.")
    if non_empty_value(item.get("evidenceCardId")):
        violations.append(f"{label} metadata-only item must not reference an EvidenceCard.")
    if item.get("supportType") in {"direct_support", "partial_support"}:
        violations.append(f"{label} metadata-only item must not claim direct or partial support.")
    if item.get("supportStatus") == "supports":
        violations.append(f"{label} metadata-only item must not be marked as supports.")
    if item.get("decision") == "suggest_insert":
        violations.append(f"{label} metadata-only item must not produce suggest_insert.")
    if item.get("matchType") in {"evidence_card", "fulltext", "abstract"}:
        violations.append(f"{label} metadata-only item must not masquerade as text-backed evidence.")
    if item.get("targetType") == "evidence_card":
        violations.append(f"{label} metadata-only item must not target EvidenceCard creation.")
    return violations


def forbid_metadata_as_evidence(item: dict[str, Any]) -> bool:
    """Return True when the item respects the metadata-only evidence boundary."""
    return not metadata_as_evidence_violations(item)


def non_empty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def requires_teacher_confirmation(action: str | None, risk_level: str | None = None) -> bool:
    """Return whether an action must stay pending until the teacher confirms it."""
    return action in {
        "citation_insert",
        "fact_conflict_resolution",
        "budget_amount_write",
        "chapter_drafting",
        "project_fact_write",
    } or risk_level in {"high", "needs_user_confirmation"}


def requires_teacher_confirmation_for_item(item: dict[str, Any]) -> bool:
    """Object-aware confirmation helper for handoff and workspace items."""
    action = item.get("action") or item.get("actionType") or item.get("targetType")
    risk_level = item.get("riskLevel") or item.get("status")
    if requires_teacher_confirmation(str(action or ""), str(risk_level or "")):
        return True
    if item.get("decision") == "suggest_insert":
        return True
    if item.get("draftStatus") == "draft_reference":
        return True
    if item.get("requiresTeacherConfirmation") is True:
        return True
    return False


def normalize_confirmation_status(value: Any, *, requires_confirmation: bool = False) -> str:
    """Normalize confirmation states used by cross-Skill handoff objects."""
    text = str(value or "").strip()
    if text in CONFIRMATION_STATUSES:
        return text
    if requires_confirmation:
        return "pending_teacher_confirmation"
    return "candidate"


def is_synthetic_source(item: dict[str, Any]) -> bool:
    """Return whether an item was generated as synthetic fixture data."""
    return item.get("sourceStatus") == "synthetic" or non_empty_value(item.get("syntheticGeneratedBy"))


def synthetic_source_violations(item: dict[str, Any], *, purpose: str | None = None, label: str = "item") -> list[str]:
    """Return violations when synthetic fixture data is used as real evidence."""
    if not is_synthetic_source(item):
        return []

    violations: list[str] = []
    usable_for = set(item.get("usableFor") or [])
    not_usable_for = set(item.get("notUsableFor") or [])
    requested = purpose or item.get("purpose") or item.get("targetUse")
    if requested in SYNTHETIC_FORBIDDEN_PURPOSES or requested in not_usable_for:
        violations.append(f"{label} synthetic source cannot be used for {requested}.")
    if requested and usable_for and requested not in usable_for:
        violations.append(f"{label} synthetic source usableFor does not include {requested}.")
    if not usable_for:
        violations.append(f"{label} synthetic source must declare usableFor.")
    if not_usable_for and not SYNTHETIC_FORBIDDEN_PURPOSES.intersection(not_usable_for):
        violations.append(f"{label} synthetic source should declare real evidence/citation/project fact limits.")
    return violations
