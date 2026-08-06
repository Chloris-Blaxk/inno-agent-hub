#!/usr/bin/env python3
"""Shared claim-to-EvidenceCard support matching helpers."""
from __future__ import annotations

import re
from typing import Any

from evidence_policy import can_support_claim


STOP_TERMS = {"研究", "教学", "课堂", "学生", "教师", "本文", "通过", "进行", "可以", "能够", "有助"}
MAJOR_TERMS = {
    "即时反馈",
    "错因",
    "典型错因",
    "讲评",
    "教学决策",
    "课堂观察",
    "学习证据",
    "成绩",
    "显著",
    "过程性评价",
}


def tokenize(text: str) -> set[str]:
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text or "")
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


def major_terms(text: str) -> set[str]:
    return {term for term in MAJOR_TERMS if term in (text or "")}


def card_text(card: dict[str, Any]) -> str:
    return f"{card.get('claim', '')} {card.get('evidenceText', '')}"


def is_background_claim(claim_text: str) -> bool:
    return any(term in (claim_text or "") for term in ["背景线索", "研究背景", "相关研究", "文献综述", "提供背景"])


def is_strong_claim(claim_text: str) -> bool:
    return any(term in (claim_text or "") for term in ["显著", "提升成绩", "因果", "证明", "提高成绩", "实验表明"])


def card_can_support_claim_type(claim_text: str, card: dict[str, Any]) -> bool:
    if can_support_claim(card.get("evidenceLevel"), card.get("supportType")):
        return True
    return card.get("supportType") == "background" and is_background_claim(claim_text) and not is_strong_claim(claim_text)


def evidence_supports_claim(claim_text: str, card: dict[str, Any]) -> bool:
    combined = card_text(card)
    if claim_text and claim_text in combined:
        return card_can_support_claim_type(claim_text, card)
    required = major_terms(claim_text)
    if not required:
        overlap = tokenize(claim_text).intersection(tokenize(combined))
        return len(overlap) >= 3 and card_can_support_claim_type(claim_text, card)
    candidate_terms = major_terms(combined)
    return required.issubset(candidate_terms) and card_can_support_claim_type(claim_text, card)


def cards_supporting_claim(claim_text: str, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [card for card in cards if evidence_supports_claim(claim_text, card)]


def check_claim_support(
    claim: str,
    evidence_cards: list[dict[str, Any]],
    candidates: list[dict[str, Any]] | None = None,
    *,
    check_id: str = "claim-support-001",
) -> dict[str, Any]:
    """Return a four-level support decision for paper writing."""
    matches = cards_supporting_claim(claim, evidence_cards)
    candidate_list = [item for item in candidates or [] if isinstance(item, dict)]
    literature_verified = any(item.get("sourceStatus") in {"whitelist", "external_verified"} for item in candidate_list)
    metadata_candidate = any(item.get("evidenceLevel") == "metadata_verified" for item in candidate_list)

    if matches:
        decision = "suggest_insert"
        reasons = ["找到真实文献对应的 EvidenceCard，且证据文本覆盖论点关键词。"]
    elif metadata_candidate or literature_verified:
        decision = "need_more_evidence"
        reasons = ["找到相关题录或文献候选，但没有可支撑该论点的 EvidenceCard。"]
    elif candidate_list:
        decision = "blocked_unsupported"
        reasons = ["候选来源与论点相关性不足或证据级别不足。"]
    else:
        decision = "blocked_fake_reference"
        reasons = ["未找到可验证的真实文献或证据卡。"]

    return {
        "checkId": check_id,
        "claim": claim,
        "literatureVerification": {
            "status": "verified" if literature_verified else "candidate_match" if metadata_candidate else "not_verified",
            "paperId": candidate_list[0].get("paperId", "") if candidate_list else "",
            "warnings": [] if matches else ["文献真实或题录相关不等于证据支撑。"],
        },
        "evidenceMatches": [
            {
                "evidenceCardId": card.get("cardId"),
                "supportType": card.get("supportType"),
                "evidenceLevel": card.get("evidenceLevel"),
                "confidence": "medium" if card.get("evidenceLevel") == "abstract_verified" else "high",
            }
            for card in matches
        ],
        "decision": decision,
        "requiresTeacherConfirmation": decision == "suggest_insert",
        "reasons": reasons,
        "limits": ["只有 suggest_insert 且教师确认后，才能进入正文引用建议。"],
    }
