from __future__ import annotations

import re

from paper_qa_runtime.schemas import PaperChunk, RuntimeConfig
from paper_qa_runtime.text_utils import estimate_tokens, normalize_markdown


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class MarkdownChunker:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def chunk(self, *, paper_md: str, title: str) -> list[PaperChunk]:
        markdown = normalize_markdown(paper_md)
        sections = self._parse_sections(markdown)
        chunks: list[PaperChunk] = []
        for section in sections:
            chunks.extend(self._chunk_section(title=title, section=section, start_index=len(chunks)))
        if not chunks and markdown.strip():
            chunks.append(
                PaperChunk(
                    chunk_index=0,
                    page_start=None,
                    page_end=None,
                    section_title=None,
                    heading_path=[],
                    content=markdown.strip(),
                    contextual_prefix=self._prefix(title, []),
                    token_count=estimate_tokens(markdown),
                )
            )
        return chunks

    @staticmethod
    def _parse_sections(markdown: str) -> list[dict]:
        sections: list[dict] = []
        heading_stack: list[str] = []
        current_lines: list[str] = []
        current_heading_path: list[str] = []

        def flush() -> None:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append(
                    {
                        "heading_path": current_heading_path[:],
                        "section_title": current_heading_path[-1] if current_heading_path else None,
                        "content": content,
                    }
                )
            current_lines.clear()

        for line in markdown.splitlines():
            match = HEADING_PATTERN.match(line)
            if match:
                flush()
                level = len(match.group(1))
                title = match.group(2).strip()
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(title)
                current_heading_path = heading_stack[:]
                current_lines.append(line)
                continue
            current_lines.append(line)

        flush()
        return sections

    def _chunk_section(self, *, title: str, section: dict, start_index: int) -> list[PaperChunk]:
        paragraphs = []
        for paragraph in self._split_paragraphs(section["content"]):
            paragraphs.extend(self._split_oversized_block(paragraph))
        chunks: list[PaperChunk] = []
        current: list[str] = []
        current_tokens = 0
        target_tokens = max(1, self.config.chunk_target_tokens)
        max_tokens = max(target_tokens, self.config.chunk_max_tokens)
        overlap_tokens = max(0, self.config.chunk_overlap_tokens)

        def emit() -> None:
            nonlocal current, current_tokens
            content = "\n\n".join(current).strip()
            if not content:
                return
            chunks.append(
                PaperChunk(
                    chunk_index=start_index + len(chunks),
                    page_start=None,
                    page_end=None,
                    section_title=section["section_title"],
                    heading_path=section["heading_path"],
                    content=content,
                    contextual_prefix=self._prefix(title, section["heading_path"]),
                    token_count=estimate_tokens(content),
                )
            )
            overlap: list[str] = []
            overlap_count = 0
            for paragraph in reversed(current):
                tokens = estimate_tokens(paragraph)
                if overlap_count + tokens > overlap_tokens:
                    break
                overlap.insert(0, paragraph)
                overlap_count += tokens
            current = overlap
            current_tokens = overlap_count

        for paragraph in paragraphs:
            paragraph_tokens = estimate_tokens(paragraph)
            if current and current_tokens + paragraph_tokens > target_tokens:
                emit()
                if current and current_tokens + paragraph_tokens > max_tokens:
                    current = []
                    current_tokens = 0
            current.append(paragraph)
            current_tokens += paragraph_tokens
            if current_tokens >= target_tokens * 1.3:
                emit()

        if current:
            emit()
        return chunks

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        if blocks:
            return blocks
        return [text.strip()] if text.strip() else []

    def _split_oversized_block(self, text: str) -> list[str]:
        max_tokens = max(self.config.chunk_target_tokens, self.config.chunk_max_tokens)
        if estimate_tokens(text) <= max_tokens:
            return [text]
        overlap_tokens = min(self.config.chunk_overlap_tokens, max_tokens // 4)
        pieces: list[str] = []
        current: list[str] = []
        current_tokens = 0

        def emit() -> None:
            nonlocal current, current_tokens
            content = "".join(current).strip()
            if content:
                pieces.append(content)
            overlap: list[str] = []
            overlap_count = 0
            for unit in reversed(current):
                tokens = estimate_tokens(unit)
                if overlap_count + tokens > overlap_tokens:
                    break
                overlap.insert(0, unit)
                overlap_count += tokens
            current = overlap
            current_tokens = overlap_count

        for unit in self._sentence_units(text):
            unit_tokens = estimate_tokens(unit)
            if unit_tokens > max_tokens:
                if current:
                    emit()
                    current = []
                    current_tokens = 0
                pieces.extend(_split_by_estimated_tokens(unit, max_tokens, overlap_tokens))
                continue
            if current and current_tokens + unit_tokens > max_tokens:
                emit()
                if current and current_tokens + unit_tokens > max_tokens:
                    current = []
                    current_tokens = 0
            current.append(unit)
            current_tokens += unit_tokens

        if current:
            emit()
        return pieces or [text.strip()]

    @staticmethod
    def _sentence_units(text: str) -> list[str]:
        units = [
            unit
            for unit in re.split(r"(?<=[。！？!?；;])|(?<=\.)\s+", text)
            if unit and unit.strip()
        ]
        return units or [text]

    @staticmethod
    def _prefix(title: str, heading_path: list[str]) -> str:
        if heading_path:
            path = " > ".join(heading_path)
            return f"本文题为《{title}》。该片段位于“{path}”。"
        return f"本文题为《{title}》。"


def _split_by_estimated_tokens(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    token_count = estimate_tokens(text)
    chars_per_token = max(1, len(text) // max(1, token_count))
    window_chars = max(200, max_tokens * chars_per_token)
    overlap_chars = min(window_chars // 3, max(0, overlap_tokens * chars_per_token))
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + window_chars)
        while end > start + 1 and estimate_tokens(text[start:end]) > max_tokens:
            end = start + max(1, int((end - start) * 0.9))
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = end - overlap_chars
        start = next_start if next_start > start else end
    return pieces
