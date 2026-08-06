from __future__ import annotations

from dataclasses import asdict, dataclass, field
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse


AgentName = Literal["review", "method", "result", "discussion", "general"]
IndexBackend = Literal["memory", "local_file"]
EmbeddingProvider = Literal["openai_compatible", "tei"]
DEFAULT_INNOSPARK_LLM_BASE_URL = "https://innospark-api.aiecnu.net/v1"
DEFAULT_INNOSPARK_LLM_MODEL = "InnoSpark-235B"


def default_prompt_dir() -> Path:
    package_prompt_dir = Path(__file__).resolve().parent / "prompts"
    if package_prompt_dir.exists():
        return package_prompt_dir
    return Path(__file__).resolve().parents[1] / "prompts"


@dataclass(slots=True)
class RuntimeConfig:
    llm_base_url: str = DEFAULT_INNOSPARK_LLM_BASE_URL
    llm_api_key: str = ""
    llm_model: str = DEFAULT_INNOSPARK_LLM_MODEL
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2000
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    embedding_provider: EmbeddingProvider = "openai_compatible"
    embedding_base_url: str = "https://api-inference.modelscope.cn/v1"
    embedding_api_key: str = ""
    embedding_model: str = "Qwen/Qwen3-Embedding-8B"
    embedding_dimensions: int = 4096
    embedding_batch_size: int = 64
    embedding_timeout_seconds: float = 60.0
    embedding_normalize: bool = True
    embedding_send_dimensions: bool = False
    embedding_query_instruction: str = (
        "Given a question about a single academic paper, retrieve relevant passages "
        "from the same paper that answer the question."
    )
    allow_unauthenticated_llm: bool = False
    allow_unauthenticated_embedding: bool = False

    index_backend: IndexBackend = "local_file"
    index_dir: str = ".paper_qa_index"
    prompt_dir: str | None = None

    chunk_target_tokens: int = 700
    chunk_overlap_tokens: int = 120
    chunk_max_tokens: int = 1200
    retrieval_top_k: int = 8
    vector_candidates: int = 30
    keyword_candidates: int = 30
    context_max_tokens: int = 6000
    neighbor_window: int = 1

    query_rewrite_enabled: bool = True
    query_rewrite_max_queries: int = 4
    query_rewrite_max_tokens: int = 300

    routing_use_llm: bool = True
    @property
    def resolved_prompt_dir(self) -> Path:
        return Path(self.prompt_dir).expanduser().resolve() if self.prompt_dir else default_prompt_dir()

    @property
    def resolved_index_dir(self) -> Path:
        return Path(self.index_dir).expanduser().resolve()

    def validate_llm_auth(self) -> None:
        if (
            not self.llm_api_key
            and not self.allow_unauthenticated_llm
            and _requires_api_key(self.llm_base_url)
        ):
            raise ValueError(
                "llm_api_key is required for public LLM providers. "
                "Set llm_api_key in RuntimeConfig/config file, or set "
                "allow_unauthenticated_llm=true only for trusted local/private services."
            )

    def validate_embedding_auth(self) -> None:
        if (
            not self.embedding_api_key
            and not self.allow_unauthenticated_embedding
            and _requires_api_key(self.embedding_base_url)
        ):
            raise ValueError(
                "embedding_api_key is required for public embedding providers. "
                "Set embedding_api_key in RuntimeConfig/config file, or set "
                "allow_unauthenticated_embedding=true only for trusted local/private services."
            )

    def fingerprint_payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "chunk_target_tokens": self.chunk_target_tokens,
            "chunk_overlap_tokens": self.chunk_overlap_tokens,
            "chunk_max_tokens": self.chunk_max_tokens,
            "embedding_provider": self.embedding_provider,
            "embedding_base_url": self.embedding_base_url,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "embedding_normalize": self.embedding_normalize,
            "embedding_send_dimensions": self.embedding_send_dimensions,
        }


def _requires_api_key(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host:
        return True
    lowered = host.lower()
    if lowered in {"localhost"} or lowered.endswith(".local"):
        return False
    try:
        address = ip_address(lowered)
    except ValueError:
        return True
    return not (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
    )


@dataclass(slots=True)
class ChatMessage:
    role: Literal["user", "assistant", "system"]
    content: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ChatMessage":
        role = str(value.get("role") or "user")
        if role not in {"user", "assistant", "system"}:
            role = "user"
        return cls(role=role, content=str(value.get("content") or ""))

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(slots=True)
class PaperChunk:
    chunk_index: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    heading_path: list[str]
    content: str
    contextual_prefix: str
    token_count: int


@dataclass(slots=True)
class IndexedPaper:
    cache_key: str
    paper_hash: str
    title: str
    chunks: list[PaperChunk]
    embeddings: list[list[float]]
    index_status: Literal["hit", "built"]


@dataclass(slots=True)
class RetrievedChunk:
    chunk: PaperChunk
    vector_score: float = 0.0
    keyword_score: float = 0.0
    structure_boost: float = 0.0
    multi_query_boost: float = 0.0
    final_score: float = 0.0
    is_anchor: bool = False


@dataclass(slots=True)
class QueryRewriteResult:
    enabled: bool
    standalone_query: str = ""
    expanded_terms: list[str] = field(default_factory=list)
    section_hint: list[str] = field(default_factory=list)
    retrieval_queries: list[str] = field(default_factory=list)

    @classmethod
    def disabled(cls) -> "QueryRewriteResult":
        return cls(enabled=False)


@dataclass(slots=True)
class Citation:
    chunk_index: int
    page: int | None
    section: str | None


@dataclass(slots=True)
class RetrievalChunkTrace:
    chunk_index: int
    section_title: str | None
    content_preview: str
    vector_score: float
    keyword_score: float
    final_score: float
    is_anchor: bool


@dataclass(slots=True)
class RetrievalTrace:
    queries: list[str]
    chunks: list[RetrievalChunkTrace]


@dataclass(slots=True)
class PaperQAResponse:
    answer: str
    agent: AgentName
    citations: list[Citation]
    retrieval: RetrievalTrace
    trace: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
