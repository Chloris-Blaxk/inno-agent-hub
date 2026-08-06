#!/usr/bin/env python3
"""
种子题库数据生成脚本
====================
使用 InnoSpark-235B 生成特定学科、年级、知识点的种子题目，
输出符合 exercise-generation-skill seed-question-bank schema 的 JSON。

用法:
  python3 scripts/generate_seed_data.py \
    --subject 数学 --grade 七年级 \
    --topic "一元一次方程" \
    --count 30 \
    --output references/seed-question-bank-math-g7-linear-equation.json

依赖:
  - INNOSPARK_AIECNU_API_KEY 环境变量（或 INNOSPARK_API_KEY）
  - openai 包
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# 加载项目根目录 .env
SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
PROJECT_ROOT = SKILL_DIR.parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
except ImportError:
    # 手动加载 .env
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

# ── 配置 ─────────────────────────────────────────
API_KEY = os.getenv("INNOSPARK_AIECNU_API_KEY") or os.getenv("INNOSPARK_API_KEY")
BASE_URL = os.getenv("INNOSPARK_AIECNU_BASE_URL", "https://innospark-api.aiecnu.net/v1")
MODEL = "InnoSpark-235B"

# ── Schema ───────────────────────────────────────
QUESTION_SCHEMA = {
    "id": "<unique-id>",
    "sourceId": "<unique-id>",
    "knowledgePointIds": ["<kp-id>"],
    "layer": "A|B|C",
    "questionType": "计算题|应用题|比较题|判断题|填空题",
    "difficulty": 1,  # 1-5
    "cognitiveLevel": "识记|理解|应用|分析|评价",
    "stem": "<题目正文>",
    "answer": "<标准答案>",
    "solutionSteps": ["<步骤1>", "<步骤2>"],
    "commonErrors": ["<err-tag>"],
    "scorePoints": 5,
    "teachingNote": "<教学提示>",
    "estimatedTimeSec": 60,
    "isOriginal": True,
    "licenseNote": "InnoSpark-235B 生成·仅供教学使用"
}


def get_client():
    if not API_KEY:
        raise RuntimeError("缺少 INNOSPARK_AIECNU_API_KEY 或 INNOSPARK_API_KEY 环境变量")
    from openai import OpenAI
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def call_generator(system: str, prompt: str, temperature: float = 0.5, max_tokens: int = 8192) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("InnoSpark-235B 返回空内容")
    return content


def extract_json_array(text: str) -> list:
    """从模型输出中提取 JSON 数组。"""
    # 先尝试直接解析
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "questions" in parsed:
            return parsed["questions"]
    except json.JSONDecodeError:
        pass

    # 尝试从 code block 中提取
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "questions" in parsed:
                return parsed["questions"]
        except json.JSONDecodeError:
            continue

    # 尝试找到 JSON 数组
    for match in re.finditer(r"\[[\s\S]*\]", text):
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError("无法从模型输出中提取 JSON 数组")


def validate_question(q: dict, index: int) -> list[str]:
    """校验单道题目的必填字段。"""
    required = [
        "id", "knowledgePointIds", "layer", "questionType", "difficulty",
        "stem", "answer", "solutionSteps", "scorePoints"
    ]
    errors = []
    for field in required:
        if field not in q or not q[field]:
            errors.append(f"题目 #{index} 缺少字段: {field}")
    if q.get("difficulty", 0) not in range(1, 6):
        errors.append(f"题目 #{index} difficulty 超出 1-5: {q.get('difficulty')}")
    if q.get("layer") not in ("A", "B", "C"):
        errors.append(f"题目 #{index} layer 无效: {q.get('layer')}")
    return errors


def build_prompt(subject: str, grade: str, topic: str, knowledge_points: list[dict], count: int) -> str:
    """构建生成 prompt。"""
    kp_desc = "\n".join(
        f"  - {kp['id']}: {kp['name']}（{kp.get('description', '')}），难度层 {kp.get('layer', 'A/B/C')}"
        for kp in knowledge_points
    )

    layer_dist = f"A层(基础·识记理解)约{count//3}题, B层(巩固·应用)约{count//3}题, C层(拓展·分析评价)约{count - 2*(count//3)}题"

    return f"""请为{grade}{subject}「{topic}」生成 {count} 道种子题目，输出为 JSON 数组。

## 知识点

{kp_desc}

## 题目分布要求

- 总题数: {count}
- 分层: {layer_dist}
- 题型比例: 计算题约40%, 应用题约30%, 填空题约15%, 判断题约15%
- 题目之间不能雷同，要有变式

## 每道题目的 JSON 格式

{json.dumps(QUESTION_SCHEMA, ensure_ascii=False, indent=2)}

## 重要规则

1. `id` 和 `sourceId` 都使用 `q-<topic-slug>-<3位序号>` 格式
2. `knowledgePointIds` 从上面知识点的 id 中选择
3. `layer` 取 "A"（基础）、"B"（巩固）或 "C"（拓展）
4. `difficulty` 取值 1-5，A层1-2，B层2-3，C层3-5
5. `cognitiveLevel` 取 识记/理解/应用/分析/评价 之一
6. `solutionSteps` 必须是数组，每一步一个字符串
7. `commonErrors` 列出学生常见错误标签
8. 数学题目中的分数用 LaTeX \\frac{{分子}}{{分母}} 格式
9. 只输出 JSON 数组，不要额外解释"""


def generate_seed_bank(
    subject: str,
    grade: str,
    topic: str,
    knowledge_points: list[dict],
    count: int,
    output_path: Path,
    batch_size: int = 10,
) -> list[dict]:
    """分批生成种子题库。"""
    all_questions = []
    batches = (count + batch_size - 1) // batch_size
    remaining = count

    system_prompt = f"你是一位资深的{grade}{subject}命题专家，精通课程标准、学生认知规律和命题规范。你输出的每道题目必须符合给定的 JSON Schema，包含完整的题干、答案、解析步骤和教学提示。只输出 JSON 数组，不输出任何其他文字。"

    for batch_idx in range(batches):
        batch_count = min(batch_size, remaining)
        print(f"\n📝 批次 {batch_idx + 1}/{batches}: 生成 {batch_count} 道题...", flush=True)

        prompt = build_prompt(subject, grade, topic, knowledge_points, batch_count)
        if all_questions:
            prompt += f"\n\n## 已生成的题目（避免雷同）\n{json.dumps([q['stem'][:80] for q in all_questions], ensure_ascii=False, indent=2)}"

        try:
            raw = call_generator(system_prompt, prompt, temperature=0.6, max_tokens=8192)
            questions = extract_json_array(raw)
        except Exception as e:
            print(f"  ❌ 批次 {batch_idx + 1} 失败: {e}")
            # 重试一次
            print(f"  🔄 重试...")
            time.sleep(2)
            try:
                raw = call_generator(system_prompt, prompt, temperature=0.7, max_tokens=8192)
                questions = extract_json_array(raw)
            except Exception as e2:
                print(f"  ❌ 重试也失败: {e2}")
                continue

        valid_count = 0
        for q in questions:
            errors = validate_question(q, len(all_questions) + valid_count + 1)
            if errors:
                print(f"  ⚠️ 题目校验失败: {'; '.join(errors)}")
                continue
            # 补全可选字段
            q.setdefault("sourceId", q.get("id", ""))
            q.setdefault("commonErrors", [])
            q.setdefault("teachingNote", "")
            q.setdefault("estimatedTimeSec", 60)
            q.setdefault("isOriginal", True)
            q.setdefault("licenseNote", "InnoSpark-235B 生成·仅供教学使用")
            all_questions.append(q)
            valid_count += 1

        print(f"  ✅ 本批有效 {valid_count} 题，累计 {len(all_questions)}/{count}")
        remaining = count - len(all_questions)

        if remaining <= 0:
            break
        time.sleep(1)  # 避免限流

    return all_questions[:count]


def main():
    parser = argparse.ArgumentParser(description="使用 InnoSpark-235B 生成种子题库")
    parser.add_argument("--subject", required=True, help="学科，如 数学")
    parser.add_argument("--grade", required=True, help="年级，如 七年级")
    parser.add_argument("--topic", required=True, help="课题，如 一元一次方程")
    parser.add_argument("--count", type=int, default=30, help="生成题目总数（默认 30）")
    parser.add_argument("--batch-size", type=int, default=10, help="每批生成数量（默认 10）")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--knowledge-points", required=True, help="知识点 JSON 文件路径（包含 [{id, name, description, layer}] 数组）")
    args = parser.parse_args()

    # 加载知识点定义
    kp_path = Path(args.knowledge_points)
    if not kp_path.exists():
        print(f"知识点文件不存在: {kp_path}", file=sys.stderr)
        sys.exit(1)
    knowledge_points = json.loads(kp_path.read_text(encoding="utf-8"))

    # 生成
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"🎓 种子题库生成器")
    print(f"  学科: {args.subject}")
    print(f"  年级: {args.grade}")
    print(f"  课题: {args.topic}")
    print(f"  目标题数: {args.count}")
    print(f"  知识点: {len(knowledge_points)} 个")
    print(f"  输出: {output_path}")

    questions = generate_seed_bank(
        subject=args.subject,
        grade=args.grade,
        topic=args.topic,
        knowledge_points=knowledge_points,
        count=args.count,
        output_path=output_path,
        batch_size=args.batch_size,
    )

    # 保存
    output_data = {
        "metadata": {
            "subject": args.subject,
            "grade": args.grade,
            "topic": args.topic,
            "generatedBy": "InnoSpark-235B",
            "questionCount": len(questions),
            "knowledgePointIds": [kp["id"] for kp in knowledge_points],
        },
        "questions": questions,
    }

    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 已保存 {len(questions)} 道题目到 {output_path}")

    # 打印分布
    layers = {"A": 0, "B": 0, "C": 0}
    types = {}
    for q in questions:
        layers[q.get("layer", "?")] = layers.get(q.get("layer", "?"), 0) + 1
        t = q.get("questionType", "?")
        types[t] = types.get(t, 0) + 1

    print(f"\n📊 分布:")
    print(f"  分层: A={layers['A']}, B={layers['B']}, C={layers['C']}")
    for t, c in sorted(types.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
