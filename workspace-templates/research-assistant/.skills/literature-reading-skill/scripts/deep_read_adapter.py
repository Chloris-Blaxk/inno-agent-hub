#!/usr/bin/env python3
"""deep_read 模式适配器——在文献阅读助手全流程中调用 paper_qa_runtime 进行单篇精读。

用法：
    PYTHONPATH=scripts python scripts/deep_read_adapter.py \
      --paper examples/sample-paper-for-deep-read.md \
      --question "这篇论文采用了什么研究方法？" \
      --title "示例论文"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


COMMON_ROOT = Path(__file__).resolve().parents[1].parent / "research-line-common"
sys.path.insert(0, str(COMMON_ROOT))
from education_generator_config import (  # noqa: E402
    DEFAULT_BASE_URL,
    education_generator_api_key,
    education_generator_base_url,
    education_generator_model,
)


def run_deep_read(
    paper_md: str,
    question: str,
    title: str | None = None,
    history: list[dict[str, str]] | None = None,
    *,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    embedding_base_url: str | None = None,
    embedding_api_key: str | None = None,
    embedding_model: str | None = None,
    embedding_dimensions: int | None = None,
) -> dict[str, Any]:
    """调用 paper_qa_runtime 进行单篇论文深度问答。

    返回包含 answer / citations / retrieval / trace 的字典。
    如果 paper_qa_runtime 未安装或 LLM 未配置，返回 mock 结果用于测试流程。
    """
    try:
        from paper_qa_runtime import PaperQARuntime, RuntimeConfig  # noqa: PLC0415
    except Exception:
        return _mock_deep_read(paper_md, question, title)

    try:
        runtime = PaperQARuntime(
            RuntimeConfig(
                llm_base_url=llm_base_url
                or os.environ.get("PAPER_QA_LLM_BASE_URL")
                or education_generator_base_url()
                or DEFAULT_BASE_URL,
                llm_api_key=llm_api_key or os.environ.get("PAPER_QA_LLM_API_KEY") or education_generator_api_key(),
                llm_model=llm_model or os.environ.get("PAPER_QA_LLM_MODEL") or education_generator_model(),
                embedding_base_url=embedding_base_url
                or os.environ.get(
                    "PAPER_QA_EMBEDDING_BASE_URL",
                    "https://api-inference.modelscope.cn/v1",
                ),
                embedding_api_key=embedding_api_key or os.environ.get("PAPER_QA_EMBEDDING_API_KEY", ""),
                embedding_model=embedding_model
                or os.environ.get("PAPER_QA_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                embedding_dimensions=embedding_dimensions or 4096,
            )
        )
    except ValueError:
        return _mock_deep_read(paper_md, question, title)

    result = runtime.answer(
        paper_md=paper_md,
        history=[{"role": m["role"], "content": m["content"]} for m in (history or [])],
        question=question,
        title=title,
    )
    return {
        "answer": result.answer,
        "agent": result.agent,
        "citations": [
            {"chunkIndex": c.chunk_index, "page": c.page, "section": c.section}
            for c in result.citations
        ],
        "retrieval": {
            "queries": result.retrieval.queries,
            "chunks": [
                {
                    "chunkIndex": ch.chunk_index,
                    "sectionTitle": ch.section_title,
                    "contentPreview": ch.content_preview,
                    "finalScore": ch.final_score,
                    "isAnchor": ch.is_anchor,
                }
                for ch in result.retrieval.chunks
            ],
        },
        "trace": result.trace,
        "_mock": False,
    }


def _mock_deep_read(paper_md: str, question: str, title: str | None = None) -> dict[str, Any]:
    """当 paper_qa_runtime 不可用时，返回模拟结果供流程测试。"""
    title = title or "未命名论文"
    preview = paper_md[:200].replace("\n", " ")

    method_keywords = ["方法", "method", "采用", "样本", "数据", "问卷", "实验", "调查"]
    result_keywords = ["结果", "发现", "result", "结论", "finding"]
    is_method_q = any(kw in question for kw in method_keywords)
    is_result_q = any(kw in question for kw in result_keywords)

    if is_method_q:
        agent = "method"
        answer = (
            f"**[简答]** {title} 采用的研究方法需从原文中确认。当前为 mock 模式，无法进行真实检索。\n\n"
            f"**[分析]** 建议提供论文全文或摘要后重新提问，精读引擎将自动进行章节路由和原文片段检索。\n\n"
            f"**[拓展]** 在等待原文的同时，你可以先思考：你期望这篇论文采用什么类型的研究方法？量化、质性还是混合？"
        )
    elif is_result_q:
        agent = "result"
        answer = (
            f"**[简答]** {title} 的主要发现需从原文中确认。当前为 mock 模式。\n\n"
            f"**[分析]** 请提供论文全文后重新提问。"
        )
    else:
        agent = "general"
        answer = (
            f"**[简答]** 关于「{question}」，需要基于论文原文内容回答。\n\n"
            f"**[分析]** 当前为 mock 模式。请配置 LLM 和 Embedding 凭证后重新提问，或提供论文全文。\n\n"
            f"论文预览：{preview}..."
        )

    return {
        "answer": answer,
        "agent": agent,
        "citations": [],
        "retrieval": {"queries": [question], "chunks": []},
        "trace": {"mock": True, "paper_title": title},
        "_mock": True,
    }


def multi_turn_deep_read(
    paper_md: str,
    questions: list[str],
    title: str | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """执行多轮精读：逐轮调用 deep_read，每轮携带上一轮的历史。

    返回 deepReadSessions 数组，可直接嵌入 DeepReadCard。
    """
    sessions: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    for question in questions:
        result = run_deep_read(
            paper_md=paper_md,
            question=question,
            title=title,
            history=history,
            **kwargs,
        )
        sessions.append(
            {
                "question": question,
                "answer": result["answer"],
                "agent": result["agent"],
                "citations": result["citations"],
                "_mock": result.get("_mock", False),
            }
        )
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": result["answer"]})
    return sessions


def main() -> int:
    parser = argparse.ArgumentParser(description="deep_read 模式适配器——单篇论文多轮精读")
    parser.add_argument("--paper", required=True, help="论文 Markdown 文件路径")
    parser.add_argument("--question", action="append", dest="questions", help="单轮问题（可多次指定）")
    parser.add_argument("--title", help="论文标题")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON（含 citations/retrieval/trace）")
    args = parser.parse_args()

    paper_md = Path(args.paper).read_text(encoding="utf-8")
    title = args.title or Path(args.paper).stem
    questions = args.questions or ["这篇论文采用了什么研究方法？"]

    sessions = multi_turn_deep_read(paper_md=paper_md, questions=questions, title=title)

    if args.json:
        output = {
            "paperTitle": title,
            "deepReadSessions": sessions,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    for i, session in enumerate(sessions, 1):
        print(f"\n{'='*60}")
        print(f"  第 {i} 轮 · Agent: {session['agent']}")
        print(f"{'='*60}")
        print(f"Q: {session['question']}")
        print(f"\n{session['answer']}")
        if session["citations"]:
            print(f"\n📎 引用来源：")
            for c in session["citations"]:
                print(f"  - Chunk {c['chunkIndex']} | {c.get('section', '未知章节')} | p.{c.get('page', 'N/A')}")
        if session.get("_mock"):
            print("\n⚠️ 以上为 mock 结果，非真实精读。请配置 LLM/Embedding 凭证。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
