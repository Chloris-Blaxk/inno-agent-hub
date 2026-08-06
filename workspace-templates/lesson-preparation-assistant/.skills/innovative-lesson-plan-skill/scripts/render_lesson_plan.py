#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

ENV_PATH = PROJECT_ROOT / ".env"


def load_env_file(path: Path) -> None:
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
    load_env_file(ENV_PATH)


REFERENCES_DIR = ROOT / "references"
EXAMPLES_DIR = ROOT / "examples"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_lesson_plan.py"

BASE_URL = os.getenv("DASHSCOPE_BASE_URL", os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
MODEL = os.getenv("GENERATOR_MODEL", os.getenv("QWEN_MODEL", "qwen3.5-122b-a10b"))
DEBUG_DIR = Path(os.getenv("LESSON_PLAN_DEBUG_DIR", "/tmp/lesson_plan_debug"))

TYPE_ALIASES = {
    "pbl": "PBL",
    "PBL": "PBL",
    "project_based_learning": "PBL",
    "interdisciplinary": "interdisciplinary",
    "cross_subject": "interdisciplinary",
    "cross-disciplinary": "interdisciplinary",
    "ai_integrated": "ai_integrated",
    "ai-integrated": "ai_integrated",
    "AI": "ai_integrated",
    "ai": "ai_integrated"
}

ALLOWED_TYPES = {"PBL", "interdisciplinary", "ai_integrated"}

TYPE_CONTEXT_FIELDS = {
    "PBL": ["drivingQuestionDirection", "finalProductType", "projectSpan"],
    "interdisciplinary": ["linkedSubject", "integrationNodeDescription", "applicableBoundaryHint"],
    "ai_integrated": ["aiInterventionStage", "useBoundaryHint", "critiqueApproach"]
}

SAMPLE_CONFIGS = {
    "pbl": EXAMPLES_DIR / "pbl-campus-water-saving.json",
    "interdisciplinary": EXAMPLES_DIR / "interdisciplinary-campus-water-data.json",
    "ai": EXAMPLES_DIR / "ai-integrated-expository-writing.json"
}

OUTPUT_CONTRACT = {
    "lessonMeta": {
        "subject": "请求中的学科",
        "grade": "请求中的年级",
        "topic": "请求中的课题",
        "innovationType": "PBL | interdisciplinary | ai_integrated",
        "durationMin": 40,
        "lessonType": "创新教案类型"
    },
    "backgroundAnalysis": {
        "_doc": "PBL 必含 textbookPosition/priorKnowledge/inquiryExperience/collaborationAbility；跨学科：primarySubject 和 linkedSubject 必须是对象 {{unitPosition, standardRequirement}} 绝不能是字符串，外加 curriculumIntersection；AI融合必含 textbookPosition/aiInterventionRationale",
        "_example_interdisciplinary": {
            "primarySubject": {"unitPosition": "主学科教材单元位置", "standardRequirement": "主学科课标要求内容"},
            "linkedSubject": {"unitPosition": "关联学科教材单元位置", "standardRequirement": "关联学科课标要求内容"},
            "curriculumIntersection": "两学科在课标层面的交汇依据描述"
        }
    },
    "studentAnalysis": {
        "_doc": "PBL 无此字段（合入 backgroundAnalysis）；跨学科必含 primarySubjectReadiness/linkedSubjectReadiness/crossSubjectExperience；AI融合必含 priorKnowledge/aiToolExperience/critiqueAbility/independentThinkingHabit"
    },
    "coreCompetencies": [
        {
            "id": "cc-1",
            "dimension": "学科核心素养维度（如：科学观念、科学思维、探究实践）",
            "target": "具体表现描述"
        }
    ],
    "objectives": [
        {
            "id": "obj-1",
            "description": "使用可校验行为动词表述的学习目标",
            "behaviorVerb": "识别|列举|描述|整理|解释|比较|分析|设计|评价|改进",
            "owningSubject": "跨学科必填：语文/化学/语文+化学",
            "linkedActivities": ["act-1"],
            "assessmentEvidence": ["rubric-1"]
        }
    ],
    "teachingFocus": "教学重点，必须对齐主目标",
    "teachingDifficulty": "教学难点，必须在教学流程中有对应支架",
    "innovationDesign": {
        "type": "与 innovationType 一致；PBL 必含 drivingQuestion/milestones/finalProduct；跨学科必含 disciplineConnections/integrationNodes/commonProduct/applicableBoundary；AI 融合必含 aiToolRoles/interventionStages/useBoundaries/studentCritiqueTasks"
    },
    "activityFlow": [
        {
            "id": "act-1",
            "stage": "教学环节",
            "durationMin": 5,
            "subjectTag": "跨学科必填：语文/化学/学科交汇",
            "teacherActions": ["教师活动"],
            "studentActions": ["学生活动"],
            "outputs": ["学生或小组产出"],
            "assessmentLinks": ["rubric-1"]
        }
    ],
    "assessmentRubric": [
        {
            "id": "rubric-1",
            "dimension": "评价维度",
            "excellent": "优秀表现",
            "qualified": "合格表现",
            "needsImprovement": "待改进表现",
            "evidence": "评价证据"
        }
    ],
    "resources": [
        {
            "type": "资源类型",
            "name": "资源名称",
            "usage": "使用方式"
        }
    ],
    "export": {
        "format": "markdown",
        "markdown": "可留空，脚本会重建 Word-ready Markdown"
    },
    "qualityReport": {
        "checks": [
            {
                "id": "duration",
                "status": "pass",
                "message": "活动总时长与请求一致"
            }
        ],
        "warnings": []
    }
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_data() -> dict[str, Any]:
    data: dict[str, Any] = {}
    for path in sorted(REFERENCES_DIR.glob("*.json")):
        data[path.stem] = load_json(path)
    return data


def normalize_type(value: Any) -> str:
    return TYPE_ALIASES.get(str(value), str(value))


def non_empty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def validate_request_config(request: dict[str, Any]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for key in ["subject", "grade", "topic", "innovationType", "durationMin"]:
        if key not in request or not non_empty(request[key]):
            failures.append(f"请求缺少必要字段或字段为空: {key}")

    innovation_type = normalize_type(request.get("innovationType"))
    if non_empty(request.get("innovationType")) and innovation_type not in ALLOWED_TYPES:
        failures.append(f"innovationType 不支持: {request.get('innovationType')}，仅支持 {', '.join(sorted(ALLOWED_TYPES))}")

    try:
        duration = float(request.get("durationMin"))
        if duration <= 0:
            failures.append("durationMin 必须大于 0")
    except (TypeError, ValueError):
        failures.append("durationMin 必须是数字")

    confirmed_context = request.get("confirmedContext")
    if confirmed_context is None:
        warnings.append("请求缺少 confirmedContext；生成会退化为仅基于基础课题信息。")
    elif not isinstance(confirmed_context, dict):
        failures.append("confirmedContext 必须是对象。")
    elif innovation_type in TYPE_CONTEXT_FIELDS:
        missing_fields = [field for field in TYPE_CONTEXT_FIELDS[innovation_type] if not non_empty(confirmed_context.get(field))]
        if missing_fields:
            warnings.append(f"confirmedContext 未补齐类型专属字段: {', '.join(missing_fields)}")

    return failures, warnings


def get_client() -> Any:
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 DASHSCOPE_API_KEY，请参考 agent_design/script/test_connection/test_qwen.py 配置。")
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("缺少 openai Python 包，请先安装项目运行依赖。") from error
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_system_prompt() -> str:
    return (
        "你是创新教案生成智能体，面向中国中小学教师。"
        "你必须基于用户请求和提供的 mock 数据生成可落地教案。"
        "只返回一个合法 JSON 对象，不要输出 Markdown 代码块、解释文字或额外前后缀。"
        "不得虚构超出课标边界的内容。"
    )


def build_user_prompt(request: dict[str, Any], references: dict[str, Any]) -> str:
    context_section = ""
    confirmed_context = request.get("confirmedContext")
    if confirmed_context and isinstance(confirmed_context, dict):
        context_lines = ["以下是教师在需求明确阶段提供的类型专属信息，请在生成时优先遵循："]
        for key, value in confirmed_context.items():
            if value:
                context_lines.append(f"- {key}: {value}")
        context_section = "\n\n## 教师确认的需求上下文\n\n" + "\n".join(context_lines)

    return f"""
请根据以下请求和 mock references 生成创新教案 JSON。

## 生成硬性要求

1. 输出必须是一个 JSON 对象，根字段严格包含：
   lessonMeta, backgroundAnalysis, studentAnalysis, coreCompetencies, objectives, teachingFocus, teachingDifficulty, innovationDesign, activityFlow, assessmentRubric, resources, export, qualityReport。
2. activityFlow 中所有 durationMin 相加必须等于请求 durationMin。
3. objectives[].behaviorVerb 必须从 action-verbs.json 的 allowedVerbs 中选择，不要使用"了解、掌握、培养、提高"。
4. coreCompetencies 必须填写中国新课标核心素养维度（如：科学观念、科学思维、探究实践、社会责任等）。
5. PBL 必须在 innovationDesign 中包含 drivingQuestion、milestones、finalProduct。
6. interdisciplinary 必须在 innovationDesign 中包含 disciplineConnections、integrationNodes、commonProduct、applicableBoundary。
   - disciplineConnections 必须是数组格式：[{{"subject": "学科名（如：语文）", "contribution": "该学科对核心任务的贡献描述", "standardId": "课标编号"}}]
   - integrationNodes 必须是数组格式：[{{"id": "node-1", "description": "融合节点描述", "linkedActivities": ["act-1"]}}]
   - 不能写成字符串描述，必须是结构化 JSON 数组！
7. ai_integrated 必须在 innovationDesign 中包含 aiToolRoles、interventionStages、useBoundaries、studentCritiqueTasks。
8. backgroundAnalysis 必须按类型填写：
   - PBL 必含 textbookPosition（字符串）、priorKnowledge（字符串）、inquiryExperience（字符串）、collaborationAbility（字符串）。
   - 跨学科：primarySubject 和 linkedSubject 必须是对象（绝不能是字符串），各自包含 unitPosition（字符串）和 standardRequirement（字符串）；同时必含 curriculumIntersection（字符串）。格式示例：
     {{"primarySubject": {{"unitPosition": "统编版九年级下册第六单元——古代诗歌鉴赏", "standardRequirement": "课标要求..."}}, "linkedSubject": {{"unitPosition": "人教版九年级化学上册第六单元", "standardRequirement": "课标要求..."}}, "curriculumIntersection": "两学科在课标层面的交汇依据..."}}
   - AI融合必含 textbookPosition（字符串）、aiInterventionRationale（字符串）。
9. studentAnalysis 必须按类型填写：PBL 不需要此字段（合入 backgroundAnalysis）；跨学科必含 primarySubjectReadiness（字符串）、linkedSubjectReadiness（字符串）、crossSubjectExperience（字符串）；AI融合必含 priorKnowledge、aiToolExperience、critiqueAbility、independentThinkingHabit。
10. objectives 数组每个目标必须包含 owningSubject 字段（跨学科），标注该目标归属学科，取值为"语文"/"化学"/"语文+化学"。格式示例：{{"id": "obj-1", "description": "...", "behaviorVerb": "分析", "owningSubject": "语文+化学", ...}}
11. activityFlow 数组每个活动必须包含 subjectTag 字段（跨学科），标注该环节由哪个学科主导，取值为"语文"/"化学"/"学科交汇"。格式示例：{{"id": "act-1", "stage": "...", "subjectTag": "学科交汇", ...}}
12. teachingFocus 必须非空，对齐主目标：PBL 通常是驱动问题的探究过程；跨学科通常是融合节点；AI融合通常是AI服务的目标达成+审辨。
13. teachingDifficulty 必须非空，对齐教学流程支架：PBL 通常是保持真正探究+支架时机；跨学科通常是融合自然性+交汇处认知负荷；AI融合通常是人机边界管理+审辨深度。
14. 活动、产出和评价量规必须互相对齐。
15. export.markdown 可以先留空字符串，脚本会生成 Word-ready Markdown。
16. 如果用户请求包含 confirmedContext，必须在 innovationDesign、activityFlow 或 assessmentRubric 中显式体现，不要丢失阶段一确认信息。
{context_section}
## 输出结构契约

{compact_json(OUTPUT_CONTRACT)}

## 用户请求

{compact_json(request)}

## Mock references

{compact_json(references)}
""".strip()


def fix_invalid_json_escapes(content: str) -> str:
    return re.sub(r'\\([^"\\/bfnrtu])', r'\1', content)


def iter_fenced_blocks(content: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", content, flags=re.IGNORECASE)
    ]


def iter_balanced_json_objects(content: str) -> list[str]:
    candidates: list[str] = []
    for start, char in enumerate(content):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(content)):
            current = content[index]
            if in_string:
                if escape:
                    escape = False
                elif current == "\\":
                    escape = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(content[start:index + 1])
                    break
    return candidates


def parse_json_candidate(candidate: str) -> dict[str, Any]:
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        parsed = json.loads(fix_invalid_json_escapes(candidate))
    if not isinstance(parsed, dict):
        raise ValueError("模型返回的 JSON 顶层不是对象。")
    return parsed


def extract_json_object(text: str, debug_dir: Path = DEBUG_DIR) -> dict[str, Any]:
    content = text.strip()

    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / "raw_response.txt").write_text(text, encoding="utf-8")

    candidates = [content]
    candidates.extend(iter_fenced_blocks(content))
    candidates.extend(iter_balanced_json_objects(content))

    errors: list[str] = []
    for index, candidate in enumerate(candidates, 1):
        try:
            parsed = parse_json_candidate(candidate)
            if index > 1:
                (debug_dir / "selected_candidate.txt").write_text(candidate, encoding="utf-8")
            return parsed
        except (json.JSONDecodeError, ValueError) as error:
            errors.append(f"candidate {index}: {error}")

    (debug_dir / "failed_content.txt").write_text(content, encoding="utf-8")
    (debug_dir / "errors.txt").write_text("\n".join(errors), encoding="utf-8")
    raise ValueError("无法解析模型返回的 JSON。已写入调试目录。")


def ensure_lesson_meta(plan: dict[str, Any], request: dict[str, Any]) -> None:
    meta = plan.setdefault("lessonMeta", {})
    if not isinstance(meta, dict):
        plan["lessonMeta"] = {}
        meta = plan["lessonMeta"]
    for key in ["subject", "grade", "topic", "innovationType", "durationMin"]:
        meta.setdefault(key, request.get(key))
    meta.setdefault("lessonType", f"{request.get('innovationType', '创新')} 创新教案")


def append_local_quality_check(plan: dict[str, Any], check_id: str, status: str, message: str) -> None:
    quality = plan.setdefault("qualityReport", {})
    if not isinstance(quality, dict):
        plan["qualityReport"] = {}
        quality = plan["qualityReport"]
    checks = quality.setdefault("checks", [])
    if not isinstance(checks, list):
        quality["checks"] = []
        checks = quality["checks"]
    checks.append({"id": check_id, "status": status, "message": message})


def value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "；".join(value_to_text(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {value_to_text(val)}" for key, val in value.items())
    return str(value)


def table_cell(value: Any) -> str:
    return value_to_text(value).replace("|", "\\|").replace("\n", "<br>")


def ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def item_get(item: Any, key: str, default: Any = "") -> Any:
    return item.get(key, default) if isinstance(item, dict) else default


def _build_meta_section(meta: dict[str, Any], lesson_type: str) -> list[str]:
    """Build the basic info section, type-aware for subject display."""
    lines = [
        f"# {meta.get('topic', '创新教案')}",
        "",
        "## 一、基本信息",
        ""
    ]
    if lesson_type == "interdisciplinary":
        linked = meta.get("linkedSubject", "")
        subject_display = f"{meta.get('subject', '')} + {linked}" if linked else meta.get("subject", "")
    else:
        subject_display = meta.get("subject", "")
    type_labels = {"PBL": "PBL 项目化学习", "interdisciplinary": "跨学科融合", "ai_integrated": "AI 融合课堂"}
    type_label = type_labels.get(lesson_type, lesson_type)

    lines.extend([
        f"| 学科 | {table_cell(subject_display)} | 年级 | {table_cell(meta.get('grade', ''))} | 课时 | {table_cell(meta.get('durationMin', ''))} 分钟 |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| **课题** | **{table_cell(meta.get('topic', ''))}** | **创新类型** | **{type_label}** | **课型** | {table_cell(meta.get('lessonType', ''))} |",
        ""
    ])
    return lines


def _build_pbl_background_section(background: dict[str, Any]) -> list[str]:
    """PBL: 课题背景与学情分析（合并）"""
    lines = [
        "## 二、课题背景与学情分析",
        "",
        "### 教材定位",
        "",
        table_cell(background.get("textbookPosition", "")),
        "",
        "### 学情概况",
        "",
        "| 维度 | 分析 |",
        "| :--- | :--- |",
        f"| 先备知识 | {table_cell(background.get('priorKnowledge', ''))} |",
        f"| 探究经验 | {table_cell(background.get('inquiryExperience', ''))} |",
        f"| 合作能力 | {table_cell(background.get('collaborationAbility', ''))} |",
        ""
    ]
    return lines


def _build_interdisciplinary_background_section(background: dict[str, Any]) -> list[str]:
    """跨学科：双学科教材分析"""
    lines = [
        "## 二、双学科教材分析",
        ""
    ]
    primary = background.get("primarySubject", {})
    linked = background.get("linkedSubject", {})
    if isinstance(primary, dict):
        lines.extend([
            f"### 主学科：{table_cell(primary.get('unitPosition', ''))}".split('：')[0] + "：" + table_cell(background.get("primarySubjectName", "")),
            "",
            "| 维度 | 内容 |",
            "| :--- | :--- |",
            f"| 单元定位 | {table_cell(primary.get('unitPosition', ''))} |",
            f"| 课标要求 | {table_cell(primary.get('standardRequirement', ''))} |",
            ""
        ])
    if isinstance(linked, dict):
        lines.extend([
            f"### 关联学科：{table_cell(linked.get('unitPosition', ''))}".split('：')[0] + "：" + table_cell(background.get("linkedSubjectName", "")),
            "",
            "| 维度 | 内容 |",
            "| :--- | :--- |",
            f"| 单元定位 | {table_cell(linked.get('unitPosition', ''))} |",
            f"| 课标要求 | {table_cell(linked.get('standardRequirement', ''))} |",
            ""
        ])
    lines.extend([
        "### 课标交汇依据",
        "",
        table_cell(background.get("curriculumIntersection", "")),
        ""
    ])
    return lines


def _build_ai_integrated_background_section(background: dict[str, Any]) -> list[str]:
    """AI融合：教材分析"""
    lines = [
        "## 二、教材分析",
        "",
        "### 教材定位",
        "",
        table_cell(background.get("textbookPosition", "")),
        "",
        "### AI 介入必要性",
        "",
        table_cell(background.get("aiInterventionRationale", "")),
        ""
    ]
    return lines


def _build_interdisciplinary_student_analysis_section(student: dict[str, Any]) -> list[str]:
    """跨学科：学情分析"""
    lines = [
        "## 四、学情分析",
        "",
        "| 维度 | 分析 |",
        "| :--- | :--- |",
        f"| 主学科预备水平 | {table_cell(student.get('primarySubjectReadiness', ''))} |",
        f"| 关联学科预备水平 | {table_cell(student.get('linkedSubjectReadiness', ''))} |",
        f"| 跨学科思维经验 | {table_cell(student.get('crossSubjectExperience', ''))} |",
        ""
    ]
    return lines


def _build_ai_integrated_student_analysis_section(student: dict[str, Any]) -> list[str]:
    """AI融合：学情与AI素养分析"""
    lines = [
        "## 四、学情与AI素养分析",
        "",
        "| 维度 | 分析 |",
        "| :--- | :--- |",
        f"| 先备知识 | {table_cell(student.get('priorKnowledge', ''))} |",
        f"| AI工具使用经验 | {table_cell(student.get('aiToolExperience', ''))} |",
        f"| 信息审辨能力 | {table_cell(student.get('critiqueAbility', ''))} |",
        f"| 自主思考习惯 | {table_cell(student.get('independentThinkingHabit', ''))} |",
        ""
    ]
    return lines


def _build_pbl_innovation_section(innovation: dict[str, Any]) -> list[str]:
    """PBL: 驱动问题与产出设计"""
    lines = [
        "## 三、驱动问题与产出设计",
        "",
        "### 驱动问题",
        "",
        table_cell(innovation.get("drivingQuestion", "")),
        "",
        "### 最终产出",
        ""
    ]
    final_product = innovation.get("finalProduct", "")
    if isinstance(final_product, dict):
        lines.extend([
            "| 产出类型 | 评价标准 |",
            "| :--- | :--- |",
            f"| {table_cell(final_product.get('type', ''))} | {table_cell(final_product.get('criteria', final_product.get('description', '')))} |"
        ])
    else:
        lines.append(f"- {table_cell(final_product)}")
    lines.extend([""])
    return lines


def _build_interdisciplinary_innovation_section(innovation: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    """跨学科：学科关联与融合设计"""
    lines = [
        "## 三、学科关联与融合设计",
        "",
        "### 学科关联",
        "",
        "| 学科 | 贡献 | 课标依据 |",
        "| :--- | :--- | :--- |"
    ]
    for item in ensure_list(innovation.get("disciplineConnections")):
        if isinstance(item, dict):
            subj = item.get("subject", item.get("primarySubject", ""))
            contrib = item.get("contribution", item.get("connection", ""))
            std = item.get("standardId", "")
            tag = "（主学科）" if subj == meta.get("subject", "") else "（关联学科）"
            lines.append(f"| {table_cell(subj)}{tag} | {table_cell(contrib)} | {table_cell(std)} |")
    lines.extend([""])

    # 融合节点
    nodes = ensure_list(innovation.get("integrationNodes"))
    if nodes:
        lines.extend([
            "### 融合节点",
            "",
            "| 节点 | 描述 | 关联活动 |",
            "| :--- | :--- | :--- |"
        ])
        for node in nodes:
            if isinstance(node, dict):
                lines.append(f"| {table_cell(node.get('id', node.get('description', '')))} | {table_cell(node.get('description', ''))} | {table_cell(node.get('linkedActivities', []))} |")
        lines.extend([""])

    lines.extend([
        "### 共同产出",
        "",
        table_cell(innovation.get("commonProduct", "")),
        "",
        "### 适用边界",
        "",
        table_cell(innovation.get("applicableBoundary", "")),
        ""
    ])
    return lines


def _build_ai_integrated_innovation_section(innovation: dict[str, Any]) -> list[str]:
    """AI融合：AI融合设计"""
    lines = [
        "## 三、AI 融合设计",
        "",
        "### AI 工具角色与介入环节",
        "",
        "| AI 角色 | 工具类型 | 介入环节 | 使用边界 |",
        "| :--- | :--- | :--- | :--- |"
    ]
    roles = ensure_list(innovation.get("aiToolRoles"))
    for item in roles:
        if isinstance(item, dict):
            role = item.get("toolRole", item.get("role", ""))
            tool_type = item.get("toolType", "")
            stage = item.get("interventionStage", "")
            boundary = item.get("useBoundary", "")
            lines.append(f"| {table_cell(role)} | {table_cell(tool_type)} | {table_cell(stage)} | {table_cell(boundary)} |")
    lines.extend([""])

    # 使用边界
    boundaries = ensure_list(innovation.get("useBoundaries"))
    if isinstance(innovation.get("useBoundaries"), str):
        boundaries = [innovation.get("useBoundaries")]
    if boundaries:
        lines.extend(["### 使用边界", ""])
        for b in boundaries:
            lines.append(f"- {table_cell(b)}")
        lines.extend([""])

    # 审辨任务
    critiques = ensure_list(innovation.get("studentCritiqueTasks"))
    if critiques:
        lines.extend([
            "### 学生审辨任务",
            "",
            "| 环节 | 审辨任务 | 预期证据 |",
            "| :--- | :--- | :--- |"
        ])
        for c in critiques:
            if isinstance(c, dict):
                lines.append(f"| {table_cell(c.get('activityId', ''))} | {table_cell(c.get('taskDescription', c.get('description', '')))} | {table_cell(c.get('evidenceExpected', c.get('evidence', '')))} |")
            else:
                lines.append(f"|  | {table_cell(c)} |  |")
        lines.extend([""])
    return lines


def _build_core_competencies_section(core_competencies: list[Any], lesson_type: str) -> list[str]:
    """Build core competencies section (中国新课标核心素养维度)."""
    if not core_competencies:
        return []
    # PBL: 四、跨学科/AI融合: 五、
    chapter_num = "四" if lesson_type == "PBL" else "五"
    lines = [
        f"## {chapter_num}、核心素养目标",
        "",
        "| 维度 | 具体表现 |",
        "| :--- | :--- |"
    ]
    for cc in core_competencies:
        if not isinstance(cc, dict):
            continue
        dimension = table_cell(cc.get("dimension", ""))
        target = table_cell(cc.get("target", ""))
        lines.append(f"| {dimension} | {target} |")
    lines.extend([""])
    return lines


def _build_objectives_section(objectives: list[Any], lesson_type: str, plan: Optional[dict[str, Any]] = None) -> list[str]:
    """Build objectives section, type-aware for column headers. Includes teaching focus and difficulty."""
    # PBL: 五、跨学科/AI融合: 六、
    chapter_num = "五" if lesson_type == "PBL" else "六"
    lines = [f"## {chapter_num}、教学目标", ""]
    if lesson_type == "interdisciplinary":
        lines.extend([
            "| 目标 | 归属学科 | 行为动词 | 评价证据 |",
            "| :--- | :--- | :--- | :--- |"
        ])
    elif lesson_type == "ai_integrated":
        lines.extend([
            "| 目标 | 是否借助 AI | 行为动词 | 评价证据 |",
            "| :--- | :--- | :--- | :--- |"
        ])
    else:  # PBL
        lines.extend([
            "| 目标 | 行为动词 | 关联里程碑 | 评价证据 |",
            "| :--- | :--- | :--- | :--- |"
        ])

    for obj in ensure_list(objectives):
        if not isinstance(obj, dict):
            lines.append(f"| {table_cell(obj)} | | | |")
            continue
        desc = table_cell(obj.get("description", ""))
        verb = table_cell(obj.get("behaviorVerb", ""))
        evidence = table_cell(obj.get("assessmentEvidence", []))
        if lesson_type == "interdisciplinary":
            owning = table_cell(obj.get("owningSubject", obj.get("subject", "")))
            lines.append(f"| {desc} | {owning} | {verb} | {evidence} |")
        elif lesson_type == "ai_integrated":
            needs_ai = table_cell(obj.get("needsAI", obj.get("aiAssisted", "")))
            lines.append(f"| {desc} | {needs_ai} | {verb} | {evidence} |")
        else:  # PBL
            linked = table_cell(obj.get("linkedActivities", []))
            lines.append(f"| {desc} | {verb} | {linked} | {evidence} |")
    lines.extend([""])

    # 教学重点
    focus = ""
    if plan and isinstance(plan, dict):
        focus = plan.get("teachingFocus", "")
    if focus:
        lines.extend(["### 教学重点", "", table_cell(focus), ""])

    # 教学难点
    difficulty = ""
    if plan and isinstance(plan, dict):
        difficulty = plan.get("teachingDifficulty", "")
    if difficulty:
        lines.extend(["### 教学难点", "", table_cell(difficulty), ""])

    return lines


def _build_activity_flow_section(activities: list[Any], innovation: dict[str, Any], lesson_type: str) -> list[str]:
    """Build activity flow section, type-aware for columns."""
    if lesson_type == "PBL":
        return _build_pbl_activity_flow(activities, innovation)
    elif lesson_type == "interdisciplinary":
        return _build_interdisciplinary_activity_flow(activities)
    elif lesson_type == "ai_integrated":
        return _build_ai_activity_flow(activities, innovation)
    else:
        return _build_generic_activity_flow(activities)


def _build_pbl_activity_flow(activities: list[Any], innovation: dict[str, Any]) -> list[str]:
    """PBL: 里程碑与探究流程"""
    lines = [
        "## 六、里程碑与探究流程",
        "",
        "| 里程碑 | 时长 | 学生探究任务 | 教师支架 | 阶段产出 |",
        "| :--- | ---: | :--- | :--- | :--- |"
    ]
    milestones = ensure_list(innovation.get("milestones"))
    milestone_map: dict[str, dict[str, Any]] = {}
    for ms in milestones:
        if isinstance(ms, dict):
            ms_id = ms.get("id", ms.get("name", ""))
            milestone_map[ms_id] = ms

    for activity in ensure_list(activities):
        if not isinstance(activity, dict):
            continue
        stage = table_cell(activity.get("stage", ""))
        duration = table_cell(activity.get("durationMin", ""))
        student = table_cell(activity.get("studentActions", []))
        teacher = table_cell(activity.get("teacherActions", []))
        outputs = table_cell(activity.get("outputs", []))
        lines.append(f"| {stage} | {duration} | {student} | {teacher} | {outputs} |")
    lines.extend([""])
    return lines


def _build_interdisciplinary_activity_flow(activities: list[Any]) -> list[str]:
    """跨学科：融合教学流程"""
    lines = [
        "## 七、融合教学流程",  # 跨学科共10章，教学流程是第七章
        "",
        "| 环节 | 时长 | 学科归属 | 教师活动 | 学生活动 | 产出 |",
        "| :--- | ---: | :--- | :--- | :--- | :--- |"
    ]
    for activity in ensure_list(activities):
        if not isinstance(activity, dict):
            continue
        stage = table_cell(activity.get("stage", ""))
        duration = table_cell(activity.get("durationMin", ""))
        subject_tag = table_cell(activity.get("subjectTag", activity.get("owningSubject", "")))
        teacher = table_cell(activity.get("teacherActions", []))
        student = table_cell(activity.get("studentActions", []))
        outputs = table_cell(activity.get("outputs", []))
        lines.append(f"| {stage} | {duration} | {subject_tag} | {teacher} | {student} | {outputs} |")
    lines.extend([""])
    return lines


def _build_ai_activity_flow(activities: list[Any], innovation: dict[str, Any]) -> list[str]:
    """AI融合：人机协同教学流程"""
    lines = [
        "## 七、人机协同教学流程",  # AI融合共10章，教学流程是第七章
        "",
        "| 环节 | 时长 | 执行者 | 教师活动 | 学生活动 | AI 活动 | 审辨任务 |",
        "| :--- | ---: | :--- | :--- | :--- | :--- | :--- |"
    ]
    stages_map: dict[str, dict[str, Any]] = {}
    for stage in ensure_list(innovation.get("interventionStages")):
        if isinstance(stage, dict):
            stages_map[stage.get("activityId", "")] = stage

    critiques_map: dict[str, dict[str, Any]] = {}
    for critique in ensure_list(innovation.get("studentCritiqueTasks")):
        if isinstance(critique, dict):
            critiques_map[critique.get("activityId", "")] = critique

    for activity in ensure_list(activities):
        if not isinstance(activity, dict):
            continue
        act_id = activity.get("id", "")
        stage = table_cell(activity.get("stage", ""))
        duration = table_cell(activity.get("durationMin", ""))
        executor = table_cell(activity.get("executor", item_get(stages_map.get(act_id, {}), "executor", "")))
        teacher = table_cell(activity.get("teacherActions", []))
        student = table_cell(activity.get("studentActions", []))
        ai_action = table_cell(item_get(stages_map.get(act_id, {}), "aiAction", ""))
        critique = table_cell(item_get(critiques_map.get(act_id, {}), "taskDescription", ""))
        lines.append(f"| {stage} | {duration} | {executor} | {teacher} | {student} | {ai_action} | {critique} |")
    lines.extend([""])
    return lines


def _build_generic_activity_flow(activities: list[Any]) -> list[str]:
    """Fallback: generic activity flow table."""
    lines = [
        "## 六、教学流程",
        "",
        "| 环节 | 时间 | 教师活动 | 学生活动 | 产出与评价 |",
        "| :--- | ---: | :--- | :--- | :--- |"
    ]
    for activity in ensure_list(activities):
        if not isinstance(activity, dict):
            continue
        outputs = {"outputs": activity.get("outputs", []), "assessmentLinks": activity.get("assessmentLinks", [])}
        lines.append(
            f"| {table_cell(activity.get('stage', ''))} | {table_cell(activity.get('durationMin', ''))} | "
            f"{table_cell(activity.get('teacherActions', []))} | {table_cell(activity.get('studentActions', []))} | {table_cell(outputs)} |"
        )
    lines.extend([""])
    return lines


def _build_rubric_section(rubrics: list[Any], lesson_type: str) -> list[str]:
    """Build rubric section. PBL uses dual (process + product) rubrics."""
    lines = []
    if lesson_type == "PBL":
        process_rubrics = [r for r in ensure_list(rubrics) if isinstance(r, dict) and r.get("category", "") != "product"]
        product_rubrics = [r for r in ensure_list(rubrics) if isinstance(r, dict) and r.get("category", "") == "product"]
        if not product_rubrics and process_rubrics:
            # If model didn't split, show all as single table
            lines.extend(["## 七、评价量规", ""])
            lines.extend(_rubric_table(ensure_list(rubrics)))
        else:
            lines.extend(["## 七、评价量规", "", "### 过程评价", ""])
            lines.extend(_rubric_table(process_rubrics))
            lines.extend(["### 作品评价", ""])
            lines.extend(_rubric_table(product_rubrics))
    else:
        lines.extend(["## 八、评价量规", ""])  # 跨学科/AI融合共10章，评价量规是第八章
        lines.extend(_rubric_table(ensure_list(rubrics)))
    return lines


def _rubric_table(rubrics: list[Any]) -> list[str]:
    """Build a single rubric table."""
    lines = [
        "| 维度 | 优秀 | 合格 | 待改进 | 证据来源 |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for item in rubrics:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {table_cell(item.get('dimension', ''))} | {table_cell(item.get('excellent', ''))} | "
            f"{table_cell(item.get('qualified', ''))} | {table_cell(item.get('needsImprovement', ''))} | {table_cell(item.get('evidence', ''))} |"
        )
    lines.extend([""])
    return lines


def _build_resources_section(resources: list[Any], lesson_type: str) -> list[str]:
    """Build resources section. AI融合 separates AI tools and devices."""
    chapter_num = "八" if lesson_type == "PBL" else "九"
    lines = [f"## {chapter_num}、资源与条件", ""]
    if lesson_type == "ai_integrated":
        ai_tools = [r for r in ensure_list(resources) if isinstance(r, dict) and r.get("type", "").lower() in ("ai工具", "ai tool", "ai_tool")]
        other_resources = [r for r in ensure_list(resources) if not isinstance(r, dict) or r.get("type", "").lower() not in ("ai工具", "ai tool", "ai_tool")]
        if ai_tools:
            lines.extend(["| AI 工具 | 使用方式 |", "| :--- | :--- |"])
            for r in ai_tools:
                lines.append(f"| {table_cell(r.get('name', ''))} | {table_cell(r.get('usage', ''))} |")
            lines.extend([""])
        if other_resources:
            lines.extend(["| 类型 | 名称 | 使用方式 |", "| :--- | :--- | :--- |"])
            for r in other_resources:
                if isinstance(r, dict):
                    lines.append(f"| {table_cell(r.get('type', ''))} | {table_cell(r.get('name', ''))} | {table_cell(r.get('usage', ''))} |")
            lines.extend([""])
    else:
        lines.extend(["| 类型 | 名称 | 使用方式 |", "| :--- | :--- | :--- |"])
        for resource in ensure_list(resources):
            if not isinstance(resource, dict):
                lines.append(f"| 资源 | {table_cell(resource)} |  |")
                continue
            lines.append(f"| {table_cell(resource.get('type', ''))} | {table_cell(resource.get('name', ''))} | {table_cell(resource.get('usage', ''))} |")
        lines.extend([""])
    return lines


def _build_reflection_section(lesson_type: str) -> list[str]:
    """Build reflection prompts section, type-specific."""
    chapter_num = "九" if lesson_type == "PBL" else "十"
    lines = [f"## {chapter_num}、教学反思要点", ""]
    if lesson_type == "PBL":
        lines.extend([
            "- 驱动问题是否真正驱动了探究？（还是变成了资料搜集或手抄报）",
            "- 里程碑之间的衔接是否自然？学生在哪个里程碑最需要支架？",
            "- 最终产出是否体现了学生的真实理解？（还是仅停留在表面展示）"
        ])
    elif lesson_type == "interdisciplinary":
        lines.extend([
            "- 融合节点是否是完成核心任务的必要环节？（去掉关联学科后核心任务能否完成）",
            "- 两个学科的知识是否在融合节点自然交汇？（还是简单的前半节A后半节B）",
            "- 共同产出是否真正融合了两学科的方法和成果？（还是两学科产出的简单拼接）"
        ])
    elif lesson_type == "ai_integrated":
        lines.extend([
            "- AI 是否真正服务了教学目标？（去掉 AI 后学习目标还能达成吗）",
            "- 学生是否真正审辨了 AI 输出？（还是直接采用了 AI 建议）",
            "- 使用边界是否得到了遵守？（AI 是否越界替学生完成了核心认知任务）"
        ])
    else:
        lines.append("- 教学目标是否达成？活动与评价是否对齐？")
    lines.extend([""])
    return lines


def build_markdown(plan: dict[str, Any]) -> str:
    meta = plan.get("lessonMeta", {})
    innovation = plan.get("innovationDesign", {})
    background = plan.get("backgroundAnalysis", {})
    student = plan.get("studentAnalysis", {})
    lesson_type = meta.get("innovationType", "")

    lines: list[str] = []
    # 一、基本信息
    lines.extend(_build_meta_section(meta, lesson_type))
    # 二、背景/教材分析章节
    if lesson_type == "PBL":
        lines.extend(_build_pbl_background_section(background))
    elif lesson_type == "interdisciplinary":
        lines.extend(_build_interdisciplinary_background_section(background))
    elif lesson_type == "ai_integrated":
        lines.extend(_build_ai_integrated_background_section(background))
    else:
        lines.extend(["## 二、课题背景", "", value_to_text(background), ""])
    # 三、类型专属创新设计章节
    if lesson_type == "PBL":
        lines.extend(_build_pbl_innovation_section(innovation))
    elif lesson_type == "interdisciplinary":
        lines.extend(_build_interdisciplinary_innovation_section(innovation, meta))
    elif lesson_type == "ai_integrated":
        lines.extend(_build_ai_integrated_innovation_section(innovation))
    else:
        lines.extend(["## 三、创新设计", "", value_to_text(innovation), ""])
    # 四、学情分析（PBL 无此独立章节，跨学科和AI融合有）
    if lesson_type == "interdisciplinary":
        lines.extend(_build_interdisciplinary_student_analysis_section(student))
    elif lesson_type == "ai_integrated":
        lines.extend(_build_ai_integrated_student_analysis_section(student))
    # 四/五、核心素养目标
    lines.extend(_build_core_competencies_section(ensure_list(plan.get("coreCompetencies")), lesson_type))
    # 五/六、教学目标（含教学重点/难点）
    lines.extend(_build_objectives_section(ensure_list(plan.get("objectives")), lesson_type, plan))
    # 六/七、教学流程（类型差异化）
    lines.extend(_build_activity_flow_section(ensure_list(plan.get("activityFlow")), innovation, lesson_type))
    # 七/八、评价量规
    lines.extend(_build_rubric_section(ensure_list(plan.get("assessmentRubric")), lesson_type))
    # 八/九、资源与条件
    lines.extend(_build_resources_section(ensure_list(plan.get("resources")), lesson_type))
    # 九/十、教学反思要点
    lines.extend(_build_reflection_section(lesson_type))

    return "\n".join(lines).strip() + "\n"


def convert_markdown_to_docx(md_path: Path, docx_path: Path) -> Path:
    """将 Markdown 文件转换为 DOCX，使用系统 pandoc。"""
    pandoc_cmd = shutil.which("pandoc")
    if not pandoc_cmd:
        raise RuntimeError("未找到 pandoc 命令，请先安装 pandoc（brew install pandoc 或 apt install pandoc）。")
    result = subprocess.run(
        [pandoc_cmd, str(md_path), "-o", str(docx_path), "--from=markdown", "--to=docx"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc 转 DOCX 失败: {result.stderr}")
    return docx_path


def write_outputs(output_base: Path, plan: dict[str, Any], export_docx: bool = False) -> tuple[Path, Path, Optional[Path]]:
    # 规范化输出路径：去掉.json/.md/.docx 后缀，确保是目录或文件名基名
    if output_base.suffix in {".json", ".md", ".docx"}:
        output_base = output_base.with_suffix("")

    # 如果 output_base 指向一个已存在的目录，在其内部创建文件
    if output_base.is_dir():
        json_path = output_base / f"{output_base.name}.json"
        md_path = output_base / f"{output_base.name}.md"
        docx_path = output_base / f"{output_base.name}.docx"
    else:
        # 自动在 generated-outputs 下创建子文件夹，模仿 math-g5-line-chart 模式
        output_dir = ROOT / "generated-outputs" / output_base.name
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{output_base.name}.json"
        md_path = output_dir / f"{output_base.name}.md"
        docx_path = output_dir / f"{output_base.name}.docx"

    markdown = build_markdown(plan)
    plan["export"] = {
        "format": "markdown",
        "filename": output_base.name,
        "markdown": markdown
    }

    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")

    actual_docx_path: Optional[Path] = None
    if export_docx:
        actual_docx_path = convert_markdown_to_docx(md_path, docx_path)
        plan["export"]["docxGenerated"] = str(actual_docx_path)

    return json_path, md_path, actual_docx_path


def validate_output(json_path: Path, request_path: Path) -> int:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(json_path), "--request", str(request_path)],
        capture_output=True,
        text=True
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


def call_generator(prompt: str, system: str, model: str, thinking: bool, max_tokens: int, temperature: Optional[float]) -> str:
    client = get_client()
    request_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    if thinking:
        request_kwargs["extra_body"] = {"enable_thinking": True}

    response = client.chat.completions.create(**request_kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("模型返回内容为空。")
    return content


def resolve_config(args: argparse.Namespace) -> Path:
    if args.sample:
        return SAMPLE_CONFIGS[args.sample]
    if args.config:
        return Path(args.config)
    raise SystemExit("请提供 --config 路径或 --sample。")


def main() -> int:
    parser = argparse.ArgumentParser(description="调用生成模型生成创新教案 JSON 和 Markdown。")
    parser.add_argument("output", help="输出路径基名；脚本会写出 .json 和 .md")
    parser.add_argument("--config", help="输入请求 JSON 路径")
    parser.add_argument("--sample", choices=sorted(SAMPLE_CONFIGS), help="使用内置示例请求")
    parser.add_argument("--thinking", action="store_true", help="启用 Qwen enable_thinking 参数")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default=None, help="兼容旧命令参数；Qwen 生成链路不使用该值")
    parser.add_argument("--max-tokens", type=int, default=8000, help="最大输出 token 数")
    parser.add_argument("--temperature", type=float, default=0.2, help="温度参数")
    parser.add_argument("--model", default=MODEL, help="生成模型名称，默认读取 GENERATOR_MODEL/QWEN_MODEL 或 qwen3.5-122b-a10b")
    parser.add_argument("--debug-dir", default=str(DEBUG_DIR), help="模型原始响应与解析错误调试目录")
    parser.add_argument("--no-validate", action="store_true", help="跳过本地校验")
    parser.add_argument("--docx", action="store_true", default=True, help="导出 .docx 文件（默认启用，需要系统安装 pandoc）")
    parser.add_argument("--no-docx", action="store_true", help="不导出 .docx 文件，仅输出 .json 和 .md")
    args = parser.parse_args()

    config_path = resolve_config(args)
    if not config_path.exists():
        print(f"请求文件不存在: {config_path}", file=sys.stderr)
        return 2

    try:
        request = load_json(config_path)
        if not isinstance(request, dict):
            raise ValueError("请求 JSON 顶层必须是对象。")
        failures, warnings = validate_request_config(request)
        if failures:
            raise ValueError("请求预检失败：\n- " + "\n- ".join(failures))
        for warning in warnings:
            print(f"请求预检警告: {warning}", file=sys.stderr)
        references = load_reference_data()
        prompt = build_user_prompt(request, references)
        raw_content = call_generator(
            prompt=prompt,
            system=build_system_prompt(),
            model=args.model,
            thinking=args.thinking,
            max_tokens=args.max_tokens,
            temperature=args.temperature
        )
        lesson_plan = extract_json_object(raw_content, Path(args.debug_dir))
    except Exception as error:
        print(f"生成失败: {error}", file=sys.stderr)
        return 1

    ensure_lesson_meta(lesson_plan, request)
    append_local_quality_check(
        lesson_plan,
        "local-renderer",
        "pass",
        "本地脚本已重建 export.markdown，并将继续执行结构校验。"
    )
    json_path, md_path, docx_path = write_outputs(Path(args.output), lesson_plan, export_docx=args.docx and not args.no_docx)
    print(json_path)
    print(md_path)
    if docx_path:
        print(docx_path)

    if not args.no_validate:
        return validate_output(json_path, config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
