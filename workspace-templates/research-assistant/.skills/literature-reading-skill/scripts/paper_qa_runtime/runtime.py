from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from paper_qa_runtime.context_builder import ContextBuilder
from paper_qa_runtime.embeddings import EmbeddingClient, OpenAICompatibleEmbeddingClient
from paper_qa_runtime.generation import AnswerGenerator
from paper_qa_runtime.indexing import PaperIndexer
from paper_qa_runtime.llm import ChatClient, OpenAICompatibleChatClient
from paper_qa_runtime.prompts import PromptStore
from paper_qa_runtime.query_rewrite import QueryRewriteService
from paper_qa_runtime.retrieval import HybridRetriever
from paper_qa_runtime.routing import AgentRouter
from paper_qa_runtime.schemas import (
    ChatMessage,
    Citation,
    PaperQAResponse,
    RetrievalChunkTrace,
    RetrievalTrace,
    RuntimeConfig,
)
from paper_qa_runtime.storage import IndexStore, create_index_store
from paper_qa_runtime.text_utils import preview


class PaperQARuntime:
    def __init__(
        self,
        config: RuntimeConfig | None = None,
        *,
        embedding_client: EmbeddingClient | None = None,
        llm_client: ChatClient | None = None,
        index_store: IndexStore | None = None,
    ):
        self.config = config or RuntimeConfig()
        self.embedding_client = embedding_client or OpenAICompatibleEmbeddingClient(self.config)
        self.llm_client = llm_client or OpenAICompatibleChatClient(self.config)
        self.index_store = index_store or create_index_store(self.config)
        self.prompts = PromptStore(self.config)
        self.indexer = PaperIndexer(
            config=self.config,
            embedding_client=self.embedding_client,
            store=self.index_store,
        )
        self.router = AgentRouter(
            config=self.config,
            prompts=self.prompts,
            llm_client=self.llm_client,
        )
        self.query_rewriter = QueryRewriteService(config=self.config, llm_client=self.llm_client)
        self.retriever = HybridRetriever(config=self.config, embedding_client=self.embedding_client)
        self.context_builder = ContextBuilder()
        self.generator = AnswerGenerator(
            config=self.config,
            prompts=self.prompts,
            llm_client=self.llm_client,
        )

    def answer(
        self,
        *,
        paper_md: str,
        history: Sequence[dict[str, Any] | ChatMessage] | None,
        question: str,
        title: str | None = None,
    ) -> PaperQAResponse:
        normalized_history = _normalize_history(history or [])
        index = self.indexer.load_or_build(paper_md=paper_md, title=title)
        agent = self.router.route(title=index.title, question=question, history=normalized_history)
        base_query = self.retriever.build_base_query(question, "chat", normalized_history)
        rewrite = self.query_rewriter.rewrite(
            title=index.title,
            question=question,
            base_query=base_query,
            task_type="chat",
            agent_name=agent,
            history=normalized_history,
        )
        retrieval = self.retriever.retrieve(
            index=index,
            question=question,
            task_type="chat",
            agent_name=agent,
            history=normalized_history,
            rewrite=rewrite,
        )
        context = self.context_builder.build(
            index=index,
            question=question,
            task_type="chat",
            agent_name=agent,
            retrieval=retrieval,
            history=normalized_history,
        )
        answer = self.generator.generate(
            agent=agent,
            context=context,
            question=question,
            history=normalized_history,
        )
        return PaperQAResponse(
            answer=answer,
            agent=agent,
            citations=[
                Citation(
                    chunk_index=item.chunk.chunk_index,
                    page=item.chunk.page_start,
                    section=item.chunk.section_title,
                )
                for item in retrieval.chunks
                if item.is_anchor
            ],
            retrieval=RetrievalTrace(
                queries=retrieval.queries,
                chunks=[
                    RetrievalChunkTrace(
                        chunk_index=item.chunk.chunk_index,
                        section_title=item.chunk.section_title,
                        content_preview=preview(item.chunk.content, 180),
                        vector_score=round(item.vector_score, 6),
                        keyword_score=round(item.keyword_score, 6),
                        final_score=round(item.final_score, 6),
                        is_anchor=item.is_anchor,
                    )
                    for item in retrieval.chunks
                ],
            ),
            trace={
                "paper_hash": index.paper_hash,
                "cache_key": index.cache_key,
                "index_status": index.index_status,
                "chunk_count": len(index.chunks),
                "query_rewrite_enabled": rewrite.enabled,
            },
        )


def _normalize_history(history: Sequence[dict[str, Any] | ChatMessage]) -> list[ChatMessage]:
    normalized = []
    for item in history:
        if isinstance(item, ChatMessage):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.append(ChatMessage.from_mapping(item))
        else:
            raise TypeError(f"Unsupported history item: {type(item).__name__}")
    return normalized
