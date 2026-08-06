#!/usr/bin/env python3
"""Deterministic runner for classroom-reflection-skill.

The script owns fragile workflow steps: input normalization, rubric selection,
output directory/state creation, prompt payload assembly, and report validation.
The LLM still owns classroom judgment and report writing.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
GENERATED_ROOT = SKILL_ROOT / "generated-outputs"
INTERNAL_DIR_NAME = ".internal"
DEFAULT_TRANSCRIPT_PREVIEW_CHARS = 0
RUBRIC_MAP_PATH = SKILL_ROOT / "assets" / "rubric" / "rubric-map.json"
RUBRIC_DIR = SKILL_ROOT / "assets" / "rubric"
REPORT_PROMPT_PATH = SKILL_ROOT / "assets" / "prompts" / "review_report_prompt.md"
REPORT_TEMPLATE_PATH = SKILL_ROOT / "assets" / "output-templates" / "report_template.md"
MEDIA_TOOL_SCRIPT = SKILL_ROOT.parent / "classroom-reflection-media-tool" / "transcribe_media.py"
MEDIA_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".m4a",
    ".mov",
    ".mpeg",
    ".mpg",
    ".wav",
    ".webm",
}
MEDIA_REQUEST_NAME = "media-transcription-request.json"
MEDIA_RAW_ARTIFACT_NAME = "tingwu-direct-raw.json"
MEDIA_RAW_DIR_NAME = "tingwu-raw"

REQUIRED_REPORT_SECTIONS = [
    "## 一、基本判断",
    "## 二、课堂流程复盘",
    "## 三、定性评价结果",
    "## 四、主要优点",
    "## 五、关键问题",
    "## 六、具体修改建议",
    "## 七、可直接替换的课堂语言",
]

AUDIO_UNSUPPORTED_EVALUATION_PATTERNS = [
    r"板书",
    r"教态",
    r"课堂纪律",
    r"学生表情|表情",
    r"眼神|站位|巡视",
    r"动作质量|体能表现",
    r"队形|场地|器材组织",
    r"作品质量|视觉美感",
    r"实验操作质量",
    r"课件(?:美观|设计|使用|呈现|切换|规范|有效)",
]

SUBJECT_HINTS = {
    "语文": ["课文", "作文", "阅读", "自然段", "作者", "习作", "朗读", "中心意思", "修辞"],
    "数学": ["计算", "分数", "方程", "图形", "面积", "周长", "证明", "函数"],
    "英语": ["english", "word", "sentence", "grammar", "listen", "speak", "read", "write"],
    "科学": ["实验", "观察", "假设", "现象", "探究", "记录"],
    "物理": ["力", "电路", "电压", "光", "声", "运动", "压强"],
    "化学": ["化学", "反应", "溶液", "酸", "碱", "实验"],
    "历史": ["历史", "朝代", "事件", "人物", "制度"],
    "地理": ["地理", "地图", "气候", "地形", "经纬"],
}

SPEAKER_MAP = {
    "教师": "教师",
    "老师": "教师",
    "teacher": "教师",
    "t": "教师",
    "学生": "学生",
    "student": "学生",
    "s": "学生",
    "生": "学生",
    "其他": "其他",
    "other": "其他",
}


@dataclass(frozen=True)
class RubricSelection:
    source: str
    matched_subject: str | None
    rubric_file: str | None
    rubric_path: Path | None
    rubric_text: str
    warning: str | None = None


@dataclass(frozen=True)
class MediaTranscriptionArtifacts:
    source: str
    source_type: str
    request_path: Path
    raw_artifact_path: Path
    raw_dir: Path


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def is_media_input(path: Path | None) -> bool:
    """判断 prepare 输入是否为本地视音频文件。"""
    return path is not None and path.suffix.lower() in MEDIA_EXTENSIONS


def transcribe_media_input(media_path: Path, work_dir: Path) -> MediaTranscriptionArtifacts:
    """调用 classroom-reflection-media-tool，把本地媒体转成 request JSON。

    这里不把媒体转写逻辑复制进 reflection skill，只做编排。真正的抽音频、
    通义听悟实时推流、原始事件保存和 request 生成仍由 media tool 负责。
    """
    if not media_path.exists():
        raise FileNotFoundError(f"Media input does not exist: {media_path}")
    if not MEDIA_TOOL_SCRIPT.exists():
        raise FileNotFoundError(f"Media transcription tool not found: {MEDIA_TOOL_SCRIPT}")

    request_path = work_dir / MEDIA_REQUEST_NAME
    raw_artifact_path = work_dir / MEDIA_RAW_ARTIFACT_NAME
    raw_dir = work_dir / MEDIA_RAW_DIR_NAME
    command = [
        sys.executable,
        str(MEDIA_TOOL_SCRIPT),
        "transcribe-realtime",
        "--media-file",
        str(media_path),
        "--quiet",
        "--raw-dir",
        str(raw_dir),
        "--raw-output",
        str(raw_artifact_path),
        "--output",
        str(request_path),
    ]
    proc = subprocess.run(command, text=True, capture_output=True)
    if proc.returncode != 0:
        detail = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part)
        raise RuntimeError(f"Media transcription failed for {media_path}.\n{detail}")
    if not request_path.exists():
        raise RuntimeError(f"Media transcription did not create request JSON: {request_path}")
    return MediaTranscriptionArtifacts(
        source=str(media_path),
        source_type="local-file",
        request_path=request_path,
        raw_artifact_path=raw_artifact_path,
        raw_dir=raw_dir,
    )


def transcribe_media_url(media_url: str, work_dir: Path) -> MediaTranscriptionArtifacts:
    """调用 media tool 的离线模式，把公网媒体 URL 转成 request JSON。

    这个入口适合 cloudflared/ngrok 临时隧道，也适合以后切换到学校服务器、
    NAS 反代或其他公网存储。reflection skill 不关心 URL 来自哪里，只关心
    media tool 最终生成标准 request JSON。
    """
    if not media_url.startswith(("http://", "https://")):
        raise ValueError("--media-url must be an HTTP/HTTPS URL.")
    if not MEDIA_TOOL_SCRIPT.exists():
        raise FileNotFoundError(f"Media transcription tool not found: {MEDIA_TOOL_SCRIPT}")

    request_path = work_dir / MEDIA_REQUEST_NAME
    raw_artifact_path = work_dir / MEDIA_RAW_ARTIFACT_NAME
    raw_dir = work_dir / MEDIA_RAW_DIR_NAME
    command = [
        sys.executable,
        str(MEDIA_TOOL_SCRIPT),
        "transcribe",
        "--media-url",
        media_url,
        "--wait",
        "--raw-dir",
        str(raw_dir),
        "--raw-output",
        str(raw_artifact_path),
        "--output",
        str(request_path),
    ]
    proc = subprocess.run(command, text=True, capture_output=True)
    if proc.returncode != 0:
        detail = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part)
        raise RuntimeError(f"Media URL transcription failed for {media_url}.\n{detail}")
    if not request_path.exists():
        raise RuntimeError(f"Media URL transcription did not create request JSON: {request_path}")
    return MediaTranscriptionArtifacts(
        source=media_url,
        source_type="media-url",
        request_path=request_path,
        raw_artifact_path=raw_artifact_path,
        raw_dir=raw_dir,
    )


def archive_media_artifacts(artifacts: MediaTranscriptionArtifacts, internal_dir: Path) -> dict[str, Any]:
    """把媒体转写中间产物归档进本次 run 的 .internal 目录。"""
    request_dest = internal_dir / MEDIA_REQUEST_NAME
    shutil.copy2(artifacts.request_path, request_dest)

    raw_artifact_dest = internal_dir / MEDIA_RAW_ARTIFACT_NAME
    if artifacts.raw_artifact_path.exists():
        shutil.copy2(artifacts.raw_artifact_path, raw_artifact_dest)
    else:
        raw_artifact_dest = None

    raw_dir_dest = internal_dir / MEDIA_RAW_DIR_NAME
    if artifacts.raw_dir.exists():
        shutil.copytree(artifacts.raw_dir, raw_dir_dest, dirs_exist_ok=True)
    else:
        raw_dir_dest = None

    return {
        "source": artifacts.source,
        "sourceType": artifacts.source_type,
        "tool": str(MEDIA_TOOL_SCRIPT),
        "requestPath": str(request_dest),
        "rawArtifactPath": str(raw_artifact_dest) if raw_artifact_dest else None,
        "rawDir": str(raw_dir_dest) if raw_dir_dest else None,
    }


def read_input(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None:
        raw = sys.stdin.read()
        source = "<stdin>"
    else:
        raw = path.read_text(encoding="utf-8")
        source = str(path)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"transcription": parse_plain_text_transcript(raw)}

    if isinstance(data, list):
        data = {"transcription": data}
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object, JSON transcription array, or plain text transcript.")
    return data, source


def parse_plain_text_transcript(raw: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current = 0.0
    pattern = re.compile(
        r"^\s*(?:\[(?P<start>\d+(?:\.\d+)?)\s*[-,~]\s*(?P<end>\d+(?:\.\d+)?)\]\s*)?"
        r"(?:(?P<speaker>教师|老师|学生|其他|teacher|student|other|T|S)\s*[:：]\s*)?"
        r"(?P<content>.+?)\s*$",
        re.IGNORECASE,
    )
    for line in raw.splitlines():
        if not line.strip():
            continue
        match = pattern.match(line)
        if not match:
            continue
        content = match.group("content").strip()
        if not content:
            continue
        start = float(match.group("start")) if match.group("start") else current
        end = float(match.group("end")) if match.group("end") else max(start + estimate_duration(content), start + 1)
        speaker = normalize_speaker(match.group("speaker") or infer_speaker(content))
        rows.append({"id": len(rows) + 1, "content": content, "start": start, "end": end, "speaker": speaker})
        current = end
    return rows


def estimate_duration(content: str) -> float:
    return max(1.0, min(30.0, len(content) / 4.0))


def infer_speaker(content: str) -> str:
    teacher_markers = ["同学们", "请坐", "谁来说", "请你", "看屏幕", "打开", "开始吧"]
    if any(marker in content for marker in teacher_markers):
        return "教师"
    return "其他"


def normalize_request(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    transcription = data.get("transcription")
    if not isinstance(transcription, list) or not transcription:
        if data.get("transcriptionProvider") or data.get("mediaUrl") or data.get("mediaFile"):
            raise ValueError(
                "Media transcription output has no non-empty transcription[]. "
                "Check the archived Tingwu raw result or rerun the media tool with --raw-dir to inspect its sentence fields."
            )
        raise ValueError("Missing required non-empty transcription[].")

    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(transcription, start=1):
        if not isinstance(row, dict):
            warnings.append(f"transcription[{index}] is not an object and was skipped.")
            continue
        content = str(row.get("content", "")).strip()
        if not content:
            warnings.append(f"transcription[{index}] has empty content and was skipped.")
            continue
        start = coerce_float(row.get("start"), default=None)
        end = coerce_float(row.get("end"), default=None)
        if start is None:
            start = normalized_rows[-1]["end"] if normalized_rows else 0.0
            warnings.append(f"transcription[{index}] missing numeric start; inferred {start}.")
        if end is None or end <= start:
            end = start + estimate_duration(content)
            warnings.append(f"transcription[{index}] missing/invalid end; inferred {end:.2f}.")
        speaker = normalize_speaker(row.get("speaker"))
        if speaker == "其他" and row.get("speaker") not in ("其他", "other", "Other"):
            warnings.append(f"transcription[{index}] speaker normalized to 其他.")
        normalized_rows.append(
            {
                "id": row.get("id", len(normalized_rows) + 1),
                "content": content,
                "start": round(float(start), 3),
                "end": round(float(end), 3),
                "speaker": speaker,
            }
        )

    if not normalized_rows:
        raise ValueError("No valid transcription rows after normalization.")
    if all(row["speaker"] == "其他" for row in normalized_rows):
        raise ValueError("No effective classroom data: all transcription rows are speaker=其他.")

    data = dict(data)
    data["transcription"] = normalized_rows
    if not data.get("lessonDurationMin"):
        data["lessonDurationMin"] = round(max(row["end"] for row in normalized_rows) / 60, 1)
    return data, warnings


def coerce_float(value: Any, default: float | None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_speaker(value: Any) -> str:
    key = str(value or "").strip().lower()
    return SPEAKER_MAP.get(key, SPEAKER_MAP.get(str(value or "").strip(), "其他"))


def normalize_slug(value: str | None, fallback: str = "classroom-reflection") -> str:
    if not value:
        return fallback
    cleaned = str(value).strip().strip("《》「」“”\"'").lower()
    if cleaned == "盼":
        return "pan-lesson"
    replacements = {
        "异分母分数加减法": "fraction-add-sub",
    }
    if cleaned in replacements:
        return replacements[cleaned]
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", cleaned, flags=re.UNICODE)
    return cleaned or fallback


def safe_id(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    cleaned = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", str(value).strip(), flags=re.UNICODE).strip("-").lower()
    return cleaned or fallback


def next_conversation_id(generated_root: Path, lesson_slug: str, requested_id: str | None, reuse_existing: bool = False) -> str:
    base_id = safe_id(requested_id, f"case-{lesson_slug}-001")
    lesson_dir = generated_root / lesson_slug
    if requested_id and reuse_existing:
        if not (lesson_dir / base_id).exists():
            raise ValueError(f"--reuse-existing requested but conversation directory does not exist: {lesson_dir / base_id}")
        return base_id
    if not (lesson_dir / base_id).exists():
        return base_id

    match = re.match(r"^(?P<prefix>.*?)-(?P<number>\d{3,})$", base_id)
    if match:
        prefix = match.group("prefix")
        start = int(match.group("number")) + 1
    else:
        prefix = base_id
        start = 2

    for number in range(start, 10000):
        candidate = f"{prefix}-{number:03d}"
        if not (lesson_dir / candidate).exists():
            return candidate
    raise ValueError(f"Could not allocate a new conversation id under {lesson_dir}.")


def infer_subject(data: dict[str, Any]) -> tuple[str | None, str, list[str]]:
    explicit = str(data.get("subject") or "").strip()
    if explicit:
        return explicit, "用户提供", ["request.subject"]

    text = " ".join(
        [
            str(data.get("topic") or ""),
            str(data.get("grade") or ""),
            " ".join(map(str, data.get("objectives") or [])) if isinstance(data.get("objectives"), list) else "",
            str(data.get("requirements") or ""),
            " ".join(row["content"] for row in data.get("transcription", [])[:80]),
        ]
    ).lower()
    scores: list[tuple[int, str, list[str]]] = []
    for subject, hints in SUBJECT_HINTS.items():
        hits = [hint for hint in hints if hint.lower() in text]
        if hits:
            scores.append((len(hits), subject, hits[:5]))
    scores.sort(reverse=True)
    if not scores:
        return None, "未能可靠识别", []
    if len(scores) > 1 and scores[0][0] == scores[1][0]:
        return None, "低", scores[0][2] + scores[1][2]
    confidence = "高" if scores[0][0] >= 3 else "中"
    return scores[0][1], confidence, scores[0][2]


def select_rubric(data: dict[str, Any], inferred_subject_arg: str | None = None) -> RubricSelection:
    custom = data.get("customRubric")
    if custom:
        text = custom_rubric_text(custom)
        if text:
            return RubricSelection(
                source="用户自定义评价量规",
                matched_subject=None,
                rubric_file=None,
                rubric_path=None,
                rubric_text=text,
            )

    rubric_map = load_json(RUBRIC_MAP_PATH)
    default_file = rubric_map.get("default", "00_通用.md")
    subject = str(data.get("subject") or inferred_subject_arg or data.get("inferredSubject") or "").strip()
    matched = match_rubric(subject, rubric_map) if subject else None
    warning = None
    if not matched:
        inferred, confidence, _evidence = infer_subject(data)
        if inferred and confidence != "低":
            matched = match_rubric(inferred, rubric_map)
            subject = inferred
    if not matched:
        matched = {"subject": "通用", "file": default_file}
        warning = "未能可靠匹配学科评价量规，已回退通用评价量规。"

    rubric_file = matched["file"]
    rubric_path = RUBRIC_DIR / rubric_file
    return RubricSelection(
        source=f"匹配评价量规 `{rubric_file}`" if rubric_file != default_file else f"通用评价量规 `{rubric_file}`",
        matched_subject=matched.get("subject") or subject,
        rubric_file=rubric_file,
        rubric_path=rubric_path,
        rubric_text=rubric_path.read_text(encoding="utf-8"),
        warning=warning,
    )


def custom_rubric_text(custom: Any) -> str:
    if isinstance(custom, str):
        return custom.strip()
    if isinstance(custom, (dict, list)):
        return json.dumps(custom, ensure_ascii=False, indent=2)
    return ""


def match_rubric(subject: str, rubric_map: dict[str, Any]) -> dict[str, Any] | None:
    normalized = subject.strip().lower()
    for item in rubric_map.get("rubrics", []):
        candidates = [item.get("subject", ""), *item.get("aliases", [])]
        if any(normalized == str(candidate).strip().lower() for candidate in candidates):
            return item
    for item in rubric_map.get("rubrics", []):
        candidates = [item.get("subject", ""), *item.get("aliases", [])]
        if any(str(candidate).strip().lower() and str(candidate).strip().lower() in normalized for candidate in candidates):
            return item
    return None


def compute_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    durations = {"教师": 0.0, "学生": 0.0, "其他": 0.0}
    counts = {"教师": 0, "学生": 0, "其他": 0}
    question_count = 0
    for row in rows:
        speaker = row["speaker"]
        duration = max(0.0, float(row["end"]) - float(row["start"]))
        durations[speaker] += duration
        counts[speaker] += 1
        if speaker == "教师":
            question_count += row["content"].count("？") + row["content"].count("?")
    total_speaking = sum(durations.values()) or 1.0
    return {
        "utteranceCount": {"total": len(rows), "teacher": counts["教师"], "student": counts["学生"], "other": counts["其他"]},
        "speakingDurationSec": {"teacher": round(durations["教师"], 2), "student": round(durations["学生"], 2), "other": round(durations["其他"], 2)},
        "talkRatio": {
            "teacher": round(durations["教师"] / total_speaking, 3),
            "student": round(durations["学生"] / total_speaking, 3),
            "other": round(durations["其他"] / total_speaking, 3),
        },
        "totalDurationSec": round(max(row["end"] for row in rows) - min(row["start"] for row in rows), 2),
        "teacherQuestionMarkCount": question_count,
    }


def draft_segments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = min(row["start"] for row in rows)
    end = max(row["end"] for row in rows)
    duration = max(1.0, end - start)
    names = ["导入与目标唤起", "新知建构与文本/任务推进", "学生练习或探究活动", "总结提升与作业布置"]
    segments = []
    for index, name in enumerate(names):
        seg_start = start + duration * index / 4
        seg_end = start + duration * (index + 1) / 4
        seg_rows = [row for row in rows if row["start"] < seg_end and row["end"] > seg_start]
        segments.append(
            {
                "name": name,
                "startSec": round(seg_start, 2),
                "endSec": round(seg_end, 2),
                "timeLabel": format_range(seg_start, seg_end),
                "utteranceCount": len(seg_rows),
                "teacherUtteranceCount": sum(1 for row in seg_rows if row["speaker"] == "教师"),
                "studentUtteranceCount": sum(1 for row in seg_rows if row["speaker"] == "学生"),
            }
        )
    return segments


def format_range(start: float, end: float) -> str:
    return f"{format_min_sec(start)}-{format_min_sec(end)}（{round(start)}-{round(end)} 秒）"


def format_min_sec(seconds: float) -> str:
    seconds_int = int(round(seconds))
    return f"{seconds_int // 60}分{seconds_int % 60:02d}秒"


def prepare(args: argparse.Namespace) -> None:
    media_context: TemporaryDirectory[str] | None = None
    media_artifacts: MediaTranscriptionArtifacts | None = None
    try:
        if args.media_url and args.input:
            raise ValueError("Use either positional input or --media-url, not both.")
        if args.media_url:
            media_context = TemporaryDirectory(prefix="classroom-reflection-media-")
            media_artifacts = transcribe_media_url(args.media_url, Path(media_context.name))
            data, _media_request_source = read_input(media_artifacts.request_path)
            input_source = args.media_url
        elif is_media_input(args.input):
            media_context = TemporaryDirectory(prefix="classroom-reflection-media-")
            media_artifacts = transcribe_media_input(args.input, Path(media_context.name))
            data, _media_request_source = read_input(media_artifacts.request_path)
            input_source = str(args.input)
        else:
            data, input_source = read_input(args.input)

        data, warnings = normalize_request(data)
        generated_root = args.output_root or GENERATED_ROOT
        lesson_slug = normalize_slug(args.lesson_slug or data.get("outputSlug") or data.get("topic"), fallback=input_slug(args.input))
        conversation_id = next_conversation_id(generated_root, lesson_slug, args.conversation_id, args.reuse_existing)
        output_dir = generated_root / lesson_slug / conversation_id
        internal_dir = output_dir / INTERNAL_DIR_NAME
        output_dir.mkdir(parents=True, exist_ok=True)
        internal_dir.mkdir(parents=True, exist_ok=True)

        media_state = archive_media_artifacts(media_artifacts, internal_dir) if media_artifacts else None

        rubric = select_rubric(data, args.inferred_subject)
        if rubric.warning:
            warnings.append(rubric.warning)
        subject, subject_confidence, subject_evidence = infer_subject(data)
        stats = compute_stats(data["transcription"])
        segments = data.get("lessonContext", {}).get("stages") if isinstance(data.get("lessonContext"), dict) else None
        if not segments:
            segments = draft_segments(data["transcription"])

        state = {
            "skill": "classroom-reflection-skill",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "lessonSlug": lesson_slug,
            "conversationId": conversation_id,
            "inputFile": input_source,
            "generatedRoot": str(generated_root),
            "outputDir": str(output_dir),
            "rubricSource": rubric.source,
            "matchedSubject": rubric.matched_subject,
            "matchedRubric": rubric.rubric_file,
            "rubricPath": str(rubric.rubric_path) if rubric.rubric_path else None,
            "reportPath": str(output_dir / "reflection-report.md"),
            "lessonPlanPath": str(output_dir / "optimized-lesson-plan.md"),
            "teacherTranscriptPath": str(output_dir / "teacher-transcript.md"),
            "internalDir": str(internal_dir),
            "promptPayloadPath": str(internal_dir / "prompt-payload.md"),
            "normalizedInputPath": str(internal_dir / "normalized-input.json"),
            "validationReportPath": str(internal_dir / "validation-report.json"),
            "promptTranscriptPreviewChars": args.transcript_preview_chars,
            "warnings": warnings,
        }
        if media_state:
            state["mediaTranscription"] = media_state

        normalized_payload = {
            "request": data,
            "subjectInference": {
                "subject": subject,
                "confidence": subject_confidence,
                "evidence": subject_evidence,
            },
            "stats": stats,
            "draftSegments": segments,
            "rubric": {
                "source": rubric.source,
                "matchedSubject": rubric.matched_subject,
                "rubricFile": rubric.rubric_file,
                "content": rubric.rubric_text,
            },
            "state": state,
        }
        write_json(internal_dir / "normalized-input.json", normalized_payload)
        write_json(output_dir / "run-state.json", state)
        (internal_dir / "prompt-payload.md").write_text(
            build_prompt_payload(normalized_payload, args.transcript_preview_chars),
            encoding="utf-8",
        )

        print(json.dumps(state, ensure_ascii=False, indent=2))
    finally:
        if media_context:
            media_context.cleanup()


def input_slug(path: Path | None) -> str:
    if path is None:
        return "classroom-reflection"
    return normalize_slug(path.stem, fallback="classroom-reflection")


def build_prompt_payload(payload: dict[str, Any], transcript_preview_chars: int = DEFAULT_TRANSCRIPT_PREVIEW_CHARS) -> str:
    request = payload["request"]
    rubric = payload["rubric"]
    state = payload["state"]
    prompt = REPORT_PROMPT_PATH.read_text(encoding="utf-8")
    template = REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    transcription_preview = json.dumps(request["transcription"], ensure_ascii=False, indent=2)
    if transcript_preview_chars < 0:
        transcript_preview_chars = DEFAULT_TRANSCRIPT_PREVIEW_CHARS
    transcript_heading = "完整逐字稿"
    transcript_note = ""
    if transcript_preview_chars > 0 and len(transcription_preview) > transcript_preview_chars:
        transcript_heading = "逐字稿节选"
        transcription_preview = (
            transcription_preview[:transcript_preview_chars]
            + f"\n...（已截断；完整规范化逐字稿见 {state['normalizedInputPath']}，仅在需要核对原句证据时读取）"
        )
        transcript_note = (
            f"\n注意：本材料包使用了逐字稿节选；如需覆盖整节课评价，必须读取 `{state['normalizedInputPath']}` "
            "补足截断范围外的课堂证据。\n"
        )

    return f"""# 课堂反思报告生成任务

必须把最终 Markdown 报告写入：

```text
{state["reportPath"]}
```

写完后运行：

```bash
python3 agent_cases/classroom-reflection-skill/scripts/run_reflection.py validate --state {state["outputDir"]}/run-state.json
```

## 输出目录状态

```json
{json.dumps(state, ensure_ascii=False, indent=2)}
```

## 系统提示词

{prompt}

## 报告模板

{template}

## 本次评价量规

量规来源：{rubric["source"]}
匹配学科：{rubric["matchedSubject"]}
匹配文件：{rubric["rubricFile"]}

```markdown
{rubric["content"]}
```

## 脚本统计与初步环节

```json
{json.dumps({"stats": payload["stats"], "draftSegments": payload["draftSegments"], "subjectInference": payload["subjectInference"]}, ensure_ascii=False, indent=2)}
```

## 用户请求元数据

```json
{json.dumps({k: v for k, v in request.items() if k != "transcription"}, ensure_ascii=False, indent=2)}
```

## {transcript_heading}

```json
{transcription_preview}
```
{transcript_note}
"""


def save_report(args: argparse.Namespace) -> None:
    state = load_json(args.state)
    report_path = Path(state["reportPath"])
    draft = args.report.read_text(encoding="utf-8") if args.report else sys.stdin.read()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(draft, encoding="utf-8")
    result = validate_report(state, draft)
    write_json(validation_report_path(state), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "fail":
        raise SystemExit(2)


def validate(args: argparse.Namespace) -> None:
    state = load_json(args.state)
    report_path = Path(state["reportPath"])
    if not report_path.exists():
        result = {"status": "fail", "failures": [f"Missing report file: {report_path}"], "warnings": []}
    else:
        result = validate_report(state, report_path.read_text(encoding="utf-8"))
    write_json(validation_report_path(state), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "fail":
        raise SystemExit(2)


def validate_report(state: dict[str, Any], markdown: str) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    for section in REQUIRED_REPORT_SECTIONS:
        if section not in markdown:
            failures.append(f"Missing required section: {section}")

    report_path = Path(state["reportPath"])
    expected_dir = Path(state["outputDir"])
    generated_root = Path(state.get("generatedRoot") or GENERATED_ROOT)
    if report_path.parent != expected_dir:
        failures.append("reportPath is not inside outputDir.")
    if expected_dir.parent.parent != generated_root:
        failures.append("outputDir must be generated-outputs/<lesson-slug>/<conversation-id>/, not lesson root.")

    if "生成时间：" not in markdown:
        warnings.append("Report does not include 生成时间： near the beginning.")
    if "## 二、评价依据" in markdown:
        failures.append("Report should not include a standalone ## 二、评价依据 section.")
    if "依据说明：" in markdown:
        failures.append("Report should use 学科与量规 instead of 依据说明.")
    if "## 八、后续优化建议" in markdown:
        failures.append("Report should not include a standalone ## 八、后续优化建议 section.")
    if "## 三、评分结果" in markdown:
        failures.append("Report should use ## 三、定性评价结果 instead of ## 三、评分结果.")
    quantitative_score_patterns = [
        r"总分[:：]\s*\d+(?:\.\d+)?\s*/\s*100",
        r"(?:总分|得分|分数|评分|分值|满分|扣分|加分)\s*[:：]?\s*\d+(?:\.\d+)?",
        r"\d+(?:\.\d+)?\s*/\s*(?:100|10|5)",
        r"百分制|满分\s*\d+(?:\.\d+)?",
    ]
    if any(re.search(pattern, markdown) for pattern in quantitative_score_patterns):
        failures.append("Report should not include a quantitative total score.")
    if any(
        line.lstrip().startswith("|") and re.search(r"\|\s*[^|\n]*(?:分值|得分|分数|权重|满分)[^|\n]*\|", line)
        for line in markdown.splitlines()
    ):
        failures.append("Report should not include quantitative score columns.")

    evaluation_section = extract_section(markdown, "## 三、定性评价结果", "## 四、主要优点")
    if any(re.search(pattern, evaluation_section) for pattern in AUDIO_UNSUPPORTED_EVALUATION_PATTERNS):
        failures.append("Report evaluation table should not include audio-unsupported visual or in-person observation items.")
    if not ("导入语" in markdown and "提问语" in markdown and "评价语" in markdown):
        warnings.append("Replacement language section may be incomplete.")

    return {"status": "fail" if failures else ("warn" if warnings else "ok"), "failures": failures, "warnings": warnings}


def extract_section(markdown: str, start_marker: str, end_marker: str) -> str:
    if start_marker not in markdown:
        return ""
    after_start = markdown.split(start_marker, 1)[1]
    if end_marker not in after_start:
        return after_start
    return after_start.split(end_marker, 1)[0]


def validation_report_path(state: dict[str, Any]) -> Path:
    if state.get("validationReportPath"):
        return Path(state["validationReportPath"])
    return Path(state["outputDir"]) / INTERNAL_DIR_NAME / "validation-report.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, save, and validate classroom reflection runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Normalize input and build prompt payload.")
    prepare_parser.add_argument("input", nargs="?", type=Path, help="JSON/plain text transcript or local classroom media file. Reads stdin when omitted.")
    prepare_parser.add_argument("--media-url", help="Public HTTP/HTTPS classroom media URL for offline Tingwu transcription.")
    prepare_parser.add_argument("--conversation-id", help="Explicit id for this conversation/case.")
    prepare_parser.add_argument("--lesson-slug", help="Explicit lesson slug for generated-outputs.")
    prepare_parser.add_argument("--inferred-subject", help="LLM-inferred subject candidate to map through rubric-map.json.")
    prepare_parser.add_argument("--output-root", type=Path, help="Override generated-outputs root; mainly for tests.")
    prepare_parser.add_argument("--reuse-existing", action="store_true", help="Reuse an explicit --conversation-id directory instead of allocating the next id.")
    prepare_parser.add_argument(
        "--transcript-preview-chars",
        type=int,
        default=DEFAULT_TRANSCRIPT_PREVIEW_CHARS,
        help="Maximum characters of normalized transcription embedded in prompt-payload.md. Defaults to 0, meaning embed the full transcript. Full input always remains in .internal/normalized-input.json.",
    )
    prepare_parser.set_defaults(func=prepare)

    save_parser = subparsers.add_parser("save-report", help="Write an LLM-generated report to state.reportPath and validate it.")
    save_parser.add_argument("--state", required=True, type=Path, help="Path to run-state.json.")
    save_parser.add_argument("--report", type=Path, help="Markdown draft path. Reads stdin when omitted.")
    save_parser.set_defaults(func=save_report)

    validate_parser = subparsers.add_parser("validate", help="Validate reflection-report.md for a prepared run.")
    validate_parser.add_argument("--state", required=True, type=Path, help="Path to run-state.json.")
    validate_parser.set_defaults(func=validate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
