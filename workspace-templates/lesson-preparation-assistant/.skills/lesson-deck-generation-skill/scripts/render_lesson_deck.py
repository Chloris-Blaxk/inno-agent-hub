#!/usr/bin/env python3
"""教育版课件生成器。

生成：
  - edu-deck-v1 结构化 JSON
  - 教师逐字稿 Markdown
  - 单文件 HTML 横向课件
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ENV_PATH = PROJECT_ROOT / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


if load_dotenv:
    load_dotenv(ENV_PATH)
else:
    _load_env_file(ENV_PATH)

TEMPLATE_PATH = ROOT / "assets" / "lesson-deck-template.html"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_lesson_deck.py"
VALIDATE_HTML_SCRIPT = ROOT / "scripts" / "validate_lesson_deck_html.py"
KNOWLEDGE_PACKS_PATH = ROOT / "references" / "subject-knowledge-packs.json"

LLM_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
LLM_MODEL = os.getenv("GENERATOR_MODEL", "qwen3.5-122b-a10b")

VISUAL_SYSTEM = "edu-deck-v1"
LAYOUT_LOCK_VERSION = "edu-layout-lock-v1"


GRADE_MAP: dict[str, tuple[int, str]] = {
    "一年级": (1, "小学低段"), "1年级": (1, "小学低段"),
    "二年级": (2, "小学低段"), "2年级": (2, "小学低段"),
    "三年级": (3, "小学中段"), "3年级": (3, "小学中段"),
    "四年级": (4, "小学中段"), "4年级": (4, "小学中段"),
    "五年级": (5, "小学高段"), "5年级": (5, "小学高段"),
    "六年级": (6, "小学高段"), "6年级": (6, "小学高段"),
    "初一": (7, "初中"), "七年级": (7, "初中"), "7年级": (7, "初中"),
    "初二": (8, "初中"), "八年级": (8, "初中"), "8年级": (8, "初中"),
    "初三": (9, "初中"), "九年级": (9, "初中"), "9年级": (9, "初中"),
    "高一": (10, "高中"), "高二": (11, "高中"), "高三": (12, "高中"),
}


def unwrap_config_envelope(raw: dict[str, Any]) -> dict[str, Any]:
    """Unify envelope and flat config formats.

    If ``raw`` contains an ``input`` key, treat it as the standard envelope:
    merge ``input`` as the core config, and stash envelope metadata under
    ``_envelope`` for downstream use.

    If ``raw`` is flat (legacy), return it as-is for backward compatibility.
    """
    if "input" in raw and isinstance(raw.get("input"), dict):
        envelope = {
            "requestId": raw.get("requestId", ""),
            "sourceRequest": raw.get("sourceRequest", ""),
            "taskIntent": raw.get("taskIntent", ""),
            "options": raw.get("options", {}),
            "constraints": raw.get("constraints", []),
            "assumptions": raw.get("assumptions", []),
        }
        config: dict[str, Any] = {**raw["input"]}
        # Merge options into config (e.g. stylePreset)
        if isinstance(envelope["options"], dict):
            for key, value in envelope["options"].items():
                config.setdefault(key, value)
        # Merge constraints into config
        if envelope["constraints"]:
            config.setdefault("constraints", envelope["constraints"])
        # Store envelope metadata for downstream
        config["_envelope"] = envelope
        return config
    return raw


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

REQUIRED_FIELDS: dict[str, list[str]] = {
    "ED01": ["headline", "subtitle", "outcome"],
    "ED02": ["headline", "route"],
    "ED03": ["headline", "question", "visualBrief"],
    "ED04": ["headline", "prompt", "comparePoints"],
    "ED05": ["headline", "keyIdea", "bullets", "visualBrief"],
    "ED06": ["headline", "modelSteps"],
    "ED07": ["headline", "example", "steps"],
    "ED08": ["headline", "tasks"],
    "ED09": ["headline", "misconception", "correction", "checkQuestion"],
    "ED10": ["headline", "activity"],
    "ED11": ["headline", "summary"],
    "ED12": ["headline", "tickets"],
}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_grade(grade: str) -> tuple[int, str]:
    for key, parsed in GRADE_MAP.items():
        if key in grade:
            return parsed
    return 5, "小学高段"


def choose_style(config: dict[str, Any]) -> str:
    explicit = config.get("stylePreset")
    if explicit and explicit != "auto":
        return explicit
    subject = config.get("subject", "")
    grade_level, _ = parse_grade(config.get("grade", ""))
    if subject in {"物理", "化学", "生物", "科学", "信息科技"}:
        return "science-lab"
    if subject in {"语文", "历史", "道德与法治"}:
        return "humanities-ink"
    if subject == "数学" and grade_level >= 5:
        return "chalk-grid"
    return "daylight"


def subject_mark(subject: str) -> str:
    mapping = {
        "数学": "MATH",
        "科学": "SCI",
        "物理": "PHY",
        "化学": "CHEM",
        "生物": "BIO",
        "语文": "CN",
        "英语": "EN",
        "历史": "HIS",
        "地理": "GEO",
    }
    return mapping.get(subject, "LESSON")


def load_knowledge_packs() -> dict[str, Any]:
    if KNOWLEDGE_PACKS_PATH.exists():
        return json.loads(KNOWLEDGE_PACKS_PATH.read_text(encoding="utf-8"))
    return {}


def topic_pack(config: dict[str, Any]) -> dict[str, Any]:
    packs = load_knowledge_packs()
    subject = config.get("subject", "")
    topic = config.get("topic", "")
    generic = packs.get("_generic", {})
    subject_packs = packs.get(subject, {})
    if isinstance(subject_packs, dict) and topic in subject_packs:
        return subject_packs[topic]

    def fill(obj: Any) -> Any:
        if isinstance(obj, str):
            return obj.replace("{{topic}}", topic)
        if isinstance(obj, list):
            return [fill(item) for item in obj]
        if isinstance(obj, dict):
            return {key: fill(value) for key, value in obj.items()}
        return obj

    return fill(generic)


def compact_title(text: str, limit: int = 18) -> str:
    text = str(text or "").strip()
    return text if len(text) <= limit else text[: max(1, limit - 3)] + "..."


def visual_slot(layout_id: str, screen: dict[str, Any], topic: str) -> dict[str, Any]:
    slot_id, slot_type, ratio = LAYOUTS[layout_id]["slot"]
    description = (
        screen.get("visualBrief")
        or screen.get("question")
        or screen.get("example")
        or screen.get("headline")
        or topic
    )
    return {
        "id": slot_id,
        "type": slot_type,
        "ratio": ratio,
        "assetStatus": "placeholder",
        "description": description,
        "prompt": (
            f"{ratio} classroom teaching visual for {topic}; clean editable composition; "
            "no title, no footer, no logo, keep labels as editable text outside image"
        ),
    }


def script(
    say: str,
    ask: list[str] | None = None,
    expected: list[str] | None = None,
    transition: str = "",
) -> dict[str, Any]:
    return {
        "say": say,
        "ask": ask or [],
        "expectedResponses": expected or [],
        "transition": transition,
    }


def slide(
    page: int,
    stage: str,
    layout_id: str,
    title: str,
    intent: str,
    screen: dict[str, Any],
    teacher_script: dict[str, Any],
    minutes: float,
    feedback: str,
    notes: list[str] | None = None,
    topic: str = "",
) -> dict[str, Any]:
    screen.setdefault("eyebrow", stage.upper())
    return {
        "id": f"s{page:02d}",
        "page": page,
        "stage": stage,
        "layoutId": layout_id,
        "layoutName": LAYOUTS[layout_id]["name"],
        "title": title,
        "teachingIntent": intent,
        "screen": screen,
        "teacherScript": teacher_script,
        "visualSlots": [visual_slot(layout_id, screen, topic or title)],
        "feedbackEvidence": feedback,
        "timing": {"minutes": minutes},
        "notes": notes or [],
    }


def task_item(content: str, target: str, feedback: str, label: str) -> dict[str, str]:
    return {"label": label, "content": content, "target": target, "feedback": feedback}


def step_item(content: str, index: int) -> dict[str, str]:
    return {
        "label": str(index),
        "content": content,
        "teacherCue": "追问：这一步解决了什么问题？依据是什么？",
    }


def base_context(config: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    subject = config.get("subject", "学科")
    grade = config.get("grade", "年级")
    topic = config.get("topic", "本课主题")
    prior = as_list(config.get("studentProfile", {}).get("priorKnowledge"))
    difficulties = as_list(config.get("studentProfile", {}).get("commonDifficulties"))
    concept = as_list(pack.get("concept"))[:4] or [f"明确「{topic}」的核心概念", "形成可迁移的方法"]
    steps = as_list(pack.get("steps"))[:5] or ["读题并圈出关键信息", "选择合适的方法", "分步完成并检查"]
    tasks = as_list(pack.get("tasks"))[:3] or [f"基础练习：完成一道「{topic}」题"]
    exit_items = as_list(pack.get("exit"))[:2] or [f"完成一道「{topic}」小题", "写下今天最容易错的一点"]
    return {
        "subject": subject,
        "grade": grade,
        "topic": topic,
        "prior": prior,
        "difficulties": difficulties,
        "hook": pack.get("hook", f"生活中哪里会遇到「{topic}」这个问题？"),
        "visual": pack.get("visual", f"围绕「{topic}」制作一个课堂图示。"),
        "concept": concept,
        "example": pack.get("example", f"一道关于「{topic}」的典型例题"),
        "steps": steps,
        "tasks": tasks,
        "misconception": pack.get("misconception") or (difficulties[0] if difficulties else "只记住结论，没有说明原因。"),
        "correction": pack.get("correction", "回到概念、条件和方法，检查每一步是否有依据。"),
        "exit": exit_items,
    }


HUMANITIES_SUBJECTS = {"语文", "历史", "道德与法治", "地理", "政治"}


def build_new_concept(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    c = base_context(config, pack)
    topic = c["topic"]
    prior_text = c["prior"][0] if c["prior"] else "已有知识"
    is_hum = c["subject"] in HUMANITIES_SUBJECTS

    # Subject-aware text for each slide
    if is_hum:
        route = ["诵读感知", "整体把握", "深入分析", "迁移运用", "交流与检测"]
        s3_title = "问题导入"
        s3_headline = "带着问题来读"
        s3_script_say = f"还记得我们学过的{prior_text}吗？请先不要急着看注释，先自己读一遍，说说你从题目中能联想到什么。"
        s3_script_ask = [c["hook"], "你读这篇文章时最大的困难是什么？"]
        s3_script_expected = ["学生会有不同的阅读体验或提出疑问。"]
        s4_stage = "text_explore"
        s4_title = "比较与讨论"
        s4_headline = "文中哪里读得懂，哪里读不懂"
        s4_prompt = "同桌互说：哪些句子意思清楚？哪些地方需要借助注释仍有困难？"
        s4_points = ["已读懂：字面意思清晰的句子", "有困难：文言句式或深层含义"]
        s4_script_say = "请同桌用 1 分钟互相交流：哪些句子一读就懂？哪些地方需要反复推敲？"
        s4_script_ask = ["读不懂的地方在哪里？", "需要补充什么知识才能理解？"]
        s4_script_expected = ["学生能说出理解上的困难点。"]
        s4_script_transition = "当困难清晰起来，分析方法就有了方向。"
        s4_feedback = "收集 2-3 个同桌讨论结果，比较不同理解。"
        s5_stage = "analysis"
        s5_title = "要点梳理"
        s5_headline_override = "核心要义"
        s5_script_say = "我们把刚才的阅读发现整理成要点。注意，每一点都要回到原文找依据，而不是凭感觉概括。"
        s5_script_ask = ["这些要点中，哪一点最关键？"]
        s5_script_expected = ["学生能说出核心论点或主旨。"]
        s5_script_transition = "接下来用第一段来示范完整的分析方法。"
        s5_feedback = "学生能说出本页关键论点、层次或手法。"
        s5_note = "把核心分析板书保留到课末。"
        s6_stage = "example"
        s6_title = "典型分析"
        s6_layout = "ED07"
        s6_headline = "逐层分析"
        s6_script_say = "请一边看分析，一边想每一步揭示了什么。只会背注释不算会，能说明为什么这样理解才算会。"
        s6_script_ask = ["这一步的分析依据是什么？", "最后为什么要回到全文验证？"]
        s6_script_expected = ["学生能说明分析思路。"]
        s6_script_transition = "现在换一段文字，由你们来试。"
        s6_feedback = "学生能说明分析过程中每一步的作用。"
        s6_note = "PPTX 可按分析步骤做分步动画。"
        s7_stage = "practice"
        s7_title = "课堂练习"
        s7_headline = "先说思路再下笔"
        s7_script_say = "每道题先口头说你的理解思路，再开始写。做完后和同桌互查：思路是否清晰？依据是否充分？"
        s7_script_ask = ["你的分析思路是什么？", "你如何判断自己的翻译准确？"]
        s7_script_expected = ["学生能独立完成并解释分析思路。"]
        s7_script_transition = "练习中最常见的偏差，我们单独拿出来辨析。"
        s7_feedback = "教师巡视、同伴互查或抽取板演，判断是否能独立分析。"
        s7_task_target = "检验分析能力能否迁移"
        s7_note = "屏幕只放题目，反馈方式进备注。"
        s8_stage = "misconception_check"
        s8_title = "偏差辨析"
        s8_headline = "这个理解哪里不够"
        s8_script_say = "这个理解看起来似乎有道理，但它忽略了文章的深层含义。请先指出偏差所在，再用正确方法分析。"
        s8_script_ask = ["偏差是什么？", "应该如何理解？"]
        s8_script_expected = ["学生能说出偏差并修正。"]
        s8_script_transition = "能辨析偏差，说明理解正在深入。"
        s8_feedback = "学生能修正偏差并解释原因。"
        s8_check = "请指出这个理解的不当之处，并用原文说明正确理解。"
        s8_note = "把偏差当作理解层次的标志，不否定学生。"
        s9_stage = "summary"
        s9_title = "要点小结"
        s9_headline = "把理解带走"
        s9_script_say = "今天的内容请压缩成三句话。以后遇到同类文章，先看什么，再分析什么，最后怎样验证理解。"
        s9_script_ask = ["哪一个分析步骤最容易忽略？"]
        s9_script_expected = ["学生能指出关键步骤。"]
        s9_script_transition = "最后用一道短测确认掌握情况。"
        s9_feedback = "学生能用一句话复述本课核心要点。"
        s9_note = "小结用于板书回收。"
        exit_ticket_say = "请独立完成出门测。第一题看会不会答，第二题看能不能说清楚依据。"
        exit_ticket_expected = "学生能独立完成并说明关键依据。"
    else:
        route = ["唤醒旧知", "发现新问题", "建立方法", "练习迁移", "辨析与检测"]
        s3_title = "问题导入"
        s3_headline = "先判断再计算"
        s3_script_say = f"还记得我们学过的{prior_text}吗？请先不要急着算，先判断这个想法是否合理，并说出依据。"
        s3_script_ask = [c["hook"], "你判断的依据是什么？"]
        s3_script_expected = ["学生会套用旧方法、犹豫或提出新问题。"]
        s4_stage = "explore"
        s4_title = "观察与讨论"
        s4_headline = "旧方法够用吗"
        s4_prompt = "同桌互说：旧方法哪里能用？哪里开始不够用？"
        s4_points = ["旧知识：能解决什么", "新问题：卡在哪里"]
        s4_script_say = "请同桌用 1 分钟互相解释：旧方法能解决哪一部分？到了哪里开始不够用？"
        s4_script_ask = ["卡住的地方在哪里？", "需要补哪一步？"]
        s4_script_expected = ["学生能说出需要补一个关键步骤。"]
        s4_script_transition = "当问题暴露出来，方法就有了生长的位置。"
        s4_feedback = "收集 2-3 个同桌讨论结果，比较不同解释。"
        s5_stage = "concept_build"
        s5_title = "概念建构"
        s5_headline_override = None
        s5_script_say = "我们把刚才的观察整理成方法。注意，每一步都要回答一个问题，而不是机械照做。"
        s5_script_ask = ["这个方法中最关键的一步是什么？"]
        s5_script_expected = ["学生能说出核心条件或步骤。"]
        s5_script_transition = "接下来用一道例题完整走一遍。"
        s5_feedback = "学生能说出本页关键概念、步骤或条件。"
        s5_note = "把核心方法板书保留到课末。"
        s6_stage = "example"
        s6_title = "典型例题"
        s6_layout = "ED07"
        s6_headline = "完整走一遍"
        s6_script_say = "请一边看步骤，一边想每一步解决了什么问题。只会看答案不算会，能解释步骤才算会。"
        s6_script_ask = ["每一步的目的是什么？", "最后为什么要检查？"]
        s6_script_expected = ["学生能说明步骤作用。"]
        s6_script_transition = "现在换一组题，由你们来试。"
        s6_feedback = "学生能说明每一步解决了什么问题。"
        s6_note = "PPTX 可按步骤做分步动画。"
        s7_stage = "guided_practice"
        s7_title = "课堂练习"
        s7_headline = "先说方法再动笔"
        s7_script_say = "每道题先口头说第一步，再开始写。做完后和同桌互查：第一步是否合理？结果是否检查？"
        s7_script_ask = ["第一步是什么？", "你如何检查答案？"]
        s7_script_expected = ["学生能独立完成并解释方法。"]
        s7_script_transition = "练习中最常见的错误，我们单独拿出来辨析。"
        s7_feedback = "教师巡视、同伴互查或抽取板演，判断是否能独立迁移。"
        s7_task_target = "检验方法能否迁移"
        s7_note = "屏幕只放题目，反馈方式进备注。"
        s8_stage = "misconception_check"
        s8_title = "错误诊所"
        s8_headline = "这个做法哪里不对"
        s8_script_say = "这个错误看起来很像以前学过的方法，但它忽略了今天的新条件。请先指出错因，再用正确方法改正。"
        s8_script_ask = ["错因是什么？", "应该如何改？"]
        s8_script_expected = ["学生能说出错因并修正。"]
        s8_script_transition = "能辨析错误，说明方法边界正在变清楚。"
        s8_feedback = "学生能改正错误并解释错因。"
        s8_check = "请改正这个做法，并用一句话说明错因。"
        s8_note = "把错误当作方法边界，不羞辱学生。"
        s9_stage = "summary"
        s9_title = "方法小结"
        s9_headline = "把方法带走"
        s9_script_say = "今天的方法请压缩成三句话。以后遇到类似问题，先问条件，再选方法，最后检查。"
        s9_script_ask = ["哪一步最容易漏？"]
        s9_script_expected = ["学生能指出关键步骤。"]
        s9_script_transition = "最后用一道短测确认掌握情况。"
        s9_feedback = "学生能用一句话复述本课核心方法。"
        s9_note = "小结用于板书回收。"
        exit_ticket_say = "请独立完成出门测。第一题看会不会做，第二题看能不能说清楚为什么。"
        exit_ticket_expected = "学生能独立完成并说明关键理由。"

    # Slide 5 headline: use override for humanities, concept[0] for STEM
    s5_headline = s5_headline_override or compact_title(c["concept"][0])

    # Summary items
    if is_hum:
        summary_items = c["concept"][:3] + ["遇到同类文章先问：体裁和写作背景是否清楚"]
    else:
        summary_items = c["concept"][:3] + ["遇到新题先问：条件是否一样"]

    return [
        slide(1, "cover", "ED01", topic, "建立学习主题和课堂期待。",
              {"headline": topic, "subtitle": f"{c['grade']}{c['subject']} · 新授课",
               "outcome": "本节课结束时，学生能说清要点、完成练习并辨析常见偏差。"},
              script(f"同学们，今天我们一起研究「{topic}」。这节课不只记结论，更要弄清楚背后的道理。"),
              1, "教师观察学生是否进入学习状态。", ["封面只建立主题，不讲细节。"], topic),
        slide(2, "objective_map", "ED02", "学习路线", "让学生明确本课路径。",
              {"headline": "今天走五步", "route": route},
              script("今天我们按五步推进。每一步都要留下一个证据，证明你真的理解了。",
                     transition="先从你们已经会的内容开始。"),
              2, "学生能复述本课学习路径。", ["路线图用学生能懂的语言。"], topic),
        slide(3, "lead_in", "ED03", s3_title, "激活旧知并制造认知冲突。",
              {"headline": s3_headline, "question": c["hook"], "visualBrief": c["visual"]},
              script(s3_script_say, s3_script_ask, s3_script_expected, "这个分歧就是今天要解决的关键。"),
              4, "抽取 2-3 个学生判断或理由，记录认知冲突。", ["保留不同理解，为后续分析服务。"], topic),
        slide(4, s4_stage, "ED04", s4_title, "让学生通过比较形成解释需求。",
              {"headline": s4_headline, "prompt": s4_prompt, "comparePoints": s4_points},
              script(s4_script_say, s4_script_ask, s4_script_expected, s4_script_transition),
              5, s4_feedback, ["教师板书学生表达中的关键词。"], topic),
        slide(5, s5_stage, "ED05", s5_title, "把观察提升为可迁移方法。",
              {"headline": s5_headline, "keyIdea": c["concept"][0], "bullets": c["concept"], "visualBrief": c["visual"]},
              script(s5_script_say, s5_script_ask, s5_script_expected, s5_script_transition),
              6, s5_feedback, [s5_note], topic),
        slide(6, s6_stage, s6_layout, s6_title, "示范标准分析过程。",
              {"headline": s6_headline, "example": c["example"],
               "steps": [step_item(item, i + 1) for i, item in enumerate(c["steps"])]},
              script(s6_script_say, s6_script_ask, s6_script_expected, s6_script_transition),
              8, s6_feedback, [s6_note], topic),
        slide(7, s7_stage, "ED08", s7_title, "检查方法迁移。",
              {"headline": s7_headline, "tasks": [
                  task_item(str(item), s7_task_target, "教师巡视并抽取 1-2 个代表性做法讲评。", str(i + 1))
                  for i, item in enumerate(c["tasks"])
              ]},
              script(s7_script_say, s7_script_ask, s7_script_expected, s7_script_transition),
              6, s7_feedback, [s7_note], topic),
        slide(8, s8_stage, "ED09", s8_title, "定位并修正常见误解。",
              {"headline": s8_headline, "misconception": c["misconception"],
               "correction": c["correction"], "checkQuestion": s8_check},
              script(s8_script_say, s8_script_ask, s8_script_expected, s8_script_transition),
              4, s8_feedback, [s8_note], topic),
        slide(9, s9_stage, "ED11", s9_title, "形成可复述的板书结构。",
              {"headline": s9_headline, "summary": summary_items},
              script(s9_script_say, s9_script_ask, s9_script_expected, s9_script_transition),
              3, s9_feedback, [s9_note], topic),
        slide(10, "exit_ticket", "ED12", "出门测", "判断是否达成本课目标。",
              {"headline": "两分钟出门测", "tickets": [
                  task_item(str(item), "判断本课目标是否达成",
                            "教师课后快速分类：已掌握 / 需巩固 / 需补救。", str(i + 1))
                  for i, item in enumerate(c["exit"])
              ]},
              script(exit_ticket_say, expected=[exit_ticket_expected]),
              1, "根据完成情况判断下一课补救、巩固或进入新内容。", ["根据出门测决定是否补充练习。"], topic),
    ]


def build_review(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    c = base_context(config, pack)
    topic = c["topic"]
    slides = build_new_concept(config, pack)
    slides[0]["screen"]["subtitle"] = f"{c['grade']}{c['subject']} · 复习课"
    slides[1]["screen"]["route"] = ["快速诊断", "整理知识网络", "重建关键方法", "错因诊所", "综合检测"]
    slides[2]["stage"] = "diagnosis"
    slides[2]["layoutId"] = "ED08"
    slides[2]["layoutName"] = LAYOUTS["ED08"]["name"]
    slides[2]["screen"] = {"eyebrow": "DIAGNOSIS", "headline": "先试试看", "tasks": [
        task_item(str(item), "诊断掌握情况", "教师统计全班共性困难。", str(i + 1))
        for i, item in enumerate(c["tasks"][:2])
    ]}
    slides[2]["visualSlots"] = [visual_slot("ED08", slides[2]["screen"], topic)]
    slides[2]["feedbackEvidence"] = "教师记录 3-5 个典型错误，用于后续讲评。"
    return renumber(slides[:8])


def build_practice(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    c = base_context(config, pack)
    slides = build_new_concept(config, pack)
    slides[0]["screen"]["subtitle"] = f"{c['grade']}{c['subject']} · 练习讲评课"
    slides[1]["screen"]["route"] = ["看整体表现", "定位典型错误", "重建方法", "变式再练", "自查反思"]
    return renumber([slides[0], slides[1], slides[7], slides[4], slides[6], slides[8], slides[9]])


def build_inquiry(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    c = base_context(config, pack)
    slides = build_new_concept(config, pack)
    slides[0]["screen"]["subtitle"] = f"{c['grade']}{c['subject']} · 探究课"
    slides[1]["screen"]["route"] = ["提出问题", "形成猜想", "小组探究", "证据分享", "形成结论", "迁移应用"]
    activity = slide(4, "group_explore", "ED10", "小组探究", "组织学生收集证据。",
                     {"headline": "用证据说话", "activity": {
                         "studentAction": "小组设计验证方式，记录发现，比较猜想与证据。",
                         "materials": "按实际课堂条件准备材料或观察记录表。",
                         "feedback": "各组提交一条证据和一个仍有疑问的地方。"
                     }},
                     script("请每组用自己的方法验证猜想。记录看到什么、数据是什么、和猜想是否一致。",
                            ["证据支持你的猜想吗？"], ["学生能产出记录和初步结论。"], "各组都有证据后，我们比较哪些发现一致。"),
                     10, "收集小组记录和汇报，比较证据是否支持猜想。", ["教师巡回追问，不直接给结论。"], c["topic"])
    return renumber([slides[0], slides[2], slides[1], slides[3], activity, slides[4], slides[6], slides[8], slides[9]])


def build_experiment(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    c = base_context(config, pack)
    slides = build_inquiry(config, pack)
    slides[0]["screen"]["subtitle"] = f"{c['grade']}{c['subject']} · 实验/演示课"
    prediction_slide = next((item for item in slides if item.get("layoutId") == "ED03"), None)
    if prediction_slide:
        prediction_slide["screen"]["headline"] = "先预测现象"
        prediction_slide["screen"]["question"] = c["hook"]
    activity_slide = next((item for item in slides if item.get("layoutId") == "ED10"), None)
    if activity_slide:
        activity = activity_slide.setdefault("screen", {}).setdefault("activity", {})
        activity["studentAction"] = "按步骤操作，观察关键现象，记录数据，标注意料之外的发现。"
        activity["feedback"] = "实验单记录现象、数据和预测差异。"
    return renumber(slides)


def renumber(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, item in enumerate(slides, start=1):
        item["page"] = index
        item["id"] = f"s{index:02d}"
        item["visualSlots"] = [visual_slot(item["layoutId"], item["screen"], item["title"])]
    return slides


def build_slides(config: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    lesson_type = config.get("lessonType", "new_concept")
    builders = {
        "new_concept": build_new_concept,
        "review": build_review,
        "practice": build_practice,
        "inquiry": build_inquiry,
        "experiment": build_experiment,
    }
    return builders.get(lesson_type, build_new_concept)(config, pack)


def adjust_timing(slides: list[dict[str, Any]], duration: int) -> None:
    current = sum(float(item["timing"]["minutes"]) for item in slides)
    if current <= 0:
        return
    diff = float(duration) - current
    adjustable = [item for item in slides if item["stage"] not in {"cover", "exit_ticket"}]
    if not adjustable or abs(diff) < 0.5:
        return
    per = round(diff / len(adjustable), 1)
    for item in adjustable:
        item["timing"]["minutes"] = max(1.5, round(float(item["timing"]["minutes"]) + per, 1))
    final = sum(float(item["timing"]["minutes"]) for item in slides)
    if abs(final - float(duration)) > 0.2 and adjustable:
        adjustable[-1]["timing"]["minutes"] = max(
            1.5, round(float(adjustable[-1]["timing"]["minutes"]) + float(duration) - final, 1)
        )


# ---- LLM-based content generation ----

def _get_llm_client() -> Any:
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 DASHSCOPE_API_KEY 或 QWEN_API_KEY。")
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("缺少 openai Python 包。") from error
    return OpenAI(api_key=api_key, base_url=LLM_BASE_URL)


def _call_llm(prompt: str, system: str, model: str, thinking: bool, max_tokens: int, temperature: float) -> str:
    client = _get_llm_client()
    request_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if thinking:
        request_kwargs["extra_body"] = {"enable_thinking": True}
    response = client.chat.completions.create(**request_kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("模型返回内容为空。")
    return content


def _parse_llm_json(text: str) -> Any:
    """Extract JSON from LLM response, handling markdown fences."""
    content = text.strip()
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", content, flags=re.IGNORECASE):
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    # Try to find array with balanced brace matching
    for start, char in enumerate(content):
        if char == "[":
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(content)):
                c = content[i]
                if in_string:
                    if escape:
                        escape = False
                    elif c == "\\":
                        escape = True
                    elif c == '"':
                        in_string = False
                    continue
                if c == '"':
                    in_string = True
                elif c == "[":
                    depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(content[start:i + 1])
                        except json.JSONDecodeError:
                            break
    # Last resort: write to /tmp for debugging and raise
    debug_path = Path("/tmp/llm_deck_debug.txt")
    debug_path.write_text(text, encoding="utf-8")
    raise ValueError(f"无法解析 LLM 返回的 JSON。原始内容前 500 字符: {content[:500]}")


def _build_llm_system_prompt() -> str:
    return (
        "你是教育课件生成智能体，面向中国中小学教师。"
        "你必须基于用户请求生成可落地的课件 JSON 数组。"
        "只返回一个合法 JSON 数组（slides），不要输出解释文字。"
        "不得虚构超出课标边界的内容。"
    )


def _build_llm_user_prompt(config: dict[str, Any], pack: dict[str, Any], layouts: dict[str, Any]) -> str:
    subject = config.get("subject", "学科")
    grade = config.get("grade", "年级")
    topic = config.get("topic", "本课主题")
    lesson_type = config.get("lessonType", "new_concept")
    duration = config.get("durationMin", 40)
    prior = pack.get("priorKnowledge", config.get("studentProfile", {}).get("priorKnowledge", []))
    difficulties = pack.get("commonDifficulties", config.get("studentProfile", {}).get("commonDifficulties", []))
    hook = pack.get("hook", f"生活中哪里会遇到「{topic}」这个问题？")
    concept = pack.get("concept", [f"明确「{topic}」的核心概念"])
    example = pack.get("example", f"一道关于「{topic}」的典型例题")
    tasks = pack.get("tasks", [f"基础练习：完成一道「{topic}」题"])
    misconception = pack.get("misconception", difficulties[0] if difficulties else "只记住结论，没有说明原因。")
    correction = pack.get("correction", "回到概念和方法，检查每一步是否有依据。")
    exit_items = pack.get("exit", [f"完成一道「{topic}」小题"])

    layout_ids = list(layouts.keys())

    return f"""
请生成一份课件的 slides 数组（JSON 数组），用于中国中小学课堂。

## 课堂信息
- 学科：{subject}
- 年级：{grade}
- 课题：{topic}
- 课型：{lesson_type}
- 时长：{duration} 分钟
- 学生已有知识：{json.dumps(prior, ensure_ascii=False)}
- 常见困难：{json.dumps(difficulties, ensure_ascii=False)}

## 内容素材
- 导入 hook：{hook}
- 核心概念：{json.dumps(concept, ensure_ascii=False)}
- 例题：{example}
- 练习任务：{json.dumps(tasks, ensure_ascii=False)}
- 常见误解：{misconception}
- 纠正方法：{correction}
- 出门测：{json.dumps(exit_items, ensure_ascii=False)}

## 输出结构要求

必须返回一个 JSON 数组，每个元素代表一页幻灯片，结构如下：
```json
[
  {{
    "stage": "cover|objective_map|lead_in|explore|concept_build|example|guided_practice|misconception_check|summary|exit_ticket",
    "layoutId": "ED01-ED12 之一",
    "title": "页面标题",
    "teachingIntent": "本页的教学目标和课堂动作，不能为空",
    "screen": {{
      "headline": "大标题",
      "subtitle": "副标题（可选）",
      "keyIdea": "核心观点（concept_build 页必填）",
      "bullets": ["要点1", "要点2"],
      "question": "导入问题",
      "visualBrief": "图示描述",
      "tasks": [{{"label": "1", "content": "任务内容", "target": "检测目标", "feedback": "反馈方式"}}],
      "misconception": "错误示例",
      "correction": "纠正方法",
      "checkQuestion": "检测题",
      "summary": ["要点1", "要点2"],
      "tickets": [{{"label": "1", "content": "题目", "target": "检测目标"}}],
      "steps": [{{"label": "1", "content": "步骤说明"}}],
      "route": ["步骤1", "步骤2"]
    }},
    "teacherScript": {{
      "say": "教师说的话",
      "ask": ["追问问题1"],
      "expectedResponses": ["学生可能的回答"],
      "transition": "过渡到下一页的话"
    }},
    "feedbackEvidence": "本节课可收集的反馈证据",
    "timing": {{"minutes": 5}},
    "notes": ["备注"]
  }}
]
```

可用 layoutId: {json.dumps(layout_ids)}
- ED01: 封面
- ED02: 学习路线
- ED03: 导入场景
- ED04: 探究讨论
- ED05: 概念建构
- ED06: 黑板模型
- ED07: 例题流程
- ED08: 练习
- ED09: 错误诊所
- ED10: 活动工作室
- ED11: 要点小结
- ED12: 出门测

## 硬性规则
1. 必须包含 8-12 页（40 分钟课）。
2. 每页必须有 stage, layoutId, title, teachingIntent, screen.headline, teacherScript.say, feedbackEvidence, timing.minutes。
3. stage 顺序建议：cover → objective_map → lead_in → explore → concept_build → example → guided_practice → misconception_check → summary → exit_ticket。
4. 教师逐字稿（teacherScript）不得出现在学生屏幕上。
5. 练习/互动/出门测必须有可收集的反馈证据。
6. teachingIntent 必须说明本页的教学目标和课堂动作，不能为空。

只返回 JSON 数组，不要其他内容。
""".strip()


def _align_slides_to_design_plan(
    slides: list[dict[str, Any]], confirmed_plan: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Force-align LLM-returned slides to the confirmed design plan.

    Rules:
    - stage and layoutId are overwritten by the confirmed plan.
    - page count is trimmed/padded to match the plan (excess slides dropped,
      missing slots kept with a warning note).
    - id and page are renumbered.
    """
    plan_len = len(confirmed_plan)
    slide_len = len(slides)
    result: list[dict[str, Any]] = []

    for plan_idx, plan_item in enumerate(confirmed_plan, start=1):
        if plan_idx <= slide_len:
            slide = slides[plan_idx - 1]
        else:
            # Plan has more pages than LLM returned: create a placeholder slide
            reason = plan_item.get("reason", f"第{plan_idx}页")
            slide = {
                "title": reason,
                "teachingIntent": reason,
                "screen": {"headline": reason},
                "teacherScript": {"say": ""},
                "feedbackEvidence": plan_item.get("feedbackEvidence", ""),
                "timing": {"minutes": 5},
                "notes": ["本页由 confirmed design plan 补充，LLM 未生成对应内容。"],
            }

        # Force overwrite stage / layoutId
        slide["stage"] = plan_item.get("stage", slide.get("stage", "lesson"))
        slide["layoutId"] = plan_item.get("layoutId", slide.get("layoutId", "ED05"))
        slide["layoutName"] = LAYOUTS.get(slide["layoutId"], {}).get("name", "")
        slide["page"] = plan_idx
        slide["id"] = f"s{plan_idx:02d}"

        # Ensure visualSlots matches the new layoutId
        screen = cast(dict[str, Any], slide.setdefault("screen", {}))
        layout_id = cast(str, slide.get("layoutId", "ED05"))
        title = cast(str, slide.get("title", ""))
        slide["visualSlots"] = [visual_slot(layout_id, screen, title)]

        result.append(slide)

    if slide_len > plan_len:
        # Excess LLM pages are dropped
        pass  # silently ignore; could log a warning if logging is added later

    return result


def _normalize_slide_fields(slides: list[dict[str, Any]]) -> None:
    """Post-normalize LLM-generated slides to satisfy per-layout required fields.

    The LLM may return content under field names that differ from what the
    validator expects.  This function maps common LLM output patterns to the
    canonical schema so that validation passes without re-prompting.
    """
    for slide in slides:
        lid = slide.get("layoutId", "")
        screen = slide.get("screen", {})
        title = slide.get("title", "")
        intent = slide.get("teachingIntent", "")
        ts = slide.get("teacherScript", {})

        # Ensure headline always has a value
        if not screen.get("headline") and title:
            screen["headline"] = title

        # ED01 Cover: needs headline, subtitle, outcome
        if lid == "ED01":
            if not screen.get("subtitle") and title:
                screen["subtitle"] = title
            if not screen.get("outcome"):
                screen["outcome"] = intent or screen.get("subtitle", "")

        # ED02 Lesson Journey: needs headline, route
        elif lid == "ED02":
            if not screen.get("route") and screen.get("bullets"):
                screen["route"] = screen["bullets"]
            if not screen.get("route") and intent:
                screen["route"] = [intent]

        # ED03 Hook Scene: needs headline, question, visualBrief
        elif lid == "ED03":
            if not screen.get("visualBrief") and screen.get("description"):
                screen["visualBrief"] = screen["description"]
            if not screen.get("visualBrief") and screen.get("question"):
                screen["visualBrief"] = screen["question"]
            if not screen.get("visualBrief"):
                screen["visualBrief"] = f"（请插入与{title}相关的情境图）"

        # ED04 Inquiry Split: needs headline, prompt, comparePoints
        elif lid == "ED04":
            if not screen.get("prompt") and screen.get("question"):
                screen["prompt"] = screen["question"]
            if not screen.get("prompt") and ts.get("say"):
                screen["prompt"] = ts["say"]
            if not screen.get("comparePoints") and screen.get("bullets"):
                screen["comparePoints"] = screen["bullets"]
            if not screen.get("comparePoints"):
                screen["comparePoints"] = [f"对比{title}中的关键特征"]

        # ED05 Concept Canvas: needs headline, keyIdea, bullets, visualBrief
        elif lid == "ED05":
            if not screen.get("keyIdea") and screen.get("prompt"):
                screen["keyIdea"] = screen["prompt"]
            if not screen.get("keyIdea") and intent:
                screen["keyIdea"] = intent
            if not screen.get("keyIdea") and screen.get("bullets"):
                screen["keyIdea"] = screen["bullets"][0]
            if not screen.get("bullets"):
                screen["bullets"] = [screen.get("keyIdea", intent)]
            if not screen.get("visualBrief"):
                screen["visualBrief"] = f"（请插入与{title}相关的知识图示）"
            # Clean up ED04 remnants when a slide was re-aligned from ED04 → ED05
            screen.pop("comparePoints", None)
            screen.pop("prompt", None)

        # ED06 Board Model: needs headline, modelSteps
        elif lid == "ED06":
            if not screen.get("modelSteps") and screen.get("bullets"):
                screen["modelSteps"] = screen["bullets"]
            if not screen.get("modelSteps") and screen.get("steps"):
                screen["modelSteps"] = [
                    s.get("content", s) if isinstance(s, dict) else s
                    for s in screen["steps"]
                ]
            if not screen.get("modelSteps"):
                screen["modelSteps"] = [intent]
            # Clean up ED05 / ED07 remnants after re-alignment
            screen.pop("keyIdea", None)
            screen.pop("bullets", None)
            screen.pop("steps", None)
            screen.pop("example", None)

        # ED07 Example Flow: needs headline, example, steps (with content+teacherCue)
        elif lid == "ED07":
            if not screen.get("example") and title:
                screen["example"] = title
            steps = screen.get("steps", [])
            if isinstance(steps, list):
                normalized = []
                for s in steps:
                    if isinstance(s, str):
                        normalized.append({"content": s, "teacherCue": intent or f"讲解步骤"})
                    elif isinstance(s, dict):
                        s.setdefault("content", "")
                        s.setdefault("teacherCue", ts.get("say", f"讲解{title}的关键步骤"))
                        normalized.append(s)
                if normalized:
                    screen["steps"] = normalized

        # ED08 Practice Lab: needs headline, tasks (with content+target+feedback)
        elif lid == "ED08":
            tasks = screen.get("tasks", [])
            if isinstance(tasks, list):
                normalized = []
                for t in tasks:
                    if isinstance(t, str):
                        normalized.append({
                            "content": t,
                            "target": f"检验对{title}的理解",
                            "feedback": "口头回答后教师点评",
                        })
                    elif isinstance(t, dict):
                        t.setdefault("content", "")
                        t.setdefault("target", f"检验对{title}的理解")
                        t.setdefault("feedback", "口头回答后教师点评")
                        normalized.append(t)
                if normalized:
                    screen["tasks"] = normalized
            # Clean up ED10 remnants (activity) when aligned from ED10 → ED08
            screen.pop("activity", None)

        # ED09 Error Clinic: needs headline, misconception, correction, checkQuestion
        elif lid == "ED09":
            if not screen.get("misconception") and screen.get("wrongAnswer"):
                screen["misconception"] = screen["wrongAnswer"]
            if not screen.get("correction") and screen.get("rightAnswer"):
                screen["correction"] = screen["rightAnswer"]
            if not screen.get("checkQuestion") and screen.get("question"):
                screen["checkQuestion"] = screen["question"]
            if not screen.get("checkQuestion"):
                screen["checkQuestion"] = f"关于{title}，你的判断是什么？"

        # ED10 Activity Studio: needs headline, activity (with studentAction+feedback)
        elif lid == "ED10":
            activity = screen.get("activity")
            # If LLM produced ED08-style content (tasks) that was re-aligned to
            # ED10, convert the first task into an activity description.
            if not isinstance(activity, dict) and screen.get("tasks"):
                tasks = screen["tasks"]
                if isinstance(tasks, list) and tasks:
                    first = tasks[0]
                    desc = first.get("content", str(first)) if isinstance(first, dict) else str(first)
                    activity = {"studentAction": desc, "feedback": "小组展示后教师点评"}
            if isinstance(activity, dict):
                activity.setdefault("studentAction", f"完成{title}相关任务")
                activity.setdefault("feedback", "小组展示后教师点评")
                screen["activity"] = activity
            elif isinstance(activity, str):
                screen["activity"] = {
                    "studentAction": activity,
                    "feedback": "小组展示后教师点评",
                }
            else:
                screen["activity"] = {
                    "studentAction": f"完成{title}相关任务",
                    "feedback": "小组展示后教师点评",
                }
            # Clean up ED08 remnants when a slide was re-aligned from ED08 → ED10
            screen.pop("tasks", None)

        # ED11 Summary Board: needs headline, summary
        elif lid == "ED11":
            if not screen.get("summary") and screen.get("bullets"):
                screen["summary"] = screen["bullets"]
            if not screen.get("summary") and screen.get("tickets"):
                # Convert ED12-style tickets → summary points
                screen["summary"] = [
                    t.get("content", str(t)) if isinstance(t, dict) else str(t)
                    for t in screen["tickets"]
                ]
            if not screen.get("summary"):
                screen["summary"] = [intent]
            # Clean up mis-aligned remnants
            screen.pop("tickets", None)
            screen.pop("bullets", None)

        # ED12 Exit Ticket: needs headline, tickets (with content+target+feedback)
        elif lid == "ED12":
            tickets = screen.get("tickets", [])
            # If LLM produced ED11-style content (summary/bullets) aligned to
            # ED12, convert each summary point into a ticket.
            if (not isinstance(tickets, list) or not tickets) and screen.get("summary"):
                tickets = [
                    {"content": item, "target": f"检验{title}的掌握程度",
                     "feedback": "独立完成，教师巡堂观察"}
                    for item in screen["summary"]
                ]
            if (not isinstance(tickets, list) or not tickets) and screen.get("bullets"):
                tickets = [
                    {"content": item, "target": f"检验{title}的掌握程度",
                     "feedback": "独立完成，教师巡堂观察"}
                    for item in screen["bullets"]
                ]
            if isinstance(tickets, list):
                normalized = []
                for t in tickets:
                    if isinstance(t, str):
                        normalized.append({
                            "content": t,
                            "target": f"检验{title}的掌握程度",
                            "feedback": "独立完成，教师巡堂观察",
                        })
                    elif isinstance(t, dict):
                        t.setdefault("content", "")
                        t.setdefault("target", f"检验{title}的掌握程度")
                        t.setdefault("feedback", "独立完成，教师巡堂观察")
                        normalized.append(t)
                if normalized:
                    screen["tickets"] = normalized
            # Clean up ED11 remnants
            screen.pop("summary", None)
            screen.pop("bullets", None)


def build_deck_llm(
    config: dict[str, Any],
    pack: dict[str, Any],
    *,
    model: str = LLM_MODEL,
    thinking: bool = False,
    max_tokens: int = 8000,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Generate deck content via LLM, then wrap with deck meta and outputs."""
    system = _build_llm_system_prompt()
    prompt = _build_llm_user_prompt(config, pack, LAYOUTS)

    raw = _call_llm(prompt, system, model, thinking, max_tokens, temperature)
    slides_data = _parse_llm_json(raw)

    if not isinstance(slides_data, list):
        raise ValueError("LLM 返回的 JSON 顶层不是数组。")

    # Normalize slides to match expected schema
    slides = []
    for idx, item in enumerate(slides_data, 1):
        item.setdefault("id", f"s{idx:02d}")
        item.setdefault("page", idx)
        item.setdefault("layoutId", "ED05")
        item.setdefault("layoutName", LAYOUTS.get(item["layoutId"], {}).get("name", ""))
        screen = item.setdefault("screen", {})
        item.setdefault("teachingIntent", screen.get("headline", item.get("title", "")))
        screen.setdefault("eyebrow", item.get("stage", "LESSON").upper())
        item.setdefault("teacherScript", {})
        item["teacherScript"].setdefault("say", "")
        item["teacherScript"].setdefault("ask", [])
        item["teacherScript"].setdefault("expectedResponses", [])
        item["teacherScript"].setdefault("transition", "")
        item.setdefault("feedbackEvidence", "")
        item.setdefault("timing", {"minutes": 5})
        item.setdefault("notes", [])
        item["visualSlots"] = [visual_slot(item["layoutId"], item["screen"], item.get("title", ""))]
        slides.append(item)

    # Post-normalize: fill layout-required fields from LLM output
    _normalize_slide_fields(slides)

    # Apply confirmed design plan alignment if available
    confirmed_plan = config.get("_confirmed_designPlan")
    if confirmed_plan:
        slides = _align_slides_to_design_plan(slides, confirmed_plan)
        # Re-normalize after alignment: layoutIds may have changed (e.g.
        # ED04→ED05, ED08→ED10), so screen fields must be re-mapped to
        # satisfy the new layout's required fields.
        _normalize_slide_fields(slides)

    # Re-render
    return build_deck({**config, "_llm_slides": slides})


def build_deck(config: dict[str, Any]) -> dict[str, Any]:
    pack = topic_pack(config)

    # Use LLM-generated slides if available, otherwise use deterministic templates
    if "_llm_slides" in config:
        slides = renumber(config["_llm_slides"])
    else:
        slides = build_slides(config, pack)
    duration = int(config.get("durationMin", 40))
    adjust_timing(slides, duration)
    topic = config.get("topic", "本课主题")
    style = choose_style(config)
    assumptions: list[str] = []
    if not config.get("textbookVersion"):
        assumptions.append("未提供教材版本，按课题常见教学位置处理。")
    if not config.get("unit"):
        assumptions.append("未提供教材单元，需教师确认课时边界。")
    if not config.get("period"):
        assumptions.append("未提供课时序号，默认按第一课时设计。")
    if not config.get("curriculumStandard"):
        assumptions.append("未接入真实课标库，教学目标和知识边界需教师最终确认。")

    design_plan = [
        {
            "page": item["page"],
            "slideId": item["id"],
            "stage": item["stage"],
            "layoutId": item["layoutId"],
            "reason": item["teachingIntent"],
            "visualSlots": [slot["id"] for slot in item["visualSlots"]],
            "feedbackEvidence": item["feedbackEvidence"],
        }
        for item in slides
    ]
    lesson_outline = [
        {
            "stage": item["stage"],
            "title": item["title"],
            "layoutId": item["layoutId"],
            "minutes": item["timing"]["minutes"],
            "goal": item["teachingIntent"],
        }
        for item in slides
    ]
    teacher_script = [
        {
            "slideId": item["id"],
            "title": item["title"],
            "say": item["teacherScript"]["say"],
            "ask": item["teacherScript"].get("ask", []),
            "expectedResponses": item["teacherScript"].get("expectedResponses", []),
            "transition": item["teacherScript"].get("transition", ""),
            "feedbackEvidence": item["feedbackEvidence"],
        }
        for item in slides
    ]
    deck = {
        "deckMeta": {
            "title": topic,
            "visualSystem": VISUAL_SYSTEM,
            "layoutLockVersion": LAYOUT_LOCK_VERSION,
            "subject": config.get("subject", "学科"),
            "grade": config.get("grade", "年级"),
            "lessonType": config.get("lessonType", "new_concept"),
            "durationMin": duration,
            "slideCount": len(slides),
            "stylePreset": style,
            "subjectMark": subject_mark(config.get("subject", "")),
        },
        "curriculumContext": {
            "textbookVersion": config.get("textbookVersion", "待确认"),
            "unit": config.get("unit", "待确认"),
            "period": config.get("period", "待确认"),
            "assumptions": assumptions,
        },
        "designPlan": design_plan,
        "lessonOutline": lesson_outline,
        "slides": slides,
        "teacherScript": teacher_script,
        "exportPlan": {
            "htmlPreview": True,
            "pptxReady": True,
            "pageSize": "16:9",
            "editableObjects": ["text", "shape", "visual-slot", "speaker-notes"],
            "visualSlotRules": "references/lesson-layout-lock.md",
        },
        "qualityReport": {
            "status": "draft",
            "warnings": [],
            "assumptions": assumptions,
        },
    }
    return inject_quality_report(deck)


def inject_quality_report(deck: dict[str, Any]) -> dict[str, Any]:
    if not VALIDATE_SCRIPT.exists():
        deck["qualityReport"] = {
            "status": "draft",
            "warnings": ["未找到校验脚本。"],
            "assumptions": deck.get("curriculumContext", {}).get("assumptions", []),
        }
        return deck
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as temp:
        json.dump(deck, temp, ensure_ascii=False, indent=2)
        temp_path = temp.name
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATE_SCRIPT), temp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        warnings = [line[2:].strip() for line in result.stdout.splitlines() if line.startswith("- ")]
        errors = [line[2:].strip() for line in result.stderr.splitlines() if line.startswith("- ")]
        deck["qualityReport"] = {
            "status": "fail" if result.returncode else ("warning" if warnings else "pass"),
            "warnings": warnings + errors,
            "assumptions": deck.get("curriculumContext", {}).get("assumptions", []),
            "checkedRules": ["edu_layout_lock", "visual_slots", "feedback_evidence", "timing", "teacher_script", "projection_density", "html_runtime"],
        }
    finally:
        Path(temp_path).unlink(missing_ok=True)
    return deck


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_items(items: list[Any], cls: str = "bullet-list") -> str:
    return f'<ul class="{cls}">' + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def render_route(route: list[str]) -> str:
    parts = []
    for index, item in enumerate(route, start=1):
        parts.append(f'<div class="route-item"><div class="route-index">{index}</div><div class="route-text">{e(item)}</div></div>')
    return '<div class="route">' + "".join(parts) + "</div>"


def render_steps(steps: list[dict[str, Any]]) -> str:
    parts = []
    for index, item in enumerate(steps, start=1):
        label = e(item.get("label", str(index)))
        content = e(item.get("content", ""))
        cue = e(item.get("teacherCue", ""))
        parts.append(f'<div class="step"><div class="num">{label}</div><div><div class="step-title">{content}</div><div class="cue">{cue}</div></div></div>')
    return '<div class="step-list">' + "".join(parts) + "</div>"


def render_task_cards(tasks: list[dict[str, Any]]) -> str:
    parts = []
    for index, item in enumerate(tasks, start=1):
        label = e(item.get("label", str(index)))
        content = e(item.get("content", ""))
        parts.append(f'<div class="task-card"><div class="num">{label}</div><div class="task-title">{content}</div></div>')
    return "".join(parts)


def render_tasks(tasks: list[dict[str, Any]], cls: str = "task-grid") -> str:
    return f'<div class="{cls}">' + render_task_cards(tasks) + "</div>"


def first_visual_slot(slide_data: dict[str, Any]) -> dict[str, Any]:
    slots = slide_data.get("visualSlots")
    if isinstance(slots, list) and slots and isinstance(slots[0], dict):
        return slots[0]
    return {}


def slot_attrs(slide_data: dict[str, Any]) -> str:
    slot = first_visual_slot(slide_data)
    attrs = {
        "data-slot": slot.get("id", ""),
        "data-slot-type": slot.get("type", ""),
        "data-slot-ratio": slot.get("ratio", ""),
        "data-asset-status": slot.get("assetStatus", ""),
    }
    return " ".join(f'{name}="{e(value)}"' for name, value in attrs.items())


def render_main(slide_data: dict[str, Any], meta: dict[str, Any]) -> str:
    screen = slide_data.get("screen", {})
    layout_id = slide_data.get("layoutId")
    headline = e(screen.get("headline", slide_data.get("title", "")))
    slot = slot_attrs(slide_data)
    if layout_id == "ED01":
        return (
            '<div class="main" data-animate="rise">'
            f'<div><h1 class="headline large">{headline}</h1>'
            f'<p class="subtitle">{e(screen.get("subtitle", ""))}</p>'
            f'<div class="outcome">{e(screen.get("outcome", ""))}</div></div>'
            f'<div class="visual-mark visual-slot" {slot} data-mark="{e(meta.get("subjectMark", "LESSON"))}"></div>'
            '</div>'
        )
    if layout_id == "ED02":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">先知道要去哪里，课堂才不会迷路。</p></div><div class="panel journey-panel visual-slot" {slot}>{render_route(screen.get("route", []))}</div></div>'
    if layout_id == "ED03":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="question">{e(screen.get("question", ""))}</p></div><div class="visual-card hook-card visual-slot" {slot}><p class="brief">{e(screen.get("visualBrief", ""))}</p></div></div>'
    if layout_id == "ED04":
        points = screen.get("comparePoints", [])
        cards = "".join(f'<div class="compare-card"><div class="task-title">{e(item)}</div></div>' for item in points)
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">{e(screen.get("prompt", ""))}</p></div><div class="compare-grid visual-slot" {slot}>{cards}</div></div>'
    if layout_id == "ED05":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="key-idea">{e(screen.get("keyIdea", ""))}</p>{render_items(screen.get("bullets", []))}</div><div class="visual-card concept-canvas visual-slot" {slot}><p class="brief">{e(screen.get("visualBrief", ""))}</p></div></div>'
    if layout_id == "ED06":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">把方法留在黑板上，后面的练习都回到这里。</p></div><div class="panel board-panel visual-slot" {slot}>{render_items(screen.get("modelSteps", []))}</div></div>'
    if layout_id == "ED07":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">{e(screen.get("example", ""))}</p></div><div class="panel step-panel visual-slot" {slot}>{render_steps(screen.get("steps", []))}</div></div>'
    if layout_id == "ED08":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">先说方法，再开始动笔。</p></div><div class="task-grid visual-slot" {slot}>{render_task_cards(screen.get("tasks", []))}</div></div>'
    if layout_id == "ED09":
        return (
            f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">错误不是终点，是看清方法边界的入口。</p></div>'
            f'<div class="error-stack visual-slot" {slot}>'
            f'<div class="error-box">{e(screen.get("misconception", ""))}</div>'
            f'<div class="fix-box">{e(screen.get("correction", ""))}</div>'
            f'<div class="check-box">{e(screen.get("checkQuestion", ""))}</div>'
            '</div></div>'
        )
    if layout_id == "ED10":
        activity = screen.get("activity", {})
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">让学生留下可观察的课堂证据。</p></div><div class="activity-card visual-slot" {slot}><div class="task-title">{e(activity.get("studentAction", ""))}</div><p class="brief">{e(activity.get("materials", ""))}</p></div></div>'
    if layout_id == "ED11":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">把今天的方法压缩成可带走的句子。</p></div><div class="panel summary-panel visual-slot" {slot}>{render_items(screen.get("summary", []), "summary-list")}</div></div>'
    if layout_id == "ED12":
        return f'<div class="main" data-animate="rise"><div><h2 class="headline">{headline}</h2><p class="subtitle">用短测决定下一步教学。</p></div><div class="ticket-grid visual-slot" {slot}>{render_task_cards(screen.get("tickets", []))}</div></div>'
    return f'<div class="main" data-animate="rise"><h2 class="headline">{headline}</h2></div>'


STAGE_LABEL_MAP: dict[str, str] = {
    "cover": "封面",
    "objective_map": "学习路线",
    "lead_in": "导入",
    "text_explore": "文本探究",
    "analysis": "要点梳理",
    "example": "典型分析",
    "practice": "课堂练习",
    "misconception_check": "偏差辨析",
    "summary": "要点小结",
    "exit_ticket": "出门测",
}


def stage_label(stage: str, eyebrow: str) -> str:
    """Return a human-readable stage label for the kicker.

    If ``eyebrow`` is a raw stage name, map it to Chinese.
    Otherwise return ``eyebrow`` as-is.
    """
    if not eyebrow:
        return STAGE_LABEL_MAP.get(stage, stage)
    # eyebrow may be the upper-cased stage name (e.g. "LEAD_IN")
    normalized = eyebrow.lower().replace(" ", "_")
    if normalized == stage.lower():
        return STAGE_LABEL_MAP.get(stage, stage)
    return eyebrow


def render_slide_html(slide_data: dict[str, Any], meta: dict[str, Any], total: int) -> str:
    screen = slide_data.get("screen", {})
    layout_id = slide_data.get("layoutId", "")
    family = LAYOUTS.get(layout_id, {}).get("family", "default")
    slot = slot_attrs(slide_data)
    stage = slide_data.get('stage', '')
    eyebrow_raw = screen.get('eyebrow', '')
    eyebrow = stage_label(stage, eyebrow_raw)
    kicker_html = f'<div class="kicker">{e(eyebrow)}</div>' if eyebrow else ''
    return f"""
    <section class="slide layout-{e(layout_id).lower()} layout-{family}" data-layout="{e(layout_id)}" data-stage="{e(slide_data.get('stage'))}" {slot}>
      <div class="slide-inner">
        <aside class="rail">
          <div class="page-no">{slide_data.get('page', 0):02d}</div>
          <div class="rail-time">{e(slide_data.get('timing', {}).get('minutes'))} min</div>
        </aside>
        <div class="content">
          <div class="topbar" data-animate="fade">
            {kicker_html}
          </div>
          {render_main(slide_data, meta)}
          <div class="footer" data-animate="fade"><span>{slide_data.get('page')} / {total}</span></div>
        </div>
      </div>
    </section>
    """


def render_html(deck: dict[str, Any]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    slides = deck.get("slides", [])
    meta = deck.get("deckMeta", {})
    slide_html = "\n".join(render_slide_html(item, meta, len(slides)) for item in slides)
    deck_json = json.dumps(deck, ensure_ascii=False).replace("</script>", "<\\/script>")
    return (
        template
        .replace("{{TITLE}}", e(meta.get("title", "课堂课件")))
        .replace("{{THEME}}", e(meta.get("stylePreset", "daylight")))
        .replace("{{SLIDES}}", slide_html)
        .replace("{{DECK_JSON}}", deck_json)
    )


def render_design_markdown(deck: dict[str, Any]) -> str:
    """Render the design-stage document: outline + design plan only."""
    meta = deck.get("deckMeta", {})
    ctx = deck.get("curriculumContext", {})
    lines = [
        f"# {meta.get('title', '课堂课件')} 教学设计稿",
        "",
        f"- 学科：{meta.get('subject')}",
        f"- 年级：{meta.get('grade')}",
        f"- 课型：{meta.get('lessonType')}",
        f"- 时长：{meta.get('durationMin')} 分钟",
        f"- 预计页数：{meta.get('slideCount')}",
        f"- 风格预设：{meta.get('stylePreset')}",
        "",
        "## 教学背景与假设",
        "",
    ]
    for assumption in ctx.get("assumptions", []):
        lines.append(f"- {assumption}")
    lines.extend([
        "",
        f"- 教材版本：{ctx.get('textbookVersion', '待确认')}",
        f"- 单元：{ctx.get('unit', '待确认')}",
        f"- 课时：{ctx.get('period', '待确认')}",
        "",
        "## 课堂大纲",
        "",
    ])
    for idx, item in enumerate(deck.get("lessonOutline", []), 1):
        lines.extend([
            f"### 第{idx}页 · {item.get('stage', '')} · {item.get('title', '')}",
            "",
            f"- 版式：{item.get('layoutId', '')}",
            f"- 时长：{item.get('minutes', '')} 分钟",
            f"- 教学目标：{item.get('goal', '')}",
            "",
        ])
    lines.extend([
        "",
        "## 页面设计规划",
        "",
    ])
    for item in deck.get("designPlan", []):
        lines.extend([
            f"### 第{item.get('page', 0)}页 · {item.get('slideId', '')}",
            "",
            f"- 教学阶段：{item.get('stage', '')}",
            f"- 版式锁定：{item.get('layoutId', '')}",
            f"- 设计意图：{item.get('reason', '')}",
            f"- 视觉槽位：{', '.join(item.get('visualSlots', []))}",
            f"- 反馈证据：{item.get('feedbackEvidence', '')}",
            "",
        ])
    q = deck.get("qualityReport", {})
    lines.extend([
        "",
        "## 质量自检",
        "",
        f"- 状态：{q.get('status', 'draft')}",
    ])
    for warning in q.get("warnings", []):
        lines.append(f"- ⚠️ {warning}")
    for rule in q.get("checkedRules", []):
        lines.append(f"- ✅ 已检查：{rule}")
    return "\n".join(lines)


def render_markdown(deck: dict[str, Any]) -> str:
    meta = deck.get("deckMeta", {})
    lines = [
        f"# {meta.get('title', '课堂课件')} 教师逐字稿",
        "",
        f"- 视觉系统：{meta.get('visualSystem')}",
        f"- 学科：{meta.get('subject')}",
        f"- 年级：{meta.get('grade')}",
        f"- 课型：{meta.get('lessonType')}",
        f"- 时长：{meta.get('durationMin')} 分钟",
        f"- 页数：{meta.get('slideCount')}",
        "",
        "## 逐页话术",
        "",
    ]
    for item in deck.get("slides", []):
        ts = item.get("teacherScript", {})
        lines.extend([
            f"### {item.get('id')} · {item.get('layoutId')} · {item.get('title')}",
            "",
            f"- 教学意图：{item.get('teachingIntent')}",
            f"- 时间：{item.get('timing', {}).get('minutes')} 分钟",
            f"- 教师说：{ts.get('say', '')}",
        ])
        if ts.get("ask"):
            lines.append(f"- 追问：{' / '.join(ts.get('ask', []))}")
        if ts.get("expectedResponses"):
            lines.append(f"- 预设回应：{' / '.join(ts.get('expectedResponses', []))}")
        if item.get("feedbackEvidence"):
            lines.append(f"- 反馈证据：{item.get('feedbackEvidence')}")
        if ts.get("transition"):
            lines.append(f"- 过渡语：{ts.get('transition')}")
        if item.get("notes"):
            lines.append(f"- 备注：{'；'.join(item.get('notes', []))}")
        lines.append("")
    return "\n".join(lines)


def output_prefix(path_text: str) -> Path:
    """Resolve output prefix, creating a <case-name>/ subfolder.

    Example:
      input:  "generated-outputs/math-g5-fraction-addition"
      output: "generated-outputs/math-g5-fraction-addition/math-g5-fraction-addition"

    All stage outputs are written inside the subfolder.
    """
    path = Path(path_text)
    case_name = path.stem if path.suffix else path.name
    case_dir = path.with_suffix("") if path.suffix else path
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir / case_name


def validate_json(path: Path) -> bool:
    result = subprocess.run([sys.executable, str(VALIDATE_SCRIPT), str(path)], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def validate_html(path: Path) -> bool:
    if not VALIDATE_HTML_SCRIPT.exists():
        print("HTML validation skipped: validate_lesson_deck_html.py not found.", file=sys.stderr)
        return False
    result = subprocess.run([sys.executable, str(VALIDATE_HTML_SCRIPT), str(path)], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="生成教育版课堂课件。")
    parser.add_argument("output", help="输出文件前缀")
    parser.add_argument("--config", help="输入请求 JSON（design/script/all 阶段必填）")
    parser.add_argument("--deck-json", help="已生成的完整 deck JSON 路径（render 阶段必填）")
    parser.add_argument(
        "--design-json", help="阶段一产出的 design.json 路径（script 阶段可选，用于锁定已确认的教学设计）"
    )
    parser.add_argument(
        "--stage", choices=["design", "script", "render"], default="design",
        help="生成阶段：design=教学设计稿, script=逐字稿, render=课件",
    )
    parser.add_argument("--no-html", action="store_true", help="不生成 HTML")
    parser.add_argument("--no-validate", action="store_true", help="跳过校验")
    parser.add_argument("--no-llm", action="store_true", help="禁用 LLM，使用本地模板生成")
    parser.add_argument("--model", default=LLM_MODEL, help="Generator 模型名称（默认从 GENERATOR_MODEL 环境变量读取）")
    parser.add_argument("--temperature", type=float, default=0.2, help="温度参数")
    parser.add_argument("--max-tokens", type=int, default=8000, help="最大输出 token 数")
    parser.add_argument("--thinking", action="store_true", help="启用 Qwen enable_thinking")
    args = parser.parse_args()

    # 阶段校验
    if args.stage in ("design", "script") and not args.config:
        parser.error(f"--stage {args.stage} 需要提供 --config")
    if args.stage == "render" and not args.deck_json:
        parser.error("--stage render 必须提供 --deck-json")
    if args.stage == "render" and args.config:
        parser.error("--stage render 不应与 --config 同时使用，请提供 --deck-json")
    if args.stage in ("design", "render") and args.design_json:
        parser.error("--design-json 仅在 --stage script 时可用")

    # 构建或加载 deck
    if args.stage in ("design", "script"):
        raw_config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        config = unwrap_config_envelope(raw_config)

        # 若提供了 design.json，将其中的已确认设计合并到 config，作为生成约束
        if args.design_json:
            design_data = json.loads(Path(args.design_json).read_text(encoding="utf-8"))
            if design_data.get("designPlan"):
                config["_confirmed_designPlan"] = design_data["designPlan"]
            if design_data.get("lessonOutline"):
                config["_confirmed_lessonOutline"] = design_data["lessonOutline"]

        if not args.no_llm:
            pack = topic_pack(config)
            try:
                deck = build_deck_llm(
                    config, pack,
                    model=args.model,
                    thinking=args.thinking,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
            except Exception as error:
                print(f"LLM 生成失败: {error}", file=sys.stderr)
                return 1
        else:
            deck = build_deck(config)
    else:  # render
        deck = json.loads(Path(args.deck_json).read_text(encoding="utf-8"))

    prefix = output_prefix(args.output)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    if args.stage == "design":
        # 输出教学设计稿
        design_md_path = prefix.with_suffix(".design.md")
        design_md_path.write_text(render_design_markdown(deck), encoding="utf-8")
        print(design_md_path)
        # 输出轻量设计 JSON
        design_json = {
            "deckMeta": deck.get("deckMeta", {}),
            "curriculumContext": deck.get("curriculumContext", {}),
            "designPlan": deck.get("designPlan", []),
            "lessonOutline": deck.get("lessonOutline", []),
            "qualityReport": deck.get("qualityReport", {}),
        }
        design_json_path = prefix.with_suffix(".design.json")
        design_json_path.write_text(json.dumps(design_json, ensure_ascii=False, indent=2), encoding="utf-8")
        print(design_json_path)

    if args.stage == "script":
        # 输出逐字稿
        md_path = prefix.with_suffix(".md")
        md_path.write_text(render_markdown(deck), encoding="utf-8")
        print(md_path)
        # 输出完整 JSON
        json_path = prefix.with_suffix(".json")
        json_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json_path)

    if args.stage == "render":
        html_path = prefix.with_suffix(".html")
        if not args.no_html:
            html_path.write_text(render_html(deck), encoding="utf-8")
            print(html_path)

        if not args.no_validate:
            json_for_validate = Path(args.deck_json)
            if not validate_json(json_for_validate):
                return 1
            if not args.no_html and html_path.exists():
                if not validate_html(html_path):
                    return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
