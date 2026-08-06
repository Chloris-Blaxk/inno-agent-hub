from __future__ import annotations

from paper_qa_runtime.retrieval import RetrievalResult
from paper_qa_runtime.schemas import ChatMessage, IndexedPaper, RetrievedChunk


class ContextBuilder:
    def build(
        self,
        *,
        index: IndexedPaper,
        question: str,
        task_type: str,
        agent_name: str | None,
        retrieval: RetrievalResult,
        history: list[ChatMessage],
    ) -> str:
        parts = [
            f"论文标题：{index.title}",
            f"当前任务：{task_type}",
            f"用户最新问题：{question}",
        ]
        if agent_name:
            parts.append(f"当前智能体：{agent_name}")

        recent_history = _format_recent_history(history)
        if recent_history:
            parts.append(f"最近对话：\n{recent_history}")

        parts.append("检索 query：\n" + "\n".join(f"{idx + 1}. {q}" for idx, q in enumerate(retrieval.queries)))
        if retrieval.chunks:
            parts.append("检索到的论文片段：\n" + self.format_chunks(retrieval.chunks))
        else:
            parts.append("检索到的论文片段：无。回答时必须说明当前论文中未检索到足够证据。")

        parts.append(
            "回答约束：\n"
            "1. 只能基于当前论文片段回答论文内容相关问题。\n"
            "2. 如果证据不足，明确说明当前论文中未检索到足够证据。\n"
            "3. 涉及论文内容的判断、总结或解释需要带引用，例如 [chunk:12, section:研究方法]。"
        )
        return "\n\n".join(parts)

    @staticmethod
    def format_chunks(chunks: list[RetrievedChunk]) -> str:
        formatted = []
        for item in chunks:
            chunk = item.chunk
            section = chunk.section_title or "未知章节"
            page = f", p.{chunk.page_start}" if chunk.page_start else ""
            formatted.append(
                f"[chunk:{chunk.chunk_index}{page}, section:{section}]\n"
                f"{chunk.contextual_prefix}\n\n{chunk.content}"
            )
        return "\n\n---\n\n".join(formatted)


def _format_recent_history(history: list[ChatMessage]) -> str:
    lines = []
    for msg in history[-6:]:
        role = "用户" if msg.role == "user" else "助手"
        content = msg.content.strip()
        if content:
            lines.append(f"{role}: {content[:500]}")
    return "\n".join(lines)
