from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from paper_qa_runtime.schemas import RuntimeConfig
from paper_qa_runtime.text_utils import normalize_vector


class EmbeddingClient(Protocol):
    def embed_query(self, query: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class OpenAICompatibleEmbeddingClient:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.config.validate_embedding_auth()

    def embed_query(self, query: str) -> list[float]:
        formatted = f"Instruct: {self.config.embedding_query_instruction}\nQuery: {query.strip()}"
        return self.embed_texts([formatted])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_texts(texts)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        batch_size = max(1, self.config.embedding_batch_size)
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            if self.config.embedding_provider == "tei":
                batch_embeddings = self._embed_tei(batch)
            elif _requires_single_input_embedding(self.config):
                batch_embeddings = []
                for text in batch:
                    batch_embeddings.extend(
                        self._embed_openai_compatible([text], single_input=True)
                    )
            else:
                batch_embeddings = self._embed_openai_compatible(batch)
            embeddings.extend(self._prepare_embedding(item) for item in batch_embeddings)
        return embeddings

    def _embed_openai_compatible(
        self,
        texts: list[str],
        *,
        single_input: bool = False,
    ) -> list[list[float]]:
        url = f"{self.config.embedding_base_url.rstrip('/')}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.config.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.config.embedding_api_key}"
        input_payload: str | list[str] = texts[0] if single_input and len(texts) == 1 else texts
        payload = {
            "model": self.config.embedding_model,
            "input": input_payload,
            "encoding_format": "float",
        }
        if self.config.embedding_send_dimensions:
            payload["dimensions"] = self.config.embedding_dimensions
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.config.embedding_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                "Embedding request failed: "
                f"status={response.status_code}, body={_format_payload(response.text)}"
            ) from exc
        return self._parse_openai_compatible_payload(response.json())

    @staticmethod
    def _parse_openai_compatible_payload(payload: Any) -> list[list[float]]:
        if not isinstance(payload, dict):
            raise RuntimeError(f"Embedding response has invalid type: {type(payload).__name__}")
        error = (
            payload.get("error")
            or payload.get("errors")
            or payload.get("message")
            or payload.get("Message")
        )
        if error:
            raise RuntimeError(f"Embedding service returned error: {error}")
        data = payload.get("data")
        if not isinstance(data, list):
            raise RuntimeError(
                "Embedding response missing data list. "
                f"Raw response preview: {_format_payload(payload)}"
            )
        sorted_data = sorted(
            data,
            key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
        )
        embeddings = []
        for item in sorted_data:
            if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                raise RuntimeError("Embedding response item missing embedding vector")
            embeddings.append(item["embedding"])
        return embeddings

    def _embed_tei(self, texts: list[str]) -> list[list[float]]:
        url = self.config.embedding_base_url.rstrip("/")
        if not url.endswith("/embed"):
            url = f"{url}/embed"
        headers = {}
        if self.config.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.config.embedding_api_key}"
        response = httpx.post(
            url,
            json={"inputs": texts},
            headers=headers,
            timeout=self.config.embedding_timeout_seconds,
        )
        response.raise_for_status()
        return self._parse_tei_payload(response.json())

    @staticmethod
    def _parse_tei_payload(payload: Any) -> list[list[float]]:
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            return payload
        if isinstance(payload, dict):
            for key in ("embeddings", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    if value and isinstance(value[0], dict) and "embedding" in value[0]:
                        return [item["embedding"] for item in value]
                    if value and isinstance(value[0], list):
                        return value
        raise RuntimeError("Cannot parse TEI embedding response")

    def _prepare_embedding(self, embedding: list[float]) -> list[float]:
        dimensions = self.config.embedding_dimensions
        if len(embedding) != dimensions:
            raise RuntimeError(
                f"Embedding dimensions mismatch: got {len(embedding)}, expected {dimensions}. "
                "Adjust embedding_dimensions, or enable dimension selection on the provider."
            )
        vector = [float(value) for value in embedding]
        if self.config.embedding_normalize:
            vector = normalize_vector(vector)
        return vector


def _format_payload(payload: Any, *, limit: int = 800) -> str:
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit]}..."


def _requires_single_input_embedding(config: RuntimeConfig) -> bool:
    base_url = config.embedding_base_url.lower()
    return (
        "modelscope" in base_url
        or "dashscope" in base_url
        or "aliyuncs" in base_url
    )
