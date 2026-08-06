#!/usr/bin/env python3
"""出题智能体产物校验脚本。"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT_REQUIRED = [
    "exerciseMeta",
    "blueprint",
    "questions",
    "answerKey",
    "coverageReport",
    "difficultyReport",
    "riskReport",
    "teachingSuggestions",
    "replacementSuggestions",
    "qualityReport",
]

QUESTION_REQUIRED = [
    "id",
    "sourceId",
    "layer",
    "questionType",
    "difficulty",
    "knowledgePointIds",
    "stem",
    "answer",
    "solutionSteps",
    "commonErrors",
    "scorePoints",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def validate(data: dict[str, Any], strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in ROOT_REQUIRED:
        if field not in data:
            errors.append(f"缺少根字段：{field}")

    if errors:
        return errors, warnings

    meta = data.get("exerciseMeta", {})
    blueprint = data.get("blueprint", {})
    questions = data.get("questions", [])
    answer_key = data.get("answerKey", [])

    if not isinstance(questions, list) or not questions:
        errors.append("questions 必须是非空数组。")
        return errors, warnings

    expected_count = int(meta.get("questionCount", 0))
    if expected_count and len(questions) != expected_count:
        errors.append(f"题量不一致：exerciseMeta.questionCount={expected_count}，实际={len(questions)}。")

    ids = [question.get("id") for question in questions]
    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"题目 ID 重复：{duplicate_ids}")

    stems = [question.get("stem", "") for question in questions]
    duplicate_stems = [item for item, count in Counter(stems).items() if count > 1]
    if duplicate_stems:
        errors.append(f"题干重复：{duplicate_stems}")

    answer_ids = {item.get("questionId") for item in answer_key}
    missing_answer = [question.get("id") for question in questions if question.get("id") not in answer_ids]
    if missing_answer:
        errors.append(f"answerKey 缺少题目：{missing_answer}")

    for index, question in enumerate(questions, 1):
        for field in QUESTION_REQUIRED:
            if field not in question or not non_empty(question[field]):
                errors.append(f"第 {index} 题缺少或为空：{field}")
        difficulty = question.get("difficulty")
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            errors.append(f"第 {index} 题 difficulty 必须是 1-5 的整数。")

    if meta.get("taskType") == "layered_homework":
        layer_plan = blueprint.get("layerPlan", [])
        if not layer_plan:
            errors.append("分层作业缺少 blueprint.layerPlan。")
        counts = Counter(question.get("layer") for question in questions)
        for item in layer_plan:
            layer = item.get("layer")
            target = int(item.get("targetCount", 0))
            actual = counts[layer]
            if actual != target:
                errors.append(f"{layer} 层题量不一致：目标 {target}，实际 {actual}。")
        for required_layer in ["A", "B", "C"]:
            if required_layer in [item.get("layer") for item in layer_plan] and counts[required_layer] == 0:
                errors.append(f"分层作业缺少 {required_layer} 层题目。")

    coverage = data.get("coverageReport", {})
    uncovered = coverage.get("uncoveredKnowledgePointIds", [])
    if uncovered:
        errors.append(f"存在未覆盖知识点：{uncovered}")

    risk_report = data.get("riskReport", {})
    replacement_suggestions = data.get("replacementSuggestions", [])
    if risk_report.get("overScopeRisks"):
        errors.append(f"存在超纲风险：{risk_report['overScopeRisks']}")

    if not isinstance(replacement_suggestions, list):
        errors.append("replacementSuggestions 必须是数组。")

    quality_report = data.get("qualityReport", {})
    failed_checks = [
        item for item in quality_report.get("checks", [])
        if item.get("status") == "fail"
    ]
    if failed_checks:
        errors.append(f"qualityReport 存在失败检查：{[item.get('id') for item in failed_checks]}")

    if strict:
        type_counts = Counter(question.get("questionType") for question in questions)
        if len(type_counts) < 2:
            errors.append("strict 模式要求至少包含两种题型。")
    elif len(Counter(question.get("questionType") for question in questions)) < 2:
        warnings.append("当前题型少于 2 种，可能不适合正式作业。")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验出题智能体 JSON 产物。")
    parser.add_argument("output_json", help="待校验 JSON 文件")
    parser.add_argument("--strict", action="store_true", help="启用更严格检查")
    args = parser.parse_args()

    path = Path(args.output_json)
    data = load_json(path)
    errors, warnings = validate(data, strict=args.strict)

    if errors:
        print("不通过")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"- 警告：{warning}")
        return 1

    print("通过")
    print(f"- 已检查 {path}")
    print(f"- 题量：{len(data.get('questions', []))}")
    print("- 题量、分层、覆盖、解析、重复和超纲风险已校验")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
