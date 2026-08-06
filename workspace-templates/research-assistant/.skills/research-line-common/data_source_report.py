#!/usr/bin/env python3
"""Shared data-source report helpers for research-line Skills."""
from __future__ import annotations

from typing import Any


MOCK_SOURCE_TYPES = {"mock", "local_mock", "local_sample"}
MOCK_AUTH_STATUSES = {"mock_sample", "sample_only"}
AUTHORIZED_SOURCE_TYPES = {"authorized_database"}
AUTHORIZED_STATUSES = {"authorized", "licensed", "public_metadata_service"}
EXTERNAL_STATUSES = {"external_verified", "public_metadata_service"}
USER_STATUSES = {"user_provided"}


def build_source(
    *,
    source_id: str,
    source_name: str,
    source_type: str,
    data_type: str,
    record_count: int,
    authorization_status: str,
    version: str = "",
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "sourceId": source_id,
        "sourceName": source_name,
        "sourceType": source_type,
        "dataType": data_type,
        "recordCount": max(int(record_count), 0),
        "authorizationStatus": authorization_status,
        "version": version,
        "limitations": limitations or [],
    }


def build_data_source_report(
    *,
    skill_id: str,
    task_intent: str,
    sources: list[dict[str, Any]],
    overall_limitations: list[str] | None = None,
) -> dict[str, Any]:
    normalized = [source for source in sources if isinstance(source, dict)]
    mock_used = any(
        source.get("sourceType") in MOCK_SOURCE_TYPES or source.get("authorizationStatus") in MOCK_AUTH_STATUSES
        for source in normalized
    )
    user_used = any(source.get("authorizationStatus") in USER_STATUSES or source.get("sourceType") == "user_provided" for source in normalized)
    authorized_used = any(
        source.get("authorizationStatus") in AUTHORIZED_STATUSES or source.get("sourceType") in AUTHORIZED_SOURCE_TYPES
        for source in normalized
    )
    external_used = any(source.get("authorizationStatus") in EXTERNAL_STATUSES for source in normalized)
    limitations = list(overall_limitations or [])
    if mock_used and not any("mock" in item.lower() or "样例" in item for item in limitations):
        limitations.append("当前包含 mock/local sample 数据源，结果只能作为流程样例或候选建议，不能视为真实库完整检索。")
    return {
        "reportId": f"dsr-{skill_id}",
        "skillId": skill_id,
        "taskIntent": task_intent,
        "dataSources": normalized,
        "mockDataUsed": mock_used,
        "userProvidedDataUsed": user_used,
        "authorizedDataUsed": authorized_used,
        "externalVerifiedDataUsed": external_used,
        "overallLimitations": limitations,
    }


def validate_data_source_report(report: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["dataSourceReport 必须是对象。"]
    sources = report.get("dataSources", [])
    if not isinstance(sources, list) or not sources:
        errors.append("dataSourceReport.dataSources 必须是非空数组。")
        sources = []
    for index, source in enumerate(sources, 1):
        label = f"dataSourceReport.dataSources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        for field in ["sourceId", "sourceName", "sourceType", "dataType", "recordCount", "authorizationStatus", "limitations"]:
            if field not in source:
                errors.append(f"{label} 缺少字段：{field}")
        if not isinstance(source.get("recordCount"), int) or source.get("recordCount", -1) < 0:
            errors.append(f"{label}.recordCount 必须是非负整数。")
        if not isinstance(source.get("limitations", []), list):
            errors.append(f"{label}.limitations 必须是数组。")
    mock_expected = any(
        isinstance(source, dict)
        and (source.get("sourceType") in MOCK_SOURCE_TYPES or source.get("authorizationStatus") in MOCK_AUTH_STATUSES)
        for source in sources
    )
    if report.get("mockDataUsed") is not mock_expected:
        errors.append("dataSourceReport.mockDataUsed 与 dataSources 不一致。")
    limitations = report.get("overallLimitations", [])
    if not isinstance(limitations, list):
        errors.append("dataSourceReport.overallLimitations 必须是数组。")
        limitations = []
    if mock_expected and not any("mock" in str(item).lower() or "样例" in str(item) for item in limitations):
        errors.append("使用 mock/local sample 数据源时 overallLimitations 必须显式说明样例或 mock 限制。")
    return errors
