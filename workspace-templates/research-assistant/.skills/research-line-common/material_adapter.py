#!/usr/bin/env python3
"""Shared SourceMaterial and MaterialDigest helpers for research-line Skills."""
from __future__ import annotations

import re
from typing import Any, Callable


SIGNAL_TERMS = [
    "即时反馈",
    "错因诊断",
    "错因分析",
    "小学数学",
    "分数教学",
    "课堂投票",
    "课堂观察",
    "过程性评价",
    "学习证据",
    "讲评",
    "学生作品",
    "教学案例",
    "课题成果",
]

MATERIAL_TYPE_ALIASES = {
    "paper": "published_paper",
    "published_paper": "published_paper",
    "lesson": "lesson_case",
    "lesson_case": "lesson_case",
    "case": "lesson_case",
    "reflection": "teaching_reflection",
    "teaching_reflection": "teaching_reflection",
    "project_outcome": "project_result",
    "project_result": "project_result",
    "data_record": "project_process_record",
    "process_record": "project_process_record",
    "project_process_record": "project_process_record",
    "team_info": "team_info",
    "budget_info": "budget_info",
    "uploaded_paper_text": "uploaded_paper_text",
}
ALLOWED_MATERIAL_TYPES = {
    "published_paper",
    "lesson_case",
    "teaching_reflection",
    "project_result",
    "project_process_record",
    "team_info",
    "budget_info",
    "policy_notice",
    "uploaded_paper_text",
    "other",
}


def text_for_material(material: dict[str, Any]) -> str:
    return str(material.get("content") or material.get("rawText") or material.get("text") or "")


def normalize_material_type(value: Any, default: str = "other") -> str:
    text = str(value or "").strip()
    normalized = MATERIAL_TYPE_ALIASES.get(text, text)
    return normalized if normalized in ALLOWED_MATERIAL_TYPES else default


def normalize_source_status(material: dict[str, Any]) -> str:
    status = str(material.get("sourceStatus") or material.get("authorizationStatus") or "").strip()
    if status:
        return status
    if material.get("syntheticGeneratedBy"):
        return "synthetic"
    return "user_provided"


def default_permissions(source_status: str) -> dict[str, Any]:
    return {
        "canUseForGeneration": True,
        "canStore": source_status != "sensitive",
        "canExport": source_status in {"user_provided", "synthetic", "mock_sample", "authorized", "external_verified"},
        "limits": ["用户材料事实需由教师确认。"] if source_status == "user_provided" else ["synthetic 样例不得作为真实证据。"] if source_status == "synthetic" else [],
    }


def normalize_source_materials(
    raw_materials: list[dict[str, Any]] | None,
    *,
    default_material_type: str = "other",
) -> list[dict[str, Any]]:
    """Normalize user, project, or synthetic inputs into SourceMaterial shape."""
    materials: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_materials or [], 1):
        if not isinstance(raw, dict):
            continue
        source_status = normalize_source_status(raw)
        material_id = str(raw.get("materialId") or raw.get("sourceId") or f"mat-{index:03d}")
        raw_text = text_for_material(raw)
        normalized = dict(raw)
        normalized.update(
            {
                "materialId": material_id,
                "materialType": normalize_material_type(raw.get("materialType") or raw.get("type"), default_material_type),
                "title": str(raw.get("title") or f"未命名材料-{index}"),
                "rawText": raw_text,
                "content": raw_text,
                "sourceStatus": source_status,
                "sensitivity": raw.get("sensitivity") or "unknown",
                "permissions": raw.get("permissions") or default_permissions(source_status),
            }
        )
        if source_status == "synthetic":
            normalized.setdefault("syntheticGeneratedBy", raw.get("syntheticGeneratedBy") or "unknown")
            normalized.setdefault("usableFor", raw.get("usableFor") or ["fixture", "validator_test", "workflow_demo"])
            normalized.setdefault(
                "notUsableFor",
                raw.get("notUsableFor") or ["real_evidence", "citation_support", "project_fact_without_user_confirmation"],
            )
        materials.append(normalized)
    return materials


def material_text(materials: list[dict[str, Any]]) -> str:
    return "\n".join(f"{item.get('title', '')}：{text_for_material(item)}" for item in materials if isinstance(item, dict))


def source_for(materials: list[dict[str, Any]], keyword: str, fallback: str = "user-request") -> list[str]:
    for item in materials:
        if keyword in f"{item.get('title', '')}{text_for_material(item)}":
            return [str(item.get("materialId") or fallback)]
    return [fallback]


def values_by_material(
    materials: list[dict[str, Any]],
    field: str,
    pattern: str,
    formatter: Callable[[re.Match[str]], Any],
) -> list[dict[str, Any]]:
    values = []
    for material in materials:
        text = f"{material.get('title', '')}：{text_for_material(material)}"
        match = re.search(pattern, text)
        if match:
            values.append({"field": field, "value": formatter(match), "sourceRef": material.get("materialId", "user-material")})
    return values


def signal_terms_for_text(text: str) -> list[str]:
    signals = [term for term in SIGNAL_TERMS if term in text]
    return list(dict.fromkeys(signals))


def build_material_digests(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract conservative, source-linked material digests.

    This is intentionally deterministic and shallow. It creates stable fixtures
    for render scripts; deeper LLM extraction can replace the keyFacts later as
    long as it preserves source spans and limits.
    """
    digests: list[dict[str, Any]] = []
    normalized = normalize_source_materials(materials)
    for index, material in enumerate(normalized, 1):
        content = text_for_material(material)
        title = str(material.get("title") or f"未命名材料-{index}")
        signals = signal_terms_for_text(f"{title}{content}") or [material.get("materialType", "教学实践")]
        fact = content[:80] if content else "材料内容缺失，不能抽取事实。"
        limits = [] if content else ["缺少材料正文。"]
        if material.get("sourceStatus") == "synthetic":
            limits.append("该材料为 synthetic fixture，只能用于流程和校验测试。")
        digests.append(
            {
                "digestId": f"digest-{index:03d}",
                "materialId": material["materialId"],
                "materialType": material.get("materialType", "other"),
                "title": title,
                "keyFacts": [
                    {
                        "fact": fact,
                        "sourceSpan": "content[:80]" if content else "missing_content",
                        "confidence": "high" if content else "low",
                        "usableFor": ["research_topic", "project_basis"] if content else ["needs_more_evidence"],
                    }
                ],
                "topicSignals": signals,
                "claims": [],
                "events": [],
                "outcomes": [],
                "sourceStatus": material.get("sourceStatus", "user_provided"),
                "sourceRefs": [material["materialId"]],
                "usableFor": ["research_topic", "project_basis"] if content else ["needs_more_evidence"],
                "limits": limits,
                "limitations": limits,
            }
        )
    return digests


def build_source_materials_from_files(
    filepaths: list[str],
    material_type_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """从文件路径列表解析并生成 SourceMaterial 列表。

    这是 material_file_parser 的便捷封装，调用方无需手动导入文件解析模块。
    支持 .pdf / .pptx / .docx / .txt 四种格式。

    Args:
        filepaths: 文件路径列表
        material_type_map: 文件名 → materialType 的映射（可选）

    Returns:
        SourceMaterial 字典列表，可直接传入 build_material_digests()。
        解析失败的文件的 content 为空字符串，errors 记录在 metadata.parseErrors 中。
    """
    try:
        from material_file_parser import batch_parse_files, batch_to_source_materials  # type: ignore[import-untyped]
    except ImportError:
        # 文件解析模块不可用时返回空列表
        return []

    parsed = batch_parse_files(filepaths)
    return batch_to_source_materials(parsed, material_type_map)


def merge_file_materials_and_user_materials(
    filepaths: list[str] | None,
    user_materials: list[dict[str, Any]] | None,
    material_type_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """合并文件解析材料和用户直接提供的材料。

    文件解析的材料在前面（mat-001 起），用户材料在后面编号。
    两者都会被 normalize。

    Args:
        filepaths: 要解析的文件路径列表
        user_materials: 用户直接在 JSON 中提供的材料
        material_type_map: 文件名 → materialType 的映射（可选）

    Returns:
        合并后的 SourceMaterial 列表
    """
    file_materials = []
    if filepaths:
        file_materials = build_source_materials_from_files(filepaths, material_type_map)

    user_normalized = normalize_source_materials(user_materials or [])

    # 重新编号：文件材料从 mat-001 开始，用户材料接在后面
    offset = len(file_materials)
    for i, mat in enumerate(user_normalized):
        mat["materialId"] = f"mat-{offset + i + 1:03d}"

    return file_materials + user_normalized


def digest_fact(digest: dict[str, Any]) -> str:
    facts = digest.get("keyFacts", [])
    if facts and isinstance(facts[0], dict):
        return str(facts[0].get("fact", ""))
    return ""
