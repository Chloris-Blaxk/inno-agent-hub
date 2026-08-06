#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[1]
ACTION_VERBS_PATH = ROOT / "references" / "action-verbs.json"

TYPE_ALIASES = {
    "pbl": "PBL",
    "PBL": "PBL",
    "project_based_learning": "PBL",
    "interdisciplinary": "interdisciplinary",
    "cross_subject": "interdisciplinary",
    "cross-disciplinary": "interdisciplinary",
    "ai_integrated": "ai_integrated",
    "ai-integrated": "ai_integrated",
    "AI": "ai_integrated",
    "ai": "ai_integrated"
}

REQUIRED_ROOT_KEYS = [
    "lessonMeta",
    "backgroundAnalysis",
    "coreCompetencies",
    "objectives",
    "teachingFocus",
    "teachingDifficulty",
    "innovationDesign",
    "activityFlow",
    "assessmentRubric",
    "resources",
    "export",
    "qualityReport"
]

# studentAnalysis 对于 PBL 不是根字段（合入 backgroundAnalysis），但对跨学科和AI融合是必需的
ROOT_KEYS_BY_TYPE = {
    "interdisciplinary": ["studentAnalysis"],
    "ai_integrated": ["studentAnalysis"],
}

BACKGROUND_ANALYSIS_FIELDS = {
    "PBL": ["textbookPosition", "priorKnowledge", "inquiryExperience", "collaborationAbility"],
    "interdisciplinary": ["primarySubject", "linkedSubject", "curriculumIntersection"],
    "ai_integrated": ["textbookPosition", "aiInterventionRationale"],
}

STUDENT_ANALYSIS_FIELDS = {
    "interdisciplinary": ["primarySubjectReadiness", "linkedSubjectReadiness", "crossSubjectExperience"],
    "ai_integrated": ["priorKnowledge", "aiToolExperience", "critiqueAbility", "independentThinkingHabit"],
}

TYPE_CONTEXT_FIELDS = {
    "PBL": ["drivingQuestionDirection", "finalProductType", "projectSpan"],
    "interdisciplinary": ["linkedSubject", "integrationNodeDescription", "applicableBoundaryHint"],
    "ai_integrated": ["aiInterventionStage", "useBoundaryHint", "critiqueApproach"]
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_type(value: Any) -> str:
    return TYPE_ALIASES.get(str(value), str(value))


def infer_age_band(grade: str) -> str:
    text = str(grade)
    if any(token in text for token in ["幼儿", "学前", "一年级", "二年级", "1年级", "2年级"]):
        return "lower-primary"
    if any(token in text for token in ["三年级", "四年级", "五年级", "六年级", "3年级", "4年级", "5年级", "6年级"]):
        return "upper-primary"
    if any(token in text for token in ["七年级", "八年级", "九年级", "初中", "7年级", "8年级", "9年级"]):
        return "middle-school"
    if any(token in text for token in ["高一", "高二", "高三", "高中", "10年级", "11年级", "12年级"]):
        return "high-school"
    return "upper-primary"


def non_empty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "；".join(value_to_text(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {value_to_text(val)}" for key, val in value.items())
    return str(value)


def objective_verb(objective: Any) -> str:
    if not isinstance(objective, dict):
        return ""
    return str(objective.get("behaviorVerb", "")).strip()


def collect_ids(items: Any, label: str, failures: list[str]) -> set[str]:
    ids: set[str] = set()
    seen: set[str] = set()
    if not isinstance(items, list):
        return ids
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        if item_id in seen:
            failures.append(f"{label}[{index}] id 重复: {item_id}")
        seen.add(item_id)
        ids.add(item_id)
    return ids


def validate_id_refs(refs: Any, allowed: set[str], source: str, target_label: str, failures: list[str]) -> None:
    for ref in ensure_list(refs):
        ref_text = str(ref).strip()
        if ref_text and ref_text not in allowed:
            failures.append(f"{source} 引用了不存在的 {target_label}: {ref_text}")


def context_value_present(value: Any, text: str) -> bool:
    """Check if a confirmedContext value is explicitly present in the output text.

    Threshold increased to 0.7 (was 0.5) to reduce false positives.
    """
    normalized_text = re.sub(r"\s+", "", text)
    value_text = re.sub(r"\s+", "", value_to_text(value))
    if not value_text:
        return True
    if value_text in normalized_text:
        return True
    tokens = [token for token in re.split(r"[，,；;、/+|（）()\[\]\s]+", value_to_text(value)) if len(token) >= 2]
    if tokens:
        hits = sum(1 for token in tokens if token in text)
        if hits >= min(2, len(tokens)):
            return True
    if len(value_text) < 6:
        return value_text in normalized_text
    shingles = {value_text[index:index + 2] for index in range(len(value_text) - 1)}
    if not shingles:
        return False
    matched = sum(1 for shingle in shingles if shingle in normalized_text)
    return matched / len(shingles) >= 0.7  # Increased from 0.5 to reduce false positives


def validate_document(data: dict[str, Any], request: Optional[dict[str, Any]] = None) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_ROOT_KEYS:
        if key not in data:
            failures.append(f"缺少根字段: {key}")

    # 类型专属根字段
    request = request or {}
    expected_type = normalize_type(request.get("innovationType") or data.get("lessonMeta", {}).get("innovationType"))
    type_required_keys = ROOT_KEYS_BY_TYPE.get(expected_type, [])
    for key in type_required_keys:
        if key not in data:
            failures.append(f"缺少根字段（{expected_type} 必需）: {key}")

    if failures:
        return failures, warnings

    lesson_meta = data.get("lessonMeta", {})
    if not isinstance(lesson_meta, dict):
        failures.append("lessonMeta 必须是对象")
        lesson_meta = {}

    actual_type = normalize_type(lesson_meta.get("innovationType") or data.get("innovationDesign", {}).get("type"))
    if actual_type != expected_type:
        failures.append(f"innovationType 不一致: 期望 {expected_type}, 实际 {actual_type}")

    for key in ["subject", "grade", "topic"]:
        if request.get(key) and lesson_meta.get(key) and str(request[key]).strip() != str(lesson_meta[key]).strip():
            warnings.append(f"lessonMeta.{key} 与请求不一致: 请求 {request[key]}, 输出 {lesson_meta[key]}")

    expected_duration = request.get("durationMin") or lesson_meta.get("durationMin")
    if expected_duration is None:
        failures.append("缺少 durationMin，无法校验总时长")
    else:
        try:
            expected_duration = float(expected_duration)
        except (TypeError, ValueError):
            failures.append("durationMin 必须是数字")
            expected_duration = None

    activity_flow = data.get("activityFlow")
    activity_ids: set[str] = set()
    if not isinstance(activity_flow, list) or not activity_flow:
        failures.append("activityFlow 必须是非空数组")
    else:
        activity_ids = collect_ids(activity_flow, "activityFlow", failures)
        total_duration = 0.0
        for index, activity in enumerate(activity_flow, 1):
            if not isinstance(activity, dict):
                failures.append(f"activityFlow[{index}] 必须是对象")
                continue
            for key in ["id", "stage", "durationMin", "teacherActions", "studentActions", "outputs"]:
                if key not in activity or not non_empty(activity[key]):
                    failures.append(f"activityFlow[{index}] 缺少或为空: {key}")
            try:
                total_duration += float(activity.get("durationMin", 0))
            except (TypeError, ValueError):
                failures.append(f"activityFlow[{index}].durationMin 必须是数字")
        if expected_duration is not None and abs(total_duration - expected_duration) > 0.01:
            failures.append(f"活动总时长不匹配: 期望 {expected_duration:g} 分钟, 实际 {total_duration:g} 分钟")

    action_rules = load_json(ACTION_VERBS_PATH)
    allowed_levels = {item["verb"]: int(item["level"]) for item in action_rules.get("allowedVerbs", [])}
    vague_verbs = set(action_rules.get("discouragedVagueVerbs", []))
    age_band = infer_age_band(str(request.get("grade") or lesson_meta.get("grade") or ""))
    max_level = int(action_rules.get("maxLevelByAgeBand", {}).get(age_band, 4))

    # 新增：coreCompetencies 校验
    core_competencies = data.get("coreCompetencies")
    if not isinstance(core_competencies, list) or not core_competencies:
        failures.append("coreCompetencies 必须是非空数组（中国新课标核心素养维度）")
    else:
        for index, cc in enumerate(core_competencies, 1):
            if not isinstance(cc, dict):
                failures.append(f"coreCompetencies[{index}] 必须是对象")
                continue
            for key in ["id", "dimension", "target"]:
                if key not in cc or not non_empty(cc[key]):
                    failures.append(f"coreCompetencies[{index}] 缺少或为空：{key}")

    objectives = data.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        failures.append("objectives 必须是非空数组")
    else:
        collect_ids(objectives, "objectives", failures)
        for index, objective in enumerate(objectives, 1):
            if not isinstance(objective, dict):
                failures.append(f"objectives[{index}] 必须是对象")
                continue
            for key in ["id", "description", "behaviorVerb", "linkedActivities", "assessmentEvidence"]:
                if key not in objective or not non_empty(objective[key]):
                    failures.append(f"objectives[{index}] 缺少或为空: {key}")
            verb = objective_verb(objective)
            if verb in vague_verbs:
                failures.append(f"objectives[{index}] 使用了模糊行为动词: {verb}")
            elif verb not in allowed_levels:
                failures.append(f"objectives[{index}] 行为动词不在 mock 动词表中: {verb}")
            elif allowed_levels[verb] > max_level:
                failures.append(f"objectives[{index}] 行为动词越级: {verb} 等级 {allowed_levels[verb]} > {age_band} 上限 {max_level}")

    rubric = data.get("assessmentRubric")
    rubric_ids: set[str] = set()
    if not isinstance(rubric, list) or not rubric:
        failures.append("assessmentRubric 必须是非空数组")
    else:
        rubric_ids = collect_ids(rubric, "assessmentRubric", failures)
        for index, item in enumerate(rubric, 1):
            if not isinstance(item, dict):
                failures.append(f"assessmentRubric[{index}] 必须是对象")
                continue
            for key in ["id", "dimension", "excellent", "qualified", "needsImprovement", "evidence"]:
                if key not in item or not non_empty(item[key]):
                    failures.append(f"assessmentRubric[{index}] 缺少或为空: {key}")

    if isinstance(objectives, list):
        for index, objective in enumerate(objectives, 1):
            if not isinstance(objective, dict):
                continue
            validate_id_refs(objective.get("linkedActivities"), activity_ids, f"objectives[{index}].linkedActivities", "activityFlow.id", failures)
            validate_id_refs(objective.get("assessmentEvidence"), rubric_ids, f"objectives[{index}].assessmentEvidence", "assessmentRubric.id", failures)

    if isinstance(activity_flow, list):
        for index, activity in enumerate(activity_flow, 1):
            if not isinstance(activity, dict):
                continue
            validate_id_refs(activity.get("assessmentLinks"), rubric_ids, f"activityFlow[{index}].assessmentLinks", "assessmentRubric.id", failures)

    resources = data.get("resources")
    if not isinstance(resources, list) or not resources:
        failures.append("resources 必须是非空数组")

    export = data.get("export")
    if not isinstance(export, dict):
        failures.append("export 必须是对象")
    else:
        if export.get("format") != "markdown":
            failures.append("export.format 必须是 markdown")
        if not non_empty(export.get("markdown")):
            failures.append("export.markdown 不能为空")

    quality_report = data.get("qualityReport")
    if not isinstance(quality_report, dict):
        failures.append("qualityReport 必须是对象")
    elif "checks" not in quality_report:
        failures.append("qualityReport 缺少 checks")
    elif not isinstance(quality_report.get("checks"), list):
        failures.append("qualityReport.checks 必须是数组")
    if isinstance(quality_report, dict) and "warnings" in quality_report and not isinstance(quality_report.get("warnings"), list):
        failures.append("qualityReport.warnings 必须是数组")

    # teachingFocus / teachingDifficulty
    teaching_focus = data.get("teachingFocus")
    if not non_empty(teaching_focus):
        failures.append("teachingFocus 不能为空")
    teaching_difficulty = data.get("teachingDifficulty")
    if not non_empty(teaching_difficulty):
        failures.append("teachingDifficulty 不能为空")

    # backgroundAnalysis
    background = data.get("backgroundAnalysis")
    if not isinstance(background, dict):
        failures.append("backgroundAnalysis 必须是对象")
    elif expected_type in BACKGROUND_ANALYSIS_FIELDS:
        for field in BACKGROUND_ANALYSIS_FIELDS[expected_type]:
            if not non_empty(background.get(field)):
                failures.append(f"backgroundAnalysis.{field} 不能为空（{expected_type} 必需）")

    # studentAnalysis（PBL 无此字段，跨学科和AI融合必需）
    if expected_type in STUDENT_ANALYSIS_FIELDS:
        student = data.get("studentAnalysis")
        if not isinstance(student, dict):
            failures.append("studentAnalysis 必须是对象（跨学科/AI融合必需）")
        else:
            for field in STUDENT_ANALYSIS_FIELDS[expected_type]:
                if not non_empty(student.get(field)):
                    failures.append(f"studentAnalysis.{field} 不能为空（{expected_type} 必需）")

    innovation = data.get("innovationDesign")
    if not isinstance(innovation, dict):
        failures.append("innovationDesign 必须是对象")
        innovation = {}

    if expected_type == "PBL":
        for key in ["drivingQuestion", "milestones", "finalProduct"]:
            if key not in innovation or not non_empty(innovation[key]):
                failures.append(f"PBL innovationDesign 缺少或为空: {key}")
    elif expected_type == "interdisciplinary":
        for key in ["disciplineConnections", "integrationNodes", "commonProduct", "applicableBoundary"]:
            if key not in innovation or not non_empty(innovation[key]):
                failures.append(f"跨学科 innovationDesign 缺少或为空：{key}")
            # 强化检查：disciplineConnections 和 integrationNodes 必须是数组！
            elif key in ["disciplineConnections", "integrationNodes"] and not isinstance(innovation.get(key), list):
                val_preview = str(innovation.get(key))[:50]
                failures.append(f"跨学科创新设计.{key} 必须是 JSON 数组格式，不能是字符串！错误示例：'{val_preview}...'")
    elif expected_type == "ai_integrated":
        for key in ["aiToolRoles", "interventionStages", "useBoundaries", "studentCritiqueTasks"]:
            if key not in innovation or not non_empty(innovation[key]):
                failures.append(f"AI 融合 innovationDesign 缺少或为空: {key}")
    else:
        failures.append(f"未知 innovationType: {expected_type}")

    confirmed_context = request.get("confirmedContext")
    if isinstance(confirmed_context, dict) and expected_type in TYPE_CONTEXT_FIELDS:
        innovation_text = value_to_text(innovation)
        meta_text = value_to_text(lesson_meta)
        activity_text = value_to_text(data.get("activityFlow"))
        assessment_text = value_to_text(data.get("assessmentRubric"))
        searchable_text = "；".join([innovation_text, meta_text, activity_text, assessment_text])
        for field in TYPE_CONTEXT_FIELDS[expected_type]:
            value = confirmed_context.get(field)
            if field == "projectSpan" and str(lesson_meta.get("durationMin", "")) in value_to_text(value):
                continue
            if non_empty(value) and not context_value_present(value, searchable_text):
                warnings.append(f"confirmedContext.{field} 未在输出设计中明确体现: {value_to_text(value)}")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验创新教案 JSON 输出。")
    parser.add_argument("output_json", help="生成的教案 JSON 路径")
    parser.add_argument("--request", help="原始请求 JSON 路径，用于校验类型和时长")
    parser.add_argument("--strict-context", action="store_true", help="将 confirmedContext 覆盖度警告提升为失败")
    args = parser.parse_args()

    output_path = Path(args.output_json)
    if not output_path.exists():
        print(f"文件不存在: {output_path}")
        return 2

    try:
        data = load_json(output_path)
        request = load_json(Path(args.request)) if args.request else None
    except json.JSONDecodeError as error:
        print(f"JSON 解析失败: {error}")
        return 1

    if not isinstance(data, dict):
        print("失败")
        print("- 输出 JSON 顶层必须是对象")
        return 1

    failures, warnings = validate_document(data, request)
    if args.strict_context:
        context_warnings = [warning for warning in warnings if warning.startswith("confirmedContext.")]
        if context_warnings:
            failures.extend(context_warnings)
            warnings = [warning for warning in warnings if warning not in context_warnings]
    if failures:
        print("失败")
        for failure in failures:
            print(f"- {failure}")
        if warnings:
            print("警告")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    print("通过")
    print(f"- 已检查 {output_path}")
    print("- 根字段、时长、行为动词、ID 引用和类型专属结构已校验")
    if warnings:
        print("警告")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
