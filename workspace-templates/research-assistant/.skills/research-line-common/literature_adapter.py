#!/usr/bin/env python3
"""Shared literature-source adapter for research-line Skills.

The default implementation reads local mock indexes, but the public functions and
CLI shape are intentionally close to a future authorized 1.5M-paper service.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from evidence_policy import (
    EVIDENCE_CARD_TEXT_AVAILABILITY,
    canonicalize_evidence_card,
    can_support_claim,
    evidence_level_for_availability,
    has_readable_text,
    is_source_authentic,
)


CASES_ROOT = Path(__file__).resolve().parents[1]
LITERATURE_REFS = CASES_ROOT / "literature-reading-skill" / "references"
PAPER_REFS = CASES_ROOT / "paper-writing-skill" / "references"
PEDASCOPE_BUNDLE = CASES_ROOT / "research-line-common" / "pedascope-kb-mcp-bundle"
PEDASCOPE_MCP_SCRIPT = PEDASCOPE_BUNDLE / "kb_mcp.py"
PEDASCOPE_DEFAULT_BASE_URL = "https://pedascope.ecnu.edu.cn/kb_search_api"
ADAPTER_VERSION = "research-literature-adapter-v1"
EVIDENCE_TEXT_AVAILABILITY = EVIDENCE_CARD_TEXT_AVAILABILITY
PEDASCOPE_RECORD_COUNT = 1_500_000
PEDASCOPE_BACKEND = "pedascope"
PEDASCOPE_SOURCE_LIMITATIONS = [
    "仅返回安全题录和系统生成的非逐字摘要。",
    "不返回原文摘要、全文、片段、original_doc_id 或向量。",
    "trace_claim 为候选级判断，正式引用前需要人工或合法全文渠道确认。",
]
PEDASCOPE_CANDIDATE_LIMITS = [
    "PedaScope MCP 不返回原文摘要、全文或片段；该候选不能直接作为支撑性引用。",
    "正式写入正文或参考文献前，需要人工或合法全文渠道确认。",
]
PEDASCOPE_ANALYSIS_LIMITS = [
    "该分析基于 PedaScope 检索结果的题录元数据和派生信号，不构成完整研究空白证明。",
    "分析结果受查询词、检索深度和题录字段覆盖影响，正式判断前需人工复核。",
]

STOP_TERMS = {"这句", "这句话", "出自", "哪篇", "文章", "研究", "有助于", "能够", "可以"}
MAJOR_TERMS = ["即时反馈", "错因", "典型错因", "教学调整", "学习投入", "显著", "成绩", "讲评"]
REQUIRED_PAPER_FIELDS = ["paperId", "title", "authors", "year", "journal", "keywords", "sourceStatus", "textAvailability"]


class AdapterSource:
    def __init__(
        self,
        *,
        source_id: str,
        source_name: str,
        source_type: str,
        data_type: str,
        authorization_status: str,
        record_count: int = 0,
        version: str = "",
        limitations: list[str] | None = None,
    ) -> None:
        self.source_id = source_id
        self.source_name = source_name
        self.source_type = source_type
        self.data_type = data_type
        self.authorization_status = authorization_status
        self.record_count = record_count
        self.version = version
        self.limitations = limitations or []

    def to_report(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "sourceName": self.source_name,
            "sourceType": self.source_type,
            "dataType": self.data_type,
            "recordCount": self.record_count,
            "authorizationStatus": self.authorization_status,
            "version": self.version,
            "limitations": self.limitations,
        }


class BaseLiteratureAdapter:
    """Interface for literature backends used by research-line Skills."""

    adapter_id = "base"
    source_type = "unknown"
    authorization_status = "unknown"
    source_name = "未命名文献数据源"
    data_type = "literature_record"
    limitations: list[str] = []

    def load_papers(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return {}, []

    def load_evidence_cards(self) -> list[dict[str, Any]]:
        return []

    def describe_sources(self) -> list[dict[str, Any]]:
        metadata, papers = self.load_papers()
        return [
            AdapterSource(
                source_id=self.adapter_id,
                source_name=self.source_name,
                source_type=self.source_type,
                data_type=self.data_type,
                authorization_status=self.authorization_status,
                record_count=len(papers),
                version=str(metadata.get("indexVersion") or metadata.get("version") or ""),
                limitations=list(self.limitations),
            ).to_report()
        ]


class PedaScopeMcpClient:
    """Small JSON-RPC stdio client for the bundled PedaScope MCP server."""

    def __init__(self, script_path: str | Path = PEDASCOPE_MCP_SCRIPT, *, env: dict[str, str] | None = None) -> None:
        self.script_path = Path(script_path)
        self.env = env
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 0

    def __enter__(self) -> "PedaScopeMcpClient":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        if self._proc is not None:
            return
        if not self.script_path.exists():
            raise FileNotFoundError(f"PedaScope MCP server not found: {self.script_path}")
        env = os.environ.copy()
        if self.env:
            env.update(self.env)
        env.setdefault("PEDASCOPE_KB_BASE_URL", PEDASCOPE_DEFAULT_BASE_URL)
        env.setdefault("PEDASCOPE_KB_TIMEOUT_SECONDS", "30")
        self._proc = subprocess.Popen(
            [sys.executable, str(self.script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env=env,
        )
        self.send("initialize", {})

    def close(self) -> None:
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        if proc.stdin:
            proc.stdin.close()
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.start()
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("PedaScope MCP process is not available.")
        self._next_id += 1
        request: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            request["params"] = params
        self._proc.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("PedaScope MCP process closed without a response.")
        response = json.loads(line)
        if "error" in response:
            message = response["error"].get("message") if isinstance(response.get("error"), dict) else response["error"]
            raise RuntimeError(str(message))
        result = response.get("result", {})
        return result if isinstance(result, dict) else {"result": result}

    def tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.send("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            text = ""
            content = result.get("content", [])
            if isinstance(content, list) and content and isinstance(content[0], dict):
                text = str(content[0].get("text", ""))
            raise RuntimeError(text or f"PedaScope MCP tool failed: {name}")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        content = result.get("content", [])
        if isinstance(content, list) and content and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str) and text.strip():
                parsed = json.loads(text)
                return parsed if isinstance(parsed, dict) else {"result": parsed}
        return result


def source_status_for_source(source: str) -> str:
    if source in {"whitelist", "paper_writing_whitelist"}:
        return "whitelist"
    if source in {"user_available_papers", "user_upload", "user_uploaded_text"}:
        return "user_provided"
    if source in {"unverified_external"}:
        return "unverified"
    return "external_verified"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tokenize(text: str) -> set[str]:
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text)
    terms: set[str] = set()
    for chunk in chunks:
        if len(chunk) <= 1:
            continue
        for size in (4, 3, 2):
            for index in range(0, max(len(chunk) - size + 1, 0)):
                term = chunk[index : index + size]
                if term not in STOP_TERMS:
                    terms.add(term)
    return terms


def major_terms(text: str) -> set[str]:
    return {term for term in MAJOR_TERMS if term in text}


def paper_text(paper: dict[str, Any]) -> str:
    return " ".join(
        [
            str(paper.get("title", "")),
            " ".join(str(item) for item in paper.get("keywords", []) if item),
            str(paper.get("abstract", "")),
            str(paper.get("generatedSummary", "")),
            str(paper.get("fullText", "")),
            str(paper.get("uploadedText", "")),
        ]
    )


def completeness_score(paper: dict[str, Any]) -> int:
    score = sum(1 for field in REQUIRED_PAPER_FIELDS if paper.get(field))
    score += sum(1 for field in ("abstract", "fullText", "volume", "issue", "pages", "doi") if paper.get(field))
    if has_readable_text(paper.get("textAvailability")):
        score += 2
    return score


def normalize_paper(paper: dict[str, Any], source: str) -> dict[str, Any]:
    normalized = dict(paper)
    normalized.setdefault("sourceStatus", source_status_for_source(source))
    normalized.setdefault("textAvailability", "metadata")
    normalized.setdefault("evidenceLevel", evidence_level_for_availability(normalized.get("textAvailability")))
    normalized.setdefault("keywords", [])
    normalized.setdefault("authors", [])
    normalized.setdefault("database", source)
    return normalized


def dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for paper in papers:
        if not isinstance(paper, dict) or not paper.get("paperId"):
            continue
        paper_id = str(paper["paperId"])
        existing = index.get(paper_id)
        if existing is None:
            index[paper_id] = paper
            continue
        merged = {**existing, **{key: value for key, value in paper.items() if value not in (None, "", [])}}
        index[paper_id] = merged if completeness_score(merged) >= completeness_score(existing) else existing
    return list(index.values())


def load_literature_index() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = read_json(LITERATURE_REFS / "literature-index-sample.json")
    papers = [normalize_paper(paper, "local_mock_index") for paper in data.get("papers", [])]
    metadata = dict(data.get("metadata", {}))
    metadata.setdefault("simulatedCorpusSize", len(papers))
    metadata.setdefault("indexVersion", "local-mock-index")
    return metadata, papers


def load_literature_whitelist() -> list[dict[str, Any]]:
    data = read_json(LITERATURE_REFS / "literature-whitelist-sample.json")
    return [normalize_paper(paper, "whitelist") for paper in data.get("papers", [])]


def load_paper_writing_whitelist() -> list[dict[str, Any]]:
    data = read_json(PAPER_REFS / "literature-whitelist-sample.json")
    return [normalize_paper(paper, "paper_writing_whitelist") for paper in data.get("papers", [])]


def load_evidence_card_index() -> list[dict[str, Any]]:
    data = read_json(PAPER_REFS / "evidence-card-index.json")
    return [canonicalize_evidence_card(card) for card in data.get("evidenceCards", []) if isinstance(card, dict)]


class LocalMockLiteratureAdapter(BaseLiteratureAdapter):
    adapter_id = "local_mock"
    source_type = "local_mock"
    authorization_status = "mock_sample"
    source_name = "科研线本地样例文献池"
    data_type = "literature_record"
    limitations = ["读取本地 mock 索引和样例白名单，不能代表真实授权库完整覆盖。"]

    def load_papers(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        metadata, index_papers = load_literature_index()
        papers = [*index_papers, *load_literature_whitelist(), *load_paper_writing_whitelist()]
        merged_metadata = dict(metadata)
        merged_metadata["adapterId"] = self.adapter_id
        merged_metadata["sourceBackends"] = ["literature_index_sample", "literature_reading_whitelist", "paper_writing_whitelist"]
        return merged_metadata, dedupe_papers(papers)

    def load_evidence_cards(self) -> list[dict[str, Any]]:
        return load_evidence_card_index()

    def describe_sources(self) -> list[dict[str, Any]]:
        index_metadata, index_papers = load_literature_index()
        literature_whitelist = load_literature_whitelist()
        paper_whitelist = load_paper_writing_whitelist()
        return [
            AdapterSource(
                source_id="literature-index-sample",
                source_name="本地教育文献索引样例",
                source_type="local_mock",
                data_type="literature_metadata_index",
                record_count=len(index_papers),
                authorization_status="mock_sample",
                version=index_metadata.get("indexVersion", ""),
                limitations=["模拟大型文献库检索结果，不代表真实授权库完整覆盖。"],
            ).to_report(),
            AdapterSource(
                source_id="literature-reading-whitelist",
                source_name="文献阅读白名单样例",
                source_type="local_sample",
                data_type="literature_whitelist",
                record_count=len(literature_whitelist),
                authorization_status="sample_only",
                limitations=["用于流程测试和文本可用性分级，真实引用前需接入授权库。"],
            ).to_report(),
            AdapterSource(
                source_id="paper-writing-whitelist",
                source_name="论文写作共享白名单样例",
                source_type="local_sample",
                data_type="literature_whitelist",
                record_count=len(paper_whitelist),
                authorization_status="sample_only",
                limitations=["与论文写作共用的样例白名单，不能代表完整文献检索。"],
            ).to_report(),
        ]


class UserUploadAdapter(BaseLiteratureAdapter):
    adapter_id = "user_upload"
    source_type = "user_provided"
    authorization_status = "user_provided"
    source_name = "用户提供文献与证据卡"
    data_type = "literature_record"
    limitations = ["用户提供文献的题录真实性、授权状态和全文范围需另行确认。"]

    def __init__(self, papers: list[dict[str, Any]] | None = None, evidence_cards: list[dict[str, Any]] | None = None) -> None:
        self.papers = [paper for paper in (papers or []) if isinstance(paper, dict)]
        self.evidence_cards = [card for card in (evidence_cards or []) if isinstance(card, dict)]

    def load_papers(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        metadata = {
            "adapterId": self.adapter_id,
            "indexVersion": "user-provided-runtime",
            "simulatedCorpusSize": len(self.papers),
        }
        return metadata, [normalize_paper(paper, "user_available_papers") for paper in self.papers]

    def load_evidence_cards(self) -> list[dict[str, Any]]:
        return [canonicalize_evidence_card(card) for card in self.evidence_cards]

    def describe_sources(self) -> list[dict[str, Any]]:
        sources = []
        if self.papers:
            sources.append(
                AdapterSource(
                    source_id="user-available-papers",
                    source_name="用户提供文献记录",
                    source_type="user_provided",
                    data_type="literature_record",
                    record_count=len(self.papers),
                    authorization_status="user_provided",
                    limitations=list(self.limitations),
                ).to_report()
            )
        if self.evidence_cards:
            sources.append(
                AdapterSource(
                    source_id="user-evidence-cards",
                    source_name="用户提供证据卡",
                    source_type="user_provided",
                    data_type="evidence_card",
                    record_count=len(self.evidence_cards),
                    authorization_status="user_provided",
                    limitations=["用户证据卡进入写作前仍需校验 paperId、quoteLocation、supportType 和 evidenceLevel。"],
                ).to_report()
            )
        return sources


class JsonFileLiteratureAdapter(BaseLiteratureAdapter):
    adapter_id = "json_file"
    source_type = "external_verified"
    authorization_status = "external_verified"
    source_name = "JSON 文献索引"
    limitations = ["文件内容由调用方提供，适配器只做结构归一化，不额外保证授权范围。"]

    def __init__(
        self,
        path: str | Path,
        *,
        adapter_id: str,
        source_name: str,
        source_type: str,
        authorization_status: str,
        default_text_availability: str = "metadata",
    ) -> None:
        self.path = Path(path)
        self.adapter_id = adapter_id
        self.source_name = source_name
        self.source_type = source_type
        self.authorization_status = authorization_status
        self.default_text_availability = default_text_availability

    def load_papers(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        data = read_json(self.path)
        metadata = dict(data.get("metadata", {})) if isinstance(data, dict) else {}
        metadata.setdefault("indexVersion", self.path.stem)
        raw_papers = data.get("papers", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        papers = []
        for paper in raw_papers:
            if not isinstance(paper, dict):
                continue
            normalized = normalize_paper({**{"textAvailability": self.default_text_availability}, **paper}, self.adapter_id)
            papers.append(normalized)
        metadata["adapterId"] = self.adapter_id
        metadata["simulatedCorpusSize"] = len(papers)
        return metadata, papers


class AuthorizedDatabaseAdapter(JsonFileLiteratureAdapter):
    """File-backed stand-in for a future authorized education literature service."""

    def __init__(self, path: str | Path) -> None:
        super().__init__(
            path,
            adapter_id="authorized_database",
            source_name="授权文献库索引",
            source_type="authorized_database",
            authorization_status="authorized",
            default_text_availability="metadata",
        )
        self.limitations = ["当前实现读取离线 JSON 索引；接入真实授权库后仍需传回文本可用性和授权边界。"]


class ExternalMetadataAdapter(JsonFileLiteratureAdapter):
    """External metadata backend that can recommend sources but not create evidence."""

    def __init__(self, path: str | Path) -> None:
        super().__init__(
            path,
            adapter_id="external_metadata",
            source_name="外部元数据索引",
            source_type="external_metadata",
            authorization_status="external_verified",
            default_text_availability="metadata",
        )
        self.limitations = ["仅验证题录或外部元数据相关性，不能生成支撑性引用或 EvidenceCard。"]


def clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def normalize_people(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    delimiter = "|" if "|" in text else ";"
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def normalize_keywords(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[|;,，；、\s]+", text) if part.strip()]


def pedascope_item_to_record(item: dict[str, Any]) -> dict[str, Any]:
    paper_id = first_text(item.get("paper_id"), item.get("paperId"))
    generated_summary = first_text(item.get("generatedSummary"), item.get("abstract"))
    source_db = first_text(item.get("source_db"), item.get("database"), "PedaScope KB")
    record = {
        "paperId": paper_id,
        "title": first_text(item.get("title"), "题名待确认"),
        "authors": normalize_people(item.get("authors")),
        "year": first_text(item.get("year"), "年份待确认"),
        "journal": first_text(item.get("journal"), item.get("venue"), ""),
        "doi": first_text(item.get("doi")),
        "keywords": normalize_keywords(item.get("keywords")),
        "generatedSummary": generated_summary,
        "abstractType": first_text(item.get("abstract_type"), item.get("abstractType"), "generated_non_verbatim"),
        "sourceStatus": "external_verified",
        "textAvailability": "metadata",
        "evidenceLevel": "metadata_verified",
        "database": source_db,
        "sourceBackend": PEDASCOPE_BACKEND,
        "limits": list(PEDASCOPE_CANDIDATE_LIMITS),
    }
    if item.get("relevance_score") is not None:
        record["retrievalScore"] = item.get("relevance_score")
    if item.get("citation_count") is not None:
        record["citationCount"] = item.get("citation_count")
    if item.get("priority"):
        record["readingPriority"] = item.get("priority")
    if item.get("score") is not None:
        record["readingPriorityScore"] = item.get("score")
    if item.get("reasons") not in (None, [], {}):
        record["readingReasons"] = item.get("reasons")
    if item.get("metadata") not in (None, {}, []):
        record["metadata"] = item.get("metadata")
    return record


def bibliographic_candidate_from_record(
    record: dict[str, Any],
    *,
    index: int,
    relation: str,
    support_strength: str = "unknown",
    citation_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = {
        "candidateId": f"bc-pedascope-{index:03d}",
        "paperId": record.get("paperId", ""),
        "title": record.get("title", ""),
        "authors": record.get("authors", []),
        "year": record.get("year", ""),
        "journal": record.get("journal", ""),
        "doi": record.get("doi", ""),
        "keywords": record.get("keywords", []),
        "generatedSummary": record.get("generatedSummary", ""),
        "relation": relation,
        "supportStrength": support_strength or "unknown",
        "sourceStatus": "external_verified",
        "textAvailability": "metadata",
        "evidenceLevel": "metadata_verified",
        "abstractType": record.get("abstractType", "generated_non_verbatim"),
        "limits": list(PEDASCOPE_CANDIDATE_LIMITS),
    }
    if record.get("retrievalScore") is not None:
        candidate["retrievalScore"] = record.get("retrievalScore")
    if citation_draft:
        candidate["citationDraft"] = citation_draft
    return candidate


def pedascope_source_locator() -> dict[str, Any]:
    return {
        "locationType": "metadata",
        "locator": "PedaScope KB metadata",
        "confidence": "low",
    }


class PedaScopeMcpAdapter(BaseLiteratureAdapter):
    """PedaScope KB MCP backend for metadata-level discovery and source tracing."""

    adapter_id = PEDASCOPE_BACKEND
    source_type = "authorized_database"
    authorization_status = "public_metadata_service"
    source_name = "PedaScope KB 教育文献知识库"
    data_type = "literature_metadata"
    limitations = list(PEDASCOPE_SOURCE_LIMITATIONS)

    def __init__(
        self,
        *,
        client: Any | None = None,
        script_path: str | Path = PEDASCOPE_MCP_SCRIPT,
        top_k: int = 50,
        page_size: int = 20,
        env: dict[str, str] | None = None,
    ) -> None:
        self.client = client
        self.script_path = Path(script_path)
        self.top_k = clamp_int(top_k, default=50, minimum=1, maximum=200)
        self.page_size = clamp_int(page_size, default=20, minimum=1, maximum=50)
        self.env = env
        self.last_error = ""
        self.last_health: dict[str, Any] = {}

    def _client_context(self) -> Any:
        if self.client is not None:
            return nullcontext(self.client)
        return PedaScopeMcpClient(self.script_path, env=self.env)

    def _tool(self, client: Any, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if hasattr(client, "tool"):
            payload = client.tool(name, arguments or {})
        else:
            payload = client(name, arguments or {})
        return payload if isinstance(payload, dict) else {"result": payload}

    def health(self) -> dict[str, Any]:
        try:
            with self._client_context() as client:
                payload = self._tool(client, "health", {})
            self.last_health = payload
            return payload
        except Exception as exc:
            self.last_error = str(exc)
            return {}

    def describe_sources(self) -> list[dict[str, Any]]:
        health = self.last_health or self.health()
        version = first_text(health.get("version"), health.get("trace", {}).get("tool_version"), "pedascope-kb-mcp-0.2.2")
        if not version.startswith("pedascope-kb-mcp"):
            version = f"pedascope-kb-mcp-{version}"
        limitations = list(self.limitations)
        if self.last_error:
            limitations.append(f"最近一次 PedaScope MCP 调用失败：{self.last_error}")
        return [
            AdapterSource(
                source_id="pedascope-kb",
                source_name=self.source_name,
                source_type=self.source_type,
                data_type=self.data_type,
                record_count=PEDASCOPE_RECORD_COUNT,
                authorization_status=self.authorization_status,
                version=version,
                limitations=limitations,
            ).to_report()
        ]

    def load_papers(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        return {
            "adapterId": self.adapter_id,
            "indexVersion": "pedascope-kb-mcp",
            "indexSource": "pedascope_kb",
            "simulatedCorpusSize": PEDASCOPE_RECORD_COUNT,
            "sourceBackends": [self.adapter_id],
            "note": "PedaScopeMcpAdapter requires query-aware search; load_papers returns no records.",
        }, []

    def load_evidence_cards(self) -> list[dict[str, Any]]:
        return []

    def _search_tool_and_args(
        self,
        *,
        research_topic: str,
        keywords: list[str],
        domain_filters: dict[str, Any] | None,
        limit: int,
    ) -> tuple[str, dict[str, Any]]:
        top_k = clamp_int(max(self.top_k, limit), default=self.top_k, minimum=1, maximum=200)
        page_size = clamp_int(max(min(top_k, 50), min(limit, 50), self.page_size), default=self.page_size, minimum=1, maximum=50)
        filters = {key: value for key, value in (domain_filters or {}).items() if value not in (None, "", [], {})}
        if filters:
            args = {**filters, "top_k": top_k, "page_size": page_size}
            if research_topic and "topic" not in args:
                args["topic"] = research_topic
            if keywords and "keywords" not in args:
                args["keywords"] = keywords
            return "search_by_domain", args
        if research_topic:
            return "search_by_topic", {"topic": research_topic, "top_k": top_k, "page_size": page_size}
        return "search_by_keywords", {"keywords": keywords or [research_topic], "top_k": top_k, "page_size": page_size}

    def search(
        self,
        *,
        research_topic: str,
        keywords: list[str],
        limit: int = 5,
        domain_filters: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if research_topic and not domain_filters:
            reading_payload = self.build_reading_list(topic=research_topic, limit=max(limit, self.page_size))
            reading_records = reading_payload.get("records", [])
            if reading_records:
                returned = reading_records[:limit]
                returned_ids = {record.get("paperId") for record in returned}
                candidates = [
                    candidate
                    for candidate in reading_payload.get("bibliographicCandidates", [])
                    if candidate.get("paperId") in returned_ids
                ]
                report = reading_payload.get("readingListReport", {})
                trace = reading_payload.get("retrievalTrace", {})
                metadata = {
                    "adapterId": self.adapter_id,
                    "indexVersion": report.get("indexVersion", "pedascope-kb-mcp"),
                    "indexSource": "pedascope_kb",
                    "sourceBackends": [self.adapter_id],
                    "simulatedCorpusSize": PEDASCOPE_RECORD_COUNT,
                    "candidateCount": report.get("candidateCount", len(reading_records)),
                    "bibliographicCandidates": candidates,
                    "readingListReport": report,
                    "coverageNote": "结构化阅读清单来自题录元数据、相关度、引用数、年份和 DOI 等派生信号；不提供原文证据。",
                    "retrievalTrace": trace,
                }
                return metadata, returned

        tool_name, arguments = self._search_tool_and_args(
            research_topic=research_topic,
            keywords=keywords,
            domain_filters=domain_filters,
            limit=limit,
        )
        try:
            with self._client_context() as client:
                payload = self._tool(client, tool_name, arguments)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "adapterId": self.adapter_id,
                "indexVersion": "pedascope-kb-mcp",
                "indexSource": "pedascope_kb",
                "sourceBackends": [self.adapter_id],
                "simulatedCorpusSize": 0,
                "candidateCount": 0,
                "adapterWarnings": [f"PedaScope MCP search failed: {self.last_error}"],
                "retrievalTrace": {"tool": tool_name, "arguments": arguments},
            }, []

        self.last_error = ""
        items = payload.get("items") or payload.get("results") or []
        records = []
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict) or not first_text(item.get("paper_id"), item.get("paperId")):
                continue
            record = pedascope_item_to_record(item)
            record["retrievalRank"] = index
            records.append(record)
        candidates = [
            bibliographic_candidate_from_record(record, index=index, relation="topic_related")
            for index, record in enumerate(records, 1)
        ]
        pagination = payload.get("pagination", {}) if isinstance(payload.get("pagination"), dict) else {}
        trace = payload.get("trace", {}) if isinstance(payload.get("trace"), dict) else {}
        version = first_text(trace.get("tool_version"), "pedascope-kb-mcp")
        metadata = {
            "adapterId": self.adapter_id,
            "indexVersion": f"pedascope-kb-mcp-{version}" if not version.startswith("pedascope") else version,
            "indexSource": "pedascope_kb",
            "sourceBackends": [self.adapter_id],
            "simulatedCorpusSize": PEDASCOPE_RECORD_COUNT,
            "candidateCount": int(pagination.get("matched_before_pagination") or pagination.get("returned") or len(records)),
            "bibliographicCandidates": candidates,
            "coverageNote": payload.get("coverage_note", "返回为安全题录和系统生成摘要；未返回原始摘要、全文或片段。"),
            "retrievalTrace": {
                "tool": tool_name,
                "arguments": arguments,
                "queryText": payload.get("query_text", research_topic or " ".join(keywords)),
                "retrievalMode": trace.get("retrieval_mode", ""),
                "source": trace.get("source", "PedaScope KB public API"),
                "pagination": pagination,
            },
        }
        return metadata, records

    def trace_claim(self, *, query_text: str, limit: int = 5, domain_hint: str = "") -> dict[str, Any]:
        top_k = clamp_int(limit, default=5, minimum=1, maximum=50)
        try:
            with self._client_context() as client:
                payload = self._tool(client, "trace_claim", {"claim": query_text, "domain_hint": domain_hint, "top_k": top_k})
                matches = payload.get("matches", []) if isinstance(payload.get("matches"), list) else []
                papers: list[dict[str, Any]] = []
                candidates: list[dict[str, Any]] = []
                for index, match in enumerate(matches[:limit], 1):
                    if not isinstance(match, dict):
                        continue
                    record = pedascope_item_to_record(match)
                    if not record.get("paperId"):
                        continue
                    citation_draft = {}
                    try:
                        citation_payload = self._tool(client, "get_citation", {"paper_id": record["paperId"]})
                        citation_draft = {
                            "style": citation_payload.get("style", "GB/T 7714-2015 draft"),
                            "formattedReference": citation_payload.get("formatted_reference", ""),
                            "fields": citation_payload.get("fields", {}),
                            "verificationNote": citation_payload.get("verification_note", ""),
                        }
                    except Exception:
                        citation_draft = {
                            "style": "GB/T 7714-2015 draft",
                            "formattedReference": citation_for(record),
                            "verificationNote": "由题录字段生成的本地草案；正式引用前需核验。",
                        }
                    candidate = bibliographic_candidate_from_record(
                        record,
                        index=index,
                        relation="claim_candidate",
                        support_strength=str(match.get("support_strength") or "unknown"),
                        citation_draft=citation_draft,
                    )
                    candidate.update(
                        {
                            "matchType": "pedascope_claim_candidate",
                            "supportStatus": "related_only",
                            "confidence": "medium" if candidate["supportStrength"] == "strong" else "low",
                            "quoteLocation": "metadata",
                            "sourceLocator": pedascope_source_locator(),
                            "citation": citation_draft.get("formattedReference") or citation_for(record),
                            "score": match.get("overlap_signal", 0),
                            "matchSnippet": record.get("generatedSummary") or record.get("title", ""),
                            "rawEvidenceReturned": False,
                            "evidenceNote": match.get("evidence_note", "未返回原文证据片段。"),
                        }
                    )
                    papers.append(record)
                    candidates.append(candidate)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "decision": "no_source_found",
                "sourceBackends": [self.adapter_id],
                "candidates": [],
                "usableEvidenceCards": [],
                "papers": [],
                "warnings": [f"PedaScope MCP trace_claim failed: {self.last_error}"],
            }

        decision = "candidate_source_found" if candidates else "no_source_found"
        return {
            "decision": decision,
            "sourceBackends": [self.adapter_id],
            "candidates": candidates,
            "usableEvidenceCards": [],
            "papers": papers,
            "warnings": [
                "PedaScope trace_claim 仅返回候选级来源，不提供原文证据；不可直接生成 EvidenceCard 或正文插入建议。"
            ],
            "verdict": payload.get("verdict", ""),
            "notesForWriter": payload.get("notes_for_writer", []),
        }

    def verify_citation(self, citation: dict[str, Any]) -> dict[str, Any]:
        args: dict[str, Any] = {}
        for source_key, target_key in (
            ("title", "title"),
            ("year", "year"),
            ("journal", "journal"),
            ("venue", "venue"),
            ("doi", "doi"),
        ):
            value = citation.get(source_key)
            if value not in (None, "", [], {}):
                args[target_key] = value
        authors = citation.get("authors") or citation.get("author")
        if authors not in (None, "", [], {}):
            args["authors"] = authors
        if not args:
            return {
                "verified": False,
                "confidence": "none",
                "verificationStatus": "not_checked",
                "verificationNote": "缺少可用于 PedaScope 验证的题录字段。",
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }
        try:
            with self._client_context() as client:
                payload = self._tool(client, "verify_citation", args)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "verified": False,
                "confidence": "none",
                "verificationStatus": "error",
                "verificationNote": f"PedaScope MCP verify_citation failed: {self.last_error}",
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }

        best_match = payload.get("best_match") if isinstance(payload.get("best_match"), dict) else {}
        top_candidates = payload.get("top_candidates", []) if isinstance(payload.get("top_candidates"), list) else []
        verified = bool(payload.get("verified"))
        confidence = str(payload.get("confidence") or "none")
        if verified and confidence in {"high", "medium"}:
            status = "verified"
        elif best_match:
            status = "candidate_match"
        else:
            status = "not_verified"
        return {
            "verified": verified,
            "confidence": confidence,
            "verificationStatus": status,
            "bestMatch": pedascope_item_to_record(best_match) if best_match else {},
            "topCandidates": [pedascope_item_to_record(item) for item in top_candidates if isinstance(item, dict)],
            "totalCandidates": payload.get("total_candidates", 0),
            "verificationNote": payload.get("verification_note", "未匹配不等于文献不存在，可能不在 PedaScope KB 范围内。"),
            "retrievalTrace": payload.get("trace", {}),
            "limits": [
                "verify_citation 只能验证题录白名单匹配，不能证明该文献支撑某个论点。",
                "未匹配不等于文献不存在；可能不在本库范围内或字段不完整。",
            ],
        }

    def find_research_gaps(self, *, keywords: list[str], domain: str = "", limit: int = 50) -> dict[str, Any]:
        args: dict[str, Any] = {"keywords": keywords, "top_k": clamp_int(limit, default=50, minimum=1, maximum=200)}
        if domain:
            args["domain"] = domain
        try:
            with self._client_context() as client:
                payload = self._tool(client, "find_research_gaps", args)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "status": "error",
                "warnings": [f"PedaScope MCP find_research_gaps failed: {self.last_error}"],
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }
        return {
            "status": "ok",
            "queryText": payload.get("query_text", " ".join(keywords)),
            "totalPapersAnalyzed": payload.get("total_papers_analyzed", 0),
            "yearDistribution": payload.get("year_distribution", {}),
            "topKeywords": payload.get("top_keywords", []),
            "sparsePeriods": payload.get("sparse_periods", []),
            "densityAssessment": payload.get("density_assessment", {}),
            "gapHints": payload.get("gap_hints", []),
            "coverageNote": payload.get("coverage_note", ""),
            "retrievalTrace": payload.get("trace", {}),
            "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
        }

    def suggest_keywords(self, *, seed_keywords: list[str] | None = None, topic: str = "", limit: int = 30) -> dict[str, Any]:
        args: dict[str, Any] = {"top_k": clamp_int(limit, default=30, minimum=1, maximum=200)}
        if seed_keywords:
            args["seed_keywords"] = seed_keywords
        if topic:
            args["topic"] = topic
        if "seed_keywords" not in args and "topic" not in args:
            return {
                "status": "not_checked",
                "suggestedKeywords": [],
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }
        try:
            with self._client_context() as client:
                payload = self._tool(client, "suggest_keywords", args)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "status": "error",
                "suggestedKeywords": [],
                "warnings": [f"PedaScope MCP suggest_keywords failed: {self.last_error}"],
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }
        return {
            "status": "ok",
            "seedQuery": payload.get("seed_query", topic or " ".join(seed_keywords or [])),
            "totalPapersAnalyzed": payload.get("total_papers_analyzed", 0),
            "suggestedKeywords": payload.get("suggested_keywords", []),
            "usageNote": payload.get("usage_note", ""),
            "retrievalTrace": payload.get("trace", {}),
            "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
        }

    def build_reading_list(
        self,
        *,
        topic: str,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        args: dict[str, Any] = {"topic": topic, "top_k": clamp_int(limit, default=20, minimum=1, maximum=200)}
        if year_from is not None:
            args["year_from"] = year_from
        if year_to is not None:
            args["year_to"] = year_to
        try:
            with self._client_context() as client:
                payload = self._tool(client, "build_reading_list", args)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "status": "error",
                "records": [],
                "readingListReport": {
                    "warnings": [f"PedaScope MCP build_reading_list failed: {self.last_error}"],
                    "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
                },
            }

        reading_items = payload.get("reading_list", []) if isinstance(payload.get("reading_list"), list) else []
        records: list[dict[str, Any]] = []
        reading_list: list[dict[str, Any]] = []
        for index, item in enumerate(reading_items, 1):
            if not isinstance(item, dict):
                continue
            record = pedascope_item_to_record(item)
            if not record.get("paperId"):
                continue
            record["retrievalRank"] = index
            records.append(record)
            reading_list.append(
                {
                    "paperId": record["paperId"],
                    "title": record["title"],
                    "priority": item.get("priority", "optional"),
                    "score": item.get("score", 0),
                    "reasons": item.get("reasons", []),
                    "year": record.get("year", ""),
                    "journal": record.get("journal", ""),
                    "citationCount": record.get("citationCount"),
                    "textAvailability": "metadata",
                    "evidenceLevel": "metadata_verified",
                    "limits": list(PEDASCOPE_CANDIDATE_LIMITS),
                }
            )
        candidates = [
            bibliographic_candidate_from_record(record, index=index, relation="topic_related")
            for index, record in enumerate(records, 1)
        ]
        trace = payload.get("trace", {}) if isinstance(payload.get("trace"), dict) else {}
        version = first_text(trace.get("tool_version"), "pedascope-kb-mcp")
        return {
            "status": "ok",
            "records": records,
            "bibliographicCandidates": candidates,
            "retrievalTrace": {
                "tool": "build_reading_list",
                "arguments": args,
                "queryText": payload.get("topic", topic),
                "retrievalMode": trace.get("retrieval_mode", ""),
                "source": trace.get("source", "PedaScope KB public API"),
            },
            "readingListReport": {
                "indexVersion": f"pedascope-kb-mcp-{version}" if not version.startswith("pedascope") else version,
                "topic": payload.get("topic", topic),
                "candidateCount": payload.get("summary", {}).get("total", len(records)) if isinstance(payload.get("summary"), dict) else len(records),
                "returnedCount": len(records),
                "summary": payload.get("summary", {}),
                "priorityGuide": payload.get("priority_guide", {}),
                "readingList": reading_list,
                "limits": [
                    "阅读清单优先级来自题录元数据、相关度、引用数、年份和 DOI 等派生信号。",
                    "PedaScope 不返回原文证据；清单条目不能直接作为支撑性引用。",
                ],
            },
        }

    def compare_topics(self, *, topic_a: str, topic_b: str, limit: int = 30) -> dict[str, Any]:
        args = {
            "topic_a": topic_a,
            "topic_b": topic_b,
            "top_k": clamp_int(limit, default=30, minimum=1, maximum=200),
        }
        try:
            with self._client_context() as client:
                payload = self._tool(client, "compare_topics", args)
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "status": "error",
                "warnings": [f"PedaScope MCP compare_topics failed: {self.last_error}"],
                "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
            }
        return {
            "status": "ok",
            "topicA": payload.get("topic_a", topic_a),
            "topicB": payload.get("topic_b", topic_b),
            "comparison": payload.get("comparison", {}),
            "sharedPapers": payload.get("shared_papers", []),
            "sharedKeywords": payload.get("shared_keywords", []),
            "uniqueKeywordsA": payload.get("unique_keywords_a", []),
            "uniqueKeywordsB": payload.get("unique_keywords_b", []),
            "advice": payload.get("advice", ""),
            "coverageNote": payload.get("coverage_note", "结果受检索深度限制，不构成完整查重。"),
            "retrievalTrace": payload.get("trace", {}),
            "limits": list(PEDASCOPE_ANALYSIS_LIMITS),
        }


def collect_adapter_papers(adapters: list[BaseLiteratureAdapter]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(adapters) == 1:
        adapter = adapters[0]
        metadata, papers = adapter.load_papers()
        single_metadata = dict(metadata)
        single_metadata.setdefault("adapterVersion", ADAPTER_VERSION)
        single_metadata.setdefault("indexVersion", single_metadata.get("indexVersion", adapter.adapter_id))
        single_metadata["indexSource"] = "local_mock_index" if adapter.adapter_id == "local_mock" else adapter.source_type
        single_metadata["sourceBackends"] = [adapter.adapter_id]
        single_metadata.setdefault("simulatedCorpusSize", len(papers))
        return single_metadata, dedupe_papers(papers)

    papers: list[dict[str, Any]] = []
    metadata = {
        "adapterVersion": ADAPTER_VERSION,
        "indexVersion": "multi-backend",
        "indexSource": "multi_backend",
        "sourceBackends": [],
        "simulatedCorpusSize": 0,
    }
    for adapter in adapters:
        adapter_metadata, adapter_papers = adapter.load_papers()
        metadata["sourceBackends"].append(adapter.adapter_id)
        metadata["simulatedCorpusSize"] += int(adapter_metadata.get("simulatedCorpusSize", len(adapter_papers)) or len(adapter_papers))
        papers.extend(adapter_papers)
    return metadata, dedupe_papers(papers)


def adapter_search_or_load(
    adapter: BaseLiteratureAdapter,
    *,
    research_topic: str,
    keywords: list[str],
    domain_filters: dict[str, Any] | None = None,
    limit: int = 5,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    search_method = getattr(adapter, "search", None)
    if callable(search_method):
        return search_method(
            research_topic=research_topic,
            keywords=keywords,
            domain_filters=domain_filters,
            limit=limit,
        )
    return adapter.load_papers()


def collect_adapter_search_results(
    adapters: list[BaseLiteratureAdapter],
    *,
    research_topic: str,
    keywords: list[str],
    domain_filters: dict[str, Any] | None = None,
    limit: int = 5,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(adapters) == 1:
        adapter = adapters[0]
        metadata, papers = adapter_search_or_load(
            adapter,
            research_topic=research_topic,
            keywords=keywords,
            domain_filters=domain_filters,
            limit=limit,
        )
        single_metadata = dict(metadata)
        single_metadata.setdefault("adapterVersion", ADAPTER_VERSION)
        single_metadata.setdefault("indexVersion", single_metadata.get("indexVersion", adapter.adapter_id))
        single_metadata["indexSource"] = single_metadata.get(
            "indexSource",
            "local_mock_index" if adapter.adapter_id == "local_mock" else adapter.source_type,
        )
        single_metadata["sourceBackends"] = single_metadata.get("sourceBackends", [adapter.adapter_id])
        single_metadata.setdefault("simulatedCorpusSize", len(papers))
        return single_metadata, dedupe_papers(papers)

    papers: list[dict[str, Any]] = []
    metadata = {
        "adapterVersion": ADAPTER_VERSION,
        "indexVersion": "multi-backend",
        "indexSource": "multi_backend",
        "sourceBackends": [],
        "simulatedCorpusSize": 0,
        "candidateCount": 0,
        "bibliographicCandidates": [],
        "adapterWarnings": [],
        "retrievalTraces": [],
    }
    for adapter in adapters:
        try:
            adapter_metadata, adapter_papers = adapter_search_or_load(
                adapter,
                research_topic=research_topic,
                keywords=keywords,
                domain_filters=domain_filters,
                limit=limit,
            )
        except Exception as exc:
            adapter_metadata = {
                "adapterId": adapter.adapter_id,
                "simulatedCorpusSize": 0,
                "candidateCount": 0,
                "adapterWarnings": [f"{adapter.adapter_id} failed: {exc}"],
            }
            adapter_papers = []
        metadata["sourceBackends"].append(adapter.adapter_id)
        metadata["simulatedCorpusSize"] += int(adapter_metadata.get("simulatedCorpusSize", len(adapter_papers)) or len(adapter_papers))
        metadata["candidateCount"] += int(adapter_metadata.get("candidateCount", len(adapter_papers)) or len(adapter_papers))
        metadata["bibliographicCandidates"].extend(adapter_metadata.get("bibliographicCandidates", []) or [])
        metadata["adapterWarnings"].extend(adapter_metadata.get("adapterWarnings", []) or [])
        if adapter_metadata.get("retrievalTrace"):
            metadata["retrievalTraces"].append(adapter_metadata["retrievalTrace"])
        papers.extend(adapter_papers)
    return metadata, dedupe_papers(papers)


def default_adapters(
    available_papers: list[dict[str, Any]] | None = None,
    available_cards: list[dict[str, Any]] | None = None,
    *,
    backend: str | None = None,
) -> list[BaseLiteratureAdapter]:
    selected_backend = (backend or os.environ.get("RESEARCH_LITERATURE_BACKEND") or "local_mock").strip().lower()
    adapters: list[BaseLiteratureAdapter] = []
    if selected_backend in {"local_mock", "local", "mock"}:
        adapters.append(LocalMockLiteratureAdapter())
    elif selected_backend == PEDASCOPE_BACKEND:
        adapters.append(PedaScopeMcpAdapter())
    elif selected_backend == "hybrid":
        adapters.extend([PedaScopeMcpAdapter(), LocalMockLiteratureAdapter()])
    else:
        adapters.append(LocalMockLiteratureAdapter())
    if available_papers or available_cards:
        adapters.append(UserUploadAdapter(available_papers, available_cards))
    return adapters


def describe_adapters(adapters: list[BaseLiteratureAdapter]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for adapter in adapters:
        sources.extend(adapter.describe_sources())
    return sources


def load_evidence_cards(
    available_cards: list[dict[str, Any]] | None = None,
    *,
    adapters: list[BaseLiteratureAdapter] | None = None,
) -> list[dict[str, Any]]:
    adapters = adapters or default_adapters(available_cards=available_cards)
    cards: list[dict[str, Any]] = []
    for adapter in adapters:
        cards.extend(adapter.load_evidence_cards())
    if available_cards and not any(isinstance(adapter, UserUploadAdapter) for adapter in adapters):
        cards.extend(canonicalize_evidence_card(card) for card in available_cards if isinstance(card, dict))
    index: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = card.get("cardId")
        if card_id:
            index[str(card_id)] = card
    return list(index.values())


def load_default_papers(
    available_papers: list[dict[str, Any]] | None = None,
    *,
    adapters: list[BaseLiteratureAdapter] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    adapters = adapters or default_adapters(available_papers=available_papers)
    return collect_adapter_papers(adapters)


def relevance_score(paper: dict[str, Any], keywords: list[str], topic: str) -> int:
    text = paper_text(paper)
    score = sum(2 for keyword in keywords if keyword and keyword in text)
    topic_terms = [part for part in topic.replace("，", " ").replace("、", " ").split() if part]
    score += sum(1 for term in topic_terms if term and term in text)
    if has_readable_text(paper.get("textAvailability")):
        score += 1
    if is_source_authentic(paper.get("sourceStatus")):
        score += 1
    return score


def matched_keywords(paper: dict[str, Any], keywords: list[str], topic: str) -> list[str]:
    text = paper_text(paper)
    matches = [keyword for keyword in keywords if keyword and keyword in text]
    for term in topic.replace("，", " ").replace("、", " ").split():
        if term and term in text and term not in matches:
            matches.append(term)
    return list(dict.fromkeys(matches))


def citation_for(paper: dict[str, Any]) -> str:
    authors = "，".join(str(author) for author in paper.get("authors", []) if author) or "作者待确认"
    base = f"{authors}. {paper.get('title', '题名待确认')}[J]. {paper.get('journal', '期刊待确认')}, {paper.get('year', '年份待确认')}"
    volume = paper.get("volume")
    issue = paper.get("issue")
    pages = paper.get("pages")
    if volume and issue and pages:
        return f"{base}, {volume}({issue}): {pages}."
    if pages:
        return f"{base}: {pages}."
    return f"{base}."


def source_locator_for(card: dict[str, Any] | None, paper: dict[str, Any] | None = None) -> dict[str, Any]:
    if card and isinstance(card.get("sourceLocator"), dict):
        locator = dict(card["sourceLocator"])
    else:
        quote_location = card.get("quoteLocation") if card else "abstract"
        locator = {
            "locationType": quote_location or "abstract",
            "locator": quote_location or "abstract",
            "page": card.get("page", "") if card else "",
            "paragraph": card.get("paragraph", quote_location or "") if card else "",
        }
    if paper and locator.get("locationType") == "metadata":
        locator["confidence"] = "low"
    else:
        locator["confidence"] = "medium" if locator.get("locationType") == "abstract" else "high"
    return locator


def search_papers(
    *,
    research_topic: str,
    keywords: list[str],
    available_papers: list[dict[str, Any]] | None = None,
    adapters: list[BaseLiteratureAdapter] | None = None,
    limit: int = 5,
    require_readable_text: bool = False,
    domain_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapters = adapters or default_adapters(available_papers=available_papers)
    metadata, papers = collect_adapter_search_results(
        adapters,
        research_topic=research_topic,
        keywords=keywords,
        domain_filters=domain_filters,
        limit=limit,
    )
    def rank_key(paper: dict[str, Any]) -> tuple[float, int]:
        retrieval_rank = clamp_int(paper.get("retrievalRank"), default=1_000_000, minimum=1, maximum=1_000_000)
        return relevance_score(paper, keywords, research_topic), -retrieval_rank

    ranked = sorted(papers, key=rank_key, reverse=True)
    if require_readable_text:
        ranked = [paper for paper in ranked if has_readable_text(paper.get("textAvailability"))]
    returned = ranked[:limit]
    returned_ids = {paper.get("paperId") for paper in returned}
    bibliographic_candidates = [
        candidate
        for candidate in (metadata.get("bibliographicCandidates", []) or [])
        if candidate.get("paperId") in returned_ids
    ]
    report = {
        "adapterVersion": ADAPTER_VERSION,
        "indexName": metadata.get("indexVersion", "multi-backend"),
        "indexSource": metadata.get("indexSource", "multi_backend"),
        "sourceBackends": metadata.get("sourceBackends", []),
        "dataSources": describe_adapters(adapters),
        "simulatedCorpusSize": metadata.get("simulatedCorpusSize", len(papers)),
        "query": {
            "researchTopic": research_topic,
            "keywords": keywords,
            "filters": {"requireReadableText": require_readable_text, **(domain_filters or {})},
        },
        "candidateCount": max(int(metadata.get("candidateCount", len(papers)) or len(papers)), len(papers)),
        "returnedCount": len(returned),
        "rankingSignals": ["keyword_overlap", "topic_overlap", "text_availability", "source_verification"],
        "topHits": [
            {
                "paperId": paper.get("paperId"),
                "score": relevance_score(paper, keywords, research_topic),
                "matchedKeywords": matched_keywords(paper, keywords, research_topic),
                "textAvailability": paper.get("textAvailability", "metadata"),
                "sourceStatus": paper.get("sourceStatus", "unverified"),
                "selectionReason": "主题匹配且具备可读文本。" if has_readable_text(paper.get("textAvailability")) else "主题相关但当前只有元数据。",
                "source": paper.get("database", "local_mock_index"),
            }
            for paper in returned
        ],
    }
    if bibliographic_candidates:
        report["bibliographicCandidates"] = bibliographic_candidates
    if metadata.get("coverageNote"):
        report["coverageNote"] = metadata["coverageNote"]
    if metadata.get("readingListReport"):
        report["readingListReport"] = metadata["readingListReport"]
    if metadata.get("retrievalTrace"):
        report["retrievalTrace"] = metadata["retrievalTrace"]
    if metadata.get("retrievalTraces"):
        report["retrievalTraces"] = metadata["retrievalTraces"]
    if metadata.get("adapterWarnings"):
        report["adapterWarnings"] = metadata["adapterWarnings"]
    return {"corpusSearchReport": report, "records": returned}


def verify_paper(
    paper_id: str,
    available_papers: list[dict[str, Any]] | None = None,
    *,
    adapters: list[BaseLiteratureAdapter] | None = None,
) -> dict[str, Any]:
    _, papers = load_default_papers(available_papers, adapters=adapters)
    paper = next((item for item in papers if item.get("paperId") == paper_id), None)
    if not paper:
        return {
            "paperId": paper_id,
            "decision": "no_source_found",
            "isVerified": False,
            "reason": "当前适配器候选池未找到该 paperId。",
        }
    missing = [field for field in REQUIRED_PAPER_FIELDS if not paper.get(field)]
    return {
        "paperId": paper_id,
        "decision": "verified_source_found" if not missing else "related_sources_only",
        "isVerified": not missing,
        "missingFields": missing,
        "textAvailability": paper.get("textAvailability"),
        "sourceStatus": paper.get("sourceStatus"),
        "paper": paper,
    }


def can_support(query_text: str, candidate_text: str, card: dict[str, Any]) -> bool:
    if query_text and query_text in candidate_text:
        return True
    required = major_terms(query_text)
    if not required:
        return False
    candidate_terms = major_terms(candidate_text)
    return required.issubset(candidate_terms) and can_support_claim(card.get("evidenceLevel"), card.get("supportType"))


def source_trace(
    *,
    query_text: str,
    available_papers: list[dict[str, Any]] | None = None,
    available_cards: list[dict[str, Any]] | None = None,
    adapters: list[BaseLiteratureAdapter] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    adapters = adapters or default_adapters(available_papers=available_papers, available_cards=available_cards)
    trace_enabled_adapters = [adapter for adapter in adapters if callable(getattr(adapter, "trace_claim", None))]
    local_trace_adapters = [adapter for adapter in adapters if adapter not in trace_enabled_adapters]
    _, papers = load_default_papers(available_papers, adapters=local_trace_adapters) if local_trace_adapters else ({}, [])
    paper_index = {paper.get("paperId"): paper for paper in papers if paper.get("paperId")}
    query_terms = tokenize(query_text)
    candidates = []
    usable_cards = []
    trace_warnings: list[str] = []
    pedascope_papers: list[dict[str, Any]] = []
    for adapter in trace_enabled_adapters:
        trace_payload = adapter.trace_claim(query_text=query_text, limit=limit)
        candidates.extend(trace_payload.get("candidates", []) or [])
        pedascope_papers.extend(trace_payload.get("papers", []) or [])
        trace_warnings.extend(trace_payload.get("warnings", []) or [])
    for card in load_evidence_cards(available_cards, adapters=adapters):
        paper = paper_index.get(card.get("paperId"))
        if not paper:
            continue
        combined = f"{card.get('claim', '')} {card.get('evidenceText', '')}"
        score = len(query_terms.intersection(tokenize(combined)))
        if score <= 0:
            continue
        support_status = "supports" if can_support(query_text, combined, card) else "related_only"
        candidate = {
            "paperId": card.get("paperId"),
            "matchType": "evidence_card",
            "evidenceCardId": card.get("cardId"),
            "supportStatus": support_status,
            "confidence": "medium" if support_status == "supports" else "low",
            "evidenceLevel": card.get("evidenceLevel"),
            "quoteLocation": card.get("quoteLocation"),
            "sourceLocator": source_locator_for(card, paper),
            "citation": citation_for(paper),
            "score": score,
            "matchSnippet": card.get("evidenceText", ""),
        }
        candidates.append(candidate)
        if support_status == "supports":
            usable_cards.append(card)

    candidate_ids = {candidate.get("paperId") for candidate in candidates}
    for paper in papers:
        if paper.get("paperId") in candidate_ids:
            continue
        combined = paper_text(paper)
        score = len(query_terms.intersection(tokenize(combined)))
        if score <= 0:
            continue
        match_type = "abstract" if paper.get("abstract") else "metadata"
        candidates.append(
            {
                "paperId": paper.get("paperId"),
                "matchType": match_type,
                "matchSnippet": paper.get("abstract") or paper.get("title", ""),
                "supportStatus": "related_only",
                "confidence": "medium" if score >= 3 else "low",
                "quoteLocation": match_type,
                "sourceLocator": source_locator_for(None, paper),
                "evidenceLevel": "abstract_verified" if match_type == "abstract" else "metadata_verified",
                "citation": citation_for(paper),
                "score": score,
            }
        )

    if usable_cards:
        decision = "verified_source_found"
    elif any(candidate.get("matchType") == "pedascope_claim_candidate" for candidate in candidates):
        decision = "candidate_source_found"
    elif candidates:
        decision = "related_sources_only"
    else:
        decision = "no_source_found"
    return {
        "adapterVersion": ADAPTER_VERSION,
        "queryText": query_text,
        "decision": decision,
        "sourceBackends": [adapter.adapter_id for adapter in adapters],
        "candidates": candidates[:limit],
        "usableEvidenceCards": usable_cards,
        "papers": dedupe_papers([*pedascope_papers, *papers]),
        "warnings": trace_warnings,
    }


def first_capable_adapter(adapters: list[BaseLiteratureAdapter], method_name: str) -> BaseLiteratureAdapter | None:
    for adapter in adapters:
        if callable(getattr(adapter, method_name, None)):
            return adapter
    return None


def verify_citation_record(citation: dict[str, Any], *, adapters: list[BaseLiteratureAdapter] | None = None) -> dict[str, Any]:
    adapters = adapters or default_adapters()
    adapter = first_capable_adapter(adapters, "verify_citation")
    if not adapter:
        return {
            "verified": False,
            "confidence": "none",
            "verificationStatus": "not_available",
            "verificationNote": "当前文献后端不支持题录真实性验证。",
            "limits": ["未接入 verify_citation 能力。"],
        }
    return getattr(adapter, "verify_citation")(citation)


def find_research_gaps(
    *,
    keywords: list[str],
    domain: str = "",
    adapters: list[BaseLiteratureAdapter] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    adapters = adapters or default_adapters()
    adapter = first_capable_adapter(adapters, "find_research_gaps")
    if not adapter:
        return {"status": "not_available", "limits": ["当前文献后端不支持研究态势分析。"]}
    return getattr(adapter, "find_research_gaps")(keywords=keywords, domain=domain, limit=limit)


def suggest_research_keywords(
    *,
    seed_keywords: list[str] | None = None,
    topic: str = "",
    adapters: list[BaseLiteratureAdapter] | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    adapters = adapters or default_adapters()
    adapter = first_capable_adapter(adapters, "suggest_keywords")
    if not adapter:
        return {"status": "not_available", "suggestedKeywords": [], "limits": ["当前文献后端不支持关键词扩展。"]}
    return getattr(adapter, "suggest_keywords")(seed_keywords=seed_keywords, topic=topic, limit=limit)


def build_structured_reading_list(
    *,
    topic: str,
    adapters: list[BaseLiteratureAdapter] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    adapters = adapters or default_adapters()
    adapter = first_capable_adapter(adapters, "build_reading_list")
    if not adapter:
        return {"status": "not_available", "records": [], "readingListReport": {"limits": ["当前文献后端不支持结构化阅读清单。"]}}
    return getattr(adapter, "build_reading_list")(topic=topic, year_from=year_from, year_to=year_to, limit=limit)


def compare_research_topics(
    *,
    topic_a: str,
    topic_b: str,
    adapters: list[BaseLiteratureAdapter] | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    adapters = adapters or default_adapters()
    adapter = first_capable_adapter(adapters, "compare_topics")
    if not adapter:
        return {"status": "not_available", "limits": ["当前文献后端不支持选题差异化比较。"]}
    return getattr(adapter, "compare_topics")(topic_a=topic_a, topic_b=topic_b, limit=limit)


def parse_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，、\s]+", value) if item.strip()]


def load_optional_records(path: str | None, *, array_key: str) -> list[dict[str, Any]]:
    if not path:
        return []
    data = read_json(Path(path))
    records = data.get(array_key, data if isinstance(data, list) else []) if isinstance(data, dict) else data
    return [record for record in records if isinstance(record, dict)]


def build_cli_adapters(args: argparse.Namespace) -> list[BaseLiteratureAdapter]:
    user_papers = load_optional_records(getattr(args, "papers_json", None), array_key="papers")
    user_cards = load_optional_records(getattr(args, "cards_json", None), array_key="evidenceCards")
    backend = getattr(args, "backend", None) or os.environ.get("RESEARCH_LITERATURE_BACKEND") or "local_mock"
    adapters: list[BaseLiteratureAdapter] = []
    if backend in {None, "", "local_mock"} and not getattr(args, "no_local_mock", False):
        adapters.append(LocalMockLiteratureAdapter())
    elif backend == PEDASCOPE_BACKEND:
        adapters.append(PedaScopeMcpAdapter())
    elif backend == "hybrid":
        adapters.append(PedaScopeMcpAdapter())
        if not getattr(args, "no_local_mock", False):
            adapters.append(LocalMockLiteratureAdapter())
    if getattr(args, "authorized_index_json", None):
        adapters.append(AuthorizedDatabaseAdapter(args.authorized_index_json))
    if getattr(args, "external_metadata_json", None):
        adapters.append(ExternalMetadataAdapter(args.external_metadata_json))
    if user_papers or user_cards:
        adapters.append(UserUploadAdapter(user_papers, user_cards))
    return adapters or default_adapters(user_papers, user_cards)


def add_adapter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", choices=["local_mock", "pedascope", "hybrid"], help="文献检索后端。默认 local_mock；也可由 RESEARCH_LITERATURE_BACKEND 指定。")
    parser.add_argument("--no-local-mock", action="store_true", help="不加载本地 mock 索引和样例白名单。")
    parser.add_argument("--authorized-index-json", help="授权库离线索引 JSON，字段可为 papers。")
    parser.add_argument("--external-metadata-json", help="外部元数据索引 JSON，字段可为 papers。")
    parser.add_argument("--papers-json", help="用户提供文献记录 JSON，字段可为 papers。")
    parser.add_argument("--cards-json", help="用户提供 EvidenceCard JSON，字段可为 evidenceCards。")


def main() -> int:
    parser = argparse.ArgumentParser(description="科研线文献数据源适配器。")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="检索候选文献。")
    search.add_argument("--topic", default="")
    search.add_argument("--keywords", default="")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--require-readable-text", action="store_true")
    add_adapter_args(search)

    verify = sub.add_parser("verify", help="按 paperId 验证文献真实性。")
    verify.add_argument("--paper-id", required=True)
    add_adapter_args(verify)

    trace = sub.add_parser("trace", help="查找论点对应来源和支撑证据。")
    trace.add_argument("--query", required=True)
    trace.add_argument("--limit", type=int, default=5)
    add_adapter_args(trace)

    verify_citation_cmd = sub.add_parser("verify-citation", help="按题录字段验证引用真实性。")
    verify_citation_cmd.add_argument("--title", default="")
    verify_citation_cmd.add_argument("--authors", default="")
    verify_citation_cmd.add_argument("--year", default="")
    verify_citation_cmd.add_argument("--journal", default="")
    verify_citation_cmd.add_argument("--doi", default="")
    add_adapter_args(verify_citation_cmd)

    gaps = sub.add_parser("gaps", help="分析研究方向的题录密度和关键词态势。")
    gaps.add_argument("--keywords", default="")
    gaps.add_argument("--domain", default="")
    gaps.add_argument("--limit", type=int, default=50)
    add_adapter_args(gaps)

    suggest = sub.add_parser("suggest-keywords", help="基于种子关键词推荐扩展关键词。")
    suggest.add_argument("--keywords", default="")
    suggest.add_argument("--topic", default="")
    suggest.add_argument("--limit", type=int, default=30)
    add_adapter_args(suggest)

    reading = sub.add_parser("reading-list", help="生成结构化优先阅读清单。")
    reading.add_argument("--topic", required=True)
    reading.add_argument("--year-from", type=int)
    reading.add_argument("--year-to", type=int)
    reading.add_argument("--limit", type=int, default=20)
    add_adapter_args(reading)

    compare = sub.add_parser("compare-topics", help="比较两个选题的题录重叠和差异化。")
    compare.add_argument("--topic-a", required=True)
    compare.add_argument("--topic-b", required=True)
    compare.add_argument("--limit", type=int, default=30)
    add_adapter_args(compare)

    args = parser.parse_args()
    adapters = build_cli_adapters(args)
    if args.command == "search":
        payload = search_papers(
            research_topic=args.topic,
            keywords=parse_keywords(args.keywords),
            adapters=adapters,
            limit=args.limit,
            require_readable_text=args.require_readable_text,
        )
    elif args.command == "verify":
        payload = verify_paper(args.paper_id, adapters=adapters)
    elif args.command == "trace":
        payload = source_trace(query_text=args.query, adapters=adapters, limit=args.limit)
    elif args.command == "verify-citation":
        payload = verify_citation_record(
            {
                "title": args.title,
                "authors": parse_keywords(args.authors),
                "year": args.year,
                "journal": args.journal,
                "doi": args.doi,
            },
            adapters=adapters,
        )
    elif args.command == "gaps":
        payload = find_research_gaps(keywords=parse_keywords(args.keywords), domain=args.domain, adapters=adapters, limit=args.limit)
    elif args.command == "suggest-keywords":
        payload = suggest_research_keywords(seed_keywords=parse_keywords(args.keywords), topic=args.topic, adapters=adapters, limit=args.limit)
    elif args.command == "reading-list":
        payload = build_structured_reading_list(
            topic=args.topic,
            adapters=adapters,
            year_from=args.year_from,
            year_to=args.year_to,
            limit=args.limit,
        )
    else:
        payload = compare_research_topics(topic_a=args.topic_a, topic_b=args.topic_b, adapters=adapters, limit=args.limit)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
