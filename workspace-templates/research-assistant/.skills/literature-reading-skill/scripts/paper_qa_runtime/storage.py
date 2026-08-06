from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from paper_qa_runtime.schemas import IndexedPaper, PaperChunk, RuntimeConfig

COMPLETE_MARKER = ".complete"


class IndexStore(Protocol):
    def load(self, cache_key: str) -> IndexedPaper | None: ...

    def save(self, index: IndexedPaper, metadata: dict) -> None: ...


class MemoryIndexStore:
    def __init__(self):
        self._items: dict[str, IndexedPaper] = {}
        self._metadata: dict[str, dict] = {}

    def load(self, cache_key: str) -> IndexedPaper | None:
        item = self._items.get(cache_key)
        if not item:
            return None
        return IndexedPaper(
            cache_key=item.cache_key,
            paper_hash=item.paper_hash,
            title=item.title,
            chunks=item.chunks,
            embeddings=item.embeddings,
            index_status="hit",
        )

    def save(self, index: IndexedPaper, metadata: dict) -> None:
        self._items[index.cache_key] = index
        self._metadata[index.cache_key] = metadata


class LocalFileIndexStore:
    def __init__(self, config: RuntimeConfig):
        self.index_dir = config.resolved_index_dir

    def load(self, cache_key: str) -> IndexedPaper | None:
        path = self._path(cache_key)
        meta_file = path / "meta.json"
        chunks_file = path / "chunks.jsonl"
        embeddings_file = path / "embeddings.jsonl"
        complete_file = path / COMPLETE_MARKER
        if (
            not complete_file.exists()
            or not meta_file.exists()
            or not chunks_file.exists()
            or not embeddings_file.exists()
        ):
            return None
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        chunks = [
            PaperChunk(**json.loads(line))
            for line in chunks_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        embeddings = [
            [float(value) for value in json.loads(line)]
            for line in embeddings_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(chunks) != len(embeddings):
            return None
        return IndexedPaper(
            cache_key=cache_key,
            paper_hash=meta["paper_hash"],
            title=meta.get("title") or "",
            chunks=chunks,
            embeddings=embeddings,
            index_status="hit",
        )

    def save(self, index: IndexedPaper, metadata: dict) -> None:
        path = self._path(index.cache_key)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.index_dir / f".{index.cache_key}.{uuid.uuid4().hex}.tmp"
        temp_path.mkdir()
        try:
            (temp_path / "meta.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _write_jsonl(temp_path / "chunks.jsonl", [asdict(chunk) for chunk in index.chunks])
            _write_jsonl(temp_path / "embeddings.jsonl", index.embeddings)
            (temp_path / COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
            self._promote_temp_cache(temp_path=temp_path, path=path)
        finally:
            if temp_path.exists():
                shutil.rmtree(temp_path, ignore_errors=True)

    def _path(self, cache_key: str) -> Path:
        return self.index_dir / cache_key

    @staticmethod
    def _promote_temp_cache(*, temp_path: Path, path: Path) -> None:
        if path.exists() and (path / COMPLETE_MARKER).exists():
            return
        if path.exists():
            shutil.rmtree(path)
        try:
            temp_path.replace(path)
        except OSError:
            if path.exists() and (path / COMPLETE_MARKER).exists():
                return
            raise


def create_index_store(config: RuntimeConfig) -> IndexStore:
    if config.index_backend == "memory":
        return MemoryIndexStore()
    return LocalFileIndexStore(config)


def _write_jsonl(path: Path, rows: list) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
