#!/usr/bin/env python3
"""项目申报助手最小离线渲染脚本。"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = ROOT / "generated-outputs"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_project_proposal.py"
DOCUMENT_TYPES = ("project_application", "closing_report", "achievement_report")

sys.path.insert(0, str(ROOT.parent / "research-line-common"))
from data_source_report import build_data_source_report, build_source  # noqa: E402
from education_generator_config import (  # noqa: E402
    attach_education_generator_runtime,
    build_education_generator_source,
)
from material_adapter import normalize_source_materials  # noqa: E402
import literature_adapter  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def reference_count(filename: str, key: str) -> int:
    try:
        value = load_json(REFERENCES_DIR / filename).get(key, [])
    except FileNotFoundError:
        return 0
    return len(value) if isinstance(value, list) else 0


def selected_backend(config: dict[str, Any], input_obj: dict[str, Any]) -> str | None:
    backend = (
        config.get("backend")
        or config.get("literatureBackend")
        or input_obj.get("backend")
        or input_obj.get("literatureBackend")
        or os.environ.get("RESEARCH_LITERATURE_BACKEND")
    )
    return str(backend).strip() if backend else None


def build_project_data_source_report(
    config: dict[str, Any],
    document_types: list[str],
    literature_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_obj = config.get("input", {})
    sources = [
        build_education_generator_source(record_count=1),
        build_source(
            source_id="document-templates",
            source_name="项目文档模板样例",
            source_type="local_sample",
            data_type="document_template",
            record_count=reference_count("document-templates.json", "templates"),
            authorization_status="sample_only",
            limitations=["模板为本地样例，真实申报前需替换为地区/项目级别最新模板。"],
        ),
        build_source(
            source_id="budget-rules",
            source_name="预算规则样例",
            source_type="local_sample",
            data_type="budget_rule",
            record_count=reference_count("budget-rules.json", "checks"),
            authorization_status="sample_only",
            limitations=["预算规则为样例口径，金额和科目需按科研管理/财务规则确认。"],
        ),
        build_source(
            source_id="review-rubrics",
            source_name="评审标准样例",
            source_type="local_sample",
            data_type="review_rubric",
            record_count=reference_count("review-rubrics.json", "rubrics"),
            authorization_status="sample_only",
            limitations=["评审维度为样例，不代表所有地区和项目类别权重。"],
        ),
        build_source(
            source_id="sanitized-case-patterns",
            source_name="脱敏案例模式样例",
            source_type="local_sample",
            data_type="sanitized_case_pattern",
            record_count=reference_count("sanitized-case-patterns.json", "patterns"),
            authorization_status="sample_only",
            limitations=["案例为脱敏模式样例，只能辅助结构参考，不能承诺立项结果。"],
        ),
    ]
    project_materials = input_obj.get("projectMaterials", []) or []
    if project_materials:
        sources.append(
            build_source(
                source_id="user-project-materials",
                source_name="用户提供项目材料",
                source_type="user_provided",
                data_type="project_material",
                record_count=len([item for item in project_materials if isinstance(item, dict)]),
                authorization_status="user_provided",
                limitations=["用户材料先进入 ProjectFactTable；未形成 factRefs 前不得写入正文事实。"],
            )
        )
    if input_obj.get("budgetInfo"):
        sources.append(
            build_source(
                source_id="user-budget-info",
                source_name="用户提供预算信息",
                source_type="user_provided",
                data_type="budget_input",
                record_count=1,
                authorization_status="user_provided",
                limitations=["预算金额需进入 ProjectFactTable 并由教师/财务口径确认后才能定稿。"],
            )
        )
    existing_ids = {source.get("sourceId") for source in sources}
    for source in literature_sources or []:
        if isinstance(source, dict) and source.get("sourceId") not in existing_ids:
            sources.append(source)
            existing_ids.add(source.get("sourceId"))
    return build_data_source_report(
        skill_id="project-proposal-skill",
        task_intent=config.get("taskIntent", "project_application"),
        sources=sources,
        overall_limitations=[f"当前生成 {len(document_types)} 类文档；模板、预算和评审规则仍为本地样例；文献背景候选不得写入 ProjectFactTable.facts。"],
    )


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def clean_fragment(value: Any, *, max_len: int = 140) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ：:，,；;。")
    if len(text) > max_len:
        text = text[:max_len].rstrip(" ，,；;、") + "..."
    return text


def split_sentences(text: str) -> list[str]:
    return [clean_fragment(item) for item in re.split(r"[。；;\n]+", text) if clean_fragment(item)]


def material_text(materials: list[dict[str, Any]]) -> str:
    return "\n".join(f"{item.get('title', '')}：{item.get('content', '')}" for item in materials)


def text_for_material(material: dict[str, Any]) -> str:
    return f"{material.get('title', '')}：{material.get('content', '')}"


def source_for(materials: list[dict[str, Any]], keyword: str, fallback: str = "user-request") -> list[str]:
    for item in materials:
        if keyword in f"{item.get('title', '')}{item.get('content', '')}":
            return [item.get("materialId", fallback)]
    return [fallback]


def source_for_keywords(materials: list[dict[str, Any]], keywords: list[str], fallback: str = "user-request") -> list[str]:
    refs: list[str] = []
    for item in materials:
        text = f"{item.get('title', '')}{item.get('content', '')}"
        if any(keyword and keyword in text for keyword in keywords):
            refs.append(item.get("materialId", fallback))
    return list(dict.fromkeys(refs)) or [fallback]


def make_fact(index: int, field: str, value: str, source_refs: list[str], confidence: str = "medium", status: str = "confirmed") -> dict[str, Any]:
    return {
        "factId": f"fact-{index:03d}",
        "field": field,
        "value": value,
        "sourceRefs": source_refs,
        "confidence": confidence,
        "status": status,
    }


def make_missing(field: str, reason: str, suggested_materials: list[str]) -> dict[str, Any]:
    return {"field": field, "reason": reason, "suggestedMaterials": suggested_materials}


def next_fact_index(facts: list[dict[str, Any]]) -> int:
    return len(facts) + 1


def fact_by_field(fact_table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {fact["field"]: fact for fact in fact_table.get("facts", []) if isinstance(fact, dict) and "field" in fact}


def document_required_fields(document_type: str) -> set[str]:
    template = template_for(document_type)
    fields: set[str] = set()
    for section in template.get("sections", []):
        if section.get("required"):
            fields.update(section.get("requiredFactFields", []))
    return fields


def values_by_material(materials: list[dict[str, Any]], field: str, pattern: str, formatter: Any) -> list[dict[str, Any]]:
    values = []
    for material in materials:
        text = text_for_material(material)
        match = re.search(pattern, text)
        if match:
            value = formatter(match)
            values.append({"field": field, "value": value, "sourceRef": material.get("materialId", "user-material")})
    return values


def add_fact_or_conflict(
    facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    missing_fields: list[dict[str, Any]],
    field: str,
    candidates: list[dict[str, Any]],
    missing_reason: str,
    suggested_materials: list[str],
    *,
    confidence: str = "high",
) -> None:
    if not candidates:
        missing_fields.append(make_missing(field, missing_reason, suggested_materials))
        return

    grouped: dict[str, list[str]] = {}
    for item in candidates:
        grouped.setdefault(str(item["value"]), []).append(item["sourceRef"])

    if len(grouped) > 1:
        conflicts.append(
            {
                "field": field,
                "values": [{"value": value, "sourceRefs": refs} for value, refs in grouped.items()],
                "sourceRefs": sorted({ref for refs in grouped.values() for ref in refs}),
                "resolution": "needs_user_confirmation",
            }
        )
        return

    value, refs = next(iter(grouped.items()))
    facts.append(make_fact(next_fact_index(facts), field, value, refs, confidence, "confirmed"))


def normalize_amount(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return f"{value} 元"
    text = str(value).strip()
    if not text:
        return None
    return text


def budget_category_names() -> set[str]:
    data = load_json(REFERENCES_DIR / "budget-rules.json")
    return {item.get("name") for item in data.get("categories", []) if item.get("name")}


def amount_to_yuan(value: Any) -> float | None:
    text = str(value or "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(万元|元)", text)
    if not match:
        return None
    amount = float(match.group(1))
    return amount * 10000 if match.group(2) == "万元" else amount


def extract_budget_info_from_materials(materials: list[dict[str, Any]]) -> dict[str, Any]:
    categories = sorted(budget_category_names(), key=len, reverse=True)
    total_amount = None
    total_refs: list[str] = []
    items: list[dict[str, Any]] = []
    seen_items: set[tuple[str, str, str]] = set()

    total_patterns = [
        r"(?:预算总额|经费总额|总预算|申请经费|项目经费)\s*[：:]?\s*(\d+(?:\.\d+)?)\s*(万元|元)",
        r"(?:总计|合计)\s*(\d+(?:\.\d+)?)\s*(万元|元)",
    ]
    for material in materials:
        text = text_for_material(material)
        ref = material.get("materialId", "user-material")
        for pattern in total_patterns:
            match = re.search(pattern, text)
            if match and total_amount is None:
                total_amount = f"{match.group(1)} {match.group(2)}"
                total_refs.append(ref)
                break

        for segment in split_sentences(text):
            for category in categories:
                if category not in segment:
                    continue
                amount_match = re.search(rf"{re.escape(category)}\s*[：:]?\s*(\d+(?:\.\d+)?)\s*(万元|元)", segment)
                if not amount_match:
                    continue
                amount = f"{amount_match.group(1)} {amount_match.group(2)}"
                purpose_match = re.search(r"(?:用于|用途为|用途[：:]?)\s*([^，,。；;]+)", segment)
                purpose = clean_fragment(purpose_match.group(1), max_len=60) if purpose_match else "用途待补充"
                key = (category, amount, ref)
                if key in seen_items:
                    continue
                seen_items.add(key)
                items.append(
                    {
                        "category": category,
                        "amount": amount,
                        "purpose": purpose,
                        "sourceRefs": [ref],
                    }
                )

    if not total_amount and not items:
        return {}
    refs = list(dict.fromkeys(total_refs + [ref for item in items for ref in item.get("sourceRefs", [])]))
    return {"totalAmount": total_amount, "items": items, "sourceRefs": refs, "origin": "projectMaterials"}


def build_budget(
    input_obj: dict[str, Any],
    facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    materials: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    budget_info = input_obj.get("budgetInfo") or extract_budget_info_from_materials(materials)
    if not budget_info:
        return {"items": [], "warnings": ["未提供预算金额，不能代填具体数值。"]}, ["补充预算总额、科目、金额和用途后运行 budget_check。"]

    warnings: list[str] = []
    items = budget_info.get("items", []) if isinstance(budget_info, dict) else []
    total_amount = normalize_amount(budget_info.get("totalAmount")) if isinstance(budget_info, dict) else None
    total_source_refs = budget_info.get("sourceRefs") if isinstance(budget_info, dict) and isinstance(budget_info.get("sourceRefs"), list) else ["budgetInfo"]
    known_categories = budget_category_names()
    budget_items = []
    numeric_sum_yuan = 0.0
    numeric_total: float | None = None

    if total_amount:
        facts.append(make_fact(next_fact_index(facts), "budget.total", total_amount, total_source_refs, "high", "confirmed"))
        numeric_total = amount_to_yuan(total_amount)
    else:
        warnings.append("提供了预算信息但缺少总额，无法校验明细合计。")

    for index, raw_item in enumerate(items, 1):
        if not isinstance(raw_item, dict):
            warnings.append(f"预算明细第 {index} 项不是对象，需人工确认。")
            continue
        category = raw_item.get("category") or raw_item.get("name") or "未命名科目"
        amount = normalize_amount(raw_item.get("amount"))
        purpose = raw_item.get("purpose") or raw_item.get("use") or "用途待补充"
        item_source_refs = raw_item.get("sourceRefs") if isinstance(raw_item.get("sourceRefs"), list) and raw_item.get("sourceRefs") else total_source_refs
        item = {
            "category": category,
            "amount": amount or "金额待确认",
            "purpose": purpose,
            "sourceRefs": item_source_refs,
            "status": "confirmed" if amount else "needs_user_confirmation",
        }
        budget_items.append(item)
        if category not in known_categories:
            warnings.append(f"预算科目“{category}”不在规则样例中，需人工确认。")
        if not amount:
            warnings.append(f"预算科目“{category}”缺少金额，不能代填。")
        else:
            amount_yuan = amount_to_yuan(amount)
            if amount_yuan is not None:
                numeric_sum_yuan += amount_yuan

    if budget_items:
        item_fact_refs = list(dict.fromkeys(ref for item in budget_items for ref in item.get("sourceRefs", []))) or total_source_refs
        facts.append(make_fact(next_fact_index(facts), "budget.items", budget_items, item_fact_refs, "high", "confirmed"))

    if numeric_total is not None and budget_items and round(numeric_sum_yuan, 2) != round(numeric_total, 2):
        conflicts.append(
            {
                "field": "budget.total",
                "values": [
                    {"value": total_amount, "sourceRefs": total_source_refs},
                    {"value": f"明细合计 {numeric_sum_yuan:g} 元", "sourceRefs": list(dict.fromkeys(ref for item in budget_items for ref in item.get("sourceRefs", [])))},
                ],
                "sourceRefs": list(dict.fromkeys(total_source_refs + [ref for item in budget_items for ref in item.get("sourceRefs", [])])),
                "resolution": "needs_user_confirmation",
            }
        )
        warnings.append("预算总额与明细合计不一致，需人工确认。")

    return {"totalAmount": total_amount, "items": budget_items, "warnings": warnings}, []


def direct_input_value(input_obj: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = input_obj.get(key)
        if isinstance(value, str) and value.strip():
            return clean_fragment(value, max_len=120)
    return None


def first_material_capture(materials: list[dict[str, Any]], patterns: list[str]) -> tuple[str, list[str]] | None:
    for material in materials:
        text = text_for_material(material)
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return clean_fragment(match.group(1), max_len=160), [material.get("materialId", "user-material")]
    return None


def infer_project_theme(materials: list[dict[str, Any]], all_text: str, subject: str) -> tuple[str, list[str]] | None:
    theme_patterns = [
        r"围绕([^。；\n]{4,70}?)(?:开展|进行|实施)(?:实践研究|研究|项目)",
        r"聚焦([^。；\n]{4,70}?)(?:，|,|开展|进行|实施|探索)",
        r"以([^。；\n]{4,70}?)(?:为切入点|为载体|为研究对象)",
        r"(?:研究|解决)([^。；\n]{4,70}?)(?:问题|难题)",
    ]
    found = first_material_capture(materials, theme_patterns)
    if found:
        return found
    if "课堂" in all_text:
        return f"{subject}课堂改进", source_for_keywords(materials, ["课堂", subject])
    return None


def title_from_theme(theme: str, subject: str) -> str:
    normalized = clean_fragment(theme, max_len=80)
    if normalized.endswith(("研究", "实践研究", "行动研究")):
        return normalized
    if subject and subject not in normalized and "课堂" not in normalized:
        normalized = f"{subject}{normalized}"
    return f"{normalized}的实践研究"


def extract_project_title(config: dict[str, Any], materials: list[dict[str, Any]], all_text: str, subject: str) -> tuple[str, list[str], str, str]:
    input_obj = config.get("input", {})
    direct = direct_input_value(input_obj, "projectTitle", "projectName", "title")
    if direct:
        return direct, ["input.projectTitle"], "high", "confirmed"
    source_title = first_match(r"《([^》]{4,90})》", config.get("sourceRequest", ""))
    if source_title:
        return clean_fragment(source_title, max_len=100), ["user-request"], "medium", "inferred"
    material_title = first_material_capture(materials, [r"(?:课题名称|项目名称|申报题目|研究题目)\s*[：:]\s*([^。；\n]+)"])
    if material_title:
        value, refs = material_title
        return value, refs, "high", "confirmed"
    theme = infer_project_theme(materials, all_text, subject)
    if theme:
        value, refs = theme
        return title_from_theme(value, subject), refs, "medium", "inferred"
    return f"{subject}课堂改进实践研究", ["user-request"], "low", "inferred"


def extract_main_goal(materials: list[dict[str, Any]], input_obj: dict[str, Any], all_text: str, subject: str) -> tuple[str, list[str], str, str]:
    direct = direct_input_value(input_obj, "mainGoal", "researchGoal", "goal")
    if direct:
        return direct, ["input.mainGoal"], "high", "confirmed"
    material_goal = first_material_capture(
        materials,
        [
            r"(?:研究目标|项目目标|总体目标|目标)\s*[：:]\s*([^。；\n]+)",
            r"(?:旨在|力图|拟通过)\s*([^。；\n]+)",
        ],
    )
    if material_goal:
        value, refs = material_goal
        return value, refs, "high", "confirmed"
    theme = infer_project_theme(materials, all_text, subject)
    if theme:
        value, refs = theme
        return f"围绕{value}，形成可操作的教学改进路径与成果材料。", refs, "medium", "inferred"
    return f"围绕{subject}真实教学问题，形成可验证、可复用的课堂改进方案。", ["user-request"], "low", "inferred"


def extract_policy_alignment(input_obj: dict[str, Any], materials: list[dict[str, Any]], all_text: str) -> tuple[str, list[str], str]:
    policy_terms = ["新课标", "核心素养", "双减", "过程性评价", "数字化", "课堂教学改进", "校本教研", "五育并举"]
    found_terms = [term for term in policy_terms if term in all_text or term in str(input_obj.get("requirements", ""))]
    if found_terms:
        return f"对齐{ '、'.join(dict.fromkeys(found_terms)) }等教育教学改进方向。", source_for_keywords(materials, found_terms, "user-request"), "medium"
    return "对齐真实教学问题改进、课堂证据收集与校本教研推进。", ["user-request"], "low"


def structured_team_candidates(input_obj: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    team_info = input_obj.get("teamInfo") if isinstance(input_obj.get("teamInfo"), dict) else {}
    leader_candidates: list[dict[str, Any]] = []
    member_candidates: list[dict[str, Any]] = []
    leader = team_info.get("leader") or team_info.get("leaderName") or team_info.get("principal") or team_info.get("host")
    if isinstance(leader, str) and leader.strip():
        leader_candidates.append({"field": "team.leader", "value": f"{clean_fragment(leader, max_len=40)}（项目负责人）", "sourceRef": "input.teamInfo"})
    member_count = team_info.get("memberCount") or team_info.get("coreMemberCount")
    if isinstance(member_count, (int, float)) or (isinstance(member_count, str) and member_count.strip()):
        member_candidates.append({"field": "team.memberCount", "value": f"核心成员 {clean_fragment(member_count, max_len=20)} 人", "sourceRef": "input.teamInfo"})
    members = team_info.get("members")
    if not member_candidates and isinstance(members, list) and members:
        member_candidates.append({"field": "team.memberCount", "value": f"核心成员 {len(members)} 人（由成员名单推断）", "sourceRef": "input.teamInfo"})
    return leader_candidates, member_candidates


def extract_team_candidates(input_obj: dict[str, Any], materials: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    leader_candidates, member_candidates = structured_team_candidates(input_obj)
    leader_patterns = [
        r"(?:项目负责人|课题负责人|负责人|主持人)\s*[：:]\s*([\u4e00-\u9fa5A-Za-z·]{2,20})",
        r"([\u4e00-\u9fa5A-Za-z·]{2,20})\s*(?:老师|教师)?\s*(?:担任|作为|为)\s*(?:项目负责人|课题负责人|主持人)",
    ]
    for material in materials:
        text = text_for_material(material)
        for pattern in leader_patterns:
            match = re.search(pattern, text)
            if match:
                name = clean_fragment(match.group(1), max_len=40)
                leader_candidates.append({"field": "team.leader", "value": f"{name}（项目负责人）", "sourceRef": material.get("materialId", "user-material")})
                break
        if not any(item.get("sourceRef") == material.get("materialId", "user-material") for item in leader_candidates):
            count_match = re.search(r"(?:项目负责人|课题负责人|负责人|主持人)\s*(\d+)\s*人", text)
            if count_match:
                leader_candidates.append(
                    {
                        "field": "team.leader",
                        "value": f"项目负责人 {count_match.group(1)} 人（姓名待确认）",
                        "sourceRef": material.get("materialId", "user-material"),
                    }
                )

    member_patterns = [
        (r"核心成员\s*(\d+)\s*人", lambda match: f"核心成员 {match.group(1)} 人"),
        (r"团队(?:共|共有|合计)?\s*(\d+)\s*人", lambda match: f"团队共 {match.group(1)} 人"),
        (r"研究团队由\s*(\d+)\s*人组成", lambda match: f"研究团队 {match.group(1)} 人"),
    ]
    for pattern, formatter in member_patterns:
        member_candidates.extend(values_by_material(materials, "team.memberCount", pattern, formatter))
    return leader_candidates, member_candidates


def extract_practice_record(materials: list[dict[str, Any]]) -> tuple[str, list[str]] | None:
    strong_keywords = ["已完成", "开展", "积累", "课例", "过程记录", "活动记录", "实践基础", "课堂观察记录", "课后访谈记录"]
    weak_keywords = ["课堂观察", "数据整理"]
    ordered_materials = sorted(
        materials,
        key=lambda item: 0 if str(item.get("materialType", "")) in {"practice", "process"} else 1,
    )
    for material in ordered_materials:
        material_type = str(material.get("materialType", ""))
        text = text_for_material(material)
        if material_type not in {"practice", "process", "proposal", "plan"} and not any(keyword in text for keyword in strong_keywords):
            continue
        sentences = [
            sentence
            for sentence in split_sentences(text)
            if (
                any(keyword in sentence for keyword in strong_keywords)
                or (material_type in {"practice", "process"} and any(keyword in sentence for keyword in weak_keywords))
            )
            and "预期形成" not in sentence
        ]
        if sentences:
            return "；".join(sentences[:2]), [material.get("materialId", "user-material")]
    return None


def extract_expected_outcomes(materials: list[dict[str, Any]]) -> tuple[str, list[str]] | None:
    expected = first_material_capture(materials, [r"(?:预期形成|拟形成|计划形成|成果形式)\s*[：:]?\s*([^。；\n]+)"])
    if expected:
        value, refs = expected
        return f"预期形成{value}。", refs
    for material in materials:
        text = text_for_material(material)
        if "预期" in text and "成果" in text:
            sentences = [sentence for sentence in split_sentences(text) if "预期" in sentence or "成果" in sentence]
            if sentences:
                return "；".join(sentences[:2]), [material.get("materialId", "user-material")]
    return None


def extract_actual_outcomes(materials: list[dict[str, Any]], all_text: str) -> tuple[str, list[str]] | None:
    count_patterns = [
        ("教学案例", "篇", r"教学案例\s*(\d+)\s*篇"),
        ("课堂观察记录", "份", r"课堂观察记录\s*(\d+)\s*份"),
        ("研究报告", "份", r"研究报告\s*(\d+)\s*份"),
        ("课例", "节", r"(?:完成|形成|积累)?\s*(\d+)\s*节[^。；\n]{0,10}课例"),
        ("论文", "篇", r"论文\s*(\d+)\s*篇"),
    ]
    counts: list[str] = []
    refs: list[str] = []
    for label, unit, pattern in count_patterns:
        for material in materials:
            text = text_for_material(material)
            match = re.search(pattern, text)
            if match:
                counts.append(f"{label} {match.group(1)} {unit}")
                refs.append(material.get("materialId", "user-material"))
                break
    if counts:
        return f"已有{ '、'.join(dict.fromkeys(counts)) }。", list(dict.fromkeys(refs)) or source_for(materials, "成果")
    for material in materials:
        text = text_for_material(material)
        if "成果" in text or "已形成" in text or "形成" in text:
            sentences = [sentence for sentence in split_sentences(text) if any(keyword in sentence for keyword in ["成果", "已形成", "形成"])]
            if sentences:
                return "；".join(sentences[:2]), [material.get("materialId", "user-material")]
    return None


def infer_facts(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    materials = normalize_source_materials(input_obj.get("projectMaterials", []), default_material_type="project_process_record")
    all_text = material_text(materials)
    teacher = config.get("teacherProfile", {})
    subject = teacher.get("subject") or "教育教学"
    level = input_obj.get("projectLevel") or "课题"

    leader_candidates, member_candidates = extract_team_candidates(input_obj, materials)
    cycle_candidates = values_by_material(
        materials,
        "timeline.cycle",
        r"(\d{4}[-年]\d{1,2})\s*(?:至|到|—|--|-)\s*(\d{4}[-年]\d{1,2})",
        lambda match: f"{match.group(1)} 至 {match.group(2)}",
    )
    if teacher.get("availableCycle"):
        cycle_candidates.append({"field": "timeline.cycle", "value": teacher["availableCycle"], "sourceRef": "teacherProfile"})
    sample_scope = first_match(r"(?:样本覆盖|样本范围|覆盖|涉及|面向)\s*([^。；\n]+)", all_text)
    risk_text = first_match(r"(?:风险|问题与反思|不足)\s*[：:]?\s*([^。；\n]+)", all_text)
    title, title_refs, title_confidence, title_status = extract_project_title(config, materials, all_text, subject)
    main_goal, goal_refs, goal_confidence, goal_status = extract_main_goal(materials, input_obj, all_text, subject)
    policy_alignment, policy_refs, policy_confidence = extract_policy_alignment(input_obj, materials, all_text)

    facts = [
        make_fact(1, "project.title", title, title_refs, title_confidence, title_status),
        make_fact(2, "project.level", level, ["user-request"], "high"),
        make_fact(3, "goals.mainGoal", main_goal, goal_refs, goal_confidence, goal_status),
    ]
    missing_fields: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    add_fact_or_conflict(facts, conflicts, missing_fields, "team.leader", leader_candidates, "未提供项目负责人信息。", ["团队名单", "负责人确认"])
    add_fact_or_conflict(facts, conflicts, missing_fields, "team.memberCount", member_candidates, "未提供核心成员人数。", ["团队名单"])
    add_fact_or_conflict(facts, conflicts, missing_fields, "timeline.cycle", cycle_candidates, "未提供项目周期。", ["申报通知", "项目计划时间表"], confidence="medium")
    practice_record = extract_practice_record(materials)
    if practice_record:
        value, refs = practice_record
        facts.append(make_fact(next_fact_index(facts), "basis.practiceRecords", value, refs, "high"))
    else:
        missing_fields.append(make_missing("basis.practiceRecords", "未提供已完成课例、过程记录或研究基础材料。", ["课例记录", "课堂观察表", "阶段活动记录"]))
    expected_outcomes = extract_expected_outcomes(materials)
    if expected_outcomes:
        value, refs = expected_outcomes
        facts.append(make_fact(next_fact_index(facts), "outcomes.expected", value, refs, "medium"))
    else:
        missing_fields.append(make_missing("outcomes.expected", "未提供预期成果或成果形态清单。", ["预期成果清单", "案例集/报告/工具模板说明"]))
    facts.append(make_fact(next_fact_index(facts), "policy.alignment", policy_alignment, policy_refs, policy_confidence))
    actual_outcomes = extract_actual_outcomes(materials, all_text)
    if actual_outcomes:
        value, refs = actual_outcomes
        facts.append(make_fact(next_fact_index(facts), "outcomes.actual", value, refs, "high"))
    if sample_scope:
        facts.append(make_fact(next_fact_index(facts), "data.sampleScope", sample_scope.strip(), source_for(materials, "样本"), "medium", "confirmed"))
    if risk_text:
        facts.append(make_fact(next_fact_index(facts), "risks", risk_text.strip(), source_for(materials, "风险"), "medium", "confirmed"))
    budget_report, budget_next_actions = build_budget(input_obj, facts, conflicts, materials)
    return {"projectId": "proj-render-001", "facts": facts, "missingFields": missing_fields, "conflicts": conflicts, "budgetReport": budget_report, "budgetNextActions": budget_next_actions}


def template_for(document_type: str) -> dict[str, Any]:
    templates = load_json(REFERENCES_DIR / "document-templates.json").get("templates", [])
    for template in templates:
        if template.get("documentType") == document_type:
            return template
    return templates[0]


def ensure_missing_fields_for_documents(fact_table: dict[str, Any], document_types: list[str]) -> None:
    facts_by_field = fact_by_field(fact_table)
    conflict_fields = {item.get("field") for item in fact_table.get("conflicts", []) if isinstance(item, dict)}
    existing_missing = {item.get("field") for item in fact_table.get("missingFields", []) if isinstance(item, dict)}
    field_labels = {
        "risks": "补充结题报告中的问题、反思或改进风险。",
        "data.sampleScope": "补充成果汇报所需的样本范围、班级数或学生人数。",
        "outcomes.actual": "补充已形成成果清单及数量证据。",
        "timeline.cycle": "补充项目起止周期或阶段安排。",
        "basis.practiceRecords": "补充研究过程、课例或活动记录。",
    }
    for document_type in document_types:
        for field in sorted(document_required_fields(document_type)):
            if field in facts_by_field or field in conflict_fields or field in existing_missing:
                continue
            fact_table.setdefault("missingFields", []).append(
                make_missing(field, field_labels.get(field, "补充该章节所需的事实材料。"), ["项目过程材料", "成果清单", "团队/预算确认表"])
            )
            existing_missing.add(field)


def required_section_coverage(document: dict[str, Any]) -> float:
    template = template_for(str(document.get("documentType", "")))
    expected_required = {section.get("sectionId") for section in template.get("sections", []) if section.get("required")}
    if not expected_required:
        return 1.0
    actual_section_ids = {section.get("sectionId") for section in document.get("sections", []) if isinstance(section, dict)}
    return round(len(expected_required.intersection(actual_section_ids)) / len(expected_required), 2)


def document_fields_used(document: dict[str, Any], facts_by_id: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    used: dict[str, list[str]] = {}
    for section in document.get("sections", []):
        if not isinstance(section, dict):
            continue
        for fact_id in section.get("factRefs", []):
            fact = facts_by_id.get(fact_id)
            if not fact:
                continue
            used.setdefault(fact.get("field", ""), []).append(document.get("documentType", "unknown"))
    return used


def build_cross_document_consistency_report(fact_table: dict[str, Any], documents: list[dict[str, Any]]) -> dict[str, Any]:
    facts = fact_table.get("facts", [])
    facts_by_id = {fact.get("factId"): fact for fact in facts if isinstance(fact, dict)}
    facts_by_field = fact_by_field(fact_table)
    documents_checked = [document.get("documentType") for document in documents]
    required_by_type = {document_type: document_required_fields(document_type) for document_type in documents_checked}
    all_required_fields = sorted({field for fields in required_by_type.values() for field in fields})
    missing_fields = {item.get("field") for item in fact_table.get("missingFields", []) if isinstance(item, dict)}
    conflict_fields = {item.get("field") for item in fact_table.get("conflicts", []) if isinstance(item, dict)}

    used_documents_by_field: dict[str, set[str]] = {}
    for document in documents:
        for field, used_docs in document_fields_used(document, facts_by_id).items():
            used_documents_by_field.setdefault(field, set()).update(used_docs)

    shared_fact_fields: list[dict[str, Any]] = []
    missing_shared_fields: list[dict[str, Any]] = []
    section_warnings: list[str] = []
    for field in all_required_fields:
        needed_by = [document_type for document_type, fields in required_by_type.items() if field in fields]
        fact = facts_by_field.get(field)
        if fact:
            used_docs = sorted(used_documents_by_field.get(field, set()))
            shared_fact_fields.append(
                {
                    "field": field,
                    "factId": fact.get("factId"),
                    "value": fact.get("value"),
                    "sourceRefs": fact.get("sourceRefs", []),
                    "usedInDocuments": used_docs,
                    "requiredByDocuments": needed_by,
                    "status": "consistent" if field not in conflict_fields else "needs_user_confirmation",
                }
            )
            if not set(needed_by).issubset(set(used_docs)):
                section_warnings.append(f"字段 {field} 未被所有需要它的文档章节引用。")
        elif field in missing_fields:
            missing_shared_fields.append({"field": field, "requiredByDocuments": needed_by, "reason": "ProjectFactTable.missingFields 已标记缺失。"})
        elif field in conflict_fields:
            shared_fact_fields.append(
                {
                    "field": field,
                    "factId": None,
                    "value": None,
                    "sourceRefs": [],
                    "usedInDocuments": [],
                    "requiredByDocuments": needed_by,
                    "status": "needs_user_confirmation",
                }
            )
        else:
            missing_shared_fields.append({"field": field, "requiredByDocuments": needed_by, "reason": "未进入 ProjectFactTable。"})

    conflicts = [
        {
            "field": item.get("field"),
            "sourceRefs": item.get("sourceRefs", []),
            "resolution": item.get("resolution", "needs_user_confirmation"),
        }
        for item in fact_table.get("conflicts", [])
        if isinstance(item, dict)
    ]
    status = "warn" if missing_shared_fields or conflicts or section_warnings else "pass"
    return {
        "status": status,
        "documentsChecked": documents_checked,
        "sharedFactFields": shared_fact_fields,
        "conflicts": conflicts,
        "missingSharedFields": missing_shared_fields,
        "sectionWarnings": section_warnings,
    }


def extract_counts_from_text(text: str) -> list[dict[str, Any]]:
    patterns = [
        ("教学案例", r"教学案例\s*(\d+)\s*篇"),
        ("课堂观察记录", r"课堂观察记录\s*(\d+)\s*份"),
        ("课例", r"(?:已完成\s*)?(\d+)\s*节.*?课例"),
        ("学生", r"(\d+)\s*名学生"),
        ("班级", r"(\d+)\s*个班"),
    ]
    values = []
    for label, pattern in patterns:
        match = re.search(pattern, text)
        if match:
            values.append({"label": label, "value": int(match.group(1))})
    return values


def build_presentation_support(fact_table: dict[str, Any]) -> dict[str, Any]:
    facts_by_field = fact_by_field(fact_table)
    timeline_items: list[dict[str, Any]] = []
    if "timeline.cycle" in facts_by_field:
        fact = facts_by_field["timeline.cycle"]
        timeline_items.append({"label": "项目周期", "description": fact_value_text(fact.get("value")), "factRefs": [fact.get("factId")], "status": "derived_from_fact"})
    if "basis.practiceRecords" in facts_by_field:
        fact = facts_by_field["basis.practiceRecords"]
        timeline_items.append({"label": "实践积累", "description": fact_value_text(fact.get("value")), "factRefs": [fact.get("factId")], "status": "derived_from_fact"})
    if "outcomes.actual" in facts_by_field:
        fact = facts_by_field["outcomes.actual"]
        timeline_items.append({"label": "成果形成", "description": fact_value_text(fact.get("value")), "factRefs": [fact.get("factId")], "status": "derived_from_fact"})
    if not timeline_items:
        timeline_items.append({"label": "时间线待补充", "description": "缺少项目周期或过程记录，不能生成具体时间线。", "factRefs": [], "status": "needs_evidence"})

    chart_suggestions: list[dict[str, Any]] = []
    for field in ("outcomes.actual", "basis.practiceRecords", "data.sampleScope"):
        fact = facts_by_field.get(field)
        if not fact:
            continue
        counts = extract_counts_from_text(fact_value_text(fact.get("value")))
        if counts:
            chart_suggestions.append(
                {
                    "chartId": f"chart-{len(chart_suggestions) + 1:03d}",
                    "chartType": "bar",
                    "title": f"{field} 量化展示",
                    "dataPoints": counts,
                    "factRefs": [fact.get("factId")],
                    "status": "derived_from_fact",
                }
            )
    if not chart_suggestions:
        chart_suggestions.append(
            {
                "chartId": "chart-001",
                "chartType": "placeholder",
                "title": "量化成果待补充",
                "dataPoints": [],
                "factRefs": [],
                "status": "needs_evidence",
            }
        )

    highlights = []
    for field in ("outcomes.actual", "basis.practiceRecords", "goals.mainGoal"):
        fact = facts_by_field.get(field)
        if fact:
            highlights.append({"text": fact_value_text(fact.get("value")), "factRefs": [fact.get("factId")], "status": "draft"})
    return {"timelineItems": timeline_items, "chartSuggestions": chart_suggestions, "achievementHighlights": highlights}


def fact_value_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                category = item.get("category", "未命名科目")
                amount = item.get("amount", "金额待确认")
                purpose = item.get("purpose", "用途待确认")
                parts.append(f"{category}{amount}（{purpose}）")
            else:
                parts.append(str(item))
        return "；".join(parts)
    if isinstance(value, dict):
        return "；".join(f"{key}:{val}" for key, val in value.items())
    return str(value)


def field_text(fact_by_field_map: dict[str, dict[str, Any]], field: str, fallback: str = "") -> str:
    fact = fact_by_field_map.get(field)
    return fact_value_text(fact.get("value")) if fact else fallback


def append_section_limit_note(content: str, missing_in_section: list[str], conflicts_in_section: list[str]) -> str:
    if missing_in_section:
        return f"{content} 仍需补充：{', '.join(missing_in_section)}。"
    if conflicts_in_section:
        return f"{content} 以下字段存在冲突，需人工确认：{', '.join(conflicts_in_section)}。"
    return content


def build_section_content(
    document_type: str,
    section_id: str,
    fact_by_field_map: dict[str, dict[str, Any]],
    missing_in_section: list[str],
    conflicts_in_section: list[str],
) -> str:
    project_level = field_text(fact_by_field_map, "project.level", "当前项目级别待确认")
    title = field_text(fact_by_field_map, "project.title", "项目主题待确认")
    goal = field_text(fact_by_field_map, "goals.mainGoal")
    cycle = field_text(fact_by_field_map, "timeline.cycle")
    practice = field_text(fact_by_field_map, "basis.practiceRecords")
    expected = field_text(fact_by_field_map, "outcomes.expected")
    actual = field_text(fact_by_field_map, "outcomes.actual")
    alignment = field_text(fact_by_field_map, "policy.alignment")
    member_count = field_text(fact_by_field_map, "team.memberCount")
    leader = field_text(fact_by_field_map, "team.leader")
    budget_total = field_text(fact_by_field_map, "budget.total")
    budget_items = field_text(fact_by_field_map, "budget.items")
    sample = field_text(fact_by_field_map, "data.sampleScope")
    risks = field_text(fact_by_field_map, "risks")

    content = ""
    if document_type == "project_application":
        if section_id == "sec-background":
            content = f"本项目按{project_level}口径组织申报，研究背景应从真实教学问题和政策导向两端展开。当前可用事实显示：{alignment}"
        elif section_id == "sec-goals":
            content = f"研究目标建议写成“问题链-行动链-成果链”的结构：{goal}"
        elif section_id == "sec-methods":
            parts = []
            if cycle:
                parts.append(f"研究周期为{cycle}")
            if practice:
                parts.append(f"已有实践基础包括：{practice}")
            content = "；".join(parts) + "。建议在正式稿中补充阶段任务、研究方法和关键节点。"
        elif section_id == "sec-outcomes":
            content = f"预期成果应对应研究目标和评审材料要求。当前可写入：{expected}"
        elif section_id == "sec-basis":
            parts = []
            if leader:
                parts.append(f"负责人信息：{leader}")
            if member_count:
                parts.append(f"团队基础：{member_count}")
            if practice:
                parts.append(f"实践基础：{practice}")
            content = "；".join(parts) + "。"
        elif section_id == "sec-budget":
            content = f"经费预算已形成事实：预算总额{budget_total or '待补充'}；预算明细：{budget_items or '待补充'}。定稿前需按申报通知和财务口径复核。"
    elif document_type == "closing_report":
        if section_id == "sec-summary":
            content = f"《{title}》结题概况建议先交代周期与任务边界。当前事实：项目周期为{cycle or '待补充'}。"
        elif section_id == "sec-process":
            content = f"研究过程应按关键节点梳理，不扩大未提供材料。当前可写入：{practice}"
        elif section_id == "sec-results":
            content = f"研究成果应区分已形成成果和仍待补证材料。当前已确认：{actual}"
        elif section_id == "sec-reflection":
            content = f"问题与反思建议写成“限制-原因-改进”的闭环。当前风险或不足：{risks}"
    elif document_type == "achievement_report":
        if section_id == "sec-highlight":
            content = f"成果亮点建议围绕可展示证据展开，避免夸大成效。当前可展示成果：{actual}"
        elif section_id == "sec-timeline":
            content = f"过程时间线可按周期、实践记录和成果形成三个节点展示。当前周期：{cycle or '待补充'}。"
        elif section_id == "sec-data":
            content = f"量化成果只能使用事实表已有数据。当前样本/范围：{sample or '待补充'}；成果数量：{actual or '待补充'}。"
        elif section_id == "sec-next":
            content = f"推广与下一步应从已有成果自然延伸。当前可承接成果：{expected or actual or '待补充'}。"

    if not content or "None" in content:
        available = [field_text(fact_by_field_map, field) for field in ("project.title", "goals.mainGoal", "basis.practiceRecords", "outcomes.expected") if field_text(fact_by_field_map, field)]
        content = "；".join(available) if available else "当前材料不足，需补充后再生成正文。"
    return append_section_limit_note(content, missing_in_section, conflicts_in_section)


def section_additional_fact_fields(document_type: str, section_id: str) -> list[str]:
    return {
        ("project_application", "sec-background"): ["goals.mainGoal"],
        ("project_application", "sec-basis"): ["team.leader"],
        ("achievement_report", "sec-next"): ["outcomes.actual"],
    }.get((document_type, section_id), [])


def build_document(fact_table: dict[str, Any], document_type: str) -> dict[str, Any]:
    fact_by_field = {fact["field"]: fact for fact in fact_table["facts"]}
    missing_fields = {item.get("field") for item in fact_table.get("missingFields", []) if isinstance(item, dict)}
    conflict_fields = {item.get("field") for item in fact_table.get("conflicts", []) if isinstance(item, dict)}
    template = template_for(document_type)
    sections: list[dict[str, Any]] = []
    for section in template.get("sections", []):
        required_fields = section.get("requiredFactFields", [])
        referenced_fields = list(dict.fromkeys(required_fields + section_additional_fact_fields(document_type, str(section.get("sectionId", "")))))
        fact_refs = [fact_by_field[field]["factId"] for field in referenced_fields if field in fact_by_field]
        missing_in_section = [field for field in required_fields if field in missing_fields or field not in fact_by_field and field not in conflict_fields]
        conflicts_in_section = [field for field in required_fields if field in conflict_fields]
        if conflicts_in_section:
            status = "needs_user_confirmation"
        elif missing_in_section and section.get("required"):
            status = "needs_evidence"
        else:
            status = "draft" if fact_refs or not section.get("required") else "needs_evidence"
        content = build_section_content(document_type, str(section.get("sectionId", "")), fact_by_field, missing_in_section, conflicts_in_section)
        sections.append(
            {
                "sectionId": section.get("sectionId"),
                "title": section.get("title"),
                "required": bool(section.get("required")),
                "content": content,
                "factRefs": fact_refs,
                "evidenceRefs": [],
                "status": status,
            }
        )
    return {
        "documentId": f"doc-render-{document_type}",
        "documentType": document_type,
        "title": fact_by_field.get("project.title", {}).get("value", "项目文档草稿"),
        "sections": sections,
    }


def should_build_literature_background(config: dict[str, Any], input_obj: dict[str, Any], backend: str | None) -> bool:
    if input_obj.get("enableLiteratureBackground") is True or config.get("enableLiteratureBackground") is True:
        return True
    return backend in {"pedascope", "hybrid"}


def project_keywords(fact_table: dict[str, Any], config: dict[str, Any]) -> list[str]:
    text = " ".join(
        [
            str(config.get("sourceRequest", "")),
            *[str(fact.get("value", "")) for fact in fact_table.get("facts", []) if isinstance(fact, dict)],
        ]
    )
    terms = []
    for term in ["即时反馈", "错因诊断", "讲评", "过程性评价", "小学数学", "课堂观察", "学习证据"]:
        if term in text:
            terms.append(term)
    return list(dict.fromkeys(terms)) or ["教育研究", "课堂改进"]


def compact_background_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized["relation"] = "background_candidate"
    normalized.setdefault("textAvailability", "metadata")
    normalized.setdefault("evidenceLevel", "metadata_verified")
    normalized.setdefault(
        "limits",
        [
            "该候选仅用于研究背景阅读和参考文献草案，不能写入 ProjectFactTable.facts。",
            "正式入文前需通过原文、摘要或用户上传材料形成 EvidenceCard。",
        ],
    )
    return normalized


def build_literature_background(
    *,
    config: dict[str, Any],
    fact_table: dict[str, Any],
    backend: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[str]]:
    input_obj = config.get("input", {})
    if not should_build_literature_background(config, input_obj, backend):
        return [], {}, [], []
    adapters = literature_adapter.default_adapters(backend=backend or "local_mock")
    data_sources = literature_adapter.describe_adapters(adapters)
    facts_by_field = fact_by_field(fact_table)
    topic = fact_value_text(facts_by_field.get("project.title", {}).get("value", "")) or config.get("sourceRequest", "")
    search = literature_adapter.search_papers(
        research_topic=topic,
        keywords=project_keywords(fact_table, config),
        adapters=adapters,
        limit=5,
    )
    report = search.get("corpusSearchReport", {})
    candidates = [compact_background_candidate(candidate) for candidate in report.get("bibliographicCandidates", [])]
    if not candidates:
        candidates = [
            compact_background_candidate(literature_adapter.bibliographic_candidate_from_record(record, index=index, relation="background_candidate"))
            for index, record in enumerate(search.get("records", []), 1)
            if isinstance(record, dict) and record.get("textAvailability") == "metadata"
        ]
    background_report = {
        "backend": backend or "local_mock",
        "queryTopic": topic,
        "candidateCount": report.get("candidateCount", len(candidates)),
        "returnedCount": len(candidates),
        "indexSource": report.get("indexSource", ""),
        "sourceBackends": report.get("sourceBackends", []),
        "readingListReport": report.get("readingListReport", {}),
        "limits": [
            "文献背景候选不能写入 ProjectFactTable.facts。",
            "PedaScope 返回题录和系统生成摘要，不提供原文证据。",
        ],
    }
    warnings = list(report.get("adapterWarnings", []) or [])
    return candidates, background_report, data_sources, warnings


def build_review_alignment_report(fact_table: dict[str, Any], input_obj: dict[str, Any], document_types: list[str], budget_report: dict[str, Any]) -> dict[str, Any]:
    rubrics = load_json(REFERENCES_DIR / "review-rubrics.json").get("rubrics", [])
    project_level = input_obj.get("projectLevel") or "区级课题"
    rubric = next((item for item in rubrics if item.get("projectLevel") == project_level), rubrics[0] if rubrics else {"dimensions": []})
    facts_by_field = fact_by_field(fact_table)
    missing_fields = {item.get("field") for item in fact_table.get("missingFields", []) if isinstance(item, dict)}
    conflict_fields = {item.get("field") for item in fact_table.get("conflicts", []) if isinstance(item, dict)}
    dimension_fields = {
        "problem_value": ["project.level", "policy.alignment", "goals.mainGoal"],
        "research_design": ["goals.mainGoal", "timeline.cycle", "basis.practiceRecords"],
        "basis_feasibility": ["team.leader", "team.memberCount", "basis.practiceRecords", "data.sampleScope"],
        "innovation": ["goals.mainGoal", "outcomes.expected"],
        "outcomes": ["outcomes.expected", "outcomes.actual"],
        "budget": ["budget.total", "budget.items"],
    }
    advice = {
        "problem_value": "把教学现场问题、政策导向和教师已有观察连成一段，不写空泛背景。",
        "research_design": "按目标、内容、方法、阶段任务组织，缺少周期或过程证据时先补材料。",
        "basis_feasibility": "优先使用负责人、成员、课例、样本和成果清单证明可行性。",
        "innovation": "只从材料中已有做法提炼对象、工具、流程或成果形态上的差异。",
        "outcomes": "把预期成果和已形成成果分开写，数量必须来自事实表。",
        "budget": "预算科目、金额和用途必须与研究活动对应，缺金额时不代填。",
    }
    alignments = []
    for dimension in rubric.get("dimensions", []):
        dimension_id = dimension.get("id", "")
        fields = dimension_fields.get(dimension_id, [])
        fact_refs = [facts_by_field[field]["factId"] for field in fields if field in facts_by_field]
        missing = [field for field in fields if field in missing_fields or field not in facts_by_field and field not in conflict_fields]
        conflicts = [field for field in fields if field in conflict_fields]
        status = "needs_user_confirmation" if conflicts else "needs_evidence" if missing else "aligned"
        alignments.append(
            {
                "dimensionId": dimension_id,
                "name": dimension.get("name", dimension_id),
                "scoreWeight": dimension.get("scoreWeight"),
                "criteria": dimension.get("criteria", ""),
                "factRefs": fact_refs,
                "missingFields": missing,
                "conflictFields": conflicts,
                "suggestion": advice.get(dimension_id, "按事实表组织材料，缺失处进入补充清单。"),
                "status": status,
            }
        )
    budget_warnings = budget_report.get("warnings", []) if isinstance(budget_report, dict) else []
    return {
        "rubricId": rubric.get("rubricId", ""),
        "projectLevel": project_level,
        "documentTypes": document_types,
        "alignedDimensions": [item["name"] for item in alignments if item.get("status") == "aligned"],
        "dimensionAlignments": alignments,
        "budgetWarnings": budget_warnings,
    }


def render(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    source_materials = normalize_source_materials(input_obj.get("projectMaterials", []), default_material_type="project_process_record")
    normalized_config = dict(config)
    normalized_input = dict(input_obj)
    normalized_input["projectMaterials"] = source_materials
    normalized_config["input"] = normalized_input
    task_intent = config.get("taskIntent", "project_application")
    requested_document_type = input_obj.get("documentType") or task_intent or "project_application"
    is_document_set = requested_document_type == "document_set" or task_intent == "document_set"
    if is_document_set:
        document_type = "document_set"
        document_types = list(DOCUMENT_TYPES)
    else:
        document_type = requested_document_type if requested_document_type in DOCUMENT_TYPES else "project_application"
        document_types = [document_type]
    fact_table = infer_facts(normalized_config)
    budget_report = fact_table.pop("budgetReport", {"items": [], "warnings": ["未提供预算金额，不能代填具体数值。"]})
    budget_next_actions = fact_table.pop("budgetNextActions", [])
    ensure_missing_fields_for_documents(fact_table, document_types)
    backend = selected_backend(config, input_obj)
    literature_background_candidates, literature_background_report, literature_sources, literature_warnings = build_literature_background(
        config=config,
        fact_table=fact_table,
        backend=backend,
    )
    documents = [build_document(fact_table, document_type) for document_type in document_types]
    document = documents[0] if documents else {}
    document_set = {
        "setId": "docset-render-001",
        "generationMode": "three_format_document_set",
        "documents": documents,
    } if is_document_set else {}
    cross_document_report = build_cross_document_consistency_report(fact_table, documents)
    presentation_support = build_presentation_support(fact_table) if is_document_set or "achievement_report" in document_types else {}
    review_alignment_report = build_review_alignment_report(fact_table, input_obj, document_types, budget_report if isinstance(budget_report, dict) else {})
    budget_warnings = budget_report.get("warnings", []) if isinstance(budget_report, dict) else []
    coverages = [required_section_coverage(item) for item in documents]
    coverage = round(sum(coverages) / len(coverages), 2) if coverages else 1.0
    all_warnings = list(budget_warnings) + list(literature_warnings) + [f"缺失字段：{item.get('field')}" for item in fact_table["missingFields"] if isinstance(item, dict)] + [f"冲突字段：{item.get('field')}" for item in fact_table["conflicts"] if isinstance(item, dict)]
    status = "warn" if all_warnings or fact_table["missingFields"] or fact_table["conflicts"] or cross_document_report["status"] != "pass" else "pass"
    next_actions = []
    if fact_table["missingFields"]:
        next_actions.append("补充 ProjectFactTable.missingFields 中列出的材料。")
    if fact_table["conflicts"]:
        next_actions.append("先确认 ProjectFactTable.conflicts 中的冲突字段，再生成定稿。")
    if cross_document_report.get("missingSharedFields"):
        next_actions.append("补齐跨文档共享字段后，再生成三份文档的定稿版本。")
    next_actions.extend(budget_next_actions)
    payload = {
        "requestId": config.get("requestId", "req-project-proposal-render-001"),
        "skillId": "project-proposal-skill",
        "taskIntent": task_intent,
        "status": status,
        "summary": "已先抽取 ProjectFactTable，再按模板生成文档框架。",
        "inputSummary": {
            "sourceRequest": config.get("sourceRequest", ""),
            "documentType": document_type,
            "literatureBackend": backend or "local_mock",
            "projectLevel": input_obj.get("projectLevel", ""),
            "projectMaterialCount": len(input_obj.get("projectMaterials", []) or []),
            "budgetProvided": bool(input_obj.get("budgetInfo")),
            "teamInfoProvided": bool(input_obj.get("teamInfo")),
            "assumptions": config.get("assumptions", []),
            "constraints": config.get("constraints", {}),
        },
        "warnings": all_warnings,
        "dataSourceReport": build_project_data_source_report(normalized_config, document_types, literature_sources),
        "artifacts": [],
        "result": {
            "sourceMaterials": source_materials,
            "projectFactTable": fact_table,
            "documentDraft": document if task_intent != "fact_extraction" and not is_document_set else {},
            "documentSet": document_set,
            "reviewAlignmentReport": review_alignment_report,
            "budgetReport": budget_report,
            "literatureBackgroundCandidates": literature_background_candidates,
            "literatureBackgroundReport": literature_background_report,
            "consistencyReport": {
                "conflictCount": len(fact_table["conflicts"]),
                "missingFieldCount": len(fact_table["missingFields"]),
                "notes": ["存在冲突字段，需人工确认。"] if fact_table["conflicts"] else ["缺失字段已进入补材料清单。"] if fact_table["missingFields"] else [],
            },
            "crossDocumentConsistencyReport": cross_document_report,
            "presentationSupport": presentation_support,
        },
        "handoff": {
            "projectFactTableSummary": {
                "projectId": fact_table["projectId"],
                "factCount": len(fact_table["facts"]),
                "conflictCount": len(fact_table["conflicts"]),
                "missingFields": [item.get("field") for item in fact_table["missingFields"] if isinstance(item, dict)],
            },
            "documentSummary": {
                "documentType": "document_set" if is_document_set else document_types[0],
                "documentTypes": document_types,
                "documentCount": len(documents),
                "requiredSectionCoverage": coverage,
                "crossDocumentStatus": cross_document_report.get("status"),
            },
            "literatureBackgroundCandidates": literature_background_candidates[:5],
        },
        "qualityReport": {
            "status": status,
            "checks": [
                {"id": "fact_table_first", "status": "pass"},
                {"id": "template_sections", "status": "pass"},
                {"id": "cross_document_consistency", "status": "pass" if cross_document_report.get("status") == "pass" else "warn"},
            ],
            "warnings": all_warnings,
            "metrics": {
                "factCount": len(fact_table["facts"]),
                "conflictCount": len(fact_table["conflicts"]),
                "missingFieldCount": len(fact_table["missingFields"]),
                "templateSectionCoverage": coverage,
                "budgetWarningCount": len(budget_warnings),
                "documentCount": len(documents),
                "crossDocumentConflictCount": len(cross_document_report.get("conflicts", [])),
                "crossDocumentMissingSharedFieldCount": len(cross_document_report.get("missingSharedFields", [])),
                "literatureBackgroundCandidateCount": len(literature_background_candidates),
            },
        },
        "provenanceReport": {
            "sourceCount": len(source_materials),
            "verifiedSourceCount": len([item for item in source_materials if item.get("sourceStatus") != "synthetic"]),
            "unsupportedClaimCount": len(fact_table["missingFields"]) + len(fact_table["conflicts"]),
        },
        "nextActions": next_actions,
    }
    return attach_education_generator_runtime(
        payload,
        skill_id="project-proposal-skill",
        task_intent=str(task_intent),
        used_for=["document_section_drafting", "highlight_extraction", "project_material_language_packaging"],
        generation_mode="fact_table_first_with_innospark_235b_generator_contract",
    )


def render_markdown(data: dict[str, Any]) -> str:
    result = data.get("result", {})
    fact_table = result.get("projectFactTable", {})
    document = result.get("documentDraft", {})
    document_set = result.get("documentSet", {})
    documents = []
    if isinstance(document, dict) and document:
        documents = [document]
    elif isinstance(document_set, dict):
        documents = document_set.get("documents", []) if isinstance(document_set.get("documents"), list) else []
    lines = [
        "# 项目申报助手结果",
        "",
        f"请求 ID：`{data.get('requestId')}`",
        f"校验状态：`{data.get('qualityReport', {}).get('status')}`",
        "",
        "## 项目事实表",
        "",
    ]
    for fact in fact_table.get("facts", []):
        lines.append(f"- `{fact.get('factId')}` {fact.get('field')}：{fact_value_text(fact.get('value'))}（来源：{', '.join(fact.get('sourceRefs', []))}）")
    lines.append("")
    if fact_table.get("missingFields"):
        lines.extend(["## 缺失字段", ""])
        for item in fact_table.get("missingFields", []):
            if isinstance(item, dict):
                lines.append(f"- {item.get('field')}：{item.get('reason', '')}")
            else:
                lines.append(f"- {item}")
        lines.append("")
    if documents:
        lines.extend(["## 文档框架", ""])
        for document in documents:
            lines.extend([f"### {document.get('documentType')}：{document.get('title')}", ""])
            for section in document.get("sections", []):
                lines.extend(
                    [
                        f"#### {section.get('title')}",
                        "",
                        f"- 状态：`{section.get('status')}`",
                        f"- 事实引用：{', '.join(section.get('factRefs', [])) or '无'}",
                        "",
                        section.get("content", ""),
                        "",
                    ]
                )
    background_candidates = result.get("literatureBackgroundCandidates", [])
    if background_candidates:
        lines.extend(["## 文献背景候选", ""])
        for candidate in background_candidates[:5]:
            lines.extend(
                [
                    f"- `{candidate.get('paperId')}`：{candidate.get('title')}",
                    f"  - 来源级别：`{candidate.get('evidenceLevel')}` / `{candidate.get('textAvailability')}`",
                    f"  - 限制：{'；'.join(candidate.get('limits', []))}",
                ]
            )
        lines.append("")
    presentation_support = result.get("presentationSupport", {})
    if presentation_support:
        lines.extend(["## 成果汇报辅助", "", "### 时间线", ""])
        for item in presentation_support.get("timelineItems", []):
            lines.extend(
                [
                    f"- {item.get('label')}：{item.get('description')}（{', '.join(item.get('factRefs', [])) or '待补'}）",
                ]
            )
        lines.extend(["", "### 图表建议", ""])
        for item in presentation_support.get("chartSuggestions", []):
            lines.append(f"- {item.get('title')}：{item.get('chartType')}，状态 `{item.get('status')}`")
        lines.append("")
    budget_warnings = result.get("budgetReport", {}).get("warnings", [])
    if budget_warnings:
        lines.extend(["## 预算提示", ""])
        lines.extend(f"- {item}" for item in budget_warnings)
        lines.append("")
    next_actions = data.get("nextActions", [])
    if next_actions:
        lines.extend(["## 下一步", ""])
        lines.extend(f"- {item}" for item in next_actions)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染项目申报助手 JSON 产物。")
    parser.add_argument("input_or_output_base", help="旧入口为请求 JSON；使用 --config 时为输出 base")
    parser.add_argument("--config", help="模板式入口的请求 JSON 文件：render_x.py <output_base> --config <request>")
    parser.add_argument("--output", help="输出 JSON 文件；默认写入 generated-outputs/<requestId>.json")
    parser.add_argument("--validate", action="store_true", help="输出后立即运行 validate_project_proposal.py")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else Path(args.input_or_output_base)
    config = load_json(config_path)
    output = render(config)
    if args.output:
        output_path = Path(args.output)
    elif args.config:
        output_base = Path(args.input_or_output_base)
        output_path = output_base if output_base.suffix == ".json" else output_base.with_suffix(".json")
    else:
        output_path = OUTPUT_DIR / f"{output['requestId']}.json"
    md_path = output_path.with_suffix(".md")
    output["artifacts"] = [
        {"type": "json", "path": str(output_path), "description": "结构化项目申报结果"},
        {"type": "markdown", "path": str(md_path), "description": "教师可读项目文档报告"},
    ]
    write_json(output_path, output)
    write_markdown(md_path, render_markdown(output))
    print(output_path)
    print(md_path)
    if args.validate:
        return subprocess.run(["python3", str(VALIDATE_SCRIPT), str(output_path)], check=False).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
