#!/usr/bin/env python3
"""Post-validate research-line model outputs before render, handoff, or publishing."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


CASES_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CASES_ROOT.parent

VALIDATORS = {
    "research-topic-generation-skill": CASES_ROOT / "research-topic-generation-skill/scripts/validate_research_topic.py",
    "literature-reading-skill": CASES_ROOT / "literature-reading-skill/scripts/validate_literature_reading.py",
    "paper-writing-skill": CASES_ROOT / "paper-writing-skill/scripts/validate_paper_writing.py",
    "project-proposal-skill": CASES_ROOT / "project-proposal-skill/scripts/validate_project_proposal.py",
}

NEXT_ACTION = {
    "ready_for_render": "可进入 render、Markdown 导出或压缩 workspace handoff。",
    "needs_review": "只能带警告进入人工复核或降级交付；不得自动插入引用、事实、预算或成果。",
    "rejected": "必须退回重生成、补资料或改为无法确认说明，不得 render 或 handoff。",
}

QUALITY_STATUS_TO_GATE = {
    "pass": "ready_for_render",
    "warn": "needs_review",
    "failed": "rejected",
    "fail": "rejected",
}


def resolve_input_path(path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"文件不存在：{path}"
    except json.JSONDecodeError as exc:
        return None, f"JSON 解析失败：{exc}"
    if not isinstance(data, dict):
        return None, "模型输出必须是 JSON object。"
    return data, None


def trimmed(text: str, limit: int = 1800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def warning_lines(stdout: str) -> list[str]:
    return [line.removeprefix("- 警告：").strip() for line in stdout.splitlines() if line.startswith("- 警告：")]


def summarize_output(data: dict[str, Any]) -> dict[str, Any]:
    result = data.get("result", {})
    if not isinstance(result, dict):
        result = {}
    handoff = data.get("handoff", {})
    if not isinstance(handoff, dict):
        handoff = {}

    project_fact_table = result.get("projectFactTable", {})
    if not isinstance(project_fact_table, dict):
        project_fact_table = {}
    document_set = result.get("documentSet", {})
    if not isinstance(document_set, dict):
        document_set = {}

    return {
        "taskIntent": data.get("taskIntent"),
        "topLevelStatus": data.get("status"),
        "qualityStatus": data.get("qualityReport", {}).get("status") if isinstance(data.get("qualityReport"), dict) else None,
        "topicCandidateCount": len(result.get("topicCandidates", []) or []),
        "literatureRecordCount": len(result.get("literatureRecords", []) or []),
        "evidenceCardCount": len(result.get("evidenceCards", []) or []),
        "sourceTraceResultCount": len(result.get("sourceTraceResults", []) or []),
        "usableEvidenceCardCount": len(handoff.get("usableEvidenceCards", []) or []),
        "projectFactCount": len(project_fact_table.get("facts", []) or []),
        "documentCount": len(document_set.get("documents", []) or []),
    }


def validate_path(path: Path) -> dict[str, Any]:
    path = resolve_input_path(path)
    data, error = read_json(path)
    if error is not None or data is None:
        return {
            "path": str(path),
            "status": "rejected",
            "reason": error,
            "nextAction": NEXT_ACTION["rejected"],
        }

    skill_id = data.get("skillId")
    validator = VALIDATORS.get(skill_id)
    if validator is None:
        return {
            "path": str(path),
            "skillId": skill_id,
            "status": "rejected",
            "reason": "未知或缺失 skillId，无法选择科研线 validator。",
            "nextAction": NEXT_ACTION["rejected"],
        }

    env = os.environ.copy()
    env.setdefault("PYTHONPYCACHEPREFIX", "/private/tmp/codex-pycache")
    completed = subprocess.run(
        [sys.executable, str(validator), str(path)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    quality_status = data.get("qualityReport", {}).get("status") if isinstance(data.get("qualityReport"), dict) else None
    top_level_status = data.get("status")
    if completed.returncode != 0:
        return {
            "path": str(path),
            "skillId": skill_id,
            "status": "rejected",
            "qualityStatus": quality_status,
            "validator": str(validator.relative_to(REPO_ROOT)),
            "reason": "validator_failed",
            "stdoutTail": trimmed(completed.stdout),
            "stderrTail": trimmed(completed.stderr),
            "nextAction": NEXT_ACTION["rejected"],
        }

    if top_level_status and quality_status and top_level_status != quality_status:
        return {
            "path": str(path),
            "skillId": skill_id,
            "status": "rejected",
            "qualityStatus": quality_status,
            "topLevelStatus": top_level_status,
            "validator": str(validator.relative_to(REPO_ROOT)),
            "reason": "顶层 status 必须与 qualityReport.status 一致。",
            "stdoutTail": trimmed(completed.stdout),
            "stderrTail": trimmed(completed.stderr),
            "nextAction": NEXT_ACTION["rejected"],
        }

    status = QUALITY_STATUS_TO_GATE.get(str(quality_status or ""))
    if status is None:
        return {
            "path": str(path),
            "skillId": skill_id,
            "status": "rejected",
            "qualityStatus": quality_status,
            "validator": str(validator.relative_to(REPO_ROOT)),
            "reason": "qualityReport.status 必须是 pass、warn 或 failed。",
            "stdoutTail": trimmed(completed.stdout),
            "stderrTail": trimmed(completed.stderr),
            "nextAction": NEXT_ACTION["rejected"],
        }

    if status == "rejected":
        return {
            "path": str(path),
            "skillId": skill_id,
            "status": "rejected",
            "qualityStatus": quality_status,
            "validator": str(validator.relative_to(REPO_ROOT)),
            "reason": "qualityReport.status 为 failed，不得 render 或 handoff。",
            "stdoutTail": trimmed(completed.stdout),
            "stderrTail": trimmed(completed.stderr),
            "nextAction": NEXT_ACTION["rejected"],
        }

    return {
        "path": str(path),
        "skillId": skill_id,
        "status": status,
        "qualityStatus": quality_status,
        "validator": str(validator.relative_to(REPO_ROOT)),
        "warnings": warning_lines(completed.stdout),
        "summary": summarize_output(data),
        "nextAction": NEXT_ACTION[status],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="科研线模型输出落地前总拦截。")
    parser.add_argument("output_json", nargs="+", help="待拦截的模型输出 JSON 文件")
    parser.add_argument("--strict", action="store_true", help="将 needs_review 也视为命令失败。")
    args = parser.parse_args()

    results = [validate_path(Path(path)) for path in args.output_json]
    rejected = [item for item in results if item["status"] == "rejected"]
    needs_review = [item for item in results if item["status"] == "needs_review"]
    payload = {
        "status": "failed" if rejected else "warn" if needs_review else "passed",
        "summary": {
            "total": len(results),
            "readyForRender": len([item for item in results if item["status"] == "ready_for_render"]),
            "needsReview": len(needs_review),
            "rejected": len(rejected),
            "strict": args.strict,
        },
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if rejected or (args.strict and needs_review) else 0


if __name__ == "__main__":
    raise SystemExit(main())
