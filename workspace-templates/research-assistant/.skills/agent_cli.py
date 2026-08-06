#!/usr/bin/env python3
"""CLI-first dispatcher for AgentDesign education Skills.

The dispatcher intentionally avoids keyword routing, alternate entry names,
and fuzzy matching. It only accepts the fixed Chinese entry names defined in
skill-entrypoints.json, or an explicit numeric selection from the menu.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ENTRYPOINTS_PATH = ROOT / "skill-entrypoints.json"
INDEX_DIR = ROOT / ".agent-index"
INDEX_PATH = INDEX_DIR / "skills.json"

ENTRY_BOUNDARIES = set(" \t\r\n+,+，:：;；|/")
KNOWN_COMMANDS = {"resolve", "skill", "index", "help", "run", "--help", "-h"}


class CliError(Exception):
    """Expected CLI error with a structured payload."""

    def __init__(self, message: str, *, code: str = "cli_error", payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


def dump_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"缺少入口映射表: {path}", code="missing_entrypoints") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"入口映射表 JSON 无法解析: {exc}", code="invalid_entrypoints_json") from exc


def parse_frontmatter(skill_file: Path) -> dict[str, Any]:
    if not skill_file.exists():
        return {}

    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}

    end = text.find("\n---", 4)
    if end == -1:
        return {}

    meta: dict[str, Any] = {}
    for raw_line in text[4:end].splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def load_entries() -> list[dict[str, Any]]:
    data = read_json(ENTRYPOINTS_PATH)
    raw_entries = data.get("entrypoints")
    if not isinstance(raw_entries, list):
        raise CliError("skill-entrypoints.json 必须包含 entrypoints 数组", code="invalid_entrypoints")

    seen_indexes: set[int] = set()
    seen_tokens: set[str] = set()
    seen_skills: set[str] = set()
    entries: list[dict[str, Any]] = []

    for raw in raw_entries:
        entry = dict(raw)
        index = entry.get("index")
        token = entry.get("entryToken")
        skill_id = entry.get("skillId")
        if not isinstance(index, int) or not token or not skill_id:
            raise CliError(f"入口配置不完整: {raw}", code="invalid_entry")
        if index in seen_indexes:
            raise CliError(f"入口序号重复: {index}", code="duplicate_entry_index")
        if token in seen_tokens:
            raise CliError(f"入口名称重复: {token}", code="duplicate_entry_token")
        if skill_id in seen_skills:
            raise CliError(f"Skill ID 重复绑定: {skill_id}", code="duplicate_skill_id")

        seen_indexes.add(index)
        seen_tokens.add(token)
        seen_skills.add(skill_id)

        skill_dir = ROOT / skill_id
        skill_file = skill_dir / "SKILL.md"
        frontmatter = parse_frontmatter(skill_file)
        entry["path"] = str(skill_dir.relative_to(ROOT.parent))
        entry["skillFile"] = str(skill_file.relative_to(ROOT.parent))
        entry["skillExists"] = skill_file.exists()
        entry["frontmatter"] = frontmatter
        entry["description"] = entry.get("description") or frontmatter.get("description", "")
        entries.append(entry)

    entries.sort(key=lambda item: item["index"])
    expected_indexes = list(range(1, len(entries) + 1))
    actual_indexes = [entry["index"] for entry in entries]
    if actual_indexes != expected_indexes:
        raise CliError(
            f"入口序号必须连续: expected={expected_indexes}, actual={actual_indexes}",
            code="non_contiguous_entry_indexes",
        )

    return entries


def by_index(entries: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {entry["index"]: entry for entry in entries}


def by_skill_id(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["skillId"]: entry for entry in entries}


def compact_choice(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": entry["index"],
        "skillId": entry["skillId"],
        "entryName": entry["entryName"],
        "entryToken": entry["entryToken"],
        "displayName": entry["displayName"],
        "status": entry["status"],
    }


def selected_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": entry["index"],
        "skillId": entry["skillId"],
        "entryName": entry["entryName"],
        "entryToken": entry["entryToken"],
        "displayName": entry["displayName"],
        "status": entry["status"],
        "runnable": entry.get("status") == "runnable_prototype",
        "primaryOutputs": entry.get("primaryOutputs", []),
        "skillFile": entry["skillFile"],
        "path": entry["path"],
    }


def choices(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [compact_choice(entry) for entry in entries]


def request_payload(raw: str, clean_text: str | None = None, **extra: Any) -> dict[str, Any]:
    payload = {
        "raw": raw,
        "cleanText": raw.strip() if clean_text is None else clean_text,
    }
    payload.update(extra)
    return payload


def is_boundary(text: str, token: str) -> bool:
    if not text.startswith(token):
        return False
    if len(text) == len(token):
        return True
    return text[len(token)] in ENTRY_BOUNDARIES


def extract_unknown_entry_token(text: str) -> str:
    match = re.match(r"^@\S+", text.strip())
    if not match:
        return "@"
    token = match.group(0)
    return token.rstrip("+,+，:：;；|/")


def parse_fixed_entry_tokens(raw_request: str, entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str, str | None]:
    text = raw_request.strip()
    if not text.startswith("@"):
        return [], text, None

    token_order = sorted(entries, key=lambda item: len(item["entryToken"]), reverse=True)
    selected: list[dict[str, Any]] = []
    remaining = text

    while remaining.startswith("@"):
        matched = next((entry for entry in token_order if is_boundary(remaining, entry["entryToken"])), None)
        if matched is None:
            return [], text, extract_unknown_entry_token(remaining)

        if matched in selected:
            raise CliError(f"重复入口: {matched['entryToken']}", code="duplicate_entry_in_request")

        selected.append(matched)
        remaining = remaining[len(matched["entryToken"]):]
        remaining = remaining.lstrip()

        if remaining.startswith("+"):
            remaining = remaining[1:].lstrip()
            if not remaining.startswith("@"):
                return [], text, extract_unknown_entry_token("@" + remaining)
            continue

        if remaining.startswith((",", "，", ":", "：", ";", "；", "|", "/")):
            remaining = remaining[1:].lstrip()
            if remaining.startswith("@"):
                continue
            break

        if remaining.startswith("@"):
            continue
        break

    return selected, remaining.strip(), None


def parse_selection(select_value: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parts = [part for part in re.split(r"[\s,，]+", select_value.strip()) if part]
    if not parts:
        raise CliError("--select 需要至少一个序号", code="empty_selection")

    entry_by_index = by_index(entries)
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()

    for part in parts:
        if not part.isdigit():
            raise CliError(f"Skill 序号必须是数字: {part}", code="invalid_selection")
        index = int(part)
        if index not in entry_by_index:
            raise CliError(f"Skill 序号不存在: {index}", code="selection_out_of_range", payload={"choices": choices(entries)})
        if index in seen:
            continue
        seen.add(index)
        selected.append(entry_by_index[index])

    return selected


def build_steps(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for idx, entry in enumerate(selected, 1):
        step = {
            "step": idx,
            "skillId": entry["skillId"],
            "displayName": entry["displayName"],
            "skillFile": entry["skillFile"],
        }
        if idx > 1:
            step["inputFromStep"] = idx - 1
        steps.append(step)
    return steps


def resolve_request(raw_request: str, *, select: str | None = None, skill: str | None = None) -> dict[str, Any]:
    entries = load_entries()

    if select:
        selected = parse_selection(select, entries)
        decision = "compose" if len(selected) > 1 else "selected"
        payload = {
            "decision": decision,
            "confidence": "explicit",
            "source": "user_selection",
            "selected": [selected_entry(entry) for entry in selected],
            "request": request_payload(raw_request),
        }
        if len(selected) > 1:
            payload["steps"] = build_steps(selected)
        return payload

    if skill:
        entry = by_skill_id(entries).get(skill)
        if entry is None:
            raise CliError(f"未知 Skill ID: {skill}", code="unknown_skill_id", payload={"choices": choices(entries)})
        return {
            "decision": "route",
            "confidence": "explicit",
            "source": "explicit_skill_id",
            "selected": [selected_entry(entry)],
            "request": request_payload(raw_request),
        }

    selected, clean_text, unknown = parse_fixed_entry_tokens(raw_request, entries)
    if unknown:
        return {
            "decision": "unknown_entry_name",
            "reason": "unknown_entry_name",
            "unknownEntryToken": unknown,
            "request": request_payload(raw_request),
            "message": "该 @入口名 不在固定 11 个入口中。请选择正确入口或回复序号。",
            "choices": choices(entries),
        }

    if selected:
        decision = "compose" if len(selected) > 1 else "route"
        payload = {
            "decision": decision,
            "confidence": "explicit",
            "source": "fixed_entry_name",
            "selected": [selected_entry(entry) for entry in selected],
            "request": request_payload(
                raw_request,
                clean_text,
                entryNames=[entry["entryName"] for entry in selected],
                entryTokens=[entry["entryToken"] for entry in selected],
            ),
        }
        if len(selected) > 1:
            payload["steps"] = build_steps(selected)
        return payload

    return {
        "decision": "needs_skill_selection",
        "reason": "missing_entry_name",
        "request": request_payload(raw_request),
        "message": "请先选择要使用的 Skill 序号，再继续。",
        "choices": choices(entries),
    }


def human_resolve(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    if decision == "needs_skill_selection":
        lines = [payload["message"], ""]
        for choice in payload["choices"]:
            lines.append(f"{choice['index']}. {choice['displayName']}（{choice['status']}）")
        lines.append("")
        lines.append("请回复序号，例如：2；如果需要组合产物，回复：3,6。")
        return "\n".join(lines)
    if decision == "unknown_entry_name":
        return human_resolve({"decision": "needs_skill_selection", "message": payload["message"], "choices": payload["choices"]})
    if decision == "compose":
        names = " -> ".join(item["displayName"] for item in payload["selected"])
        return f"已选择组合 Skill：{names}"
    selected = payload["selected"][0]
    return f"已选择 Skill：{selected['displayName']} ({selected['skillId']})"


def command_resolve(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_cli.py resolve", description="解析固定 @入口名或返回 Skill 选择菜单")
    parser.add_argument("request", nargs="*", help="教师请求文本")
    parser.add_argument("--select", help="用户选择的 Skill 序号，支持逗号分隔，如 3,6")
    parser.add_argument("--skill", help="显式 Skill ID，用于系统内部调用")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    raw_request = " ".join(args.request).strip()
    payload = resolve_request(raw_request, select=args.select, skill=args.skill)
    if args.json:
        dump_json(payload)
    else:
        print(human_resolve(payload))
    return 0


def command_skill_list(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_cli.py skill list", description="列出固定 11 个 Skill 入口")
    parser.add_argument("--status", help="按状态过滤，如 runnable_prototype 或 skeleton")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    entries = load_entries()
    if args.status:
        entries = [entry for entry in entries if entry.get("status") == args.status]

    payload = {
        "skills": [selected_entry(entry) for entry in entries],
        "count": len(entries),
        "routingPolicy": {
            "fixedEntryNamesOnly": True,
            "keywordRouting": "disabled",
        },
    }
    if args.json:
        dump_json(payload)
    else:
        for entry in entries:
            print(f"{entry['index']}. {entry['entryToken']} -> {entry['skillId']} ({entry['status']})")
    return 0


def command_skill_show(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_cli.py skill show", description="显示 Skill 元信息")
    parser.add_argument("skill_id")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    entry = by_skill_id(load_entries()).get(args.skill_id)
    if entry is None:
        raise CliError(f"未知 Skill ID: {args.skill_id}", code="unknown_skill_id")
    payload = selected_entry(entry)
    payload["description"] = entry.get("description", "")
    payload["requiredSlots"] = entry.get("requiredSlots", [])
    payload["optionalSlots"] = entry.get("optionalSlots", [])
    payload["execution"] = entry.get("execution", {})
    if args.json:
        dump_json(payload)
    else:
        print(f"{payload['displayName']} ({payload['skillId']})")
        print(payload.get("description", ""))
    return 0


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def list_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [str(item.relative_to(ROOT.parent)) for item in sorted(path.iterdir()) if item.is_file()]


def command_skill_read(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_cli.py skill read", description="按 section 读取 Skill 精简信息")
    parser.add_argument("skill_id")
    parser.add_argument("--section", default="meta", choices=["meta", "contract", "workflow", "boundaries", "commands", "examples", "full"])
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    entry = by_skill_id(load_entries()).get(args.skill_id)
    if entry is None:
        raise CliError(f"未知 Skill ID: {args.skill_id}", code="unknown_skill_id")

    skill_file = ROOT.parent / entry["skillFile"]
    skill_dir = ROOT / entry["skillId"]
    section = args.section
    payload: dict[str, Any] = {
        "skillId": entry["skillId"],
        "section": section,
        "skillFile": entry["skillFile"],
    }

    if section == "meta":
        payload.update(selected_entry(entry))
        payload["description"] = entry.get("description", "")
        payload["frontmatter"] = entry.get("frontmatter", {})
    elif section == "contract":
        schema_path = skill_dir / "references" / "input-output-schema.md"
        payload.update({
            "requiredSlots": entry.get("requiredSlots", []),
            "optionalSlots": entry.get("optionalSlots", []),
            "primaryOutputs": entry.get("primaryOutputs", []),
            "schemaPath": str(schema_path.relative_to(ROOT.parent)) if schema_path.exists() else None,
        })
    elif section == "commands":
        payload["execution"] = entry.get("execution", {})
        payload["scripts"] = list_files(skill_dir / "scripts")
    elif section == "examples":
        payload["examples"] = list_files(skill_dir / "examples")
    elif section in {"workflow", "boundaries"}:
        payload["content"] = "请读取 skillFile 中对应章节；当前 CLI 只提供精简定位信息。"
        payload["skillFileExists"] = skill_file.exists()
    else:
        payload["content"] = read_markdown(skill_file)

    if args.json:
        dump_json(payload)
    else:
        if "content" in payload:
            print(payload["content"])
        else:
            dump_json(payload)
    return 0


def command_skill(argv: list[str]) -> int:
    if not argv:
        raise CliError("skill 命令需要子命令: list/show/read", code="missing_skill_subcommand")
    subcommand, rest = argv[0], argv[1:]
    if subcommand == "list":
        return command_skill_list(rest)
    if subcommand == "show":
        return command_skill_show(rest)
    if subcommand == "read":
        return command_skill_read(rest)
    raise CliError(f"未知 skill 子命令: {subcommand}", code="unknown_skill_subcommand")


def build_index() -> dict[str, Any]:
    entries = load_entries()
    return {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "entrypointsFile": str(ENTRYPOINTS_PATH.relative_to(ROOT.parent)),
        "routingPolicy": {
            "mode": "fixed_entry_name",
            "fixedEntryNamesOnly": True,
            "keywordRouting": "disabled",
            "missingEntryAction": "needs_skill_selection",
        },
        "skills": [selected_entry(entry) | {
            "description": entry.get("description", ""),
            "requiredSlots": entry.get("requiredSlots", []),
            "optionalSlots": entry.get("optionalSlots", []),
            "execution": entry.get("execution", {}),
        } for entry in entries],
    }


def command_index(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent_cli.py index", description="管理 Skill 索引")
    parser.add_argument("action", choices=["rebuild"])
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    payload = build_index()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "ok",
        "indexPath": str(INDEX_PATH.relative_to(ROOT.parent)),
        "skillCount": len(payload["skills"]),
    }
    if args.json:
        dump_json(result)
    else:
        print(f"索引已生成: {result['indexPath']} ({result['skillCount']} skills)")
    return 0



def _grade_candidates(text: str) -> list[str]:
    """Return all grade tokens found in text."""
    candidates = [
        "高一", "高二", "高三",
        "初一", "初二", "初三",
        "七年级", "八年级", "九年级",
        "一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
    ]
    return [g for g in candidates if g in text]


def _subject_candidates(text: str) -> list[str]:
    """Return matching subjects."""
    candidates = [
        "道德与法治", "信息科技", "语文", "数学", "英语", "物理",
        "化学", "生物", "历史", "地理", "科学",
    ]
    return [s for s in candidates if s in text]


def _extract_topic(clean_text: str, grade: str, subject: str) -> str | None:
    """Extract topic by removing grade and subject, or using 《》<> delimiters."""
    for m in re.finditer(r"[《〈]([^》〉]+)[》〉]", clean_text):
        return m.group(1).strip()
    for m in re.finditer(r"<([^>]+)>", clean_text):
        return m.group(1).strip()
    remainder = clean_text
    if grade:
        remainder = remainder.replace(grade, "")
    if subject:
        remainder = remainder.replace(subject, "")
    remainder = re.sub(r"(课件|生成|给我|请|一个|的|关于|有关|做|制作)", "", remainder).strip()
    return remainder if remainder else None


def extract_slots(clean_text: str, entry: dict[str, Any]) -> dict[str, Any]:
    """Extract known slots from user's natural language input via local patterns."""
    grades = _grade_candidates(clean_text)
    subjects = _subject_candidates(clean_text)
    grade = grades[0] if grades else None
    subject = subjects[0] if subjects else None
    topic = _extract_topic(clean_text, grade or "", subject or "")

    result: dict[str, Any] = {}
    if subject:
        result["subject"] = subject
    if grade:
        result["grade"] = grade
    if topic:
        result["topic"] = topic
    return result


GLOBAL_DEFAULTS = {
    "lessonType": "new_concept",
    "durationMin": 40,
}


def complete_slots(slots: dict[str, Any], entry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Check required/optional slots, auto-fill from defaults, return (config, assumptions)."""
    required = entry.get("requiredSlots", [])
    optional = entry.get("optionalSlots", [])
    assumptions: list[str] = []

    for key in required:
        if key not in slots:
            if key in GLOBAL_DEFAULTS:
                slots[key] = GLOBAL_DEFAULTS[key]
                assumptions.append(f"{key} 使用默认值: {GLOBAL_DEFAULTS[key]}")
            elif key == "subject":
                assumptions.append("subject 未识别，请确认学科。")
            elif key == "grade":
                assumptions.append("grade 未识别，请确认年级。")
            elif key == "topic":
                assumptions.append("topic 未识别，请确认课题。")

    for key in optional:
        if key not in slots and key in GLOBAL_DEFAULTS:
            slots[key] = GLOBAL_DEFAULTS[key]

    return slots, assumptions


def command_run(argv: list[str]) -> int:
    """Execute full pipeline: resolve → extract slots → complete → config → render script."""
    parser = argparse.ArgumentParser(
        prog="agent_cli.py run",
        description="执行 Skill 完整链路：识别入口 → 提取槽位 → 补全需求 → 调用渲染脚本 → 输出结果",
    )
    parser.add_argument("request", nargs="*", help="教师请求文本，例如 '@课件生成 高一语文<师说>课件'")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-validate", action="store_true", help="跳过校验")
    args = parser.parse_args(argv)

    raw_request = " ".join(args.request).strip()
    if not raw_request.startswith("@"):
        dump_json({
            "status": "error",
            "code": "missing_entry_name",
            "message": "run 命令需要 @入口名，例如: run '@课件生成 高一语文<师说>课件'",
        })
        return 2

    entries = load_entries()
    selected, clean_text, unknown = parse_fixed_entry_tokens(raw_request, entries)

    if unknown:
        dump_json({
            "status": "error",
            "code": "unknown_entry_name",
            "unknownEntryToken": unknown,
            "message": "该 @入口名 不在固定入口中。",
            "choices": choices(entries),
        })
        return 2

    if not selected:
        dump_json({
            "status": "error",
            "code": "no_entry_matched",
            "message": "未匹配到任何入口。",
            "choices": choices(entries),
        })
        return 2

    entry = selected[0]
    execution = entry.get("execution", {})
    render_script = execution.get("renderScript")

    if not render_script:
        dump_json({
            "status": "error",
            "code": "no_render_script",
            "message": f"Skill '{entry['skillId']}' 尚未实现渲染脚本（状态: {entry.get('status')})。",
            "selected": selected_entry(entry),
        })
        return 2

    # Extract slots from user input
    slots = extract_slots(clean_text, entry)

    # Complete slots with defaults
    config, assumptions = complete_slots(slots, entry)

    # Check critical missing required slots
    required = entry.get("requiredSlots", [])
    critical_missing = [r for r in required if r not in config and r not in {"knowledgePointIds"}]
    if critical_missing:
        dump_json({
            "status": "error",
            "code": "missing_required_slots",
            "message": f"无法从请求中提取必填字段: {', '.join(critical_missing)}",
            "selected": selected_entry(entry),
            "extractedSlots": slots,
            "assumptions": assumptions,
        })
        return 2

    # Write config JSON
    output_dir = ROOT.parent / execution.get("outputDir", "generated-outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = config.get("topic", re.sub(r"[^a-zA-Z0-9一-鿿]", "", clean_text)[:20] or "output")
    config_path = output_dir / f"{base_name}-config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build and execute render command
    script_path = ROOT.parent / render_script
    if not script_path.exists():
        dump_json({
            "status": "error",
            "code": "render_script_not_found",
            "message": f"渲染脚本不存在: {script_path}",
        })
        return 2

    cmd = [sys.executable, str(script_path)]
    arg_pattern = execution.get("argPattern", "A")
    output_prefix = output_dir / base_name

    if arg_pattern == "A":
        cmd.extend([str(output_prefix), "--config", str(config_path)])
    else:
        cmd.extend([str(config_path), "--output", str(output_prefix)])

    if args.no_validate:
        cmd.append("--no-validate")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        dump_json({
            "status": "error",
            "code": "render_timeout",
            "message": "渲染脚本执行超时（超过 300 秒）",
            "config": config,
        })
        return 1
    except Exception as exc:
        dump_json({
            "status": "error",
            "code": "render_failed",
            "message": str(exc),
            "config": config,
        })
        return 1

    # Return result
    output_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    payload = {
        "status": "success" if result.returncode == 0 else "error",
        "decision": "executed",
        "selected": selected_entry(entry),
        "config": config,
        "assumptions": assumptions,
        "renderCommand": " ".join(cmd),
        "exitCode": result.returncode,
        "outputFiles": output_files,
        "stdout": result.stdout.strip(),
    }
    if result.stderr.strip():
        payload["stderr"] = result.stderr.strip()

    if args.json:
        dump_json(payload)
    else:
        if result.returncode == 0:
            print(f"OK: {entry['displayName']} executed successfully")
            for f in output_files:
                print(f"  -> {f}")
            if assumptions:
                for a in assumptions:
                    print(f"  ~ {a}")
        else:
            print(f"FAIL: {entry['displayName']} failed (exit code: {result.returncode})")
            if result.stderr.strip():
                print(result.stderr, end="", file=sys.stderr)

    return result.returncode


def print_help() -> None:
    print(
        """AgentDesign CLI

用法:
  python3 agent_cases/agent_cli.py resolve "@课件生成 八年级物理水的三态" --json
  python3 agent_cases/agent_cli.py resolve "八年级物理水的三态课件" --json
  python3 agent_cases/agent_cli.py resolve "八年级物理水的三态课件" --select 2 --json
  python3 agent_cases/agent_cli.py skill list --json
  python3 agent_cases/agent_cli.py skill read lesson-deck-generation-skill --section meta --json
  python3 agent_cases/agent_cli.py index rebuild --json

规则:
  - 只识别 skill-entrypoints.json 中的 11 个固定中文入口名。
  - 不做别名、同义词、关键词或模糊匹配。
  - 没有 @入口名 时返回 choices 菜单，由用户选序号后继续。
"""
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"help", "--help", "-h"}:
        print_help()
        return 0

    raw = " ".join(argv).strip()
    if argv[0] not in KNOWN_COMMANDS:
        if raw.startswith("@"):
            return command_run(argv + ["--json"])
        return command_resolve(argv + ["--json"])

    command, rest = argv[0], argv[1:]
    if command == "resolve":
        return command_resolve(rest)
    if command == "skill":
        return command_skill(rest)
    if command == "index":
        return command_index(rest)
    if command == "run":
        return command_run(rest)
    raise CliError(f"未知命令: {command}", code="unknown_command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CliError as exc:
        payload = {"status": "error", "code": exc.code, "message": str(exc)}
        payload.update(exc.payload)
        dump_json(payload)
        raise SystemExit(2)
