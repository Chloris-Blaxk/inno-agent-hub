from __future__ import annotations

from datetime import UTC, datetime

from paper_qa_runtime.chunking import MarkdownChunker
from paper_qa_runtime.embeddings import EmbeddingClient
from paper_qa_runtime.schemas import IndexedPaper, RuntimeConfig
from paper_qa_runtime.storage import IndexStore
from paper_qa_runtime.text_utils import normalize_markdown, stable_hash_payload, stable_hash_text


class PaperIndexer:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        embedding_client: EmbeddingClient,
        store: IndexStore,
    ):
        self.config = config
        self.embedding_client = embedding_client
        self.store = store
        self.chunker = MarkdownChunker(config)

    def load_or_build(self, *, paper_md: str, title: str | None = None) -> IndexedPaper:
        normalized = normalize_markdown(paper_md)
        resolved_title = title or _infer_title(normalized)
        paper_hash = stable_hash_text(normalized)
        cache_key = stable_hash_payload(
            {
                "paper_hash": paper_hash,
                "config": self.config.fingerprint_payload(),
            }
        )
        cached = self.store.load(cache_key)
        if cached:
            return cached

        chunks = self.chunker.chunk(paper_md=normalized, title=resolved_title)
        documents = [f"{chunk.contextual_prefix}\n\n{chunk.content}" for chunk in chunks]
        embeddings = self.embedding_client.embed_documents(documents)
        if len(chunks) != len(embeddings):
            raise RuntimeError("Chunk count and embedding count do not match")
        index = IndexedPaper(
            cache_key=cache_key,
            paper_hash=paper_hash,
            title=resolved_title,
            chunks=chunks,
            embeddings=embeddings,
            index_status="built",
        )
        self.store.save(
            index,
            {
                "schema_version": 1,
                "cache_key": cache_key,
                "paper_hash": paper_hash,
                "title": resolved_title,
                "chunk_count": len(chunks),
                "embedding_provider": self.config.embedding_provider,
                "embedding_model": self.config.embedding_model,
                "embedding_dimensions": self.config.embedding_dimensions,
                "chunk_config": {
                    "target_tokens": self.config.chunk_target_tokens,
                    "overlap_tokens": self.config.chunk_overlap_tokens,
                    "max_tokens": self.config.chunk_max_tokens,
                },
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        return index


def _infer_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "Untitled Paper"
        if stripped:
            return stripped[:80]
    return "Untitled Paper"
