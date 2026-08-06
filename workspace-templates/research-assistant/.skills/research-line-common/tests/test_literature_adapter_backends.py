from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = COMMON_ROOT.parents[1]


def load_module(name: str, relative_path: str):
    path = COMMON_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(COMMON_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(COMMON_ROOT))
    return module


literature_adapter = load_module("literature_adapter_backends_for_test", "literature_adapter.py")


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"args: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def write_index(path: Path, paper_id: str, title: str) -> None:
    payload = {
        "metadata": {"indexVersion": "adapter-test-index"},
        "papers": [
            {
                "paperId": paper_id,
                "title": title,
                "authors": ["测试作者"],
                "year": 2025,
                "journal": "测试期刊",
                "keywords": ["即时反馈", "错因诊断"],
                "abstract": "即时反馈和错因诊断可帮助教师调整讲评顺序。",
                "textAvailability": "abstract",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class FakePedaScopeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def tool(self, name: str, arguments: dict | None = None) -> dict:
        arguments = arguments or {}
        self.calls.append((name, arguments))
        if name == "health":
            return {
                "server": "pedascope-kb-mcp",
                "version": "0.2.2",
                "content_policy": {
                    "full_text_returned": False,
                    "raw_snippets_returned": False,
                },
            }
        if name in {"search_by_topic", "search_by_keywords", "search_by_domain"}:
            return {
                "query_text": arguments.get("topic") or " ".join(arguments.get("keywords", [])),
                "items": [
                    {
                        "paper_id": "paper_fake_pedascope_001",
                        "title": "PedaScope 题录中的即时反馈研究",
                        "abstract": "该摘要为系统根据题录和检索信号生成的非逐字摘要，未透传原始摘要或全文。",
                        "abstract_type": "generated_non_verbatim",
                        "authors": ["测试作者甲", "测试作者乙"],
                        "year": "2024",
                        "journal": "教育研究测试",
                        "doi": "10.0000/test.001",
                        "keywords": ["即时反馈", "错因诊断"],
                        "relevance_score": 0.91,
                        "source_db": "PedaScope KB",
                    }
                ],
                "pagination": {"returned": 1},
                "coverage_note": "返回为安全题录和系统生成摘要；未返回原始摘要、全文、片段、original_doc_id 或向量。",
                "trace": {
                    "tool_version": "0.2.2",
                    "retrieval_mode": "vector_internal",
                    "source": "PedaScope KB public API",
                },
            }
        if name == "build_reading_list":
            return {
                "topic": arguments.get("topic", ""),
                "reading_list": [
                    {
                        "paper_id": "paper_fake_pedascope_001",
                        "title": "PedaScope 题录中的即时反馈研究",
                        "authors": ["测试作者甲", "测试作者乙"],
                        "year": "2024",
                        "journal": "教育研究测试",
                        "doi": "10.0000/test.001",
                        "keywords": ["即时反馈", "错因诊断"],
                        "citation_count": 12,
                        "relevance_score": 0.91,
                        "priority": "must_read",
                        "score": 63.5,
                        "reasons": ["相关度 0.91", "中引用(12)", "最新研究"],
                    }
                ],
                "summary": {"total": 1, "by_priority": {"must_read": 1}},
                "priority_guide": {"must_read": "高相关度+高引用+近年发表，优先精读"},
                "trace": {
                    "tool_version": "0.2.2",
                    "retrieval_mode": "reading_list",
                    "source": "PedaScope KB public API",
                },
            }
        if name == "trace_claim":
            return {
                "claim": arguments.get("claim", ""),
                "verdict": "candidate_support_found",
                "matches": [
                    {
                        "paper_id": "paper_fake_trace_001",
                        "title": "课堂即时反馈与教学决策调整",
                        "authors": ["测试作者"],
                        "year": "2023",
                        "journal": "课堂教学测试",
                        "doi": "",
                        "keywords": ["即时反馈", "教学决策"],
                        "relation": "support_or_related_candidate",
                        "support_strength": "strong",
                        "overlap_signal": 0.5,
                        "evidence_note": "未返回原文证据片段。",
                    }
                ],
                "notes_for_writer": ["正式引用前需要人工或合法全文渠道确认。"],
            }
        if name == "get_citation":
            return {
                "paper_id": arguments.get("paper_id"),
                "style": "GB/T 7714-2015 draft",
                "formatted_reference": "测试作者. 课堂即时反馈与教学决策调整[J]. 课堂教学测试, 2023.",
                "fields": {"title": "课堂即时反馈与教学决策调整"},
                "verification_note": "题录字段生成的草案。",
            }
        if name == "verify_citation":
            return {
                "verified": True,
                "confidence": "high",
                "best_match": {
                    "paper_id": "paper_fake_pedascope_001",
                    "title": arguments.get("title", "PedaScope 题录中的即时反馈研究"),
                    "authors": arguments.get("authors", ["测试作者甲"]),
                    "year": arguments.get("year", "2024"),
                    "journal": arguments.get("journal", "教育研究测试"),
                    "doi": arguments.get("doi", "10.0000/test.001"),
                    "match_score": 0.92,
                    "fields_matched": {"title": "exact"},
                },
                "total_candidates": 1,
                "top_candidates": [],
                "verification_note": "基于 PedaScope KB 150万篇教育论文白名单的题录匹配验证。",
            }
        if name == "find_research_gaps":
            return {
                "query_text": " ".join(arguments.get("keywords", [])),
                "total_papers_analyzed": 25,
                "year_distribution": {"2023": 8, "2024": 12, "2025": 5},
                "top_keywords": [{"keyword": "即时反馈", "count": 10}],
                "sparse_periods": [],
                "density_assessment": {"total_results": 25, "year_range": "2023-2025", "avg_per_year": 8.3},
                "gap_hints": ["相关题录较多，建议细化研究对象。"],
                "coverage_note": "基于检索结果的元数据分析。",
            }
        if name == "suggest_keywords":
            return {
                "seed_query": "即时反馈",
                "total_papers_analyzed": 25,
                "suggested_keywords": [{"keyword": "错因诊断", "frequency": 7, "trend": "rising"}],
                "usage_note": "这些关键词从检索结果的元数据中提取。",
            }
        if name == "compare_topics":
            return {
                "topic_a": arguments.get("topic_a", ""),
                "topic_b": arguments.get("topic_b", ""),
                "comparison": {"papers_for_a": 20, "papers_for_b": 20, "shared_by_doi": 2, "overlap_ratio": 0.1, "differentiation": "high"},
                "shared_papers": [{"paper_id": "paper_shared_001", "title": "共享题录", "doi": "10.0000/shared"}],
                "shared_keywords": ["即时反馈"],
                "unique_keywords_a": ["错因诊断"],
                "unique_keywords_b": ["学习证据"],
                "advice": "两个选题差异明显，各自有独立研究空间。",
                "coverage_note": "结果受检索深度限制。",
            }
        raise AssertionError(f"unexpected fake PedaScope tool: {name}")


class LiteratureAdapterBackendTests(unittest.TestCase):
    def test_user_upload_adapter_marks_sources_as_user_provided(self) -> None:
        adapter = literature_adapter.UserUploadAdapter(
            papers=[
                {
                    "paperId": "user-paper-001",
                    "title": "用户上传即时反馈研究",
                    "authors": ["用户作者"],
                    "year": 2024,
                    "journal": "用户期刊",
                    "keywords": ["即时反馈"],
                    "abstract": "用户提供材料讨论即时反馈对讲评策略的启发。",
                    "textAvailability": "abstract",
                }
            ],
            evidence_cards=[
                {
                    "cardId": "user-card-001",
                    "paperId": "user-paper-001",
                    "claim": "即时反馈可启发讲评策略调整。",
                    "evidenceText": "用户提供材料讨论即时反馈对讲评策略的启发。",
                    "quoteLocation": "abstract",
                    "supportType": "partial_support",
                    "evidenceLevel": "abstract_verified",
                    "limits": ["用户提供文献真实性需另验。"],
                }
            ],
        )

        metadata, papers = literature_adapter.load_default_papers(adapters=[adapter])
        cards = literature_adapter.load_evidence_cards(adapters=[adapter])

        self.assertEqual(metadata["sourceBackends"], ["user_upload"])
        self.assertEqual(papers[0]["sourceStatus"], "user_provided")
        self.assertEqual(papers[0]["database"], "user_available_papers")
        self.assertEqual(cards[0]["cardId"], "user-card-001")

        result = literature_adapter.search_papers(
            research_topic="即时反馈",
            keywords=["即时反馈"],
            adapters=[adapter],
            limit=1,
        )
        self.assertEqual(result["corpusSearchReport"]["sourceBackends"], ["user_upload"])
        self.assertEqual(result["corpusSearchReport"]["dataSources"][0]["sourceType"], "user_provided")

    def test_authorized_database_adapter_can_replace_local_mock_pool(self) -> None:
        with tempfile.TemporaryDirectory(prefix="literature-adapter-auth-") as tmpdir:
            index_path = Path(tmpdir) / "authorized-index.json"
            write_index(index_path, "auth-paper-001", "授权库中的即时反馈研究")

            adapter = literature_adapter.AuthorizedDatabaseAdapter(index_path)
            search = literature_adapter.search_papers(
                research_topic="即时反馈",
                keywords=["即时反馈"],
                adapters=[adapter],
                limit=1,
            )
            verify = literature_adapter.verify_paper("auth-paper-001", adapters=[adapter])

            self.assertEqual(search["records"][0]["paperId"], "auth-paper-001")
            self.assertEqual(search["records"][0]["sourceStatus"], "external_verified")
            self.assertEqual(search["corpusSearchReport"]["sourceBackends"], ["authorized_database"])
            self.assertEqual(search["corpusSearchReport"]["dataSources"][0]["authorizationStatus"], "authorized")
            self.assertTrue(verify["isVerified"])

    def test_cli_can_search_without_local_mock_using_authorized_index(self) -> None:
        with tempfile.TemporaryDirectory(prefix="literature-adapter-cli-") as tmpdir:
            index_path = Path(tmpdir) / "authorized-index.json"
            write_index(index_path, "auth-paper-cli-001", "CLI 授权库即时反馈研究")

            result = run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/literature_adapter.py",
                    "search",
                    "--topic",
                    "即时反馈",
                    "--keywords",
                    "即时反馈",
                    "--no-local-mock",
                    "--authorized-index-json",
                    str(index_path),
                    "--limit",
                    "1",
                ]
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["records"][0]["paperId"], "auth-paper-cli-001")
            self.assertEqual(payload["corpusSearchReport"]["sourceBackends"], ["authorized_database"])

    def test_pedascope_adapter_maps_metadata_to_bibliographic_candidates(self) -> None:
        adapter = literature_adapter.PedaScopeMcpAdapter(client=FakePedaScopeClient())

        search = literature_adapter.search_papers(
            research_topic="小学数学即时反馈",
            keywords=["即时反馈", "错因诊断"],
            adapters=[adapter],
            limit=1,
        )

        record = search["records"][0]
        report = search["corpusSearchReport"]
        candidate = report["bibliographicCandidates"][0]
        source = report["dataSources"][0]

        self.assertEqual(report["indexSource"], "pedascope_kb")
        self.assertEqual(record["sourceStatus"], "external_verified")
        self.assertEqual(record["textAvailability"], "metadata")
        self.assertEqual(record["evidenceLevel"], "metadata_verified")
        self.assertEqual(record["abstractType"], "generated_non_verbatim")
        self.assertEqual(candidate["paperId"], record["paperId"])
        self.assertEqual(candidate["textAvailability"], "metadata")
        self.assertEqual(candidate["evidenceLevel"], "metadata_verified")
        self.assertTrue(candidate["limits"])
        self.assertEqual(record["readingPriority"], "must_read")
        self.assertEqual(report["readingListReport"]["readingList"][0]["priority"], "must_read")
        self.assertEqual(source["sourceId"], "pedascope-kb")
        self.assertEqual(source["recordCount"], 1_500_000)
        self.assertEqual(source["authorizationStatus"], "public_metadata_service")

    def test_pedascope_trace_returns_candidate_source_not_evidence_card(self) -> None:
        adapter = literature_adapter.PedaScopeMcpAdapter(client=FakePedaScopeClient())

        trace = literature_adapter.source_trace(
            query_text="课堂即时反馈有助于教师调整教学决策。",
            adapters=[adapter],
            limit=1,
        )

        self.assertEqual(trace["decision"], "candidate_source_found")
        self.assertEqual(trace["usableEvidenceCards"], [])
        self.assertEqual(trace["candidates"][0]["matchType"], "pedascope_claim_candidate")
        self.assertEqual(trace["candidates"][0]["evidenceLevel"], "metadata_verified")
        self.assertEqual(trace["candidates"][0]["quoteLocation"], "metadata")
        self.assertFalse(trace["candidates"][0]["rawEvidenceReturned"])
        self.assertIn("GB/T 7714", trace["candidates"][0]["citationDraft"]["style"])

    def test_pedascope_enhanced_tools_are_normalized(self) -> None:
        adapter = literature_adapter.PedaScopeMcpAdapter(client=FakePedaScopeClient())

        verification = adapter.verify_citation({"title": "PedaScope 题录中的即时反馈研究", "year": "2024"})
        gaps = adapter.find_research_gaps(keywords=["即时反馈"], limit=10)
        suggestions = adapter.suggest_keywords(seed_keywords=["即时反馈"], limit=10)
        comparison = adapter.compare_topics(topic_a="即时反馈", topic_b="错因诊断", limit=10)

        self.assertTrue(verification["verified"])
        self.assertEqual(verification["verificationStatus"], "verified")
        self.assertEqual(gaps["totalPapersAnalyzed"], 25)
        self.assertTrue(gaps["limits"])
        self.assertEqual(suggestions["suggestedKeywords"][0]["keyword"], "错因诊断")
        self.assertEqual(comparison["comparison"]["differentiation"], "high")
        self.assertIn("不构成完整研究空白证明", "；".join(comparison["limits"]))


if __name__ == "__main__":
    unittest.main()
