from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def estimate_tokens(text: str) -> int:
    cjk_count = len(CJK_PATTERN.findall(text))
    word_count = len(WORD_PATTERN.findall(text))
    other_count = max(0, len(text) - cjk_count)
    return max(1, math.ceil(cjk_count * 0.9 + word_count * 1.2 + other_count * 0.08))


def normalize_markdown(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def stable_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_hash_payload(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return stable_hash_text(raw)


def preview(text: str | None, limit: int = 160) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def dot_product(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


def extract_json_object(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    return match.group(1) if match else text


def clean_query(value: str, *, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = text.strip("`，。；;")
    return text[:max_chars]


def tokenize_for_keyword(text: str) -> set[str]:
    lowered = text.lower()
    terms = set(WORD_PATTERN.findall(lowered))
    cjk_chars = CJK_PATTERN.findall(text)
    terms.update(cjk_chars)
    terms.update("".join(cjk_chars[i : i + 2]) for i in range(max(0, len(cjk_chars) - 1)))
    return {item for item in terms if item.strip()}
