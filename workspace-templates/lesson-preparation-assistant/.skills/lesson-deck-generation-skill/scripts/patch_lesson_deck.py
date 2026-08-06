#!/usr/bin/env python3
"""Deck JSON 结构补丁脚本。

作为 Generator 输出后的第二层防护，自动修复可预见的确定性结构退化。
职责边界：
- 应该修：字段类型错误、缺失必填键、ID 引用断裂、重建可读格式
- 不应该修：Generator 生成的教学内容本身、需要专业判断的创意性内容

设计原则：
- 透明：每次运行后打印修复了哪些字段、改成了什么值
- 幂等：多次运行不产生累积修改
- 保守：只修结构，不改内容
- 可追溯：将修复记录写入 qualityReport.checks
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LAYOUTS: dict[str, dict[str, Any]] = {
    "ED01": {"name": "Studio Cover", "family": "cover", "slot": ("cover_mark", "symbol_mark", "1:1")},
    "ED02": {"name": "Lesson Journey", "family": "map", "slot": ("journey_map", "route", "16:9")},
    "ED03": {"name": "Hook Scene", "family": "scene", "slot": ("hook_visual", "situation_visual", "16:9")},
    "ED04": {"name": "Inquiry Split", "family": "scene", "slot": ("inquiry_workspace", "thinking_board", "16:9")},
    "ED05": {"name": "Concept Canvas", "family": "model", "slot": ("concept_diagram", "editable_diagram", "16:10")},
    "ED06": {"name": "Board Model", "family": "model", "slot": ("board_model", "editable_board", "16:9")},
    "ED07": {"name": "Example Flow", "family": "flow", "slot": ("step_flow", "editable_step_flow", "16:9")},
    "ED08": {"name": "Practice Lab", "family": "assessment", "slot": ("practice_grid", "editable_tasks", "16:9")},
    "ED09": {"name": "Error Clinic", "family": "assessment", "slot": ("error_pair", "error_correction_pair", "16:9")},
    "ED10": {"name": "Activity Studio", "family": "scene", "slot": ("activity_workspace", "class_activity", "16:9")},
    "ED11": {"name": "Summary Board", "family": "model", "slot": ("summary_board", "editable_board", "16:9")},
    "ED12": {"name": "Exit Ticket", "family": "assessment", "slot": ("exit_ticket", "editable_exit_tasks", "16:9")},
}

VALID_LAYOUT_IDS = set(LAYOUTS.keys())

REQUIRED_ROOT_KEYS = {
    "deckMeta", "curriculumContext", "designPlan", "lessonOutline",
    "slides", "teacherScript", "exportPlan", "qualityReport",
}

REQUIRED_SLIDE_KEYS = {
    "id", "page", "stage", "layoutId", "title", "teachingIntent",
    "screen", "teacherScript", "visualSlots", "feedbackEvidence",
    "timing", "notes",
}

REQUIRED_SCREEN_KEYS_BY_LAYOUT: dict[str, set[str]] = {
    "ED01": {"headline", "subtitle", "outcome"},
    "ED02": {"headline", "route"},
    "ED03": {"headline", "question", "visualBrief"},
    "ED04": {"headline", "prompt", "comparePoints"},
    "ED05": {"headline", "keyIdea", "bullets", "visualBrief"},
    "ED06": {"headline", "modelSteps"},
    "ED07": {"headline", "example", "steps"},
    "ED08": {"headline", "tasks"},
    "ED09": {"headline", "misconception", "correction", "checkQuestion"},
    "ED10": {"headline", "activity"},
    "ED11": {"headline", "summary"},
    "ED12": {"headline", "tickets"},
}


class PatchReport:
    """Collects all fixes applied during patching for transparent reporting."""

    def __init__(self) -> None:
        self.fixes: list[dict[str, Any]] = []
        self.fix_count = 0

    def add(self, path: str, issue: str, before: Any, after: Any) -> None:
        self.fixes.append({
            "path": path,
            "issue": issue,
            "before": self._summarize(before),
            "after": self._summarize(after),
        })
        self.fix_count += 1

    def _summarize(self, value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False)
        if len(text) > 120:
            return text[:117] + "..."
        return text

    def to_checks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "post-patch",
                "status": "fixed" if self.fix_count > 0 else "pass",
                "message": f"patch 脚本修复了 {self.fix_count} 处结构退化",
                "fixes": self.fixes,
            }
        ]

    def print_summary(self) -> None:
        if self.fix_count == 0:
            print("patch: 未发现结构退化，无需修复。")
            return
        print(f"patch: 共修复 {self.fix_count} 处结构退化：")
        for fix in self.fixes:
            print(f"  [{fix['path']}] {fix['issue']}")
            print(f"    修复前: {fix['before']}")
            print(f"    修复后: {fix['after']}")


def ensure_dict(value: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return default or {}


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def patch_root(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure all required root keys exist."""
    for key in REQUIRED_ROOT_KEYS:
        if key not in deck:
            deck[key] = {}
            report.add(f"root.{key}", "缺失根对象必填键，创建空对象", None, {})


def patch_deck_meta(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure deckMeta has required fields with sensible defaults."""
    meta = ensure_dict(deck.get("deckMeta"))
    defaults = {
        "visualSystem": "edu-deck-v1",
        "layoutLockVersion": "edu-layout-lock-v1",
        "subject": "学科",
        "grade": "年级",
        "lessonType": "new_concept",
        "durationMin": 40,
        "slideCount": 0,
        "stylePreset": "daylight",
        "subjectMark": "LESSON",
    }
    for key, default in defaults.items():
        if key not in meta or meta[key] is None:
            old = meta.get(key)
            meta[key] = default
            report.add(f"deckMeta.{key}", "缺失或为空，使用默认值", old, default)
    deck["deckMeta"] = meta


def patch_curriculum_context(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure curriculumContext has required fields."""
    ctx = ensure_dict(deck.get("curriculumContext"))
    defaults = {
        "textbookVersion": "待确认",
        "unit": "待确认",
        "period": "待确认",
        "assumptions": ["未接入真实课标库，教学目标和知识边界需教师最终确认。"],
    }
    for key, default in defaults.items():
        if key not in ctx or ctx[key] is None:
            old = ctx.get(key)
            ctx[key] = default
            report.add(f"curriculumContext.{key}", "缺失或为空，使用默认值", old, default)
    deck["curriculumContext"] = ctx


def patch_visual_slot(layout_id: str, slot: Any, title: str, report: PatchReport, path: str) -> dict[str, Any]:
    """Ensure a visual slot is a well-formed object."""
    if not isinstance(slot, dict):
        old = slot
        slot = {}
        report.add(f"{path}", "visualSlot 不是对象，重置为空对象", old, {})

    slot_id, slot_type, ratio = LAYOUTS.get(layout_id, {}).get("slot", ("visual", "placeholder", "16:9"))

    if "id" not in slot:
        slot["id"] = slot_id
        report.add(f"{path}.id", "缺失，使用 layout 默认值", None, slot_id)
    if "type" not in slot:
        slot["type"] = slot_type
        report.add(f"{path}.type", "缺失，使用 layout 默认值", None, slot_type)
    if "ratio" not in slot:
        slot["ratio"] = ratio
        report.add(f"{path}.ratio", "缺失，使用 layout 默认值", None, ratio)
    if "assetStatus" not in slot:
        slot["assetStatus"] = "placeholder"
        report.add(f"{path}.assetStatus", "缺失，设为 placeholder", None, "placeholder")
    if "description" not in slot:
        desc = f"{title} 的课堂图示"
        slot["description"] = desc
        report.add(f"{path}.description", "缺失，自动生成", None, desc)

    return slot


def patch_teacher_script(ts: Any, title: str, report: PatchReport, path: str) -> dict[str, Any]:
    """Ensure teacherScript is a well-formed object."""
    if isinstance(ts, str):
        old = ts
        ts = {"say": ts, "ask": [], "expectedResponses": [], "transition": ""}
        report.add(f"{path}", "teacherScript 退化为字符串，重建为对象", old, ts)
    elif not isinstance(ts, dict):
        old = ts
        ts = {"say": "", "ask": [], "expectedResponses": [], "transition": ""}
        report.add(f"{path}", "teacherScript 类型异常，重建为空对象", old, ts)

    if "say" not in ts:
        ts["say"] = ""
        report.add(f"{path}.say", "缺失，设为空字符串", None, "")
    if "ask" not in ts:
        ts["ask"] = []
        report.add(f"{path}.ask", "缺失，设为空数组", None, [])
    if "expectedResponses" not in ts:
        ts["expectedResponses"] = []
        report.add(f"{path}.expectedResponses", "缺失，设为空数组", None, [])
    if "transition" not in ts:
        ts["transition"] = ""
        report.add(f"{path}.transition", "缺失，设为空字符串", None, "")

    return ts


def patch_screen(screen: Any, layout_id: str, title: str, report: PatchReport, path: str) -> dict[str, Any]:
    """Ensure screen is a well-formed object with layout-required fields."""
    if isinstance(screen, str):
        old = screen
        screen = {"headline": screen}
        report.add(f"{path}", "screen 退化为字符串，重建为对象", old, screen)
    elif not isinstance(screen, dict):
        old = screen
        screen = {"headline": title}
        report.add(f"{path}", "screen 类型异常，重建为对象", old, screen)

    # Ensure headline
    if not screen.get("headline"):
        screen["headline"] = title
        report.add(f"{path}.headline", "缺失或为空，使用 slide title", None, title)

    # Layout-specific required fields
    required = REQUIRED_SCREEN_KEYS_BY_LAYOUT.get(layout_id, set())
    for key in required:
        if key not in screen or screen[key] is None:
            if key == "subtitle":
                screen[key] = title
                report.add(f"{path}.{key}", "缺失，使用 title 填充", None, title)
            elif key == "outcome":
                screen[key] = "本节课结束时，学生能掌握核心内容。"
                report.add(f"{path}.{key}", "缺失，使用默认文案", None, screen[key])
            elif key == "route":
                screen[key] = ["学习目标", "核心内容", "练习巩固", "总结检测"]
                report.add(f"{path}.{key}", "缺失，使用默认路线", None, screen[key])
            elif key == "question":
                screen[key] = f"关于{title}，你有什么想法？"
                report.add(f"{path}.{key}", "缺失，使用默认问题", None, screen[key])
            elif key == "visualBrief":
                screen[key] = f"（请插入与{title}相关的图示）"
                report.add(f"{path}.{key}", "缺失，使用默认描述", None, screen[key])
            elif key == "prompt":
                screen[key] = f"请讨论：{title}的关键特征是什么？"
                report.add(f"{path}.{key}", "缺失，使用默认提示", None, screen[key])
            elif key == "comparePoints":
                screen[key] = ["特征一", "特征二"]
                report.add(f"{path}.{key}", "缺失，使用默认对比项", None, screen[key])
            elif key == "keyIdea":
                screen[key] = title
                report.add(f"{path}.{key}", "缺失，使用 title 填充", None, title)
            elif key == "bullets":
                screen[key] = [title]
                report.add(f"{path}.{key}", "缺失，使用 title 填充", None, [title])
            elif key == "modelSteps":
                screen[key] = ["步骤一", "步骤二"]
                report.add(f"{path}.{key}", "缺失，使用默认步骤", None, screen[key])
            elif key == "example":
                screen[key] = f"一道关于{title}的典型例题"
                report.add(f"{path}.{key}", "缺失，使用默认例题", None, screen[key])
            elif key == "steps":
                screen[key] = [{"label": "1", "content": "第一步", "teacherCue": "讲解关键步骤"}]
                report.add(f"{path}.{key}", "缺失，使用默认步骤", None, screen[key])
            elif key == "tasks":
                screen[key] = [{"label": "1", "content": f"完成{title}相关练习", "target": "检验理解", "feedback": "教师巡视点评"}]
                report.add(f"{path}.{key}", "缺失，使用默认任务", None, screen[key])
            elif key == "misconception":
                screen[key] = f"关于{title}的常见误解"
                report.add(f"{path}.{key}", "缺失，使用默认误解", None, screen[key])
            elif key == "correction":
                screen[key] = "回到概念和方法，检查每一步是否有依据。"
                report.add(f"{path}.{key}", "缺失，使用默认纠正", None, screen[key])
            elif key == "checkQuestion":
                screen[key] = f"关于{title}，你的判断是什么？"
                report.add(f"{path}.{key}", "缺失，使用默认检测题", None, screen[key])
            elif key == "activity":
                screen[key] = {"studentAction": f"完成{title}相关任务", "feedback": "小组展示后教师点评"}
                report.add(f"{path}.{key}", "缺失，使用默认活动", None, screen[key])
            elif key == "summary":
                screen[key] = [f"{title}的核心要点"]
                report.add(f"{path}.{key}", "缺失，使用默认总结", None, screen[key])
            elif key == "tickets":
                screen[key] = [{"label": "1", "content": f"{title}出门测", "target": "检验掌握程度", "feedback": "独立完成"}]
                report.add(f"{path}.{key}", "缺失，使用默认出门测", None, screen[key])

    return screen


def patch_slide(slide: Any, design_plan: list[dict[str, Any]] | None, report: PatchReport, index: int) -> dict[str, Any]:
    """Patch a single slide to conform to schema."""
    path_prefix = f"slides[{index}]"

    if not isinstance(slide, dict):
        old = slide
        slide = {}
        report.add(path_prefix, "slide 不是对象，重置为空对象", old, {})

    # Basic identity fields
    page = slide.get("page", index + 1)
    if slide.get("page") != page:
        report.add(f"{path_prefix}.page", "缺失或与索引不一致，重新编号", slide.get("page"), page)
    slide["page"] = page

    slide_id = slide.get("id", f"s{page:02d}")
    if slide.get("id") != slide_id:
        report.add(f"{path_prefix}.id", "缺失或与 page 不一致，重新生成", slide.get("id"), slide_id)
    slide["id"] = slide_id

    # LayoutId: use design plan if available, otherwise validate
    layout_id = slide.get("layoutId", "")
    if design_plan and index < len(design_plan):
        planned_layout = design_plan[index].get("layoutId", "")
        if planned_layout and layout_id != planned_layout:
            old_layout = layout_id
            layout_id = planned_layout
            slide["layoutId"] = layout_id
            report.add(f"{path_prefix}.layoutId", "与 designPlan 不一致，强制对齐", old_layout, layout_id)

    if not layout_id or layout_id not in VALID_LAYOUT_IDS:
        old_layout = layout_id
        layout_id = "ED05"
        slide["layoutId"] = layout_id
        report.add(f"{path_prefix}.layoutId", "无效或缺失，使用默认 ED05", old_layout, layout_id)

    # layoutName
    if "layoutName" not in slide:
        slide["layoutName"] = LAYOUTS.get(layout_id, {}).get("name", "")
        report.add(f"{path_prefix}.layoutName", "缺失，自动填充", None, slide["layoutName"])

    # stage
    if design_plan and index < len(design_plan):
        planned_stage = design_plan[index].get("stage", "")
        if planned_stage and slide.get("stage") != planned_stage:
            old_stage = slide.get("stage")
            slide["stage"] = planned_stage
            report.add(f"{path_prefix}.stage", "与 designPlan 不一致，强制对齐", old_stage, planned_stage)
    if "stage" not in slide or not slide["stage"]:
        old_stage = slide.get("stage")
        slide["stage"] = "lesson"
        report.add(f"{path_prefix}.stage", "缺失或为空，使用默认值", old_stage, "lesson")

    # title
    if "title" not in slide or not slide["title"]:
        old_title = slide.get("title")
        slide["title"] = f"第{page}页"
        report.add(f"{path_prefix}.title", "缺失或为空，使用默认标题", old_title, slide["title"])

    # teachingIntent
    if "teachingIntent" not in slide or not slide["teachingIntent"]:
        old_intent = slide.get("teachingIntent")
        slide["teachingIntent"] = slide["title"]
        report.add(f"{path_prefix}.teachingIntent", "缺失或为空，使用 title 填充", old_intent, slide["title"])

    # screen
    title = slide["title"]
    screen = patch_screen(slide.get("screen"), layout_id, title, report, f"{path_prefix}.screen")
    slide["screen"] = screen

    # teacherScript
    ts = patch_teacher_script(slide.get("teacherScript"), title, report, f"{path_prefix}.teacherScript")
    slide["teacherScript"] = ts

    # visualSlots
    slots = ensure_list(slide.get("visualSlots"))
    if not slots:
        slots = [patch_visual_slot(layout_id, {}, title, report, f"{path_prefix}.visualSlots[0]")]
        report.add(f"{path_prefix}.visualSlots", "缺失，创建默认占位", None, slots)
    else:
        slots = [patch_visual_slot(layout_id, s, title, report, f"{path_prefix}.visualSlots[{i}]") for i, s in enumerate(slots)]
    slide["visualSlots"] = slots

    # feedbackEvidence
    if "feedbackEvidence" not in slide or not slide["feedbackEvidence"]:
        old = slide.get("feedbackEvidence")
        slide["feedbackEvidence"] = "教师观察学生表现"
        report.add(f"{path_prefix}.feedbackEvidence", "缺失或为空，使用默认值", old, slide["feedbackEvidence"])

    # timing
    timing = slide.get("timing")
    if not isinstance(timing, dict):
        old = timing
        timing = {"minutes": 5}
        report.add(f"{path_prefix}.timing", "类型异常或缺失，重建为默认值", old, timing)
    if "minutes" not in timing:
        timing["minutes"] = 5
        report.add(f"{path_prefix}.timing.minutes", "缺失，设为 5", None, 5)
    slide["timing"] = timing

    # notes
    notes = ensure_list(slide.get("notes"))
    if not notes:
        notes = ["（无特殊备注）"]
        report.add(f"{path_prefix}.notes", "缺失，添加默认备注", None, notes)
    slide["notes"] = notes

    return slide


def patch_slides(deck: dict[str, Any], report: PatchReport) -> None:
    """Patch all slides in the deck."""
    slides = ensure_list(deck.get("slides"))
    design_plan = deck.get("designPlan")
    if design_plan and not isinstance(design_plan, list):
        design_plan = None
        report.add("designPlan", "类型异常（非数组），忽略对齐", deck.get("designPlan"), None)

    patched = []
    for index, slide in enumerate(slides):
        patched.append(patch_slide(slide, design_plan, report, index))

    # If design plan has more pages than slides, append placeholders
    if design_plan:
        plan_len = len(design_plan)
        slide_len = len(patched)
        for i in range(slide_len, plan_len):
            plan_item = design_plan[i]
            placeholder = {
                "id": f"s{i+1:02d}",
                "page": i + 1,
                "stage": plan_item.get("stage", "lesson"),
                "layoutId": plan_item.get("layoutId", "ED05"),
                "layoutName": LAYOUTS.get(plan_item.get("layoutId", "ED05"), {}).get("name", ""),
                "title": plan_item.get("reason", f"第{i+1}页"),
                "teachingIntent": plan_item.get("reason", f"第{i+1}页"),
                "screen": {"headline": plan_item.get("reason", f"第{i+1}页")},
                "teacherScript": {"say": "", "ask": [], "expectedResponses": [], "transition": ""},
                "visualSlots": [patch_visual_slot(
                    plan_item.get("layoutId", "ED05"), {},
                    plan_item.get("reason", f"第{i+1}页"), report, f"slides[{i}].visualSlots[0]"
                )],
                "feedbackEvidence": plan_item.get("feedbackEvidence", "教师观察学生表现"),
                "timing": {"minutes": 5},
                "notes": ["本页由 designPlan 补充，原始数据缺失。"],
            }
            report.add(f"slides[{i}]", "designPlan 中有但 slides 中缺失，创建占位页", None, placeholder["title"])
            patched.append(placeholder)

    deck["slides"] = patched

    # Update slideCount in deckMeta
    meta = ensure_dict(deck.get("deckMeta"))
    if meta.get("slideCount") != len(patched):
        old_count = meta.get("slideCount")
        meta["slideCount"] = len(patched)
        report.add("deckMeta.slideCount", "与 slides 数组长度不一致，修正", old_count, len(patched))
        deck["deckMeta"] = meta


def patch_teacher_script_array(deck: dict[str, Any], report: PatchReport) -> None:
    """Rebuild teacherScript array from slides for consistency."""
    slides = ensure_list(deck.get("slides", []))
    ts_array = []
    for index, slide in enumerate(slides):
        ts = slide.get("teacherScript", {})
        ts_array.append({
            "slideId": slide.get("id", f"s{index+1:02d}"),
            "title": slide.get("title", ""),
            "say": ts.get("say", ""),
            "ask": ensure_list(ts.get("ask")),
            "expectedResponses": ensure_list(ts.get("expectedResponses")),
            "transition": ts.get("transition", ""),
            "feedbackEvidence": slide.get("feedbackEvidence", ""),
        })

    old_ts = deck.get("teacherScript")
    deck["teacherScript"] = ts_array
    if old_ts is None:
        report.add("teacherScript", "缺失，从 slides 重建", None, f"({len(ts_array)} items)")
    elif len(ensure_list(old_ts)) != len(ts_array):
        report.add("teacherScript", "长度与 slides 不一致，从 slides 重建", len(ensure_list(old_ts)), len(ts_array))


def patch_design_plan(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure designPlan is consistent with slides."""
    slides = ensure_list(deck.get("slides", []))
    design_plan = ensure_list(deck.get("designPlan", []))

    # Rebuild design plan from slides if length mismatch or missing
    if len(design_plan) != len(slides):
        old_len = len(design_plan)
        new_plan = []
        for slide in slides:
            slots = slide.get("visualSlots", [])
            slot_ids = [s["id"] for s in slots if isinstance(s, dict) and "id" in s]
            new_plan.append({
                "page": slide.get("page", 0),
                "slideId": slide.get("id", ""),
                "stage": slide.get("stage", ""),
                "layoutId": slide.get("layoutId", ""),
                "reason": slide.get("teachingIntent", ""),
                "visualSlots": slot_ids,
                "feedbackEvidence": slide.get("feedbackEvidence", ""),
            })
        deck["designPlan"] = new_plan
        report.add("designPlan", "长度与 slides 不一致，从 slides 重建", old_len, len(new_plan))


def patch_lesson_outline(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure lessonOutline is consistent with slides."""
    slides = ensure_list(deck.get("slides", []))
    outline = ensure_list(deck.get("lessonOutline", []))

    if len(outline) != len(slides):
        old_len = len(outline)
        new_outline = []
        for slide in slides:
            new_outline.append({
                "stage": slide.get("stage", ""),
                "title": slide.get("title", ""),
                "layoutId": slide.get("layoutId", ""),
                "minutes": slide.get("timing", {}).get("minutes", 5),
                "goal": slide.get("teachingIntent", ""),
            })
        deck["lessonOutline"] = new_outline
        report.add("lessonOutline", "长度与 slides 不一致，从 slides 重建", old_len, len(new_outline))


def patch_export_plan(deck: dict[str, Any], report: PatchReport) -> None:
    """Ensure exportPlan has sensible defaults."""
    plan = ensure_dict(deck.get("exportPlan"))
    defaults = {
        "htmlPreview": True,
        "pptxReady": True,
        "pageSize": "16:9",
        "editableObjects": ["text", "shape", "visual-slot", "speaker-notes"],
        "visualSlotRules": "references/lesson-layout-lock.md",
    }
    for key, default in defaults.items():
        if key not in plan or plan[key] is None:
            old = plan.get(key)
            plan[key] = default
            report.add(f"exportPlan.{key}", "缺失或为空，使用默认值", old, default)
    deck["exportPlan"] = plan


def patch_quality_report(deck: dict[str, Any], report: PatchReport) -> None:
    """Merge patch fixes into qualityReport.checks."""
    qr = ensure_dict(deck.get("qualityReport"))

    # Ensure basic structure
    if "status" not in qr:
        qr["status"] = "draft"
    if "warnings" not in qr:
        qr["warnings"] = []
    if "assumptions" not in qr:
        qr["assumptions"] = deck.get("curriculumContext", {}).get("assumptions", [])
    if "checkedRules" not in qr:
        qr["checkedRules"] = ["edu_layout_lock", "visual_slots", "feedback_evidence", "timing", "teacher_script", "projection_density", "html_runtime"]

    # Merge patch checks
    checks = qr.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    patch_checks = report.to_checks()
    # Remove any existing post-patch checks to maintain idempotency
    checks = [c for c in checks if c.get("id") != "post-patch"]
    checks.extend(patch_checks)
    qr["checks"] = checks

    # Update status if fixes were applied
    if report.fix_count > 0 and qr["status"] == "pass":
        qr["status"] = "warn"
        qr["warnings"].append(f"patch 脚本自动修复了 {report.fix_count} 处结构退化，请人工复核。")

    deck["qualityReport"] = qr


def patch_deck(deck: dict[str, Any], report: PatchReport) -> dict[str, Any]:
    """Run all patch rules on a deck."""
    patch_root(deck, report)
    patch_deck_meta(deck, report)
    patch_curriculum_context(deck, report)
    patch_slides(deck, report)
    patch_teacher_script_array(deck, report)
    patch_design_plan(deck, report)
    patch_lesson_outline(deck, report)
    patch_export_plan(deck, report)
    patch_quality_report(deck, report)
    return deck


def main() -> int:
    parser = argparse.ArgumentParser(description="修复 deck JSON 结构退化。")
    parser.add_argument("deck_json", help="deck JSON 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印修复内容，不写入文件")
    parser.add_argument("--output", "-o", help="输出路径（默认覆盖原文件）")
    args = parser.parse_args()

    path = Path(args.deck_json)
    if not path.exists():
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        return 1

    try:
        deck = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"错误：JSON 解析失败 {exc}", file=sys.stderr)
        return 1

    if not isinstance(deck, dict):
        print("错误：deck JSON 根对象必须是字典", file=sys.stderr)
        return 1

    report = PatchReport()
    patched = patch_deck(deck, report)

    report.print_summary()

    if args.dry_run:
        print("\n(dry-run 模式，未写入文件)")
        return 0

    output_path = Path(args.output) if args.output else path
    output_path.write_text(json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
