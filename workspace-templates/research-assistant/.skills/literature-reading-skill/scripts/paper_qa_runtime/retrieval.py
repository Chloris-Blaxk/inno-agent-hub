from __future__ import annotations

import re
from dataclasses import dataclass, replace

from paper_qa_runtime.embeddings import EmbeddingClient
from paper_qa_runtime.schemas import (
    ChatMessage,
    IndexedPaper,
    QueryRewriteResult,
    RetrievedChunk,
    RuntimeConfig,
)
from paper_qa_runtime.text_utils import clean_query, dot_product, estimate_tokens, tokenize_for_keyword


AGENT_SECTION_KEYWORDS = {
    "review": ("引言", "综述", "背景", "研究问题", "文献"),
    "method": ("方法", "样本", "实验", "数据", "变量", "问卷", "模型"),
    "result": ("结果", "发现", "实验结果", "分析结果", "统计"),
    "discussion": ("讨论", "结论", "局限", "启示", "展望"),
}

TASK_QUERIES = {
    "chat": "",
    "report": "论文题目 摘要 引言 研究问题 研究方法 研究结果 讨论 结论 局限",
    "conclusion": "结论 讨论 研究发现 局限 启示 未来研究",
    "readingpath": "论文结构 摘要 引言 方法 结果 讨论 结论 阅读路径",
    "mindmap": "论文结构 章节标题 摘要 方法 结果 讨论 结论",
}


@dataclass(slots=True)
class RetrievalResult:
    queries: list[str]
    chunks: list[RetrievedChunk]


class HybridRetriever:
    def __init__(self, *, config: RuntimeConfig, embedding_client: EmbeddingClient):
        self.config = config
        self.embedding_client = embedding_client

    def retrieve(
        self,
        *,
        index: IndexedPaper,
        question: str,
        task_type: str,
        agent_name: str | None,
        history: list[ChatMessage],
        rewrite: QueryRewriteResult,
    ) -> RetrievalResult:
        base_query = self.build_base_query(question, task_type, history)
        queries = self._build_retrieval_queries(base_query, rewrite)
        vector_hits = self._vector_hits(index, queries)
        keyword_hits = self._keyword_hits(index, queries)
        anchors = self._merge_results(
            index=index,
            vector_hits=vector_hits,
            keyword_hits=keyword_hits,
            queries=queries,
            agent_name=agent_name,
            section_hint=rewrite.section_hint,
        )
        expanded = self._expand_neighbors(index=index, anchors=anchors)
        selected = self._trim_by_budget(expanded, anchors=anchors)
        return RetrievalResult(queries=queries, chunks=selected)

    def build_base_query(self, question: str, task_type: str, history: list[ChatMessage]) -> str:
        task_seed = TASK_QUERIES.get(task_type, "")
        message = question.strip() or task_seed
        if task_seed and task_seed not in message:
            message = f"{task_seed}\n{message}"
        recent_user_messages = [
            item.content for item in history[-6:] if item.role == "user" and item.content
        ]
        if _looks_context_dependent(question) and recent_user_messages:
            return "\n".join([*recent_user_messages[-2:], message])
        return message

    def _vector_hits(self, index: IndexedPaper, queries: list[str]) -> list[tuple[int, int, float]]:
        hits: list[tuple[int, int, float]] = []
        for query_rank, query in enumerate(queries):
            try:
                query_embedding = self.embedding_client.embed_query(query)
            except Exception:  # noqa: BLE001
                continue
            scored = [
                (chunk.chunk_index, query_rank, dot_product(query_embedding, embedding))
                for chunk, embedding in zip(index.chunks, index.embeddings, strict=True)
            ]
            scored.sort(key=lambda item: item[2], reverse=True)
            hits.extend(scored[: self.config.vector_candidates])
        return hits

    def _keyword_hits(self, index: IndexedPaper, queries: list[str]) -> list[tuple[int, int, float]]:
        hits: list[tuple[int, int, float]] = []
        for query_rank, query in enumerate(queries):
            query_terms = tokenize_for_keyword(query)
            scored = []
            for chunk in index.chunks:
                text = " ".join(
                    [
                        chunk.section_title or "",
                        " ".join(chunk.heading_path),
                        chunk.contextual_prefix,
                        chunk.content,
                    ]
                )
                score = _keyword_score(query_terms, tokenize_for_keyword(text))
                scored.append((chunk.chunk_index, query_rank, score))
            scored.sort(key=lambda item: (item[2], -item[0]), reverse=True)
            hits.extend(scored[: self.config.keyword_candidates])
        return hits

    def _merge_results(
        self,
        *,
        index: IndexedPaper,
        vector_hits: list[tuple[int, int, float]],
        keyword_hits: list[tuple[int, int, float]],
        queries: list[str],
        agent_name: str | None,
        section_hint: list[str],
    ) -> list[RetrievedChunk]:
        records: dict[int, RetrievedChunk] = {}
        hit_query_ranks: dict[int, set[int]] = {}

        for chunk_index, query_rank, score in vector_hits:
            item = records.setdefault(chunk_index, RetrievedChunk(chunk=index.chunks[chunk_index]))
            item.vector_score = max(item.vector_score, score)
            hit_query_ranks.setdefault(chunk_index, set()).add(query_rank)

        for chunk_index, query_rank, score in keyword_hits:
            item = records.setdefault(chunk_index, RetrievedChunk(chunk=index.chunks[chunk_index]))
            item.keyword_score = max(item.keyword_score, score)
            hit_query_ranks.setdefault(chunk_index, set()).add(query_rank)

        combined_query = "\n".join(queries)
        for chunk_index, item in records.items():
            item.structure_boost = self._structure_boost(
                item,
                query=combined_query,
                agent_name=agent_name,
                section_hint=section_hint,
            )
            item.multi_query_boost = min(1.0, len(hit_query_ranks.get(chunk_index, set())) / 3)
            item.final_score = (
                0.60 * item.vector_score
                + 0.22 * item.keyword_score
                + 0.10 * item.structure_boost
                + 0.08 * item.multi_query_boost
            )
            item.is_anchor = True

        ranked = sorted(records.values(), key=lambda item: item.final_score, reverse=True)
        return ranked[: self.config.retrieval_top_k]

    def _expand_neighbors(
        self,
        *,
        index: IndexedPaper,
        anchors: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        window = max(0, self.config.neighbor_window)
        indices: set[int] = set()
        anchor_by_index = {item.chunk.chunk_index: item for item in anchors}
        for item in anchors:
            idx = item.chunk.chunk_index
            indices.add(idx)
            for offset in range(1, window + 1):
                if idx - offset >= 0:
                    indices.add(idx - offset)
                if idx + offset < len(index.chunks):
                    indices.add(idx + offset)
        expanded = []
        for idx in sorted(indices):
            if idx in anchor_by_index:
                expanded.append(anchor_by_index[idx])
            else:
                expanded.append(RetrievedChunk(chunk=index.chunks[idx], final_score=0.0))
        return expanded

    def _trim_by_budget(
        self,
        expanded: list[RetrievedChunk],
        anchors: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        max_tokens = self.config.context_max_tokens
        window = max(0, self.config.neighbor_window)
        anchor_indices = {item.chunk.chunk_index for item in anchors}
        anchor_score_by_index = {item.chunk.chunk_index: item.final_score for item in anchors}
        selected_items: dict[int, RetrievedChunk] = {}
        total = 0

        for item in sorted(anchors, key=lambda value: value.final_score, reverse=True):
            candidate = item
            token_count = candidate.chunk.token_count
            if token_count > max_tokens - total:
                if selected_items:
                    continue
                candidate = _truncate_item_to_budget(item, max_tokens)
                token_count = candidate.chunk.token_count
            if total + token_count > max_tokens:
                continue
            selected_items[candidate.chunk.chunk_index] = candidate
            total += token_count

        def neighbor_priority(item: RetrievedChunk) -> float:
            best = 0.0
            idx = item.chunk.chunk_index
            for offset in range(1, window + 1):
                best = max(
                    best,
                    anchor_score_by_index.get(idx - offset, 0.0),
                    anchor_score_by_index.get(idx + offset, 0.0),
                )
            return best

        neighbor_only = [item for item in expanded if item.chunk.chunk_index not in anchor_indices]
        for item in sorted(neighbor_only, key=neighbor_priority, reverse=True):
            token_count = item.chunk.token_count
            if total + token_count > max_tokens:
                continue
            selected_items[item.chunk.chunk_index] = item
            total += token_count

        return [selected_items[index] for index in sorted(selected_items)]

    def _build_retrieval_queries(
        self,
        base_query: str,
        rewrite: QueryRewriteResult,
    ) -> list[str]:
        raw_queries = [base_query]
        if rewrite.enabled:
            raw_queries.append(rewrite.standalone_query)
            raw_queries.extend(rewrite.retrieval_queries)
            if rewrite.expanded_terms:
                raw_queries.append(" ".join(rewrite.expanded_terms))
        queries = []
        seen = set()
        for item in raw_queries:
            text = clean_query(item or "", max_chars=120)
            if not text or text in seen:
                continue
            queries.append(text)
            seen.add(text)
            if len(queries) >= 1 + max(0, self.config.query_rewrite_max_queries):
                break
        return queries or [base_query]

    @staticmethod
    def _structure_boost(
        item: RetrievedChunk,
        *,
        query: str,
        agent_name: str | None,
        section_hint: list[str],
    ) -> float:
        chunk = item.chunk
        text = " ".join([chunk.section_title or "", " ".join(chunk.heading_path), query]).lower()
        boost = 0.0
        if chunk.section_title and chunk.section_title in query:
            boost += 0.4
        for keyword in AGENT_SECTION_KEYWORDS.get(agent_name or "", ()):
            if keyword.lower() in text:
                boost += 0.2
        for hint in section_hint:
            if hint and hint.lower() in text:
                boost += 0.2
        for keyword in ("结论", "局限", "方法", "样本", "变量", "结果", "讨论", "研究问题"):
            if keyword in query and keyword in text:
                boost += 0.2
        return min(boost, 1.0)


def _keyword_score(query_terms: set[str], chunk_terms: set[str]) -> float:
    if not query_terms or not chunk_terms:
        return 0.0
    overlap = query_terms & chunk_terms
    if not overlap:
        return 0.0
    recall = len(overlap) / len(query_terms)
    precision = len(overlap) / len(chunk_terms)
    return min(1.0, 0.85 * recall + 0.15 * precision)


def _looks_context_dependent(message: str) -> bool:
    stripped = message.strip()
    if len(stripped) <= 12:
        return True
    return bool(re.search(r"(这个|那个|上述|刚才|前面|它|这些|继续|展开)", stripped))


def _truncate_item_to_budget(item: RetrievedChunk, max_tokens: int) -> RetrievedChunk:
    notice = "\n\n[该片段过长，已按上下文预算截断。]"
    content_budget = max(1, max_tokens - estimate_tokens(notice))
    content = _truncate_text_by_estimated_tokens(item.chunk.content, content_budget)
    chunk = replace(
        item.chunk,
        content=f"{content}{notice}",
        token_count=estimate_tokens(f"{content}{notice}"),
    )
    return replace(item, chunk=chunk)


def _truncate_text_by_estimated_tokens(text: str, max_tokens: int) -> str:
    if estimate_tokens(text) <= max_tokens:
        return text
    token_count = estimate_tokens(text)
    chars_per_token = max(1, len(text) // max(1, token_count))
    limit = max(80, max_tokens * chars_per_token)
    snippet = text[:limit].strip()
    while len(snippet) > 1 and estimate_tokens(snippet) > max_tokens:
        snippet = snippet[: max(1, int(len(snippet) * 0.9))].rstrip()
    return snippet
