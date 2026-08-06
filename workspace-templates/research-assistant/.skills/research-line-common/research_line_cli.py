#!/usr/bin/env python3
"""Unified CLI for research-line guard, workspace, and DOCX export tasks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import model_output_guard
import workspace_summary


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_guard(args: argparse.Namespace) -> int:
    results = [model_output_guard.validate_path(Path(path)) for path in args.output_json]
    rejected = [item for item in results if item["status"] == "rejected"]
    needs_review = [item for item in results if item["status"] == "needs_review"]
    payload = {
        "command": "guard",
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
    print_json(payload)
    return 1 if rejected or (args.strict and needs_review) else 0


def run_workspace(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    if args.validate_only:
        workspace_summary.validate_workspace(workspace_summary.load_json(output_path))
        print_json({"command": "workspace", "status": "passed", "output": str(output_path), "validateOnly": True})
        return 0
    if not args.outputs:
        print_json(
            {
                "command": "workspace",
                "status": "failed",
                "reason": "生成 workspace summary 时至少需要 1 个科研线 Skill 输出 JSON。",
            }
        )
        return 2

    outputs = [workspace_summary.load_json(Path(path)) for path in args.outputs]
    workspace = workspace_summary.collect_workspace(outputs, args.workspace_id)
    workspace_summary.write_json(output_path, workspace)
    print_json(
        {
            "command": "workspace",
            "status": "passed",
            "output": str(output_path),
            "workspaceId": workspace["workspaceId"],
            "estimatedTokens": workspace["contextBudget"]["estimatedTokens"],
            "topicCandidates": len(workspace["topicCandidates"]),
            "literatureRecords": len(workspace["literatureRecords"]),
            "evidenceCards": len(workspace["evidenceCards"]),
            "projectFactTables": len(workspace["projectFactTables"]),
        }
    )
    return 0


def run_docx(args: argparse.Namespace) -> int:
    import docx_export

    output_dir = Path(args.output_dir)
    exported: list[Path] = []
    for item in args.output_json:
        exported.extend(docx_export.export_one(Path(item), output_dir))
    print_json(
        {
            "command": "docx",
            "status": "passed",
            "outputDir": str(output_dir),
            "files": [{"path": str(path), "bytes": path.stat().st_size} for path in exported],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="科研线公共运行时统一入口。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    guard = subparsers.add_parser("guard", help="校验模型输出是否可进入 render/handoff。")
    guard.add_argument("output_json", nargs="+", help="待拦截的模型输出 JSON 文件。")
    guard.add_argument("--strict", action="store_true", help="将 needs_review 也视为命令失败。")
    guard.set_defaults(func=run_guard)

    workspace = subparsers.add_parser("workspace", help="生成或校验 ResearchWorkspace 压缩摘要。")
    workspace.add_argument("outputs", nargs="*", help="四个科研线 Skill 输出 JSON，可传多个。")
    workspace.add_argument("--output", required=True, help="workspace summary JSON 路径。")
    workspace.add_argument("--workspace-id", default="rw-local-research-001")
    workspace.add_argument("--validate-only", action="store_true", help="只校验已有 summary，不重新生成。")
    workspace.set_defaults(func=run_workspace)

    docx = subparsers.add_parser("docx", help="从科研线 JSON 输出导出 DOCX。")
    docx.add_argument("output_json", nargs="+", help="科研线 JSON 输出。")
    docx.add_argument("--output-dir", required=True, help="DOCX 输出目录。")
    docx.set_defaults(func=run_docx)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
