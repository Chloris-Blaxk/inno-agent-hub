#!/usr/bin/env python3
"""校验出题智能体 references 数据的一致性。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
REFERENCE_FILES = {
    "standards": "curriculum-standards.json",
    "knowledge": "knowledge-graph.json",
    "textbook": "textbook-map.json",
    "misconceptions": "misconception-tags.json",
    "similar_groups": "similar-question-groups.json",
    "questions": "seed-question-bank.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_artifact(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_artifact(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_artifact(item) for item in value)
    return isinstance(value, str) and ("「" in value or "」" in value)


def non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def validate(min_questions_per_kp: int = 30) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    refs = {
        name: load_json(REFERENCES_DIR / filename)
        for name, filename in REFERENCE_FILES.items()
    }

    for name, data in refs.items():
        if contains_artifact(data):
            errors.append(f"{REFERENCE_FILES[name]} 仍包含异常分隔符。")

    standards = refs["standards"].get("standards", [])
    knowledge_points = refs["knowledge"].get("knowledgePoints", [])
    misconceptions = refs["misconceptions"].get("misconceptions", [])
    similar_groups = refs["similar_groups"].get("groups", [])
    questions = refs["questions"].get("questions", [])

    standard_ids = {item.get("standardId") for item in standards}
    kp_ids = {item.get("knowledgePointId") for item in knowledge_points}
    misconception_ids = {item.get("id") for item in misconceptions}

    duplicate_source_ids = [
        source_id
        for source_id, count in Counter(q.get("sourceId") for q in questions).items()
        if source_id and count > 1
    ]
    if duplicate_source_ids:
        errors.append(f"题目 sourceId 重复：{duplicate_source_ids}")

    question_ids = {question.get("sourceId") for question in questions}

    required_question_fields = [
        "sourceId",
        "subject",
        "grade",
        "unit",
        "knowledgePointIds",
        "layer",
        "questionType",
        "difficulty",
        "stem",
        "answer",
        "solutionSteps",
        "commonErrors",
        "scorePoints",
    ]
    for index, question in enumerate(questions, 1):
        for field in required_question_fields:
            if not non_empty(question.get(field)):
                errors.append(f"第 {index} 题缺少或为空：{field}")
        for kp_id in question.get("knowledgePointIds", []):
            if kp_id not in kp_ids:
                errors.append(f"题目 {question.get('sourceId')} 引用了未知知识点：{kp_id}")
        for error_id in question.get("commonErrors", []):
            if error_id not in misconception_ids:
                errors.append(f"题目 {question.get('sourceId')} 引用了未知错因：{error_id}")

    for kp in knowledge_points:
        kp_id = kp.get("knowledgePointId")
        for standard_id in kp.get("standardIds", []):
            if standard_id not in standard_ids:
                errors.append(f"知识点 {kp_id} 引用了未知课标：{standard_id}")
        for error_id in kp.get("commonErrors", []):
            if error_id not in misconception_ids:
                errors.append(f"知识点 {kp_id} 引用了未知错因：{error_id}")

    for textbook in refs["textbook"].get("textbooks", []):
        seen_periods: set[str] = set()
        for period in textbook.get("periods", []):
            period_name = period.get("period")
            if period_name in seen_periods:
                warnings.append(f"教材映射中课时重复：{period_name}")
            seen_periods.add(period_name)
            for kp_id in period.get("knowledgePointIds", []):
                if kp_id not in kp_ids:
                    errors.append(f"教材课时 {period_name} 引用了未知知识点：{kp_id}")

    duplicate_group_ids = [
        group_id
        for group_id, count in Counter(group.get("groupId") for group in similar_groups).items()
        if group_id and count > 1
    ]
    if duplicate_group_ids:
        errors.append(f"相似题组 groupId 重复：{duplicate_group_ids}")

    for group in similar_groups:
        group_id = group.get("groupId")
        if not non_empty(group_id):
            errors.append("相似题组缺少 groupId。")
        if group.get("knowledgePointId") not in kp_ids:
            errors.append(f"相似题组 {group_id} 引用了未知知识点：{group.get('knowledgePointId')}")
        if not non_empty(group.get("methodTag")):
            errors.append(f"相似题组 {group_id} 缺少 methodTag。")
        question_ids_in_group = group.get("questionIds", [])
        if len(question_ids_in_group) < 2:
            errors.append(f"相似题组 {group_id} 至少需要 2 道题。")
        for source_id in question_ids_in_group:
            if source_id not in question_ids:
                errors.append(f"相似题组 {group_id} 引用了未知题目：{source_id}")

    counts_by_kp: Counter[str] = Counter()
    for question in questions:
        counts_by_kp.update(question.get("knowledgePointIds", []))

    for kp_id in sorted(kp_ids):
        count = counts_by_kp[kp_id]
        if count < min_questions_per_kp:
            errors.append(
                f"知识点 {kp_id} 题量不足：{count}，要求不少于 {min_questions_per_kp}。"
            )

    return errors, warnings, dict(counts_by_kp)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验出题智能体 references 数据。")
    parser.add_argument(
        "--min-questions-per-kp",
        type=int,
        default=30,
        help="每个知识点的最小题量，默认 30。",
    )
    args = parser.parse_args()

    errors, warnings, counts_by_kp = validate(
        min_questions_per_kp=args.min_questions_per_kp
    )
    if errors:
        print("不通过")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"- 警告：{warning}")
        return 1

    print("通过")
    print("- references 数据 ID、题量、字段完整性和异常分隔符已校验")
    for kp_id, count in sorted(counts_by_kp.items()):
        print(f"- {kp_id}: {count} 题")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
