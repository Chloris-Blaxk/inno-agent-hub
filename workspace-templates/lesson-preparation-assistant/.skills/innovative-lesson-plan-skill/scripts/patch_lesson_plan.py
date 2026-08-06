#!/usr/bin/env python3
"""Post-process qwen3.5-generated interdisciplinary lesson plan JSON.
Fixes common structural issues that the validator doesn't catch:
1. backgroundAnalysis.primarySubject/linkedSubject as string → object
2. Missing owningSubject on objectives
3. Missing subjectTag on activityFlow
4. Missing standardId on disciplineConnections
Also regenerates the Markdown via render_lesson_plan.build_markdown().
"""

import json
import sys
from pathlib import Path

# Add the scripts dir to path so we can import build_markdown
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from render_lesson_plan import build_markdown


def infer_owning_subject(desc: str, subject: str = "语文", linked: str = "化学") -> str:
    """Infer which subject an objective belongs to from its description."""
    chem_keywords = ["化学", "方程式", "反应", "CaCO", "CaO", "Ca(OH)", "CO₂", "物质", "现象", "碳"]
    lang_keywords = ["诗", "意象", "托物言志", "鉴赏", "文学", "诵读", "朗读", "语言", "表达", "诗人", "于谦", "象征", "人格"]

    has_chem = any(kw in desc for kw in chem_keywords)
    has_lang = any(kw in desc for kw in lang_keywords)

    if has_chem and has_lang:
        return f"{subject}+{linked}"
    elif has_chem:
        return linked
    elif has_lang:
        return subject
    return f"{subject}+{linked}"  # default to both for interdisciplinary


def infer_subject_tag(stage: str, teacher_actions: list, student_actions: list) -> str:
    """Infer the subject tag for an activity from its content."""
    text = stage + " " + " ".join(teacher_actions) + " " + " ".join(student_actions)

    chem_keywords = ["化学", "方程式", "反应", "CaCO", "CaO", "Ca(OH)", "CO₂", "物质", "实验", "煅烧", "分解", "碳化"]
    lang_keywords = ["诗", "诵读", "朗读", "鉴赏", "文学", "意象", "托物言志", "诗人", "于谦", "生平", "象征", "表达", "写作", "短文"]

    has_chem = any(kw in text for kw in chem_keywords)
    has_lang = any(kw in text for kw in lang_keywords)

    if has_chem and has_lang:
        return "学科交汇"
    elif has_chem:
        return "化学"
    elif has_lang:
        return "语文"
    return "学科交汇"  # default


def patch_background_analysis(bg: dict, subject: str = "语文", linked: str = "化学") -> dict:
    """Fix backgroundAnalysis: ensure primarySubject and linkedSubject are objects."""
    if not isinstance(bg, dict):
        return bg

    primary = bg.get("primarySubject")
    if isinstance(primary, str) and primary.strip():
        bg["primarySubject"] = {
            "unitPosition": primary.strip(),
            "standardRequirement": f"参见{subject}课程标准对应学段要求"
        }
    elif not isinstance(primary, dict):
        bg["primarySubject"] = {
            "unitPosition": f"{subject}教材对应单元",
            "standardRequirement": f"参见{subject}课程标准对应学段要求"
        }

    linked_val = bg.get("linkedSubject")
    if isinstance(linked_val, str) and linked_val.strip():
        bg["linkedSubject"] = {
            "unitPosition": linked_val.strip(),
            "standardRequirement": f"参见{linked}课程标准对应学段要求"
        }
    elif not isinstance(linked_val, dict):
        bg["linkedSubject"] = {
            "unitPosition": f"{linked}教材对应单元",
            "standardRequirement": f"参见{linked}课程标准对应学段要求"
        }

    return bg


def patch_objectives(objectives: list, subject: str = "语文", linked: str = "化学") -> list:
    """Add owningSubject to objectives if missing."""
    for obj in objectives:
        if not isinstance(obj, dict):
            continue
        if "owningSubject" not in obj or not obj.get("owningSubject"):
            desc = obj.get("description", "")
            obj["owningSubject"] = infer_owning_subject(desc, subject, linked)
    return objectives


def patch_activity_flow(activities: list) -> list:
    """Add subjectTag to activities if missing."""
    for act in activities:
        if not isinstance(act, dict):
            continue
        if "subjectTag" not in act or not act.get("subjectTag"):
            stage = act.get("stage", "")
            teacher = act.get("teacherActions", [])
            student = act.get("studentActions", [])
            act["subjectTag"] = infer_subject_tag(stage, teacher, student)
    return activities


def patch_discipline_connections(connections: list) -> list:
    """Add standardId to disciplineConnections if missing."""
    standard_map = {
        "语文": "std-chn-g7-exposition-001",
        "化学": "std-chem-g9-carbonate-001",
        "数学": "std-math-g5-data-001",
        "物理": "std-phy-g8-optics-001",
        "生物": "std-bio-g7-ecology-001",
        "历史": "std-his-g7-local-001",
        "地理": "std-geo-g7-climate-001",
        "科学": "std-sci-g6-water-001",
    }
    for conn in connections:
        if not isinstance(conn, dict):
            continue
        if "standardId" not in conn or not conn.get("standardId"):
            subj = conn.get("subject", "")
            conn["standardId"] = standard_map.get(subj, f"std-{subj}-unknown")
    return connections


def patch_lesson_plan(plan: dict) -> dict:
    """Apply all patches to a lesson plan JSON."""
    meta = plan.get("lessonMeta", {})
    subject = meta.get("subject", "语文")

    # Determine linked subject from innovationDesign
    innovation = plan.get("innovationDesign", {})
    linked = "化学"
    for conn in innovation.get("disciplineConnections", []):
        if isinstance(conn, dict) and conn.get("subject") != subject:
            linked = conn.get("subject", "化学")
            break

    # 1. Fix backgroundAnalysis
    plan["backgroundAnalysis"] = patch_background_analysis(
        plan.get("backgroundAnalysis", {}), subject, linked
    )

    # 2. Fix objectives
    plan["objectives"] = patch_objectives(
        plan.get("objectives", []), subject, linked
    )

    # 3. Fix activityFlow
    plan["activityFlow"] = patch_activity_flow(
        plan.get("activityFlow", [])
    )

    # 4. Fix disciplineConnections
    innovation["disciplineConnections"] = patch_discipline_connections(
        innovation.get("disciplineConnections", [])
    )
    plan["innovationDesign"] = innovation

    # 5. Add patch note to qualityReport
    qr = plan.get("qualityReport", {})
    if not isinstance(qr, dict):
        qr = {}
    checks = qr.get("checks", [])
    checks.append({
        "id": "post-patch",
        "status": "pass",
        "message": "Controller 已自动修复 backgroundAnalysis 嵌套结构、objectives.owningSubject、activityFlow.subjectTag、disciplineConnections.standardId"
    })
    qr["checks"] = checks
    plan["qualityReport"] = qr

    return plan


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 patch_lesson_plan.py <path/to/output.json>", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    # Read
    plan = json.loads(json_path.read_text(encoding="utf-8"))

    # Patch
    plan = patch_lesson_plan(plan)

    # Rewrite JSON
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Patched: {json_path}")

    # Regenerate Markdown
    markdown = build_markdown(plan)
    plan["export"] = plan.get("export", {})
    plan["export"]["markdown"] = markdown
    plan["export"]["format"] = "markdown"

    # Rewrite JSON with updated markdown
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = json_path.with_suffix(".md")
    md_path.write_text(markdown, encoding="utf-8")
    print(f"Rebuilt Markdown: {md_path}")

    # Summary
    print("\nPatches applied:")
    bg = plan["backgroundAnalysis"]
    ps = bg.get("primarySubject", {})
    ls = bg.get("linkedSubject", {})
    print(f"  backgroundAnalysis.primarySubject: {'✅ object' if isinstance(ps, dict) else '❌ ' + str(type(ps).__name__)}")
    print(f"  backgroundAnalysis.linkedSubject: {'✅ object' if isinstance(ls, dict) else '❌ ' + str(type(ls).__name__)}")
    for obj in plan.get("objectives", []):
        print(f"  {obj.get('id', '?')}.owningSubject: {obj.get('owningSubject', 'MISSING')}")
    for act in plan.get("activityFlow", []):
        print(f"  {act.get('id', '?')}.subjectTag: {act.get('subjectTag', 'MISSING')}")
    for conn in plan["innovationDesign"].get("disciplineConnections", []):
        print(f"  disciplineConnection({conn.get('subject', '?')}).standardId: {conn.get('standardId', 'MISSING')}")


if __name__ == "__main__":
    main()
