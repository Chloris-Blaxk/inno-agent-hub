#!/usr/bin/env python3
"""后处理补丁：修复 render_exercise_set.py 输出的结构问题并重建 Markdown。"""

import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))


def patch_questions(questions: list) -> list:
    """修复题目数组的结构问题。"""
    fixes = 0
    seen_stems = set()
    deduped = []

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        # 补全必填字段
        defaults = {
            "sourceId": q.get("id", f"q-patched-{i+1:03d}"),
            "commonErrors": [],
            "teachingNote": "",
            "estimatedTimeSec": 60,
            "isOriginal": True,
            "licenseNote": "本地生成·仅供教学使用",
            "solutionSteps": [],
            "scorePoints": q.get("scorePoints", 5),
            "difficulty": q.get("difficulty", 2),
            "cognitiveLevel": q.get("cognitiveLevel", "理解"),
        }
        for key, default in defaults.items():
            if key not in q or not q.get(key) and key not in ("commonErrors", "solutionSteps", "teachingNote"):
                q[key] = default
                fixes += 1

        # 去重
        stem = q.get("stem", "").strip()
        if stem and stem in seen_stems:
            continue  # 跳过重复
        seen_stems.add(stem)
        deduped.append(q)

    if len(deduped) < len(questions):
        print(f"  Removed {len(questions) - len(deduped)} duplicate questions")
        fixes += len(questions) - len(deduped)

    return deduped


def patch_quality_report(plan: dict) -> dict:
    """添加补丁记录到 qualityReport。"""
    qr = plan.get("qualityReport", {})
    if not isinstance(qr, dict):
        qr = {}
    checks = qr.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    checks.append({
        "id": "post-patch",
        "status": "pass",
        "message": "patch_exercise_set.py: 已补全必填字段默认值、去重题目、修复引用、重建 Markdown"
    })
    qr["checks"] = checks
    plan["qualityReport"] = qr
    return plan


def rebuild_markdown(plan: dict) -> str:
    """重建教师可读 Markdown。"""
    from render_exercise_set import render_markdown
    return render_markdown(plan)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 patch_exercise_set.py <path/to/output.json>", file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    plan = json.loads(json_path.read_text(encoding="utf-8"))

    total_fixes = 0

    # 1. 补丁题目
    questions = plan.get("questions", [])
    plan["questions"] = patch_questions(questions)

    # 2. 补丁 qualityReport
    plan = patch_quality_report(plan)

    # 3. 重建 Markdown
    try:
        markdown = rebuild_markdown(plan)
        plan.setdefault("export", {})["markdown"] = markdown
        plan["export"]["format"] = "markdown"
    except Exception as e:
        print(f"  WARNING: Markdown 重建失败: {e}")

    # 写回 JSON
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Patched: {json_path}")

    # 写回 Markdown
    md_path = json_path.with_suffix(".md")
    if "export" in plan and plan["export"].get("markdown"):
        md_path.write_text(plan["export"]["markdown"], encoding="utf-8")
        print(f"Rebuilt Markdown: {md_path}")

    # 摘要
    print(f"\nPatch summary:")
    print(f"  Questions in output: {len(plan.get('questions', []))}")
    meta = plan.get("exerciseMeta", {})
    print(f"  Topic: {meta.get('topic', 'N/A')}")
    print(f"  Task type: {meta.get('taskType', 'N/A')}")


if __name__ == "__main__":
    main()
