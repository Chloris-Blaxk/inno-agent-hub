#!/usr/bin/env python3
"""Citation authenticity orchestration for research-line Skills."""
from __future__ import annotations

from typing import Any

import literature_adapter


def normalize_verification_result(index: int, citation: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "verificationId": f"cv-{index:03d}",
        "paperId": citation.get("paperId", ""),
        "title": citation.get("title", ""),
        "verified": verification.get("verified", False),
        "confidence": verification.get("confidence", "none"),
        "verificationStatus": verification.get("verificationStatus", "not_checked"),
        "verificationNote": verification.get("verificationNote", ""),
        "bestMatch": verification.get("bestMatch", {}),
        "limits": [
            "题录验真只说明文献可能存在，不能证明其支撑当前论点。",
            "仍需 EvidenceCard 或合法全文片段完成支撑性校验。",
        ],
    }


def verify_citations_batch(
    citations: list[dict[str, Any]],
    *,
    adapters: list[literature_adapter.BaseLiteratureAdapter] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Verify citation authenticity through the first capable adapter."""
    if not literature_adapter.first_capable_adapter(adapters, "verify_citation"):
        return []
    checks: list[dict[str, Any]] = []
    for index, citation in enumerate([item for item in citations if isinstance(item, dict)][:limit], 1):
        if not citation.get("title") and not citation.get("doi"):
            continue
        verification = literature_adapter.verify_citation_record(citation, adapters=adapters)
        checks.append(normalize_verification_result(index, citation, verification))
    return checks
