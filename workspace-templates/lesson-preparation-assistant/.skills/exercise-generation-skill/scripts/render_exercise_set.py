#!/usr/bin/env python3
"""出题智能体离线渲染脚本。

根据请求配置和 references 中的内部示例数据生成：
  - 结构化练习/作业 JSON
  - 教师可读 Markdown

当前重点闭环是五年级数学「分数的加法和减法」单元出题。
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_exercise_set.py"

# ── InnoSpark Generator 配置 ─────────────────────
PROJECT_ROOT = ROOT.parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

import os as _os
if ENV_PATH.exists():
    for _line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        _key = _key.strip()
        _value = _value.strip().strip('"').strip("'")
        if _key and _key not in _os.environ:
            _os.environ[_key] = _value

INNOSPARK_API_KEY = _os.getenv("INNOSPARK_AIECNU_API_KEY") or _os.getenv("INNOSPARK_API_KEY")
INNOSPARK_BASE_URL = _os.getenv("INNOSPARK_AIECNU_BASE_URL", "https://innospark-api.aiecnu.net/v1")
INNOSPARK_MODEL = "InnoSpark-235B"


def _get_innospark_client():
    if not INNOSPARK_API_KEY:
        raise RuntimeError("缺少 INNOSPARK_AIECNU_API_KEY 或 INNOSPARK_API_KEY 环境变量")
    from openai import OpenAI
    return OpenAI(api_key=INNOSPARK_API_KEY, base_url=INNOSPARK_BASE_URL)


def _call_innospark(system: str, prompt: str, temperature: float = 0.3, max_tokens: int = 8192) -> str:
    client = _get_innospark_client()
    resp = client.chat.completions.create(
        model=INNOSPARK_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("InnoSpark-235B 返回空内容")
    return content


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_references() -> dict[str, Any]:
    names = [
        "curriculum-standards",
        "knowledge-graph",
        "textbook-map",
        "difficulty-rules",
        "misconception-tags",
        "similar-question-groups",
        "seed-question-bank",
    ]
    return {name: load_json(REFERENCES_DIR / f"{name}.json") for name in names}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def output_prefix(path_text: str) -> Path:
    path = Path(path_text)
    if path.suffix:
        return path.with_suffix("")
    return path


def index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item[key]): item for item in items if key in item}


def resolve_textbook_context(config: dict[str, Any], refs: dict[str, Any]) -> dict[str, Any]:
    for textbook in refs["textbook-map"].get("textbooks", []):
        if textbook.get("textbookVersion") != config.get("textbookVersion"):
            continue
        if textbook.get("subject") != config.get("subject"):
            continue
        if textbook.get("grade") != config.get("grade"):
            continue
        if textbook.get("unit") != config.get("unit"):
            continue
        for period in textbook.get("periods", []):
            requested_kps = set(config.get("knowledgePointIds", []))
            period_kps = set(period.get("knowledgePointIds", []))
            if requested_kps and not requested_kps.issubset(period_kps):
                continue
            return {"textbook": textbook, "period": period}
    return {"textbook": {}, "period": {}}


def distribute_counts(total: int, layers: list[str], preferred: dict[str, int] | None = None) -> dict[str, int]:
    if not layers:
        return {}
    if preferred and sum(preferred.get(layer, 0) for layer in layers) == total:
        return {layer: int(preferred.get(layer, 0)) for layer in layers}

    base = total // len(layers)
    remainder = total % len(layers)
    counts = {layer: base for layer in layers}
    priority = [layer for layer in ["B", "C", "A"] if layer in layers]
    priority.extend(layer for layer in layers if layer not in priority)
    for layer in priority[:remainder]:
        counts[layer] += 1
    return counts


def normalize_mix(mix: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(mix, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, value in mix.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count > 0:
            normalized[str(key)] = count
    return normalized


def resolve_count_targets(
    total: int,
    keys: list[str],
    preferred: dict[str, Any] | None = None,
) -> dict[str, int]:
    preferred_counts = normalize_mix(preferred)
    if keys and preferred_counts and sum(preferred_counts.get(key, 0) for key in keys) == total:
        return {key: preferred_counts.get(key, 0) for key in keys}
    if preferred_counts and sum(preferred_counts.values()) == total:
        return preferred_counts
    return distribute_counts(total, keys, preferred_counts)


def default_difficulty_keys(config: dict[str, Any]) -> list[str]:
    difficulty_range = config.get("difficultyRange")
    if (
        isinstance(difficulty_range, list)
        and len(difficulty_range) == 2
        and all(isinstance(item, int) for item in difficulty_range)
    ):
        start, end = difficulty_range
        return [str(item) for item in range(start, end + 1)]
    return ["1", "2", "3", "4"]


def build_layer_plan(config: dict[str, Any], refs: dict[str, Any]) -> list[dict[str, Any]]:
    rules = refs["difficulty-rules"]
    task_type = config.get("taskType", "layered_homework")
    defaults = rules.get("taskTypeDefaults", {}).get(task_type, {})
    layers = config.get("layers") or defaults.get("layers") or ["A", "B", "C"]
    question_count = int(config.get("questionCount") or defaults.get("questionCount") or 9)
    layer_mix = config.get("layerMix") or defaults.get("layerMix")
    counts = resolve_count_targets(question_count, layers, layer_mix)

    plan = []
    for layer in layers:
        layer_rule = rules.get("layers", {}).get(layer, {})
        plan.append(
            {
                "layer": layer,
                "name": layer_rule.get("name", f"{layer} 层"),
                "targetCount": counts.get(layer, 0),
                "difficultyRange": layer_rule.get("difficultyRange", []),
                "goal": layer_rule.get("goal", ""),
                "cognitiveLevel": layer_rule.get("cognitiveLevel", ""),
            }
        )
    return plan


def build_blueprint_targets(config: dict[str, Any], refs: dict[str, Any]) -> dict[str, Any]:
    rules = refs["difficulty-rules"]
    task_type = config.get("taskType", "layered_homework")
    defaults = rules.get("taskTypeDefaults", {}).get(task_type, {})
    total = int(config.get("questionCount") or defaults.get("questionCount") or 9)
    layers = config.get("layers") or defaults.get("layers") or ["A", "B", "C"]
    question_types = (
        config.get("questionTypes")
        or list(normalize_mix(config.get("questionTypeMix")).keys())
        or list(normalize_mix(defaults.get("questionTypeMix")).keys())
    )
    difficulty_keys = (
        list(normalize_mix(config.get("difficultyMix")).keys())
        or list(normalize_mix(defaults.get("difficultyMix")).keys())
        or default_difficulty_keys(config)
    )

    return {
        "layerTargets": resolve_count_targets(
            total,
            list(layers),
            config.get("layerMix") or defaults.get("layerMix"),
        ),
        "questionTypeTargets": resolve_count_targets(
            total,
            list(question_types),
            config.get("questionTypeMix") or defaults.get("questionTypeMix"),
        ),
        "difficultyTargets": resolve_count_targets(
            total,
            [str(item) for item in difficulty_keys],
            config.get("difficultyMix") or defaults.get("difficultyMix"),
        ),
        "strictBlueprint": bool(config.get("strictBlueprint", False)),
    }


def question_matches(question: dict[str, Any], config: dict[str, Any], layer: str) -> bool:
    if question.get("subject") != config.get("subject"):
        return False
    if question.get("grade") != config.get("grade"):
        return False
    if config.get("unit") and question.get("unit") != config.get("unit"):
        return False
    if question.get("layer") != layer:
        return False
    requested_kps = set(config.get("knowledgePointIds", []))
    question_kps = set(question.get("knowledgePointIds", []))
    if requested_kps and not question_kps.intersection(requested_kps):
        return False
    requested_types = set(config.get("questionTypes", []))
    if requested_types and question.get("questionType") not in requested_types:
        return False
    return True


def pick_questions(
    config: dict[str, Any],
    refs: dict[str, Any],
    layer_plan: list[dict[str, Any]],
    blueprint_targets: dict[str, Any],
) -> list[dict[str, Any]]:
    bank = refs["seed-question-bank"].get("questions", [])
    type_targets = blueprint_targets.get("questionTypeTargets", {})
    difficulty_targets = blueprint_targets.get("difficultyTargets", {})
    requested_kps = list(config.get("knowledgePointIds", []))
    kp_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    used_source_ids: set[str] = set()
    variant_counter = 1

    def choose_balanced(candidates: list[dict[str, Any]]) -> dict[str, Any]:
        def target_rank(counter: Counter[str], targets: dict[str, int], key: str) -> tuple[int, int, int]:
            if not targets or key not in targets:
                return (0, 0, counter[key])
            current = counter[key]
            target = int(targets.get(key, 0))
            if current < target:
                return (0, -(target - current), current)
            return (1, current - target, current)

        def score(item: dict[str, Any]) -> tuple[Any, ...]:
            matched_kps = [
                kp_id for kp_id in item.get("knowledgePointIds", [])
                if kp_id in requested_kps
            ]
            if not matched_kps:
                kp_score = (999, 999)
            else:
                kp_score = (
                    min(kp_counts[kp_id] for kp_id in matched_kps),
                    sum(kp_counts[kp_id] for kp_id in matched_kps),
                )
            return (
                target_rank(type_counts, type_targets, str(item.get("questionType", ""))),
                target_rank(difficulty_counts, difficulty_targets, str(item.get("difficulty", ""))),
                kp_score,
                item.get("sourceId", ""),
            )

        return sorted(candidates, key=score)[0]

    for layer_item in layer_plan:
        layer = layer_item["layer"]
        target = int(layer_item["targetCount"])
        candidates = [item for item in bank if question_matches(item, config, layer)]
        if not candidates:
            raise RuntimeError(f"没有找到 {layer} 层可用种子题。")

        for index in range(target):
            unused_candidates = [
                item for item in candidates
                if item.get("sourceId") not in used_source_ids
            ]

            if unused_candidates:
                chosen = copy.deepcopy(choose_balanced(unused_candidates))
                used_source_ids.add(chosen["sourceId"])
            else:
                chosen = copy.deepcopy(choose_balanced(candidates))
                original_source_id = chosen["sourceId"]
                chosen["sourceId"] = f"{original_source_id}-variant-{variant_counter}"
                chosen["variantOf"] = original_source_id
                chosen["stem"] = f"{chosen['stem']}（变式：请写出关键步骤）"
                variant_counter += 1

            chosen["id"] = f"q{len(selected) + 1:03d}"
            selected.append(chosen)
            kp_counts.update(
                kp_id for kp_id in chosen.get("knowledgePointIds", [])
                if kp_id in requested_kps
            )
            type_counts.update([str(chosen.get("questionType", ""))])
            difficulty_counts.update([str(chosen.get("difficulty", ""))])

    return selected


def collect_forbidden_scope(config: dict[str, Any], refs: dict[str, Any]) -> list[str]:
    standards = index_by(refs["curriculum-standards"].get("standards", []), "standardId")
    kps = index_by(refs["knowledge-graph"].get("knowledgePoints", []), "knowledgePointId")
    forbidden: list[str] = []
    for kp_id in config.get("knowledgePointIds", []):
        kp = kps.get(kp_id, {})
        forbidden.extend(kp.get("forbiddenScope", []))
        for std_id in kp.get("standardIds", []):
            forbidden.extend(standards.get(std_id, {}).get("forbiddenScope", []))
    return sorted(set(forbidden))


def build_coverage_report(config: dict[str, Any], questions: list[dict[str, Any]]) -> dict[str, Any]:
    requested = config.get("knowledgePointIds", [])
    counts: Counter[str] = Counter()
    type_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for question in questions:
        for kp_id in question.get("knowledgePointIds", []):
            counts[kp_id] += 1
            type_counts[kp_id][question.get("questionType", "未标注")] += 1

    return {
        "requestedKnowledgePointIds": requested,
        "coveredKnowledgePointIds": [kp_id for kp_id in requested if counts[kp_id] > 0],
        "uncoveredKnowledgePointIds": [kp_id for kp_id in requested if counts[kp_id] == 0],
        "coverageByKnowledgePoint": {
            kp_id: {
                "questionCount": counts[kp_id],
                "questionTypes": dict(type_counts[kp_id]),
            }
            for kp_id in requested
        },
    }


def build_difficulty_report(questions: list[dict[str, Any]]) -> dict[str, Any]:
    by_layer: dict[str, list[int]] = defaultdict(list)
    by_difficulty: Counter[int] = Counter()
    for question in questions:
        difficulty = int(question.get("difficulty", 0))
        by_layer[question.get("layer", "未分层")].append(difficulty)
        by_difficulty[difficulty] += 1

    return {
        "byLayer": {
            layer: {
                "questionCount": len(values),
                "min": min(values),
                "max": max(values),
                "average": round(sum(values) / len(values), 2),
            }
            for layer, values in by_layer.items()
            if values
        },
        "byDifficulty": {str(key): value for key, value in sorted(by_difficulty.items())},
    }


def build_risk_report(
    config: dict[str, Any],
    refs: dict[str, Any],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    forbidden_scope = collect_forbidden_scope(config, refs)
    over_scope_risks = []
    for question in questions:
        haystack = " ".join(
            [
                question.get("stem", ""),
                question.get("answer", ""),
                " ".join(question.get("solutionSteps", [])),
            ]
        )
        matched = [term for term in forbidden_scope if term and term in haystack]
        if matched:
            over_scope_risks.append(
                {
                    "questionId": question["id"],
                    "matchedForbiddenScope": matched,
                }
            )

    return {
        "forbiddenScope": forbidden_scope,
        "overScopeRisks": over_scope_risks,
        "notes": ["首批使用内部示例课标与知识点边界，真实业务需由教师或教研员最终确认。"],
    }


def build_teaching_suggestions(refs: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    misconceptions = index_by(refs["misconception-tags"].get("misconceptions", []), "id")
    counts: Counter[str] = Counter()
    for question in questions:
        counts.update(question.get("commonErrors", []))

    suggestions = []
    for error_id, count in counts.most_common():
        item = misconceptions.get(error_id, {})
        suggestions.append(
            {
                "misconceptionId": error_id,
                "name": item.get("name", error_id),
                "relatedQuestionCount": count,
                "symptom": item.get("symptom", ""),
                "remediation": item.get("remediation", ""),
            }
        )
    return suggestions


def build_replacement_suggestions(refs: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = refs.get("similar-question-groups", {}).get("groups", [])
    group_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups:
        for source_id in group.get("questionIds", []):
            group_index[source_id].append(group)

    selected_source_ids = {question.get("sourceId") for question in questions}
    suggestions: list[dict[str, Any]] = []
    for question in questions:
        source_id = question.get("sourceId")
        alternatives = []
        for group in group_index.get(source_id, []):
            for candidate_source_id in group.get("questionIds", []):
                if candidate_source_id == source_id or candidate_source_id in selected_source_ids:
                    continue
                alternatives.append(
                    {
                        "sourceId": candidate_source_id,
                        "groupId": group.get("groupId", ""),
                        "methodTag": group.get("methodTag", ""),
                        "replaceRule": group.get("replaceRule", ""),
                    }
                )
        if alternatives:
            suggestions.append(
                {
                    "questionId": question.get("id"),
                    "sourceId": source_id,
                    "alternatives": alternatives[:3],
                }
            )
    return suggestions


def actual_mix(questions: list[dict[str, Any]], key: str) -> dict[str, int]:
    if key == "difficulty":
        return dict(Counter(str(question.get(key, "")) for question in questions))
    return dict(Counter(str(question.get(key, "")) for question in questions))


def mix_matches(actual: dict[str, int], target: dict[str, int]) -> bool:
    if not target:
        return True
    for key, expected in target.items():
        if actual.get(str(key), 0) != int(expected):
            return False
    return sum(actual.values()) == sum(target.values())


def build_mix_check(
    check_id: str,
    label: str,
    actual: dict[str, int],
    target: dict[str, int],
    strict: bool,
) -> dict[str, Any]:
    if not target:
        return {
            "id": check_id,
            "status": "pass",
            "message": f"未设置{label}目标比例，已记录实际分布 {actual}。",
        }
    matched = mix_matches(actual, target)
    return {
        "id": check_id,
        "status": "pass" if matched else "fail" if strict else "warn",
        "message": (
            f"{label}符合目标 {target}。"
            if matched
            else f"{label}未完全匹配目标 {target}，实际 {actual}。"
        ),
    }


def build_quality_report(
    config: dict[str, Any],
    layer_plan: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    coverage_report: dict[str, Any],
    risk_report: dict[str, Any],
    blueprint_targets: dict[str, Any],
) -> dict[str, Any]:
    checks = []
    strict = bool(blueprint_targets.get("strictBlueprint"))
    expected_count = int(config.get("questionCount", len(questions)))
    checks.append(
        {
            "id": "question_count",
            "status": "pass" if len(questions) == expected_count else "fail",
            "message": f"生成 {len(questions)} 题，请求 {expected_count} 题。",
        }
    )

    stems = [question.get("stem", "") for question in questions]
    duplicate_count = len(stems) - len(set(stems))
    checks.append(
        {
            "id": "duplicate_stem",
            "status": "pass" if duplicate_count == 0 else "fail",
            "message": "题干无重复。" if duplicate_count == 0 else f"发现 {duplicate_count} 个重复题干。",
        }
    )

    for item in layer_plan:
        layer = item["layer"]
        actual = sum(1 for question in questions if question.get("layer") == layer)
        target = int(item["targetCount"])
        checks.append(
            {
                "id": f"layer_{layer}_count",
                "status": "pass" if actual == target else "fail",
                "message": f"{layer} 层生成 {actual} 题，目标 {target} 题。",
            }
        )

    uncovered = coverage_report.get("uncoveredKnowledgePointIds", [])
    checks.append(
        {
            "id": "knowledge_coverage",
            "status": "pass" if not uncovered else "fail",
            "message": "请求知识点均已覆盖。" if not uncovered else f"未覆盖知识点：{', '.join(uncovered)}。",
        }
    )

    over_scope = risk_report.get("overScopeRisks", [])
    checks.append(
        {
            "id": "over_scope",
            "status": "pass" if not over_scope else "fail",
            "message": "未发现明显超纲风险。" if not over_scope else f"发现 {len(over_scope)} 个超纲风险。",
        }
    )
    checks.append(
        build_mix_check(
            "question_type_mix",
            "题型比例",
            actual_mix(questions, "questionType"),
            blueprint_targets.get("questionTypeTargets", {}),
            strict,
        )
    )
    checks.append(
        build_mix_check(
            "difficulty_mix",
            "难度比例",
            actual_mix(questions, "difficulty"),
            blueprint_targets.get("difficultyTargets", {}),
            strict,
        )
    )

    return {
        "status": "pass" if all(item["status"] != "fail" for item in checks) else "fail",
        "checks": checks,
        "warnings": [
            "难度、分层和区分度为规则型近似，不代表真实测量学参数。",
            "当前 references 为内部示例数据，扩学科前需补充真实授权数据。",
        ],
    }


import re as _re


def _extract_json_array(text: str) -> list:
    """从模型输出中提取 JSON 题目数组。"""
    text = text.strip()
    for attempt in [text] + [
        m.group(1).strip()
        for m in _re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, flags=_re.IGNORECASE)
    ]:
        try:
            parsed = json.loads(attempt)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "questions" in parsed:
                return parsed["questions"]
        except (json.JSONDecodeError, ValueError):
            continue
    # 最后尝试找 JSON 数组
    for m in _re.finditer(r"\[[\s\S]*\]", text):
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    raise ValueError("无法从模型输出中提取 JSON 题目数组")


def build_generator_prompt(
    config: dict[str, Any],
    refs: dict[str, Any],
    layer_plan: list[dict[str, Any]],
    blueprint_targets: dict[str, Any],
    batch_layers: list[str] | None = None,
    batch_count: int = 10,
) -> str:
    """构建注入专家知识的 Generator prompt。"""
    # ── 课标边界 ──
    standards = index_by(refs["curriculum-standards"].get("standards", []), "standardId")
    kps_graph = index_by(refs["knowledge-graph"].get("knowledgePoints", []), "knowledgePointId")
    kp_bounds = []
    for kp_id in config.get("knowledgePointIds", []):
        kp = kps_graph.get(kp_id, {})
        bounds = [kp.get("name", kp_id)]
        std_ids = kp.get("standardIds", [])
        for sid in std_ids:
            std = standards.get(sid, {})
            bounds.append(f"课标: {std.get('contentRequirement', '')}")
        bounds.append(f"禁止范围: {kp.get('forbiddenScope', [])}")
        kp_bounds.append("\n  ".join(bounds))

    # ── 难度规则 ──
    rules = refs["difficulty-rules"]
    layer_defs = rules.get("layers", {})
    layer_desc = []
    for lp in layer_plan:
        ldef = layer_defs.get(lp["layer"], {})
        layer_desc.append(
            f"{lp['layer']}层({ldef.get('name', lp['layer'])}): "
            f"难度{ldef.get('difficultyRange', [])}, "
            f"认知水平={ldef.get('cognitiveLevel', '')}, "
            f"目标={ldef.get('goal', '')}"
        )

    # ── 蓝图 ──
    bp_lines = []
    for lp in layer_plan:
        bp_lines.append(f"  {lp['layer']}层: {lp['targetCount']}题")
    bp_lines.append(f"  题型目标: {blueprint_targets.get('questionTypeTargets', {})}")
    bp_lines.append(f"  难度目标: {blueprint_targets.get('difficultyTargets', {})}")

    # ── Few-shot 样例 ──
    bank = refs["seed-question-bank"].get("questions", [])
    few_shots = []
    for lp in layer_plan:
        layer_qs = [
            q for q in bank
            if q.get("layer") == lp["layer"]
            and set(q.get("knowledgePointIds", [])) & set(config.get("knowledgePointIds", []))
        ]
        # 每种题型抽1题
        seen_types = set()
        for q in layer_qs:
            qt = q.get("questionType", "")
            if qt not in seen_types:
                seen_types.add(qt)
                few_shots.append({
                    "layer": lp["layer"],
                    "questionType": qt,
                    "difficulty": q.get("difficulty", 2),
                    "stem": q.get("stem", ""),
                    "answer": q.get("answer", ""),
                    "solutionSteps": q.get("solutionSteps", []),
                })
            if len(seen_types) >= 2:
                break

    # ── 硬性要求 ──
    batch_info = ""
    if batch_layers:
        batch_info = f"\n\n## 本次批次限定\n只生成以下分层的题目: {', '.join(batch_layers)}"

    prompt = f"""你是资深小学数学命题专家，精通新课标核心素养导向的命题设计。

## 课标与知识点边界

{chr(10).join(kp_bounds)}

## 难度分层规则

{chr(10).join(layer_desc)}

## 出题蓝图

{chr(10).join(bp_lines)}
{batch_info}

## Few-shot 样例（保持风格一致）

{json.dumps(few_shots, ensure_ascii=False, indent=2)}

## 硬性要求

1. 输出为 JSON 数组，每个元素一道题，共 {batch_count} 题。
2. 每道题严格包含: id, knowledgePointIds, layer, questionType, difficulty, cognitiveLevel, stem, answer, solutionSteps, commonErrors, scorePoints, teachingNote。
3. 分数字用 LaTeX \\frac{{分子}}{{分母}} 格式。
4. A层题 difficulty=1-2, B层题 difficulty=2-3, C层题 difficulty=3-5。
5. 每道题必须给出 1-2 个 commonErrors（错因标签）和一个 teachingNote。
6. 题目间不能雷同——注意变式。
7. 按蓝图指定的题型和难度比例出题。
8. 不要超纲（不得涉及禁止范围内的内容）。
9. knowledgePointIds 必须使用以下精确 ID，不能使用中文名称: {json.dumps(config.get('knowledgePointIds', []))}。
10. 所有分数答案必须约到最简分数（如 6/9 必须写为 2/3）。
11. 只输出 JSON 数组，不要任何额外文字。"""

    return prompt


def generate_questions_via_model(
    config: dict[str, Any],
    refs: dict[str, Any],
    layer_plan: list[dict[str, Any]],
    blueprint_targets: dict[str, Any],
    batch_size: int = 10,
) -> list[dict[str, Any]]:
    """调用 InnoSpark-235B 动态生成题目。"""
    all_questions = []
    total = int(config.get("questionCount", 9))
    remaining = total

    # 按层分组出题，每层一批
    for lp in layer_plan:
        layer = lp["layer"]
        layer_target = int(lp["targetCount"])
        if layer_target <= 0:
            continue

        print(f"  🤖 InnoSpark 生成 {layer}层 {layer_target} 题...", flush=True)

        prompt = build_generator_prompt(
            config, refs, layer_plan, blueprint_targets,
            batch_layers=[layer], batch_count=layer_target
        )

        system_prompt = (
            f"你是小学数学命题专家。"
            f"严格按照 JSON Schema 输出 {layer_target} 道{layer}层题目。"
            f"只输出 JSON 数组，不输出任何其他文字。"
        )

        for attempt in range(2):
            try:
                raw = _call_innospark(system_prompt, prompt, temperature=0.3, max_tokens=8192)
                questions = _extract_json_array(raw)
            except Exception as e:
                if attempt == 0:
                    print(f"    ⚠️ 第1次失败({e})，重试...", flush=True)
                    import time
                    time.sleep(2)
                    continue
                print(f"    ❌ 重试也失败: {e}", flush=True)
                questions = []

            # 校验并补全
            valid = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                # 确保必填字段
                q.setdefault("id", f"q-gen-{len(all_questions)+len(valid)+1:03d}")
                q.setdefault("sourceId", q["id"])
                q.setdefault("layer", layer)
                q.setdefault("difficulty", {"A": 2, "B": 3, "C": 4}.get(layer, 2))
                q.setdefault("cognitiveLevel", "理解")
                q.setdefault("commonErrors", [])
                q.setdefault("teachingNote", "")
                q.setdefault("scorePoints", 5)
                q.setdefault("estimatedTimeSec", 60)
                q.setdefault("isOriginal", True)
                q.setdefault("licenseNote", "InnoSpark-235B 动态生成·仅供教学使用")
                # 确保 knowledgePointIds 使用精确 ID（修正 Generator 可能用的中文名）
                requested_kps = set(config.get("knowledgePointIds", []))
                q_kps = q.get("knowledgePointIds", [])
                _kps_graph = index_by(refs["knowledge-graph"].get("knowledgePoints", []), "knowledgePointId")
                fixed_kps = []
                for kp in q_kps:
                    if kp in requested_kps:
                        fixed_kps.append(kp)
                if not fixed_kps:
                    # 按知识点名模糊匹配
                    for kp_id in requested_kps:
                        kp_info = _kps_graph.get(kp_id, {})
                        if kp_info.get("name", "") in q_kps:
                            fixed_kps.append(kp_id)
                    if not fixed_kps:
                        fixed_kps = [list(requested_kps)[0]] if requested_kps else []
                q["knowledgePointIds"] = fixed_kps
                valid.append(q)

            all_questions.extend(valid[:layer_target])
            break  # 成功则跳出重试循环

    # 统一编号
    for i, q in enumerate(all_questions):
        q["id"] = f"q{i+1:03d}"

    return all_questions[:total]


def build_exercise_set(config: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    refs = load_references()
    context = resolve_textbook_context(config, refs)
    blueprint_targets = build_blueprint_targets(config, refs)
    layer_plan = build_layer_plan(config, refs)

    if model:
        questions = generate_questions_via_model(config, refs, layer_plan, blueprint_targets)
    else:
        questions = pick_questions(config, refs, layer_plan, blueprint_targets)
    coverage_report = build_coverage_report(config, questions)
    difficulty_report = build_difficulty_report(questions)
    risk_report = build_risk_report(config, refs, questions)
    teaching_suggestions = build_teaching_suggestions(refs, questions)
    replacement_suggestions = build_replacement_suggestions(refs, questions)
    quality_report = build_quality_report(
        config, layer_plan, questions, coverage_report, risk_report, blueprint_targets
    )

    task_type = config.get("taskType", "layered_homework")
    topic = config.get("topic") or context.get("period", {}).get("topic") or "练习"
    task_title_suffix = {
        "classroom_practice": "课堂练习",
        "layered_homework": "分层作业",
        "unit_test": "单元测验",
        "stage_test": "阶段测验",
        "topic_drill": "专题练习",
    }.get(task_type, "练习")

    return {
        "exerciseMeta": {
            "title": f"{topic} {task_title_suffix}",
            "subject": config.get("subject", "学科"),
            "grade": config.get("grade", "年级"),
            "textbookVersion": config.get("textbookVersion", "待确认"),
            "unit": config.get("unit", "待确认"),
            "period": config.get("period", context.get("period", {}).get("period", "待确认")),
            "topic": topic,
            "taskType": task_type,
            "questionCount": len(questions),
            "source": "InnoSpark-235B-dynamic-generation" if model else "internal-sample-seed-question-bank",
        },
        "blueprint": {
            "taskType": task_type,
            "layerPlan": layer_plan,
            "questionTypes": config.get("questionTypes", []),
            "layerTargets": blueprint_targets.get("layerTargets", {}),
            "questionTypeTargets": blueprint_targets.get("questionTypeTargets", {}),
            "difficultyTargets": blueprint_targets.get("difficultyTargets", {}),
            "strictBlueprint": blueprint_targets.get("strictBlueprint", False),
            "knowledgePointIds": config.get("knowledgePointIds", []),
            "lessonBoundary": context.get("period", {}).get("lessonBoundary", "未匹配教材边界。"),
            "requirements": config.get("requirements", ""),
        },
        "questions": questions,
        "answerKey": [
            {
                "questionId": question["id"],
                "answer": question.get("answer", ""),
                "solutionSteps": question.get("solutionSteps", []),
                "scorePoints": question.get("scorePoints", []),
            }
            for question in questions
        ],
        "coverageReport": coverage_report,
        "difficultyReport": difficulty_report,
        "riskReport": risk_report,
        "teachingSuggestions": teaching_suggestions,
        "replacementSuggestions": replacement_suggestions,
        "qualityReport": quality_report,
    }


def render_markdown(data: dict[str, Any]) -> str:
    meta = data["exerciseMeta"]
    lines = [
        f"# {meta['title']}",
        "",
        f"- 学科：{meta['subject']}",
        f"- 年级：{meta['grade']}",
        f"- 教材：{meta['textbookVersion']} · {meta['unit']} · {meta['period']}",
        f"- 课题：{meta['topic']}",
        f"- 题量：{meta['questionCount']} 题",
        "",
        "## 出题蓝图",
        "",
        data["blueprint"].get("lessonBoundary", ""),
        "",
    ]

    for item in data["blueprint"].get("layerPlan", []):
        lines.append(
            f"- {item['layer']} 层（{item.get('name', '')}）：{item['targetCount']} 题，"
            f"难度 {item.get('difficultyRange', [])}。{item.get('goal', '')}"
        )
    if data["blueprint"].get("questionTypeTargets"):
        lines.append(f"- 题型目标：{data['blueprint']['questionTypeTargets']}")
    if data["blueprint"].get("difficultyTargets"):
        lines.append(f"- 难度目标：{data['blueprint']['difficultyTargets']}")

    lines.extend(["", "## 题目", ""])
    current_layer = None
    for question in data["questions"]:
        layer = question.get("layer", "未分层")
        if layer != current_layer:
            current_layer = layer
            lines.extend([f"### {layer} 层", ""])
        lines.append(
            f"{question['id']}. 【{question.get('questionType', '')}｜难度 {question.get('difficulty', '')}】"
            f"{question.get('stem', '')}"
        )
        lines.append("")

    lines.extend(["## 答案与解析", ""])
    current_layer = None
    for question in data["questions"]:
        layer = question.get("layer", "未分层")
        if layer != current_layer:
            current_layer = layer
            lines.extend([f"### {layer} 层", ""])
        lines.append(f"**{question['id']} 答案：** {question.get('answer', '')}")
        for index, step in enumerate(question.get("solutionSteps", []), 1):
            lines.append(f"{index}. {step}")
        if question.get("teachingNote"):
            lines.append(f"讲评提示：{question['teachingNote']}")
        lines.append("")

    lines.extend(["## 覆盖与讲评建议", ""])
    coverage = data["coverageReport"]
    for kp_id, item in coverage.get("coverageByKnowledgePoint", {}).items():
        lines.append(f"- {kp_id}：{item['questionCount']} 题，题型分布 {item['questionTypes']}")
    lines.append("")
    for suggestion in data.get("teachingSuggestions", []):
        lines.append(
            f"- {suggestion['name']}：关联 {suggestion['relatedQuestionCount']} 题。"
            f"{suggestion.get('remediation', '')}"
        )

    replacement_suggestions = data.get("replacementSuggestions", [])
    if replacement_suggestions:
        lines.extend(["", "## 换题建议", ""])
        for item in replacement_suggestions:
            alternatives = "、".join(
                alt["sourceId"] for alt in item.get("alternatives", [])
            )
            lines.append(f"- {item['questionId']} 可替换为：{alternatives}")

    lines.extend(["", "## 质量报告", ""])
    for check in data["qualityReport"].get("checks", []):
        lines.append(f"- {check['id']}：{check['status']}，{check['message']}")
    for warning in data["qualityReport"].get("warnings", []):
        lines.append(f"- 提醒：{warning}")

    return "\n".join(lines) + "\n"


def validate_json(path: Path) -> bool:
    if not VALIDATE_SCRIPT.exists():
        print("警告：未找到验证脚本，跳过验证。")
        return True
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(path)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="生成练习/作业 JSON 与 Markdown。")
    parser.add_argument("output", help="输出路径基名，脚本会在 generated-outputs/ 下创建同名子文件夹")
    parser.add_argument("--config", required=True, help="输入请求 JSON")
    parser.add_argument("--no-validate", action="store_true", help="跳过 JSON 校验")
    parser.add_argument("--model", default=None, help="生成模型名称（如 InnoSpark-235B），不传则使用种子库选题模式")
    args = parser.parse_args()

    config = load_json(Path(args.config))
    if args.model:
        print(f"🎓 动态生成模式: {args.model}", flush=True)
    data = build_exercise_set(config, model=args.model)

    # 输出到独立子文件夹（与 lesson-plan-skill 保持一致）
    output_path = Path(args.output)
    if output_path.suffix in {".json", ".md"}:
        output_path = output_path.with_suffix("")
    if output_path.is_dir():
        # 已是目录，写入内部
        json_path = output_path / f"{output_path.name}.json"
        md_path = output_path / f"{output_path.name}.md"
    else:
        # 在 generated-outputs/ 下创建同名子文件夹
        case_name = output_path.name
        output_dir = output_path.parent / case_name
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{case_name}.json"
        md_path = output_dir / f"{case_name}.md"

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(data), encoding="utf-8")

    print(json_path)
    print(md_path)

    if not args.no_validate and not validate_json(json_path):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
