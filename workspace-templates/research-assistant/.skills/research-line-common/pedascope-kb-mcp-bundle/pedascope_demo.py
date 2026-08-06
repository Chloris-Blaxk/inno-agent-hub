#!/usr/bin/env python3
"""PedaScope KB 论文检索 — 全功能单文件演示

本文件封装了与 PedaScope KB MCP Server 通信的全部逻辑，并提供 11 大场景的完整案例，
直接运行即可体验所有功能。

运行方式:
    python3 pedascope_demo.py              # 运行全部 11 个场景案例
    python3 pedascope_demo.py --scenario 1  # 只运行场景 1
    python3 pedascope_demo.py --scenario 7  # 只运行场景 7（新增增强接口）
    ...                                     # --scenario 1~11

环境依赖:
    - Python 3.10+（无第三方包依赖）
    - 需要同目录下的 kb_mcp.py 作为 MCP Server
    - 需要网络访问 https://pedascope.ecnu.edu.cn/kb_search_api
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

SERVER_SCRIPT = Path(__file__).resolve().parent / "kb_mcp.py"
DEFAULT_BASE_URL = "https://pedascope.ecnu.edu.cn/kb_search_api"


# ──────────────────────────────────────────────
# MCP 客户端通信层
# ──────────────────────────────────────────────

class PedaScopeClient:
    """PedaScope KB MCP Server 的简易客户端。"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url
        self._rid = 0
        self._proc = self._start_server()

    def _start_server(self) -> subprocess.Popen[str]:
        env = os.environ.copy()
        env["PEDASCOPE_KB_BASE_URL"] = self.base_url
        env.setdefault("PEDASCOPE_KB_TIMEOUT_SECONDS", "30")
        self._proc = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        # 初始化握手
        self._send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        return self._proc

    def _next_id(self) -> int:
        self._rid += 1
        return self._rid

    def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP Server 未返回响应")
        return json.loads(line)

    def _call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        resp = self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        })
        result = resp.get("result", {})
        # 优先读取 structuredContent
        if isinstance(result.get("structuredContent"), dict):
            payload = result["structuredContent"]
        else:
            content = result.get("content") or []
            text = content[0].get("text", "{}") if content else "{}"
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"text": text}
        if result.get("isError"):
            raise RuntimeError(f"工具调用失败: {payload}")
        return payload

    def close(self) -> None:
        if self._proc.stdin is not None:
            self._proc.stdin.close()
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()

    # ── 六大工具方法 ──

    def search_by_keywords(self, keywords: str | list[str], *,
                           top_k: int = 10, page_size: int = 10) -> dict[str, Any]:
        """场景 1：按关键词检索文献。"""
        return self._call("search_by_keywords", {
            "keywords": keywords,
            "top_k": top_k,
            "page_size": page_size,
        })

    def search_by_topic(self, topic: str, *,
                        top_k: int = 10, page_size: int = 10) -> dict[str, Any]:
        """场景 2：按自然语言选题/研究问题做语义检索。"""
        return self._call("search_by_topic", {
            "topic": topic,
            "top_k": top_k,
            "page_size": page_size,
        })

    def search_by_domain(self, *, stage: str = "", subject: str = "",
                         research_domain: str = "", research_method: str = "",
                         topic: str = "", keywords: str | list[str] | None = None,
                         year_from: int | None = None, year_to: int | None = None,
                         journal: str = "", must_have_doi: bool = False,
                         citation_min: int = 0, top_k: int = 20,
                         page_size: int = 10) -> dict[str, Any]:
        """场景 3：按学段/学科/领域/方法等结构化条件检索。"""
        args: dict[str, Any] = {"top_k": top_k, "page_size": page_size}
        if stage:
            args["stage"] = stage
        if subject:
            args["subject"] = subject
        if research_domain:
            args["research_domain"] = research_domain
        if research_method:
            args["research_method"] = research_method
        if topic:
            args["topic"] = topic
        if keywords:
            args["keywords"] = keywords
        if year_from is not None:
            args["year_from"] = year_from
        if year_to is not None:
            args["year_to"] = year_to
        if journal:
            args["journal"] = journal
        if must_have_doi:
            args["must_have_doi"] = True
        if citation_min > 0:
            args["citation_min"] = citation_min
        return self._call("search_by_domain", args)

    def get_paper(self, paper_id: str) -> dict[str, Any]:
        """场景 4：根据 paper_id 获取完整题录卡片。"""
        return self._call("get_paper", {"paper_id": paper_id})

    def trace_claim(self, claim: str, *, domain_hint: str = "",
                    top_k: int = 10) -> dict[str, Any]:
        """场景 5：给定 claim，追溯支撑来源。"""
        args: dict[str, Any] = {"claim": claim, "top_k": top_k}
        if domain_hint:
            args["domain_hint"] = domain_hint
        return self._call("trace_claim", args)

    def get_citation(self, paper_id: str) -> dict[str, Any]:
        """场景 6：根据 paper_id 生成 GB/T 7714-2015 引用草案。"""
        return self._call("get_citation", {"paper_id": paper_id})

    def verify_citation(self, *, title: str = "", authors: str | list[str] | None = None,
                        year: str = "", journal: str = "", doi: str = "") -> dict[str, Any]:
        """场景 7：验证引用真实性（反幻觉锚点）。"""
        args: dict[str, Any] = {}
        if title:
            args["title"] = title
        if authors:
            args["authors"] = authors
        if year:
            args["year"] = year
        if journal:
            args["journal"] = journal
        if doi:
            args["doi"] = doi
        return self._call("verify_citation", args)

    def find_research_gaps(self, *, keywords: str | list[str] | None = None,
                           domain: str = "", top_k: int = 100) -> dict[str, Any]:
        """场景 8：研究空白/热点探测。"""
        args: dict[str, Any] = {"top_k": top_k}
        if keywords:
            args["keywords"] = keywords
        if domain:
            args["domain"] = domain
        return self._call("find_research_gaps", args)

    def suggest_keywords(self, *, seed_keywords: str | list[str] | None = None,
                         topic: str = "", top_k: int = 50) -> dict[str, Any]:
        """场景 9：关键词推荐/扩展。"""
        args: dict[str, Any] = {"top_k": top_k}
        if seed_keywords:
            args["seed_keywords"] = seed_keywords
        if topic:
            args["topic"] = topic
        return self._call("suggest_keywords", args)

    def build_reading_list(self, topic: str, *, year_from: int | None = None,
                           year_to: int | None = None, top_k: int = 30) -> dict[str, Any]:
        """场景 10：结构化阅读清单生成。"""
        args: dict[str, Any] = {"topic": topic, "top_k": top_k}
        if year_from is not None:
            args["year_from"] = year_from
        if year_to is not None:
            args["year_to"] = year_to
        return self._call("build_reading_list", args)

    def compare_topics(self, topic_a: str, topic_b: str, *,
                       top_k: int = 30) -> dict[str, Any]:
        """场景 11：选题重复度/差异化分析。"""
        return self._call("compare_topics", {
            "topic_a": topic_a, "topic_b": topic_b, "top_k": top_k,
        })


# ──────────────────────────────────────────────
# 输出格式化
# ──────────────────────────────────────────────

SEP = "=" * 65
SUBSEP = "-" * 65


def banner(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  场景: {title}")
    print(SEP)


def print_paper(paper: dict[str, Any], idx: int | None = None) -> None:
    prefix = f"  [{idx}] " if idx is not None else "  "
    title = paper.get("title") or "无标题"
    authors = paper.get("authors", [])
    year = paper.get("year") or "未知"
    journal = paper.get("journal") or paper.get("venue") or ""
    doi = paper.get("doi") or ""
    keywords = paper.get("keywords", [])
    abstract = paper.get("abstract") or ""
    score = paper.get("relevance_score")
    source_db = paper.get("source_db") or ""

    print(f"{prefix}标题:   {title}")
    if authors:
        a = ", ".join(authors[:5]) + (" 等" if len(authors) > 5 else "")
        print(f"  {' ' * len(prefix)}作者:   {a}")
    print(f"  {' ' * len(prefix)}年份:   {year}")
    if journal:
        print(f"  {' ' * len(prefix)}期刊:   {journal}")
    if doi:
        print(f"  {' ' * len(prefix)}DOI:    {doi}")
    if keywords:
        print(f"  {' ' * len(prefix)}关键词: {', '.join(keywords[:8])}")
    if source_db:
        print(f"  {' ' * len(prefix)}来源库: {source_db}")
    if score is not None:
        print(f"  {' ' * len(prefix)}相关度: {score:.4f}")
    if abstract:
        for part in abstract.split("；"):
            part = part.strip()
            if part:
                print(f"  {' ' * len(prefix)}摘要:   {part}")
    pid = paper.get("paper_id") or paper.get("id") or ""
    if pid:
        print(f"  {' ' * len(prefix)}paper_id: {pid}")
    print()


def print_items(items: list[dict[str, Any]]) -> list[str]:
    """打印搜索结果列表，返回 paper_id 列表。"""
    ids: list[str] = []
    for i, item in enumerate(items, 1):
        print_paper(item, i)
        ids.append(item.get("paper_id") or "")
    return ids


# ──────────────────────────────────────────────
# 六大场景案例
# ──────────────────────────────────────────────

def scenario_1_keywords(client: PedaScopeClient) -> list[str]:
    """场景 1：按关键词检索文献。"""
    banner("1. search_by_keywords — 按关键词检索")
    print("""
  需求: 给定关键词，返回标题、摘要、作者、年份、期刊、关键词。
  示例: 关键词 = ["人工智能", "教师专业发展"]
    """)

    result = client.search_by_keywords(
        keywords=["人工智能", "教师专业发展"],
        top_k=5,
        page_size=3,
    )

    items = result.get("items") or result.get("results") or []
    print(f"  检索词: {result.get('query_text', '')}")
    print(f"  返回数量: {len(items)}")
    print(SUBSEP)
    return print_items(items)


def scenario_2_topic(client: PedaScopeClient) -> list[str]:
    """场景 2：按自然语言选题做语义检索。"""
    banner("2. search_by_topic — 语义检索")
    print("""
  需求: 给定自然语言选题/研究问题，做语义检索，返回最相关文献。
  示例: topic = "AI如何支持教师专业发展？"
    """)

    result = client.search_by_topic(
        topic="AI如何支持教师专业发展？",
        top_k=5,
        page_size=3,
    )

    items = result.get("items") or result.get("results") or []
    print(f"  检索问题: {result.get('query_text', '')}")
    print(f"  返回数量: {len(items)}")
    print(SUBSEP)
    return print_items(items)


def scenario_3_domain(client: PedaScopeClient) -> list[str]:
    """场景 3：按学段/学科/领域/方法等结构化条件检索。"""
    banner("3. search_by_domain — 结构化条件检索")
    print("""
  需求: 给定学段、学科、研究领域、研究方法等过滤条件，找领域内代表文献。
  示例:
    学段      = "K-12"
    学科      = "数学教育"
    研究领域  = "教师专业发展"
    研究方法  = "混合方法"
    年份范围  = 2018~2025
    必须有DOI  = True
    最低引用量 = 5
    """)

    result = client.search_by_domain(
        stage="K-12",
        subject="数学教育",
        research_domain="教师专业发展",
        research_method="混合方法",
        year_from=2018,
        year_to=2025,
        must_have_doi=True,
        citation_min=5,
        top_k=20,
        page_size=3,
    )

    items = result.get("items") or result.get("results") or []
    filters = result.get("applied_filters", {})
    pagination = result.get("pagination", {})
    print(f"  检索词: {result.get('query_text', '')}")
    print(f"  已应用过滤: {json.dumps(filters, ensure_ascii=False)}")
    print(f"  匹配总数(分页前): {pagination.get('matched_before_pagination', '?')}")
    print(f"  本页返回: {pagination.get('returned', len(items))}")
    print(SUBSEP)
    return print_items(items)


def scenario_4_get_paper(client: PedaScopeClient, paper_id: str) -> None:
    """场景 4：根据 paper_id 获取完整题录。"""
    banner("4. get_paper — 获取完整题录")
    print(f"""
  需求: 给定 paper_id，返回完整题录、摘要、DOI、来源库、文本可用性。
  示例: paper_id = "{paper_id}"
    """)

    result = client.get_paper(paper_id)
    paper = result.get("paper", {})
    ta = paper.get("text_availability", {})
    meta = result.get("bibliographic_record", {}).get("metadata", {})

    print_paper(paper)
    print(f"  文本可用性:")
    print(f"    full_text_returned:   {ta.get('full_text_returned')}")
    print(f"    raw_text_exposed:     {ta.get('raw_text_exposed_chars', 0)} chars")
    print(f"    status:               {ta.get('status')}")
    print(f"    说明:                 {ta.get('note', '')}")
    if meta:
        print(f"  附加元数据:")
        for k, v in meta.items():
            print(f"    {k}: {v}")


def scenario_5_trace_claim(client: PedaScopeClient) -> None:
    """场景 5：给定 claim，追溯支撑来源。"""
    banner("5. trace_claim — Claim 来源追溯")
    print("""
  需求: 给定一句 claim，在摘要/全文/证据片段中找可支撑或相关的来源。
  示例: claim = "AI可以提升教师反馈效率和专业发展效果"
    """)

    result = client.trace_claim(
        claim="AI可以提升教师反馈效率和专业发展效果",
        domain_hint="education teacher professional development",
        top_k=5,
    )

    verdict = result.get("verdict", "")
    matches = result.get("matches", [])
    notes = result.get("notes_for_writer", [])

    verdict_map = {
        "candidate_support_found": "✅ 找到候选支撑来源",
        "related_candidates_found": "🔍 找到相关候选（支撑力度待验证）",
        "insufficient_evidence":   "⚠️  证据不足",
    }
    print(f"  Claim: {result.get('claim', '')}")
    print(f"  结论:  {verdict_map.get(verdict, verdict)}")
    print(SUBSEP)

    for i, m in enumerate(matches, 1):
        strength = m.get("support_strength", "?")
        overlap = m.get("overlap_signal", 0)
        icon = {"strong": "🟢", "moderate": "🟡", "weak": "🔴"}.get(strength, "⚪")
        print(f"  [{i}] {icon} 支撑强度: {strength} (重叠率: {overlap:.1%})")
        print(f"      标题: {m.get('title', '')}")
        authors = m.get("authors", [])
        if authors:
            print(f"      作者: {', '.join(authors[:4])}")
        print(f"      年份: {m.get('year', '未知')}  期刊: {m.get('journal', '')}")
        if m.get("doi"):
            print(f"      DOI:  {m['doi']}")
        print(f"      paper_id: {m.get('paper_id', '')}")
        note = m.get("evidence_note", "")
        if note:
            print(f"      说明: {note}")
        print()

    if notes:
        print("  写作者提示:")
        for note in notes:
            print(f"    • {note}")


def scenario_6_citation(client: PedaScopeClient, paper_id: str) -> None:
    """场景 6：生成 GB/T 7714-2015 引用草案。"""
    banner("6. get_citation — 生成 GB/T 7714 引用")
    print(f"""
  需求: 给定 paper_id，返回 GB/T 7714 所需字段和格式化引用草案。
  示例: paper_id = "{paper_id}"
    """)

    result = client.get_citation(paper_id)
    fields = result.get("fields", {})
    ref = result.get("formatted_reference", "")
    note = result.get("verification_note", "")
    style = result.get("style", "")

    print(f"  引用格式: {style}")
    print(SUBSEP)
    print(f"  格式化引用:")
    print(f"    {ref}")
    print()
    print(f"  引用字段:")
    for k, v in fields.items():
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        print(f"    {k}: {v}")
    if note:
        print(f"\n  ⚠️  {note}")


def scenario_7_verify_citation(client: PedaScopeClient) -> None:
    """场景 7：引用真实性验证（反幻觉锚点）。"""
    banner("7. verify_citation — 引用真实性验证（反幻觉）")
    print("""
  需求: 给定引用信息，在 150 万篇白名单中验证文献是否真实存在。
  示例: 验证 AI 赋能教师专业发展方向的文献真实性
    """)

    # 用一个真实存在的标题做验证
    result = client.verify_citation(
        title="人工智能助推教师专业发展的若干思考",
        authors=["王宇", "汪琼"],
        year="2022",
        journal="中国远程教育",
    )

    verified = result.get("verified", False)
    confidence = result.get("confidence", "")
    best = result.get("best_match") or {}
    note = result.get("verification_note", "")

    icon = "✅" if verified else "❌"
    print(f"  验证结果: {icon} {'验证通过' if verified else '未找到匹配'}")
    print(f"  置信度:   {confidence}")
    if best:
        print(f"  最佳匹配:")
        print(f"    标题: {best.get('title', '')}")
        print(f"    作者: {', '.join(best.get('authors', []))}")
        print(f"    年份: {best.get('year', '')}  期刊: {best.get('journal', '')}")
        print(f"    DOI:  {best.get('doi', '')}")
        print(f"    匹配分: {best.get('match_score', 0)}")
        print(f"    字段匹配: {best.get('fields_matched', {})}")
    print(f"\n  说明: {note}")

    # 用一个不存在的标题做验证
    print(f"\n  {SUBSEP}")
    print(f"  --- 反例：验证一个不存在的引用 ---")

    result2 = client.verify_citation(
        title="量子纠缠在幼儿教育中的应用研究",
        year="2023",
        journal="不存在期刊",
    )

    verified2 = result2.get("verified", False)
    confidence2 = result2.get("confidence", "")
    best2 = result2.get("best_match") or {}
    icon2 = "✅" if verified2 else "❌"
    print(f"\n  验证结果: {icon2} {'验证通过' if verified2 else '未找到匹配'}")
    print(f"  置信度:   {confidence2}")
    if best2:
        print(f"  最佳匹配: {best2.get('title', '')} (匹配分: {best2.get('match_score', 0)})")


def scenario_8_find_gaps(client: PedaScopeClient) -> None:
    """场景 8：研究空白/热点探测。"""
    banner("8. find_research_gaps — 研究空白/热点探测")
    print("""
  需求: 分析某个研究方向的文献密度、年份分布和关键词聚类，发现潜在研究空白。
  示例: 探测"人工智能+教师专业发展"方向的文献布局
    """)

    result = client.find_research_gaps(
        keywords=["人工智能", "教师专业发展"],
        domain="教育技术",
        top_k=50,
    )

    total = result.get("total_papers_analyzed", 0)
    year_dist = result.get("year_distribution", {})
    top_kw = result.get("top_keywords", [])
    sparse = result.get("sparse_periods", [])
    density = result.get("density_assessment", {})
    hints = result.get("gap_hints", [])

    print(f"  检索词: {result.get('query_text', '')}")
    print(f"  分析文献数: {total}")
    print(SUBSEP)

    print(f"  年份分布:")
    for year, count in sorted(year_dist.items()):
        bar = "█" * min(count, 40)
        print(f"    {year}: {bar} {count}")

    print(f"\n  高频关键词 TOP 10:")
    for item in top_kw[:10]:
        print(f"    {item['keyword']}: {item['count']}次")

    if sparse:
        print(f"\n  年份断档: {', '.join(sparse)}")
    else:
        print(f"\n  年份分布: 连续，无断档")

    print(f"\n  密度评估:")
    for k, v in density.items():
        print(f"    {k}: {v}")

    print(f"\n  分析提示:")
    for hint in hints:
        print(f"    • {hint}")


def scenario_9_suggest_keywords(client: PedaScopeClient) -> None:
    """场景 9：关键词推荐/扩展。"""
    banner("9. suggest_keywords — 关键词推荐/扩展")
    print("""
  需求: 基于种子关键词，推荐相关研究方向的关键词，辅助选题方向扩展。
  示例: 种子关键词 = ["教师专业发展"]
    """)

    result = client.suggest_keywords(
        seed_keywords=["教师专业发展"],
        top_k=50,
    )

    suggestions = result.get("suggested_keywords", [])
    print(f"  种子查询: {result.get('seed_query', '')}")
    print(f"  分析文献数: {result.get('total_papers_analyzed', 0)}")
    print(SUBSEP)

    trend_icon = {"rising": "📈", "emerging": "🆕", "stable": "➡️", "declining": "📉"}
    print(f"  推荐关键词:")
    print(f"  {'关键词':<35} {'频次':>4}  {'趋势'}")
    print(f"  {'-'*55}")
    for item in suggestions[:20]:
        icon = trend_icon.get(item.get("trend", ""), "➡️")
        print(f"  {item['keyword']:<35} {item['frequency']:>4}  {icon} {item.get('trend', '')}")


def scenario_10_reading_list(client: PedaScopeClient) -> None:
    """场景 10：结构化阅读清单生成。"""
    banner("10. build_reading_list — 结构化阅读清单")
    print("""
  需求: 基于选题方向，生成优先级排序的阅读清单（must_read/recommended/optional/supplementary）。
  示例: topic = "AI支持教师专业发展的研究进展"
    """)

    result = client.build_reading_list(
        topic="AI支持教师专业发展的研究进展",
        year_from=2020,
        top_k=20,
    )

    reading_list = result.get("reading_list", [])
    summary = result.get("summary", {})
    guide = result.get("priority_guide", {})

    print(f"  选题: {result.get('topic', '')}")
    print(f"  文献总数: {summary.get('total', 0)}")
    print(f"  优先级分布: {summary.get('by_priority', {})}")
    print(SUBSEP)

    priority_icon = {
        "must_read": "🔴 必读",
        "recommended": "🟡 推荐",
        "optional": "🟢 可选",
        "supplementary": "⚪ 补充",
    }

    for i, item in enumerate(reading_list, 1):
        p = item.get("priority", "")
        icon = priority_icon.get(p, p)
        print(f"  [{i}] {icon} (得分:{item.get('score', 0)})")
        print(f"      标题: {item.get('title', '')}")
        authors = item.get("authors", [])
        if authors:
            print(f"      作者: {', '.join(authors[:3])}")
        print(f"      年份: {item.get('year', '')}  期刊: {item.get('journal', '')}")
        if item.get("doi"):
            print(f"      DOI:  {item['doi']}")
        print(f"      理由: {', '.join(item.get('reasons', []))}")
        print()

    print("  优先级说明:")
    for k, v in guide.items():
        print(f"    {k}: {v}")


def scenario_11_compare_topics(client: PedaScopeClient) -> None:
    """场景 11：选题重复度/差异化分析。"""
    banner("11. compare_topics — 选题差异化分析")
    print("""
  需求: 比较两个选题方向的文献重叠度，判断差异化程度。
  示例:
    选题A = "人工智能赋能教师专业发展"
    选题B = "教师数字素养提升路径"
    """)

    result = client.compare_topics(
        topic_a="人工智能赋能教师专业发展",
        topic_b="教师数字素养提升路径",
        top_k=30,
    )

    comp = result.get("comparison", {})
    shared = result.get("shared_papers", [])
    shared_kw = result.get("shared_keywords", [])
    unique_a = result.get("unique_keywords_a", [])
    unique_b = result.get("unique_keywords_b", [])
    advice = result.get("advice", "")

    diff_map = {"high": "🟢 差异明显", "moderate": "🟡 有重叠", "low": "🔴 高度重叠"}
    diff = comp.get("differentiation", "")
    overlap = comp.get("overlap_ratio", 0)

    print(f"  选题 A: {result.get('topic_a', '')}")
    print(f"  选题 B: {result.get('topic_b', '')}")
    print(SUBSEP)
    print(f"  A 检索文献数:  {comp.get('papers_for_a', 0)}")
    print(f"  B 检索文献数:  {comp.get('papers_for_b', 0)}")
    print(f"  共同文献(DOI): {comp.get('shared_by_doi', 0)}")
    print(f"  重叠率:         {overlap:.1%}")
    print(f"  差异化评估:     {diff_map.get(diff, diff)}")
    print()
    print(f"  建议: {advice}")

    if shared:
        print(f"\n  共同文献:")
        for p in shared[:5]:
            print(f"    • {p.get('title', '')}")

    if shared_kw:
        print(f"\n  共同关键词: {', '.join(shared_kw[:10])}")

    if unique_a:
        print(f"\n  选题A独有关键词: {', '.join(unique_a[:10])}")

    if unique_b:
        print(f"\n  选题B独有关键词: {', '.join(unique_b[:10])}")


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

SCENARIOS = {
    1: scenario_1_keywords,
    2: scenario_2_topic,
    3: scenario_3_domain,
}

DESCRIPTIONS = {
    1: "search_by_keywords  — 按关键词检索",
    2: "search_by_topic     — 语义检索",
    3: "search_by_domain    — 结构化条件检索",
    4: "get_paper           — 获取完整题录",
    5: "trace_claim         — Claim 来源追溯",
    6: "get_citation        — 生成 GB/T 7714 引用",
    7: "verify_citation     — 引用真实性验证（反幻觉）",
    8: "find_research_gaps  — 研究空白/热点探测",
    9: "suggest_keywords    — 关键词推荐/扩展",
    10: "build_reading_list  — 结构化阅读清单",
    11: "compare_topics      — 选题差异化分析",
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="PedaScope KB 论文检索 — 全功能演示",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--scenario", type=int, default=0,
        help="只运行指定场景 (1~6)，默认 0 = 运行全部",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help=f"上游 API 地址 (默认 {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    s = args.scenario
    if s != 0 and (s < 1 or s > 11):
        print("场景编号必须是 1~11，0 表示全部。")
        return 1

    print(f"\n{'█' * 65}")
    print(f"  PedaScope KB 论文检索 — 全功能演示")
    print(f"  上游 API: {args.base_url}")
    print(f"{'█' * 65}")

    client = PedaScopeClient(base_url=args.base_url)
    try:
        # 场景 1~3 返回 paper_id，供场景 4/6 使用
        paper_id: str = ""

        if s in (0, 1):
            ids = scenario_1_keywords(client)
            if ids:
                paper_id = ids[0]

        if s in (0, 2):
            ids = scenario_2_topic(client)
            if not paper_id and ids:
                paper_id = ids[0]

        if s in (0, 3):
            ids = scenario_3_domain(client)
            if not paper_id and ids:
                paper_id = ids[0]

        # 如果只跑场景 4/6 但没有 paper_id，先搜索拿一个
        if s in (4, 6) and not paper_id:
            print("\n  (场景 4/6 需要 paper_id，先执行搜索...)")
            ids = scenario_1_keywords(client)
            if ids:
                paper_id = ids[0]

        if s in (0, 4) and paper_id:
            scenario_4_get_paper(client, paper_id)

        if s in (0, 5):
            scenario_5_trace_claim(client)

        if s in (0, 6) and paper_id:
            scenario_6_citation(client, paper_id)

        # 单独运行 4/6 但缺 paper_id 的提示
        if s == 4 and not paper_id:
            print("\n  ⚠️ 未获取到 paper_id，请先运行场景 1~3 搜索论文。")
        if s == 6 and not paper_id:
            print("\n  ⚠️ 未获取到 paper_id，请先运行场景 1~3 搜索论文。")

        # 新增场景 7~11
        if s in (0, 7):
            scenario_7_verify_citation(client)

        if s in (0, 8):
            scenario_8_find_gaps(client)

        if s in (0, 9):
            scenario_9_suggest_keywords(client)

        if s in (0, 10):
            scenario_10_reading_list(client)

        if s in (0, 11):
            scenario_11_compare_topics(client)

    finally:
        client.close()

    print(f"\n{'█' * 65}")
    print("  演示完成。")
    if s == 0:
        print("\n  你也可以单独运行某个场景:")
        for k, v in DESCRIPTIONS.items():
            print(f"    python3 pedascope_demo.py --scenario {k}  # {v}")
    print(f"{'█' * 65}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
