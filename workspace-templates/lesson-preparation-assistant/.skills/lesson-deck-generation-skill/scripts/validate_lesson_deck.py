#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VISUAL_SYSTEM = "edu-deck-v1"
LAYOUT_LOCK_VERSION = "edu-layout-lock-v1"

LAYOUTS = {
    "ED01": {"family": "cover", "required": {"headline", "subtitle", "outcome"}},
    "ED02": {"family": "map", "required": {"headline", "route"}},
    "ED03": {"family": "scene", "required": {"headline", "question", "visualBrief"}},
    "ED04": {"family": "scene", "required": {"headline", "prompt", "comparePoints"}},
    "ED05": {"family": "model", "required": {"headline", "keyIdea", "bullets", "visualBrief"}},
    "ED06": {"family": "model", "required": {"headline", "modelSteps"}},
    "ED07": {"family": "flow", "required": {"headline", "example", "steps"}},
    "ED08": {"family": "assessment", "required": {"headline", "tasks"}},
    "ED09": {"family": "assessment", "required": {"headline", "misconception", "correction", "checkQuestion"}},
    "ED10": {"family": "scene", "required": {"headline", "activity"}},
    "ED11": {"family": "model", "required": {"headline", "summary"}},
    "ED12": {"family": "assessment", "required": {"headline", "tickets"}},
}

REQUIRED_ROOT = {
    "deckMeta",
    "curriculumContext",
    "designPlan",
    "lessonOutline",
    "slides",
    "teacherScript",
    "exportPlan",
    "qualityReport",
}

REQUIRED_SLIDE = {
    "id",
    "page",
    "stage",
    "layoutId",
    "title",
    "teachingIntent",
    "screen",
    "teacherScript",
    "visualSlots",
    "feedbackEvidence",
    "timing",
    "notes",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("根对象必须是 JSON object。")
    return data


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def text_len(value: Any) -> int:
    if value is None:
        return 0
    return len(str(value).strip())


def validate_tasks(tasks: Any, idx: int, field: str, errors: list[str]) -> None:
    if not isinstance(tasks, list) or not tasks:
        errors.append(f"Slide {idx}: {field} 必须是非空数组。")
        return
    if len(tasks) > 3:
        errors.append(f"Slide {idx}: {field} 超过 3 项，学生屏幕过密。")
    for task_index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"Slide {idx}: {field}[{task_index}] 必须是 object。")
            continue
        for required in ("content", "target", "feedback"):
            if not has_value(task.get(required)):
                errors.append(f"Slide {idx}: {field}[{task_index}].{required} 不能为空。")


def validate_slide(slide: dict[str, Any], idx: int, errors: list[str], warnings: list[str]) -> None:
    missing = REQUIRED_SLIDE - set(slide)
    if missing:
        errors.append(f"Slide {idx}: 缺少字段 {', '.join(sorted(missing))}。")
        return

    layout_id = slide.get("layoutId")
    if layout_id not in LAYOUTS:
        errors.append(f"Slide {idx}: 未登记版式 {layout_id!r}。")
        return

    screen = slide.get("screen")
    if not isinstance(screen, dict):
        errors.append(f"Slide {idx}: screen 必须是 object。")
        return

    required_fields = LAYOUTS[layout_id]["required"]
    missing_screen = [field for field in sorted(required_fields) if not has_value(screen.get(field))]
    if missing_screen:
        errors.append(f"Slide {idx}: {layout_id} 缺少 screen 字段 {', '.join(missing_screen)}。")

    headline = screen.get("headline", slide.get("title", ""))
    if text_len(headline) > 18:
        warnings.append(f"Slide {idx}: headline 超过 18 个中文字符，建议缩短。")

    visual_slots = slide.get("visualSlots")
    if not isinstance(visual_slots, list) or not visual_slots:
        errors.append(f"Slide {idx}: visualSlots 必须是非空数组。")
    else:
        for slot_index, slot in enumerate(visual_slots, start=1):
            if not isinstance(slot, dict):
                errors.append(f"Slide {idx}: visualSlots[{slot_index}] 必须是 object。")
                continue
            for field in ("id", "type", "ratio", "assetStatus", "description", "prompt"):
                if not has_value(slot.get(field)):
                    errors.append(f"Slide {idx}: visualSlots[{slot_index}].{field} 不能为空。")

    teacher_script = slide.get("teacherScript")
    if not isinstance(teacher_script, dict) or not has_value(teacher_script.get("say")):
        errors.append(f"Slide {idx}: teacherScript.say 不能为空。")
    if not has_value(slide.get("feedbackEvidence")):
        errors.append(f"Slide {idx}: feedbackEvidence 不能为空。")

    timing = slide.get("timing")
    minutes = timing.get("minutes") if isinstance(timing, dict) else None
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        errors.append(f"Slide {idx}: timing.minutes 必须为正数。")

    if layout_id == "ED07":
        steps = screen.get("steps")
        if not isinstance(steps, list) or not (3 <= len(steps) <= 5):
            errors.append(f"Slide {idx}: ED07 steps 必须是 3-5 步。")
        else:
            for step_index, step in enumerate(steps, start=1):
                if not isinstance(step, dict) or not has_value(step.get("content")) or not has_value(step.get("teacherCue")):
                    errors.append(f"Slide {idx}: steps[{step_index}] 必须包含 content 和 teacherCue。")
    if layout_id == "ED08":
        validate_tasks(screen.get("tasks"), idx, "tasks", errors)
    if layout_id == "ED12":
        validate_tasks(screen.get("tickets"), idx, "tickets", errors)
    if layout_id == "ED09" and not has_value(screen.get("checkQuestion")):
        errors.append(f"Slide {idx}: ED09 必须包含 checkQuestion。")
    if layout_id == "ED10":
        activity = screen.get("activity")
        if not isinstance(activity, dict) or not has_value(activity.get("studentAction")) or not has_value(activity.get("feedback")):
            errors.append(f"Slide {idx}: ED10 activity 必须包含 studentAction 和 feedback。")


def validate(data: dict[str, Any], strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_root = REQUIRED_ROOT - set(data)
    if missing_root:
        errors.append(f"缺少根字段: {', '.join(sorted(missing_root))}")
        return errors, warnings

    meta = data.get("deckMeta")
    if not isinstance(meta, dict):
        errors.append("deckMeta 必须是 object。")
        return errors, warnings
    if meta.get("visualSystem") != VISUAL_SYSTEM:
        errors.append(f"deckMeta.visualSystem 必须是 {VISUAL_SYSTEM}。")
    if meta.get("layoutLockVersion") != LAYOUT_LOCK_VERSION:
        errors.append(f"deckMeta.layoutLockVersion 必须是 {LAYOUT_LOCK_VERSION}。")

    context = data.get("curriculumContext")
    if not isinstance(context, dict):
        errors.append("curriculumContext 必须是 object。")
    elif not isinstance(context.get("assumptions"), list):
        errors.append("curriculumContext.assumptions 必须是数组。")

    slides = data.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("slides 必须是非空数组。")
        return errors, warnings

    for idx, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            errors.append(f"Slide {idx}: 必须是 object。")
            continue
        validate_slide(slide, idx, errors, warnings)

    slide_count = len(slides)
    if meta.get("slideCount") != slide_count:
        errors.append(f"deckMeta.slideCount={meta.get('slideCount')} 与 slides 数量 {slide_count} 不一致。")
    if slide_count < 6:
        warnings.append(f"课件页数偏少: {slide_count} 页，可能缺少课堂支架。")
    if slide_count > 14:
        warnings.append(f"课件页数偏多: {slide_count} 页，40 分钟课可能赶课。")

    duration = meta.get("durationMin")
    if isinstance(duration, (int, float)):
        total = sum(float(slide.get("timing", {}).get("minutes", 0)) for slide in slides if isinstance(slide, dict))
        if total > 0 and abs(total - float(duration)) > max(2, float(duration) * 0.1):
            errors.append(f"课件总时长 {total:g} 分钟与 durationMin={duration:g} 偏差过大。")
    else:
        errors.append("deckMeta.durationMin 必须是数字。")

    design_plan = data.get("designPlan")
    if not isinstance(design_plan, list) or len(design_plan) != slide_count:
        errors.append("designPlan 必须与 slides 等长。")
    else:
        slide_ids = {slide.get("id") for slide in slides if isinstance(slide, dict)}
        for item_index, item in enumerate(design_plan, start=1):
            if not isinstance(item, dict):
                errors.append(f"designPlan[{item_index}] 必须是 object。")
                continue
            if item.get("slideId") not in slide_ids:
                errors.append(f"designPlan[{item_index}] slideId 未指向有效 slide。")
            for field in ("layoutId", "reason", "visualSlots", "feedbackEvidence"):
                if not has_value(item.get(field)):
                    errors.append(f"designPlan[{item_index}].{field} 不能为空。")

    teacher_script = data.get("teacherScript")
    if not isinstance(teacher_script, list) or len(teacher_script) != slide_count:
        errors.append("teacherScript 必须与 slides 等长。")

    layout_ids = [slide.get("layoutId") for slide in slides if isinstance(slide, dict)]
    unique_layouts = len(set(layout_ids))
    if slide_count <= 8 and unique_layouts < 6:
        warnings.append(f"{slide_count} 页课件建议至少 6 个不同 ED 版式，当前 {unique_layouts} 个。")
    if slide_count >= 9 and unique_layouts < 8:
        warnings.append(f"{slide_count} 页课件建议至少 8 个不同 ED 版式，当前 {unique_layouts} 个。")

    families = [LAYOUTS.get(layout_id, {}).get("family") for layout_id in layout_ids]
    for index in range(len(families) - 2):
        if families[index] and families[index] == families[index + 1] == families[index + 2]:
            errors.append(f"第 {index + 1}-{index + 3} 页连续使用 {families[index]} 结构。")

    if strict and warnings:
        errors.extend([f"strict warning: {warning}" for warning in warnings])
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 edu-deck-v1 课件 JSON。")
    parser.add_argument("deck_json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    try:
        data = load_json(Path(args.deck_json))
        errors, warnings = validate(data, strict=args.strict)
    except ValueError as exc:
        print(f"lesson deck validation failed: {exc}", file=sys.stderr)
        return 1

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("Lesson deck validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Lesson deck validation passed: {len(data.get('slides', []))} slide(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
