#!/usr/bin/env python3
"""Policy-controlled MCP stdio server for the PedaScope paper KB API.

The upstream KB can return copyrighted article text. This server intentionally
exposes only tool results derived from metadata/retrieval signals and never
returns full text, raw snippets, raw embeddings, or upstream original_doc_id
values to MCP clients.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "pedascope-kb-mcp"
SERVER_VERSION = "0.2.2"

DEFAULT_BASE_URL = "http://172.23.40.128:8000"
BASE_URL = os.environ.get("PEDASCOPE_KB_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
HTTP_TIMEOUT_SECONDS = float(os.environ.get("PEDASCOPE_KB_TIMEOUT_SECONDS", "30"))

DEFAULT_TOP_K = 20
MAX_TOP_K = 200
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

PAPER_CACHE_TTL_SECONDS = int(os.environ.get("PEDASCOPE_PAPER_CACHE_TTL_SECONDS", "86400"))

PAPER_CACHE: dict[str, dict[str, Any]] = {}
SOURCE_TO_SAFE_ID: dict[str, str] = {}


def write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def reply(message_id: Any, result: dict[str, Any]) -> None:
    write_message({"jsonrpc": "2.0", "id": message_id, "result": result})


def error(message_id: Any, code: int, message: str) -> None:
    write_message({"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}})


def text_result(text: str, *, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return result


def json_result(payload: Any) -> dict[str, Any]:
    result = text_result(json.dumps(payload, ensure_ascii=False, indent=2))
    result["structuredContent"] = payload if isinstance(payload, dict) else {"result": payload}
    return result


def endpoint(path: str) -> str:
    return f"{BASE_URL}/{path.lstrip('/')}"


def post_json(path: str, payload: dict[str, Any]) -> Any:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint(path),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {endpoint(path)}: {response_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {endpoint(path)}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from {endpoint(path)}: {exc}") from exc


def now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def optional_int(
    arguments: dict[str, Any],
    key: str,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{key} must be an integer <= {maximum}")
    return value


def optional_int_alias(
    arguments: dict[str, Any],
    keys: tuple[str, ...],
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    for key in keys:
        if key in arguments:
            return optional_int(arguments, key, default, minimum, maximum)
    return default


def optional_bool(arguments: dict[str, Any], key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean when provided")
    return value


def optional_year(arguments: dict[str, Any], key: str) -> int | None:
    value = arguments.get(key)
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer year when provided")
    if value < 1800 or value > 2200:
        raise ValueError(f"{key} must be between 1800 and 2200")
    return value


def require_text(arguments: dict[str, Any], keys: tuple[str, ...], label: str) -> str:
    for key in keys:
        value = normalize_space(arguments.get(key))
        if value:
            return value
    raise ValueError(f"{label} is required and must be a non-empty string")


def split_people(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_space(item) for item in value if normalize_space(item)]
    text = normalize_space(value)
    if not text:
        return []
    delimiter = "|" if "|" in text else ";"
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def split_keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_space(item) for item in value if normalize_space(item)]
    text = normalize_space(value)
    if not text:
        return []
    parts = re.split(r"[|;,，；]", text)
    return [part.strip() for part in parts if part.strip()]


def int_or_none(value: Any) -> int | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metadata_value(record: dict[str, Any], *keys: str) -> Any:
    metadata = record.get("metadata")
    for key in keys:
        if record.get(key) not in (None, ""):
            return record.get(key)
        if isinstance(metadata, dict) and metadata.get(key) not in (None, ""):
            return metadata.get(key)
    return None


def cleanup_cache() -> None:
    if not PAPER_CACHE:
        return
    cutoff = time.time() - PAPER_CACHE_TTL_SECONDS
    expired = [paper_id for paper_id, entry in PAPER_CACHE.items() if entry["created_at"] < cutoff]
    for paper_id in expired:
        entry = PAPER_CACHE.pop(paper_id, None)
        if entry:
            SOURCE_TO_SAFE_ID.pop(entry["source_key"], None)


def source_key_for(record: dict[str, Any]) -> str:
    for key in ("original_doc_id", "id", "doi", "title"):
        value = normalize_space(record.get(key))
        if value:
            return f"{key}:{value}"
    return "generated:" + secrets.token_urlsafe(16)


def register_paper(record: dict[str, Any]) -> str:
    cleanup_cache()
    source_key = source_key_for(record)
    existing = SOURCE_TO_SAFE_ID.get(source_key)
    if existing:
        PAPER_CACHE[existing]["record"] = record
        PAPER_CACHE[existing]["created_at"] = time.time()
        return existing

    safe_id = "paper_" + secrets.token_urlsafe(12).replace("-", "_")
    SOURCE_TO_SAFE_ID[source_key] = safe_id
    PAPER_CACHE[safe_id] = {
        "created_at": time.time(),
        "record": record,
        "source_key": source_key,
        "original_doc_id": normalize_space(record.get("original_doc_id")) or None,
    }
    return safe_id


def policy(warnings: list[str] | None = None) -> dict[str, Any]:
    base_warnings = [
        "raw_full_text_not_exposed",
        "raw_snippets_not_exposed",
        "original_doc_id_not_exposed",
        "raw_embeddings_not_exposed",
        "generated_summaries_require_human_verification",
    ]
    return {
        "rights_basis": "derived_only",
        "raw_text_exposed_chars": 0,
        "full_text_exposed": False,
        "quote_budget_remaining": 0,
        "must_human_verify": True,
        "warnings": base_warnings + (warnings or []),
    }


def common_response(
    data: dict[str, Any],
    *,
    retrieval_mode: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "request_id": "req_" + secrets.token_urlsafe(12).replace("-", "_"),
        "timestamp": now_rfc3339(),
        "policy": policy(warnings),
        "trace": {
            "tool_version": SERVER_VERSION,
            "retrieval_mode": retrieval_mode,
            "source": "PedaScope KB public API",
        },
        **data,
    }


def source_db(record: dict[str, Any]) -> str:
    value = metadata_value(record, "source_db", "source", "database", "collection")
    return normalize_space(value) or "PedaScope KB"


def generated_summary(record: dict[str, Any]) -> str:
    title = normalize_space(record.get("title"))
    keywords = split_keywords(record.get("keyword") or metadata_value(record, "keywords"))
    journal = normalize_space(record.get("journal") or metadata_value(record, "venue", "journal"))
    year = normalize_space(record.get("year"))

    parts: list[str] = []
    if title:
        parts.append(f"该文献与“{title}”相关")
    else:
        parts.append("该文献与当前检索主题相关")
    if keywords:
        parts.append("关键词信号包括" + "、".join(keywords[:5]))
    if journal or year:
        source_bits = "，".join(bit for bit in (journal, year) if bit)
        parts.append(f"来源信息为{source_bits}")
    parts.append("该摘要为系统根据题录和检索信号生成的非逐字摘要，未透传原始摘要或全文")
    return "；".join(parts) + "。"


def text_availability(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "full_text_returned": False,
        "raw_text_exposed_chars": 0,
        "note": "全文和原始片段只允许内部受控使用，不通过 MCP 返回。",
        "status": "not_probed",
        "internal_lookup": "disabled_by_mcp_policy",
    }


def sanitized_metadata(record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    allowed_keys = (
        "publisher",
        "language",
        "document_type",
        "volume",
        "issue",
        "pages",
        "issn",
        "isbn",
        "source",
        "database",
        "collection",
    )
    safe: dict[str, Any] = {}
    for key in allowed_keys:
        value = metadata.get(key, record.get(key))
        if value not in (None, "", [], {}):
            safe[key] = value
    return safe


def sanitize_paper(record: dict[str, Any], *, include_text_availability: bool = False) -> dict[str, Any]:
    paper_id = register_paper(record)
    journal = normalize_space(record.get("journal") or metadata_value(record, "venue", "journal"))
    safe: dict[str, Any] = {
        "paper_id": paper_id,
        "title": normalize_space(record.get("title")),
        "abstract": generated_summary(record),
        "abstract_type": "generated_non_verbatim",
        "authors": split_people(record.get("author") or record.get("authors")),
        "year": normalize_space(record.get("year")),
        "journal": journal,
        "venue": journal,
        "doi": normalize_space(record.get("doi")),
        "keywords": split_keywords(record.get("keyword") or metadata_value(record, "keywords")),
        "citation_count": int_or_none(record.get("citation")),
        "relevance_score": float_or_none(record.get("score")),
        "source_db": source_db(record),
    }
    if include_text_availability:
        safe["text_availability"] = text_availability(record)
    return safe


def extract_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        results = payload.get("results", [])
    else:
        results = payload
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def reject_public_filter_expr(arguments: dict[str, Any]) -> None:
    if "filter_expr" not in arguments:
        return
    value = arguments.get("filter_expr")
    if value in (None, ""):
        return
    raise ValueError(
        "filter_expr is disabled on public MCP tools. Use search_by_domain structured filters "
        "such as year_from, year_to, journal, must_have_doi, or citation_min."
    )


def run_search(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    upstream = post_json("search", payload)
    if not isinstance(upstream, dict):
        upstream = {"results": upstream}
    return upstream, extract_results(upstream)


def search_response(payload: dict[str, Any], *, retrieval_mode: str, warnings: list[str] | None = None) -> dict[str, Any]:
    upstream, raw_results = run_search(payload)
    items = [sanitize_paper(item, include_text_availability=False) for item in raw_results]
    return common_response(
        {
            "query_text": payload["query_text"],
            "topk": payload["topk"],
            "page": payload["page"],
            "page_size": payload["page_size"],
            "items": items,
            "results": items,
            "pagination": {
                "has_next": bool(upstream.get("has_next")),
                "has_previous": bool(upstream.get("has_previous")),
                "returned": len(items),
            },
            "coverage_note": "返回为安全题录和系统生成摘要；未返回原始摘要、全文、片段、original_doc_id 或向量。",
        },
        retrieval_mode=retrieval_mode,
        warnings=warnings,
    )


def handle_search_by_keywords(arguments: dict[str, Any]) -> dict[str, Any]:
    keywords = arguments.get("keywords")
    if isinstance(keywords, list):
        query_text = " ".join(normalize_space(item) for item in keywords if normalize_space(item))
    else:
        query_text = normalize_space(keywords)
    if not query_text:
        raise ValueError("keywords is required and must be a non-empty string or array")
    reject_public_filter_expr(arguments)

    payload = {
        "query_text": query_text,
        "topk": optional_int_alias(arguments, ("topk", "top_k"), DEFAULT_TOP_K, 1, MAX_TOP_K),
        "page": optional_int(arguments, "page", 1, 1),
        "page_size": optional_int(arguments, "page_size", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE),
    }
    return json_result(search_response(payload, retrieval_mode="keyword"))


def handle_search_by_topic(arguments: dict[str, Any]) -> dict[str, Any]:
    topic = require_text(arguments, ("topic", "research_question", "query_text", "query"), "topic")
    payload = {
        "query_text": topic,
        "topk": optional_int_alias(arguments, ("topk", "top_k"), DEFAULT_TOP_K, 1, MAX_TOP_K),
        "page": optional_int(arguments, "page", 1, 1),
        "page_size": optional_int(arguments, "page_size", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE),
    }
    return json_result(search_response(payload, retrieval_mode="vector_internal"))


def build_domain_query(arguments: dict[str, Any]) -> str:
    keys = (
        "stage",
        "subject",
        "research_domain",
        "domain",
        "research_method",
        "method",
        "topic",
        "keywords",
    )
    parts: list[str] = []
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, list):
            parts.extend(normalize_space(item) for item in value if normalize_space(item))
        elif normalize_space(value):
            parts.append(normalize_space(value))
    query_text = " ".join(parts)
    if not query_text:
        raise ValueError("at least one domain condition is required")
    return query_text


def filter_by_domain(items: list[dict[str, Any]], arguments: dict[str, Any]) -> list[dict[str, Any]]:
    year_from = optional_year(arguments, "year_from")
    year_to = optional_year(arguments, "year_to")
    must_have_doi = optional_bool(arguments, "must_have_doi", False)
    journal_filter = normalize_space(arguments.get("journal") or arguments.get("venue")).lower()
    citation_min = optional_int(arguments, "citation_min", 0, 0) if "citation_min" in arguments else None

    filtered: list[dict[str, Any]] = []
    for item in items:
        year = int_or_none(item.get("year"))
        if year_from is not None and (year is None or year < year_from):
            continue
        if year_to is not None and (year is None or year > year_to):
            continue
        if must_have_doi and not item.get("doi"):
            continue
        if journal_filter and journal_filter not in normalize_space(item.get("journal")).lower():
            continue
        if citation_min is not None:
            citation_count = item.get("citation_count")
            if citation_count is None or citation_count < citation_min:
                continue
        filtered.append(item)
    return filtered


def handle_search_by_domain(arguments: dict[str, Any]) -> dict[str, Any]:
    query_text = build_domain_query(arguments)
    topk = optional_int_alias(arguments, ("topk", "top_k"), 80, 1, MAX_TOP_K)
    page = optional_int(arguments, "page", 1, 1)
    page_size = optional_int(arguments, "page_size", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    payload: dict[str, Any] = {
        "query_text": query_text,
        "topk": topk,
        "page": 1,
        "page_size": min(MAX_PAGE_SIZE, max(page_size, topk if topk <= MAX_PAGE_SIZE else MAX_PAGE_SIZE)),
    }
    if "citation_min" in arguments:
        citation_min = optional_int(arguments, "citation_min", 0, 0)
        payload["filter_expr"] = f"citation >= {citation_min}"

    _, raw_results = run_search(payload)
    all_items = [sanitize_paper(item, include_text_availability=False) for item in raw_results]
    filtered = filter_by_domain(all_items, arguments)
    start = (page - 1) * page_size
    page_items = filtered[start : start + page_size]
    return json_result(
        common_response(
            {
                "query_text": query_text,
                "applied_filters": {
                    key: value
                    for key, value in arguments.items()
                    if key
                    in {
                        "stage",
                        "subject",
                        "research_domain",
                        "domain",
                        "research_method",
                        "method",
                        "year_from",
                        "year_to",
                        "journal",
                        "venue",
                        "must_have_doi",
                        "citation_min",
                    }
                },
                "items": page_items,
                "results": page_items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "returned": len(page_items),
                    "matched_before_pagination": len(filtered),
                    "has_next": start + page_size < len(filtered),
                },
                "coverage_note": "学段、学科、领域、方法等文本条件会进入检索 query；年份、DOI、期刊和引用量在安全结果上二次过滤。",
            },
            retrieval_mode="domain_filtered_vector_internal",
        )
    )


def require_cached_paper(arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    paper_id = normalize_space(arguments.get("paper_id") or arguments.get("paperId"))
    if not paper_id:
        raise ValueError("paper_id is required. Use the opaque paper_id returned by a search tool.")
    cleanup_cache()
    entry = PAPER_CACHE.get(paper_id)
    if not entry:
        raise ValueError("unknown paper_id. Run search_by_keywords/search_by_topic/search_by_domain first and use returned paper_id.")
    record = entry.get("record")
    if not isinstance(record, dict):
        raise ValueError("cached paper record is invalid. Run search again.")
    return paper_id, record


def handle_get_paper(arguments: dict[str, Any]) -> dict[str, Any]:
    if "probe_text_availability" in arguments:
        raise ValueError("probe_text_availability is disabled by MCP content policy.")
    paper_id, record = require_cached_paper(arguments)
    paper = sanitize_paper(record, include_text_availability=False)
    paper["metadata"] = sanitized_metadata(record)
    paper["text_availability"] = text_availability(record)
    return json_result(
        common_response(
            {
                "paper_id": paper_id,
                "paper": paper,
                "bibliographic_record": {
                    "title": paper["title"],
                    "authors": paper["authors"],
                    "year": paper["year"],
                    "journal": paper["journal"],
                    "doi": paper["doi"],
                    "keywords": paper["keywords"],
                    "source_db": paper["source_db"],
                    "metadata": paper["metadata"],
                },
            },
            retrieval_mode="cached_metadata",
            warnings=["raw_abstract_suppressed_generated_summary_returned"],
        )
    )


def citation_type(record: dict[str, Any]) -> str:
    if normalize_space(record.get("journal") or metadata_value(record, "journal", "venue")):
        return "J"
    return "Z"


def format_gbt7714(record: dict[str, Any]) -> str:
    title = normalize_space(record.get("title")) or "[题名不详]"
    authors = split_people(record.get("author") or record.get("authors"))
    if not authors:
        author_text = "[作者不详]"
    elif len(authors) > 3:
        author_text = ", ".join(authors[:3]) + ", 等"
    else:
        author_text = ", ".join(authors)
    year = normalize_space(record.get("year")) or "[年份不详]"
    journal = normalize_space(record.get("journal") or metadata_value(record, "journal", "venue"))
    doi = normalize_space(record.get("doi"))
    doc_type = citation_type(record)
    citation = f"{author_text}. {title}[{doc_type}]."
    if journal:
        citation += f" {journal}, {year}."
    else:
        citation += f" {year}."
    if doi:
        citation += f" DOI: {doi}."
    return citation


def handle_get_citation(arguments: dict[str, Any]) -> dict[str, Any]:
    paper_id, record = require_cached_paper(arguments)
    fields = {
        "authors": split_people(record.get("author") or record.get("authors")),
        "title": normalize_space(record.get("title")),
        "year": normalize_space(record.get("year")),
        "journal": normalize_space(record.get("journal") or metadata_value(record, "journal", "venue")),
        "doi": normalize_space(record.get("doi")),
        "document_type": citation_type(record),
        "source_db": source_db(record),
    }
    return json_result(
        common_response(
            {
                "paper_id": paper_id,
                "style": "GB/T 7714-2015 draft",
                "fields": fields,
                "formatted_reference": format_gbt7714(record),
                "verification_note": "该引用为题录字段生成的草案；正式入文前请核验作者顺序、卷期页码和 DOI。",
            },
            retrieval_mode="cached_metadata",
        )
    )


def lexical_terms(text: str) -> set[str]:
    text = text.lower()
    english = re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "are",
        "was",
        "were",
        "研究",
        "论文",
    }
    return {term for term in english + cjk if term not in stopwords}


def support_strength(claim: str, record: dict[str, Any]) -> tuple[str, float]:
    claim_terms = lexical_terms(claim)
    haystack = " ".join(
        normalize_space(value)
        for value in (
            record.get("title"),
            record.get("abstract"),
            record.get("keyword"),
            record.get("journal"),
        )
        if normalize_space(value)
    )
    source_terms = lexical_terms(haystack)
    if not claim_terms or not source_terms:
        return "weak", 0.0
    overlap_ratio = len(claim_terms & source_terms) / max(1, len(claim_terms))
    if overlap_ratio >= 0.35:
        return "strong", round(overlap_ratio, 3)
    if overlap_ratio >= 0.18:
        return "moderate", round(overlap_ratio, 3)
    return "weak", round(overlap_ratio, 3)


def handle_trace_claim(arguments: dict[str, Any]) -> dict[str, Any]:
    claim = require_text(arguments, ("claim", "claim_text"), "claim")
    domain_hint = normalize_space(arguments.get("domain_hint"))
    query_text = f"{claim} {domain_hint}".strip()
    top_k = optional_int_alias(arguments, ("topk", "top_k"), 10, 1, MAX_TOP_K)
    payload = {"query_text": query_text, "topk": top_k, "page": 1, "page_size": min(top_k, MAX_PAGE_SIZE)}
    _, raw_results = run_search(payload)

    matches: list[dict[str, Any]] = []
    for record in raw_results:
        paper = sanitize_paper(record, include_text_availability=False)
        strength, overlap = support_strength(claim, record)
        matches.append(
            {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "authors": paper["authors"],
                "year": paper["year"],
                "journal": paper["journal"],
                "doi": paper["doi"],
                "relation": "support_or_related_candidate",
                "support_strength": strength,
                "overlap_signal": overlap,
                "evidence_note": "该候选来源与 claim 在检索语义、题录、关键词或内部摘要信号上相关；未返回原文证据片段。",
                "raw_evidence_returned": False,
            }
        )

    verdict = "insufficient_evidence"
    if any(item["support_strength"] == "strong" for item in matches):
        verdict = "candidate_support_found"
    elif matches:
        verdict = "related_candidates_found"

    return json_result(
        common_response(
            {
                "claim": claim,
                "verdict": verdict,
                "matches": matches,
                "notes_for_writer": [
                    "这些结果适合做候选引用或进一步核验入口。",
                    "本工具不提供原文句子、全文片段或可拼接 snippet；正式引用前需要人工或合法全文渠道确认。",
                ],
            },
            retrieval_mode="claim_trace_vector_internal",
            warnings=["claim_trace_is_candidate_level_not_verbatim_evidence"],
        )
    )


def handle_get_article_content_disabled(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = common_response(
        {
            "error": "get_article_content is disabled by copyright policy.",
            "replacement_tools": ["get_paper", "trace_claim", "get_citation"],
            "explanation": "对外 MCP 不返回完整论文、原文段落、原始 snippet 或 original_doc_id。需要基于内容的判断时，请使用二次加工后的 trace_claim/get_paper。",
        },
        retrieval_mode="blocked_raw_content",
        warnings=["blocked_attempt_to_fetch_raw_article_content"],
    )
    return text_result(json.dumps(payload, ensure_ascii=False, indent=2), is_error=True)


def safe_error_text(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    return "tool execution failed; upstream or internal details are withheld by MCP content policy."


def handle_health(arguments: dict[str, Any]) -> dict[str, Any]:
    return json_result(
        common_response(
            {
                "server": SERVER_NAME,
                "version": SERVER_VERSION,
                "base_url": BASE_URL,
                "timeout_seconds": HTTP_TIMEOUT_SECONDS,
                "content_policy": {
                    "tool_only_catalog": True,
                    "get_article_content_exposed": False,
                    "full_text_returned": False,
                    "raw_snippets_returned": False,
                    "original_doc_id_returned": False,
                    "opaque_paper_id_cache_ttl_seconds": PAPER_CACHE_TTL_SECONDS,
                    "text_availability_probe": "disabled_by_mcp_policy",
                },
            },
            retrieval_mode="local_config",
        )
    )


def handle_verify_citation(arguments: dict[str, Any]) -> dict[str, Any]:
    """Verify if a citation reference exists in the PedaScope KB whitelist."""
    title = normalize_space(arguments.get("title"))
    authors_input = split_people(arguments.get("author") or arguments.get("authors"))
    year = normalize_space(arguments.get("year"))
    journal = normalize_space(arguments.get("journal") or arguments.get("venue"))
    doi = normalize_space(arguments.get("doi"))

    if not any([title, authors_input, year, journal, doi]):
        raise ValueError("At least one of title, author(s), year, journal, or doi is required")

    query_parts: list[str] = []
    if title:
        query_parts.append(title)
    if authors_input:
        query_parts.extend(authors_input[:3])
    if journal:
        query_parts.append(journal)
    query_text = " ".join(query_parts)

    payload = {"query_text": query_text, "topk": 20, "page": 1, "page_size": 20}
    _, raw_results = run_search(payload)

    best_match: dict[str, Any] | None = None
    best_score = 0.0
    match_details: list[dict[str, Any]] = []

    for record in raw_results:
        score = 0.0
        fields_matched: dict[str, str] = {}
        total_weight = 0.0

        if doi:
            total_weight += 40
            record_doi = normalize_space(record.get("doi"))
            if record_doi and record_doi.lower() == doi.lower():
                score += 40
                fields_matched["doi"] = "exact"
            elif record_doi and (doi.lower() in record_doi.lower() or record_doi.lower() in doi.lower()):
                score += 25
                fields_matched["doi"] = "partial"

        if title:
            total_weight += 30
            record_title = normalize_space(record.get("title")).lower()
            input_title = title.lower()
            if record_title == input_title:
                score += 30
                fields_matched["title"] = "exact"
            elif record_title and input_title:
                input_words = set(input_title.split())
                record_words = set(record_title.split())
                if input_words and record_words:
                    overlap = len(input_words & record_words) / max(len(input_words), len(record_words))
                    if overlap >= 0.5:
                        score += 30 * overlap
                        fields_matched["title"] = f"partial({overlap:.0%})"

        if journal:
            total_weight += 15
            record_journal = normalize_space(record.get("journal") or metadata_value(record, "journal", "venue")).lower()
            if record_journal and journal.lower() in record_journal:
                score += 15
                fields_matched["journal"] = "matched"

        if year:
            total_weight += 10
            record_year = normalize_space(record.get("year"))
            if record_year == year:
                score += 10
                fields_matched["year"] = "exact"

        if authors_input:
            total_weight += 5
            record_authors = split_people(record.get("author") or record.get("authors"))
            if record_authors:
                author_overlap = sum(
                    1 for a in authors_input[:3]
                    if any(a.lower().split()[0] in ra.lower() for ra in record_authors if ra)
                )
                if author_overlap > 0:
                    score += 5 * min(author_overlap, len(authors_input)) / len(authors_input)
                    fields_matched["authors"] = f"{author_overlap}/{len(authors_input)} matched"

        normalized_score = score / max(total_weight, 1) if total_weight > 0 else 0

        paper = sanitize_paper(record, include_text_availability=False)
        detail: dict[str, Any] = {
            "paper_id": paper["paper_id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "year": paper["year"],
            "journal": paper["journal"],
            "doi": paper["doi"],
            "match_score": round(normalized_score, 3),
            "fields_matched": fields_matched,
        }
        match_details.append(detail)

        if normalized_score > best_score:
            best_score = normalized_score
            best_match = detail

    if best_score >= 0.75:
        verified = True
        confidence = "high"
    elif best_score >= 0.45:
        verified = True
        confidence = "medium"
    elif best_score >= 0.25:
        verified = False
        confidence = "low"
    else:
        verified = False
        confidence = "none"

    return json_result(
        common_response(
            {
                "verified": verified,
                "confidence": confidence,
                "best_match": best_match,
                "total_candidates": len(match_details),
                "top_candidates": match_details[:5],
                "verification_note": "基于 PedaScope KB 150万篇教育论文白名单的题录匹配验证；未匹配不等于文献不存在（可能不在本库范围内）。",
            },
            retrieval_mode="citation_verification",
        )
    )


def handle_find_research_gaps(arguments: dict[str, Any]) -> dict[str, Any]:
    """Analyze publication density to identify potential research gaps."""
    keywords = arguments.get("keywords")
    if isinstance(keywords, list):
        query_text = " ".join(normalize_space(k) for k in keywords if normalize_space(k))
    else:
        query_text = normalize_space(keywords)

    domain = normalize_space(arguments.get("domain") or arguments.get("research_domain"))
    if domain:
        query_text = f"{domain} {query_text}".strip()

    if not query_text:
        raise ValueError("At least one of keywords or domain is required")

    topk = optional_int_alias(arguments, ("topk", "top_k"), 100, 1, MAX_TOP_K)
    payload = {"query_text": query_text, "topk": topk, "page": 1, "page_size": min(topk, MAX_PAGE_SIZE)}
    _, raw_results = run_search(payload)

    year_dist: dict[str, int] = {}
    keyword_counter: dict[str, int] = {}
    all_papers: list[dict[str, Any]] = []

    for record in raw_results:
        paper = sanitize_paper(record, include_text_availability=False)
        all_papers.append(paper)

        year_val = normalize_space(record.get("year"))
        if year_val and year_val.isdigit():
            year_dist[year_val] = year_dist.get(year_val, 0) + 1

        for kw in paper.get("keywords", []):
            kw_norm = normalize_space(kw)
            if kw_norm:
                keyword_counter[kw_norm] = keyword_counter.get(kw_norm, 0) + 1

    sorted_years = sorted(year_dist.items(), key=lambda x: int(x[0]))
    sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)

    all_years = sorted(int(y) for y in year_dist if y.isdigit())
    sparse_periods: list[str] = []
    if all_years:
        for i in range(len(all_years) - 1):
            if all_years[i + 1] - all_years[i] > 3:
                sparse_periods.append(f"{all_years[i]}-{all_years[i + 1]}")

    gap_hints: list[str] = [
        f"关键词 '{query_text}' 下共检索到 {len(all_papers)} 篇文献",
    ]
    if sparse_periods:
        gap_hints.append(f"年份分布中存在断档: {', '.join(sparse_periods)}")
    else:
        gap_hints.append("年份分布连续")
    if sorted_keywords:
        gap_hints.append(f"高频关键词可作为子方向入口: {', '.join(kw for kw, _ in sorted_keywords[:5])}")

    return json_result(
        common_response(
            {
                "query_text": query_text,
                "total_papers_analyzed": len(all_papers),
                "year_distribution": dict(sorted_years),
                "top_keywords": [{"keyword": kw, "count": cnt} for kw, cnt in sorted_keywords[:20]],
                "sparse_periods": sparse_periods,
                "density_assessment": {
                    "total_results": len(all_papers),
                    "year_range": f"{all_years[0]}-{all_years[-1]}" if all_years else "unknown",
                    "avg_per_year": round(len(all_papers) / max(len(all_years), 1), 1),
                },
                "gap_hints": gap_hints,
                "coverage_note": "基于检索结果的元数据分析；未覆盖的文献不代表不存在，可能是查询词未命中。",
            },
            retrieval_mode="gap_analysis",
        )
    )


def handle_suggest_keywords(arguments: dict[str, Any]) -> dict[str, Any]:
    """Suggest related research keywords based on seed terms."""
    seed_keywords = arguments.get("seed_keywords")
    if isinstance(seed_keywords, list):
        query_text = " ".join(normalize_space(k) for k in seed_keywords if normalize_space(k))
    else:
        query_text = normalize_space(seed_keywords) or normalize_space(arguments.get("topic"))

    if not query_text:
        raise ValueError("At least one of seed_keywords or topic is required")

    topk = optional_int_alias(arguments, ("topk", "top_k"), 50, 1, MAX_TOP_K)
    payload = {"query_text": query_text, "topk": topk, "page": 1, "page_size": min(topk, MAX_PAGE_SIZE)}
    _, raw_results = run_search(payload)

    keyword_counter: dict[str, int] = {}
    keyword_by_year: dict[str, dict[str, int]] = {}
    all_years_set: set[str] = set()

    for record in raw_results:
        year_val = normalize_space(record.get("year"))
        if year_val:
            all_years_set.add(year_val)

        kws = split_keywords(record.get("keyword") or metadata_value(record, "keywords"))
        for kw in kws:
            kw_norm = normalize_space(kw)
            if not kw_norm:
                continue
            keyword_counter[kw_norm] = keyword_counter.get(kw_norm, 0) + 1
            if year_val:
                if kw_norm not in keyword_by_year:
                    keyword_by_year[kw_norm] = {}
                keyword_by_year[kw_norm][year_val] = keyword_by_year[kw_norm].get(year_val, 0) + 1

    recent_years = sorted(all_years_set, reverse=True)[:3]

    sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)

    suggestions: list[dict[str, Any]] = []
    for kw, count in sorted_keywords[:30]:
        recent_count = 0
        older_count = 0
        for y in keyword_by_year.get(kw, {}):
            if y in recent_years:
                recent_count += keyword_by_year[kw][y]
            else:
                older_count += keyword_by_year[kw][y]

        if recent_count > older_count and older_count > 0:
            trend = "rising"
        elif recent_count > 0 and older_count == 0:
            trend = "emerging"
        elif older_count > recent_count:
            trend = "declining"
        else:
            trend = "stable"

        suggestions.append({"keyword": kw, "frequency": count, "trend": trend})

    return json_result(
        common_response(
            {
                "seed_query": query_text,
                "total_papers_analyzed": len(raw_results),
                "suggested_keywords": suggestions,
                "usage_note": "这些关键词从检索结果的元数据中提取；可作为选题方向扩展、检索词优化或研究热点发现的参考。",
            },
            retrieval_mode="keyword_suggestion",
        )
    )


def handle_build_reading_list(arguments: dict[str, Any]) -> dict[str, Any]:
    """Build a structured, prioritized reading list for a research topic."""
    topic = require_text(arguments, ("topic", "research_question", "query_text"), "topic")
    topk = optional_int_alias(arguments, ("topk", "top_k"), 30, 1, MAX_TOP_K)
    year_from = optional_year(arguments, "year_from")
    year_to = optional_year(arguments, "year_to")

    payload = {"query_text": topic, "topk": topk, "page": 1, "page_size": min(topk, MAX_PAGE_SIZE)}
    _, raw_results = run_search(payload)

    reading_list: list[dict[str, Any]] = []
    for record in raw_results:
        paper = sanitize_paper(record, include_text_availability=False)

        score = 0.0
        reasons: list[str] = []

        rel = float_or_none(record.get("score"))
        if rel is not None:
            score += rel * 40
            reasons.append(f"相关度 {rel:.2f}")

        citations = int_or_none(record.get("citation"))
        if citations is not None:
            if citations >= 50:
                score += 25
                reasons.append(f"高引用({citations})")
            elif citations >= 10:
                score += 15
                reasons.append(f"中引用({citations})")
            elif citations >= 1:
                score += 5
                reasons.append(f"有引用({citations})")

        year_val = normalize_space(record.get("year"))
        if year_val and year_val.isdigit():
            y = int(year_val)
            if y >= 2023:
                score += 20
                reasons.append("最新研究")
            elif y >= 2020:
                score += 15
                reasons.append("近年研究")
            elif y >= 2015:
                score += 10
                reasons.append("较新研究")
            else:
                score += 5
                reasons.append("经典研究")

        if paper.get("doi"):
            score += 5
            reasons.append("有DOI")

        if score >= 60:
            priority = "must_read"
        elif score >= 40:
            priority = "recommended"
        elif score >= 20:
            priority = "optional"
        else:
            priority = "supplementary"

        reading_list.append({
            "paper_id": paper["paper_id"],
            "title": paper["title"],
            "authors": paper["authors"][:4],
            "year": paper["year"],
            "journal": paper["journal"],
            "doi": paper["doi"],
            "keywords": paper["keywords"][:5],
            "citation_count": citations,
            "relevance_score": rel,
            "priority": priority,
            "score": round(score, 1),
            "reasons": reasons,
        })

    reading_list.sort(key=lambda x: x["score"], reverse=True)

    if year_from is not None or year_to is not None:
        filtered: list[dict[str, Any]] = []
        for item in reading_list:
            y = int_or_none(item.get("year"))
            if year_from is not None and (y is None or y < year_from):
                continue
            if year_to is not None and (y is None or y > year_to):
                continue
            filtered.append(item)
        reading_list = filtered

    priority_counts: dict[str, int] = {}
    for item in reading_list:
        p = item["priority"]
        priority_counts[p] = priority_counts.get(p, 0) + 1

    return json_result(
        common_response(
            {
                "topic": topic,
                "reading_list": reading_list,
                "summary": {
                    "total": len(reading_list),
                    "by_priority": priority_counts,
                },
                "priority_guide": {
                    "must_read": "高相关度+高引用+近年发表，优先精读",
                    "recommended": "相关度或引用较好，建议阅读",
                    "optional": "有一定相关度，时间允许时阅读",
                    "supplementary": "边缘相关，作为补充参考",
                },
            },
            retrieval_mode="reading_list",
        )
    )


def handle_compare_topics(arguments: dict[str, Any]) -> dict[str, Any]:
    """Compare two research topics for overlap and differentiation."""
    topic_a = require_text(arguments, ("topic_a", "topic_1", "first_topic"), "topic_a")
    topic_b = require_text(arguments, ("topic_b", "topic_2", "second_topic"), "topic_b")
    topk = optional_int_alias(arguments, ("topk", "top_k"), 30, 1, MAX_TOP_K)

    payload_a = {"query_text": topic_a, "topk": topk, "page": 1, "page_size": min(topk, MAX_PAGE_SIZE)}
    _, raw_results_a = run_search(payload_a)

    payload_b = {"query_text": topic_b, "topk": topk, "page": 1, "page_size": min(topk, MAX_PAGE_SIZE)}
    _, raw_results_b = run_search(payload_b)

    papers_a = [sanitize_paper(r, include_text_availability=False) for r in raw_results_a]
    papers_b = [sanitize_paper(r, include_text_availability=False) for r in raw_results_b]

    doi_set_a = {p["doi"].lower() for p in papers_a if p.get("doi")}
    doi_set_b = {p["doi"].lower() for p in papers_b if p.get("doi")}
    shared_dois = doi_set_a & doi_set_b

    kw_a: set[str] = set()
    kw_b: set[str] = set()
    for p in papers_a:
        kw_a.update(p.get("keywords", []))
    for p in papers_b:
        kw_b.update(p.get("keywords", []))
    shared_keywords = kw_a & kw_b
    unique_keywords_a = kw_a - kw_b
    unique_keywords_b = kw_b - kw_a

    total_unique = len(doi_set_a | doi_set_b)
    overlap_ratio = len(shared_dois) / max(total_unique, 1) if total_unique > 0 else 0.0

    if overlap_ratio >= 0.5:
        differentiation = "low"
        advice = "两个选题高度重叠，差异化不足，建议调整方向。"
    elif overlap_ratio >= 0.2:
        differentiation = "moderate"
        advice = "两个选题有一定重叠，但各有侧重，可进一步细化差异。"
    else:
        differentiation = "high"
        advice = "两个选题差异明显，各自有独立研究空间。"

    shared_papers: list[dict[str, Any]] = []
    for doi in shared_dois:
        for p in papers_a:
            if p.get("doi", "").lower() == doi:
                shared_papers.append({"paper_id": p["paper_id"], "title": p["title"], "doi": p["doi"]})
                break

    return json_result(
        common_response(
            {
                "topic_a": topic_a,
                "topic_b": topic_b,
                "comparison": {
                    "papers_for_a": len(papers_a),
                    "papers_for_b": len(papers_b),
                    "shared_by_doi": len(shared_dois),
                    "overlap_ratio": round(overlap_ratio, 3),
                    "differentiation": differentiation,
                },
                "shared_papers": shared_papers,
                "shared_keywords": sorted(shared_keywords)[:20],
                "unique_keywords_a": sorted(unique_keywords_a)[:15],
                "unique_keywords_b": sorted(unique_keywords_b)[:15],
                "advice": advice,
                "coverage_note": "重叠度基于 DOI 精确匹配和关键词交集计算；结果受检索深度限制，不构成完整的研究空白检测。",
            },
            retrieval_mode="topic_comparison",
        )
    )


def read_only_annotations(title: str, *, open_world: bool = True) -> dict[str, Any]:
    return {
        "title": title,
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": open_world,
    }


def policy_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "rights_basis": {"type": "string", "const": "derived_only"},
            "raw_text_exposed_chars": {"type": "integer", "const": 0},
            "full_text_exposed": {"type": "boolean", "const": False},
            "quote_budget_remaining": {"type": "integer", "const": 0},
            "must_human_verify": {"type": "boolean"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "rights_basis",
            "raw_text_exposed_chars",
            "full_text_exposed",
            "quote_budget_remaining",
            "must_human_verify",
            "warnings",
        ],
        "additionalProperties": False,
    }


def trace_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "tool_version": {"type": "string"},
            "retrieval_mode": {"type": "string"},
            "source": {"type": "string"},
        },
        "required": ["tool_version", "retrieval_mode", "source"],
        "additionalProperties": False,
    }


def envelope_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    base_properties: dict[str, Any] = {
        "request_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "policy": policy_schema(),
        "trace": trace_schema(),
    }
    base_properties.update(properties)
    return {
        "type": "object",
        "properties": base_properties,
        "required": ["request_id", "timestamp", "policy", "trace", *required],
        "additionalProperties": True,
    }


def paper_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "paper_id": {"type": "string"},
            "title": {"type": "string"},
            "abstract": {"type": "string"},
            "abstract_type": {"type": "string", "const": "generated_non_verbatim"},
            "authors": {"type": "array", "items": {"type": "string"}},
            "year": {"type": "string"},
            "journal": {"type": "string"},
            "venue": {"type": "string"},
            "doi": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "citation_count": {"type": ["integer", "null"]},
            "relevance_score": {"type": ["number", "null"]},
            "source_db": {"type": "string"},
            "metadata": {"type": "object"},
            "text_availability": {
                "type": "object",
                "properties": {
                    "full_text_returned": {"type": "boolean", "const": False},
                    "raw_text_exposed_chars": {"type": "integer", "const": 0},
                    "note": {"type": "string"},
                    "status": {"type": "string", "const": "not_probed"},
                    "internal_lookup": {"type": "string", "const": "disabled_by_mcp_policy"},
                },
                "required": ["full_text_returned", "raw_text_exposed_chars", "note", "status", "internal_lookup"],
                "additionalProperties": False,
            },
        },
        "required": [
            "paper_id",
            "title",
            "abstract",
            "abstract_type",
            "authors",
            "year",
            "journal",
            "venue",
            "doi",
            "keywords",
            "citation_count",
            "relevance_score",
            "source_db",
        ],
        "additionalProperties": True,
    }


def search_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "query_text": {"type": "string"},
            "topk": {"type": "integer"},
            "page": {"type": "integer"},
            "page_size": {"type": "integer"},
            "items": {"type": "array", "items": paper_output_schema()},
            "results": {"type": "array", "items": paper_output_schema()},
            "pagination": {"type": "object"},
            "coverage_note": {"type": "string"},
        },
        ["query_text", "items", "results", "pagination", "coverage_note"],
    )


def domain_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "query_text": {"type": "string"},
            "applied_filters": {"type": "object"},
            "items": {"type": "array", "items": paper_output_schema()},
            "results": {"type": "array", "items": paper_output_schema()},
            "pagination": {"type": "object"},
            "coverage_note": {"type": "string"},
        },
        ["query_text", "applied_filters", "items", "results", "pagination", "coverage_note"],
    )


def get_paper_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "paper_id": {"type": "string"},
            "paper": paper_output_schema(),
            "bibliographic_record": {"type": "object"},
        },
        ["paper_id", "paper", "bibliographic_record"],
    )


def trace_claim_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "claim": {"type": "string"},
            "verdict": {"type": "string"},
            "matches": {"type": "array", "items": {"type": "object"}},
            "notes_for_writer": {"type": "array", "items": {"type": "string"}},
        },
        ["claim", "verdict", "matches", "notes_for_writer"],
    )


def citation_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "paper_id": {"type": "string"},
            "style": {"type": "string"},
            "fields": {"type": "object"},
            "formatted_reference": {"type": "string"},
            "verification_note": {"type": "string"},
        },
        ["paper_id", "style", "fields", "formatted_reference", "verification_note"],
    )


def health_output_schema() -> dict[str, Any]:
    return envelope_schema(
        {
            "server": {"type": "string"},
            "version": {"type": "string"},
            "base_url": {"type": "string"},
            "timeout_seconds": {"type": "number"},
            "content_policy": {"type": "object"},
        },
        ["server", "version", "base_url", "timeout_seconds", "content_policy"],
    )


def tools_definition() -> list[dict[str, Any]]:
    return [
        {
            "name": "search_by_keywords",
            "description": "Search papers by keyword string or keyword array. Returns safe metadata, generated non-verbatim abstracts, authors, year, journal, DOI, keywords, and opaque paper_id values.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "description": "Keyword string or array, for example: ['人工智能', '教师专业发展', 'teacher professional development'].",
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        ],
                    },
                    "top_k": {"type": "integer", "default": DEFAULT_TOP_K, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": DEFAULT_TOP_K, "minimum": 1, "maximum": MAX_TOP_K},
                    "page": {"type": "integer", "default": 1, "minimum": 1},
                    "page_size": {
                        "type": "integer",
                        "default": DEFAULT_PAGE_SIZE,
                        "minimum": 1,
                        "maximum": MAX_PAGE_SIZE,
                    },
                },
                "required": ["keywords"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Search By Keywords"),
            "outputSchema": search_output_schema(),
        },
        {
            "name": "search_by_topic",
            "description": "Search semantically by natural-language topic or research question. Returns the most related papers without raw full text or raw snippets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "research_question": {"type": "string"},
                    "query_text": {"type": "string"},
                    "top_k": {"type": "integer", "default": DEFAULT_TOP_K, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": DEFAULT_TOP_K, "minimum": 1, "maximum": MAX_TOP_K},
                    "page": {"type": "integer", "default": 1, "minimum": 1},
                    "page_size": {
                        "type": "integer",
                        "default": DEFAULT_PAGE_SIZE,
                        "minimum": 1,
                        "maximum": MAX_PAGE_SIZE,
                    },
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Search By Topic"),
            "outputSchema": search_output_schema(),
        },
        {
            "name": "search_by_domain",
            "description": "Search representative papers by stage, subject, research domain, method, year, venue, DOI, and citation filters. Text filters become retrieval query terms; structured filters are applied on safe results.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "description": "学段，例如: 高中, 本科, K-12."},
                    "subject": {"type": "string", "description": "学科，例如: 数学, 英语, science education."},
                    "research_domain": {"type": "string", "description": "研究领域，例如: 教师专业发展."},
                    "domain": {"type": "string"},
                    "research_method": {"type": "string", "description": "研究方法，例如: mixed methods, quasi-experiment."},
                    "method": {"type": "string"},
                    "topic": {"type": "string"},
                    "keywords": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "year_from": {"type": "integer", "minimum": 1800, "maximum": 2200},
                    "year_to": {"type": "integer", "minimum": 1800, "maximum": 2200},
                    "journal": {"type": "string"},
                    "venue": {"type": "string"},
                    "must_have_doi": {"type": "boolean", "default": False},
                    "citation_min": {"type": "integer", "minimum": 0},
                    "top_k": {"type": "integer", "default": 80, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 80, "minimum": 1, "maximum": MAX_TOP_K},
                    "page": {"type": "integer", "default": 1, "minimum": 1},
                    "page_size": {
                        "type": "integer",
                        "default": DEFAULT_PAGE_SIZE,
                        "minimum": 1,
                        "maximum": MAX_PAGE_SIZE,
                    },
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Search By Domain"),
            "outputSchema": domain_output_schema(),
        },
        {
            "name": "get_paper",
            "description": "Return a safe paper card for an opaque paper_id from search results: bibliographic metadata, generated summary, DOI, source DB, and text availability status. Never returns full text.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string"},
                    "paperId": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Get Paper"),
            "outputSchema": get_paper_output_schema(),
        },
        {
            "name": "trace_claim",
            "description": "Given a claim, find supporting or related candidate sources using retrieval and internal signals. Returns candidate-level assessment and metadata only; no verbatim evidence snippets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "claim_text": {"type": "string"},
                    "domain_hint": {"type": "string"},
                    "top_k": {"type": "integer", "default": 10, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 10, "minimum": 1, "maximum": MAX_TOP_K},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Trace Claim"),
            "outputSchema": trace_claim_output_schema(),
        },
        {
            "name": "get_citation",
            "description": "Return GB/T 7714-2015 citation fields and a formatted reference draft for an opaque paper_id from search results.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string"},
                    "paperId": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Get Citation"),
            "outputSchema": citation_output_schema(),
        },
        {
            "name": "health",
            "description": "Return this MCP server's local configuration and copyright-control policy without calling the upstream API.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            "annotations": read_only_annotations("Health", open_world=False),
            "outputSchema": health_output_schema(),
        },
        {
            "name": "verify_citation",
            "description": "Verify if a citation reference exists in the PedaScope KB whitelist of 1.5M education papers. Takes citation fields (title, authors, year, journal, DOI) and returns verification status, confidence, and best match details.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "论文标题（支持部分匹配）"},
                    "author": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}], "description": "作者姓名"},
                    "authors": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}], "description": "作者姓名（别名）"},
                    "year": {"type": "string", "description": "发表年份"},
                    "journal": {"type": "string", "description": "期刊名"},
                    "venue": {"type": "string", "description": "期刊名（别名）"},
                    "doi": {"type": "string", "description": "DOI 标识符"},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Verify Citation"),
            "outputSchema": envelope_schema(
                {
                    "verified": {"type": "boolean"},
                    "confidence": {"type": "string"},
                    "best_match": {"type": "object"},
                    "total_candidates": {"type": "integer"},
                    "top_candidates": {"type": "array", "items": {"type": "object"}},
                    "verification_note": {"type": "string"},
                },
                ["verified", "confidence", "verification_note"],
            ),
        },
        {
            "name": "find_research_gaps",
            "description": "Analyze publication density by year and keyword for a research area to identify potential gaps, sparse periods, and sub-direction entry points.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                        "description": "研究方向关键词",
                    },
                    "domain": {"type": "string", "description": "研究领域，如 教师专业发展"},
                    "research_domain": {"type": "string", "description": "研究领域（别名）"},
                    "top_k": {"type": "integer", "default": 100, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 100, "minimum": 1, "maximum": MAX_TOP_K},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Find Research Gaps"),
            "outputSchema": envelope_schema(
                {
                    "query_text": {"type": "string"},
                    "total_papers_analyzed": {"type": "integer"},
                    "year_distribution": {"type": "object"},
                    "top_keywords": {"type": "array", "items": {"type": "object"}},
                    "sparse_periods": {"type": "array", "items": {"type": "string"}},
                    "density_assessment": {"type": "object"},
                    "gap_hints": {"type": "array", "items": {"type": "string"}},
                    "coverage_note": {"type": "string"},
                },
                ["query_text", "total_papers_analyzed", "gap_hints"],
            ),
        },
        {
            "name": "suggest_keywords",
            "description": "Suggest related research keywords based on seed terms. Extracts co-occurring keywords from search results and identifies trending, rising, and declining terms.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "seed_keywords": {
                        "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                        "description": "种子关键词",
                    },
                    "topic": {"type": "string", "description": "研究主题（种子关键词的替代输入）"},
                    "top_k": {"type": "integer", "default": 50, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 50, "minimum": 1, "maximum": MAX_TOP_K},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Suggest Keywords"),
            "outputSchema": envelope_schema(
                {
                    "seed_query": {"type": "string"},
                    "total_papers_analyzed": {"type": "integer"},
                    "suggested_keywords": {"type": "array", "items": {"type": "object"}},
                    "usage_note": {"type": "string"},
                },
                ["seed_query", "suggested_keywords"],
            ),
        },
        {
            "name": "build_reading_list",
            "description": "Build a structured, prioritized reading list for a research topic. Papers are scored by relevance, citation count, recency, and DOI availability, then categorized as must_read/recommended/optional/supplementary.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "研究主题或选题方向"},
                    "research_question": {"type": "string", "description": "研究问题（topic 的替代输入）"},
                    "query_text": {"type": "string", "description": "检索文本（topic 的替代输入）"},
                    "year_from": {"type": "integer", "minimum": 1800, "maximum": 2200},
                    "year_to": {"type": "integer", "minimum": 1800, "maximum": 2200},
                    "top_k": {"type": "integer", "default": 30, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 30, "minimum": 1, "maximum": MAX_TOP_K},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Build Reading List"),
            "outputSchema": envelope_schema(
                {
                    "topic": {"type": "string"},
                    "reading_list": {"type": "array", "items": {"type": "object"}},
                    "summary": {"type": "object"},
                    "priority_guide": {"type": "object"},
                },
                ["topic", "reading_list", "summary"],
            ),
        },
        {
            "name": "compare_topics",
            "description": "Compare two research topics for overlap and differentiation. Searches both topics, computes DOI-based overlap ratio and keyword intersection, and provides a differentiation assessment.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic_a": {"type": "string", "description": "第一个选题方向"},
                    "topic_1": {"type": "string", "description": "第一个选题（别名）"},
                    "first_topic": {"type": "string", "description": "第一个选题（别名）"},
                    "topic_b": {"type": "string", "description": "第二个选题方向"},
                    "topic_2": {"type": "string", "description": "第二个选题（别名）"},
                    "second_topic": {"type": "string", "description": "第二个选题（别名）"},
                    "top_k": {"type": "integer", "default": 30, "minimum": 1, "maximum": MAX_TOP_K},
                    "topk": {"type": "integer", "default": 30, "minimum": 1, "maximum": MAX_TOP_K},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations("Compare Topics"),
            "outputSchema": envelope_schema(
                {
                    "topic_a": {"type": "string"},
                    "topic_b": {"type": "string"},
                    "comparison": {"type": "object"},
                    "shared_papers": {"type": "array", "items": {"type": "object"}},
                    "shared_keywords": {"type": "array", "items": {"type": "string"}},
                    "unique_keywords_a": {"type": "array", "items": {"type": "string"}},
                    "unique_keywords_b": {"type": "array", "items": {"type": "string"}},
                    "advice": {"type": "string"},
                    "coverage_note": {"type": "string"},
                },
                ["topic_a", "topic_b", "comparison", "advice"],
            ),
        },
    ]


def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "search_by_keywords": handle_search_by_keywords,
        "search_by_topic": handle_search_by_topic,
        "search_by_domain": handle_search_by_domain,
        "get_paper": handle_get_paper,
        "trace_claim": handle_trace_claim,
        "get_citation": handle_get_citation,
        "get_article_content": handle_get_article_content_disabled,
        "verify_citation": handle_verify_citation,
        "find_research_gaps": handle_find_research_gaps,
        "suggest_keywords": handle_suggest_keywords,
        "build_reading_list": handle_build_reading_list,
        "compare_topics": handle_compare_topics,
        "health": handle_health,
    }
    handler = handlers.get(name)
    if handler is None:
        return text_result(f"unknown tool: {name}", is_error=True)

    try:
        return handler(arguments)
    except Exception as exc:
        return text_result(safe_error_text(exc), is_error=True)


def handle_message(message: dict[str, Any]) -> None:
    method = message.get("method")
    message_id = message.get("id")

    if method == "initialize":
        reply(
            message_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            },
        )
        return

    if method == "ping":
        reply(message_id, {})
        return

    if method == "tools/list":
        reply(message_id, {"tools": tools_definition()})
        return

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            reply(message_id, text_result("missing tool name", is_error=True))
            return
        if not isinstance(arguments, dict):
            reply(message_id, text_result("tool arguments must be an object", is_error=True))
            return
        reply(message_id, handle_tool_call(name, arguments))
        return

    if message_id is not None:
        error(message_id, -32601, f"Method not found: {method}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            error(None, -32700, f"Parse error: {exc}")
            continue

        if not isinstance(message, dict):
            error(None, -32600, "Invalid Request")
            continue

        try:
            handle_message(message)
        except Exception:
            error(message.get("id"), -32000, "Server error")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
