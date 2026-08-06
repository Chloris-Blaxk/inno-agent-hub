from __future__ import annotations

import json

from paper_qa_runtime.llm import ChatClient
from paper_qa_runtime.schemas import ChatMessage, QueryRewriteResult, RuntimeConfig
from paper_qa_runtime.text_utils import clean_query, extract_json_object, preview


class QueryRewriteService:
    def __init__(self, *, config: RuntimeConfig, llm_client: ChatClient):
        self.config = config
        self.llm_client = llm_client
        self.prompt_path = config.resolved_prompt_dir / "rag" / "query_rewrite.md"

    def rewrite(
        self,
        *,
        title: str,
        question: str,
        base_query: str,
        task_type: str,
        agent_name: str | None,
        history: list[ChatMessage],
    ) -> QueryRewriteResult:
        if not self.config.query_rewrite_enabled:
            return QueryRewriteResult.disabled()
        try:
            prompt = self.prompt_path.read_text(encoding="utf-8")
            raw = self.llm_client.complete(
                system_prompt=prompt,
                context="",
                user_message=self._build_user_message(
                    title=title,
                    question=question,
                    base_query=base_query,
                    task_type=task_type,
                    agent_name=agent_name,
                    history=history,
                ),
                history=[],
                max_tokens=self.config.query_rewrite_max_tokens,
                temperature=0.1,
            )
            result = self._parse_response(raw)
            if not result.standalone_query and not result.retrieval_queries and not result.expanded_terms:
                return QueryRewriteResult.disabled()
            return result
        except Exception:  # noqa: BLE001
            return QueryRewriteResult.disabled()

    @staticmethod
    def _build_user_message(
        *,
        title: str,
        question: str,
        base_query: str,
        task_type: str,
        agent_name: str | None,
        history: list[ChatMessage],
    ) -> str:
        recent = []
        for item in history[-6:]:
            role = "用户" if item.role == "user" else "助手"
            content = preview(item.content, 300)
            if content:
                recent.append(f"{role}: {content}")
        recent_text = "\n".join(recent) if recent else "无"
        return (
            f"论文标题：{title}\n"
            f"当前任务：{task_type}\n"
            f"当前智能体：{agent_name or 'general'}\n"
            f"最近对话：\n{recent_text}\n\n"
            f"用户最新问题：{question}\n"
            f"现有规则 query：{base_query}\n"
        )

    @staticmethod
    def _parse_response(raw: str) -> QueryRewriteResult:
        payload = json.loads(extract_json_object(raw))
        standalone_query = clean_query(str(payload.get("standalone_query") or ""), max_chars=120)
        expanded_terms = _clean_list(payload.get("expanded_terms"), max_items=8, max_chars=24)
        section_hint = _clean_list(payload.get("section_hint"), max_items=4, max_chars=20)
        retrieval_queries = _clean_list(payload.get("retrieval_queries"), max_items=4, max_chars=80)
        return QueryRewriteResult(
            enabled=True,
            standalone_query=standalone_query,
            expanded_terms=expanded_terms,
            section_hint=section_hint,
            retrieval_queries=retrieval_queries,
        )


def _clean_list(value: object, *, max_items: int, max_chars: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    seen = set()
    for item in value:
        text = clean_query(str(item), max_chars=max_chars)
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
        if len(cleaned) >= max_items:
            break
    return cleaned
