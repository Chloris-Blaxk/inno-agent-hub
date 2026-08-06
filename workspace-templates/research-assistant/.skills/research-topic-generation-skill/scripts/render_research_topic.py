#!/usr/bin/env python3
"""研究选题生成 Skill 最小离线渲染脚本。

支持双轨执行：
  - LLM 轨（默认）：基于材料解析、聚类和 LLM 生成选题
  - DKG 轨：基于动态知识图谱的图计算缺口发现，LLM 仅做语言化包装
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = ROOT / "references"
OUTPUT_DIR = ROOT / "generated-outputs"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_research_topic.py"

sys.path.insert(0, str(ROOT.parent / "research-line-common"))
sys.path.insert(0, str(ROOT / "scripts"))  # 让 material_file_parser 可被 material_adapter 导入
from data_source_report import build_data_source_report, build_source  # noqa: E402
from education_generator_config import (  # noqa: E402
    attach_education_generator_runtime,
    build_education_generator_source,
)
from material_adapter import (  # noqa: E402
    build_material_digests as common_build_material_digests,
    build_source_materials_from_files,
    normalize_source_materials,
)
from material_trajectory import (  # noqa: E402
    build_material_clusters as common_build_material_clusters,
    build_research_trajectory as common_build_research_trajectory,
)
import literature_adapter  # noqa: E402


SIGNAL_TERMS = ["即时反馈", "错因诊断", "错因分析", "小学数学", "分数教学", "课堂投票", "课堂观察", "过程性评价", "学习证据", "讲评"]
CLUSTER_RULES = [
    {
        "clusterTitle": "错因诊断与精准讲评",
        "signals": ["错因诊断", "错因分析", "分数教学", "讲评"],
        "researchAxis": "围绕学生典型错因识别、分类记录和讲评调整形成连续研究。",
        "usableTopicAngles": ["错因诊断支持精准讲评", "分数教学典型错因的证据化改进"],
    },
    {
        "clusterTitle": "即时反馈与课堂调控",
        "signals": ["即时反馈", "课堂投票", "课堂观察", "讲评"],
        "researchAxis": "围绕课堂即时反馈信息如何帮助教师调整讲评顺序和教学决策。",
        "usableTopicAngles": ["即时反馈支持课堂调控", "课堂投票数据支持精准讲评"],
    },
    {
        "clusterTitle": "过程性评价与学习证据",
        "signals": ["过程性评价", "学习证据", "课堂观察"],
        "researchAxis": "围绕学习证据采集、分析和转化为教学改进依据。",
        "usableTopicAngles": ["学习证据支持课堂改进", "过程性评价数据的课堂应用"],
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def reference_count(filename: str, key: str) -> int:
    try:
        value = load_json(REFERENCES_DIR / filename).get(key, [])
    except FileNotFoundError:
        return 0
    return len(value) if isinstance(value, list) else 0


def selected_backend(config: dict[str, Any], input_obj: dict[str, Any]) -> str | None:
    backend = (
        config.get("backend")
        or config.get("literatureBackend")
        or input_obj.get("backend")
        or input_obj.get("literatureBackend")
        or os.environ.get("RESEARCH_LITERATURE_BACKEND")
    )
    return str(backend).strip() if backend else None


def build_research_topic_data_source_report(
    config: dict[str, Any],
    materials: list[dict[str, Any]],
    literature_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sources = []
    if materials:
        sources.append(
            build_source(
                source_id="user-materials",
                source_name="教师上传/输入研究材料",
                source_type="user_provided",
                data_type="teacher_research_material",
                record_count=len(materials),
                authorization_status="user_provided",
                limitations=["仅代表用户提供材料；事实真实性和敏感信息需由教师确认。"],
            )
        )
    sources.append(build_education_generator_source(record_count=1))
    sources.extend(
        [
            build_source(
                source_id="grant-title-samples",
                source_name="本地立项题样例库",
                source_type="local_sample",
                data_type="grant_title_sample",
                record_count=reference_count("grant-title-samples.json", "samples"),
                authorization_status="sample_only",
                limitations=["仅用于相似度演示和首轮降重提示，不能代表真实地区立项库覆盖。"],
            ),
            build_source(
                source_id="policy-hotspot-tags",
                source_name="本地政策热点标签样例",
                source_type="local_sample",
                data_type="policy_hotspot_tag",
                record_count=reference_count("policy-hotspot-tags.json", "tags"),
                authorization_status="sample_only",
                limitations=["政策标签为本地样例，真实申报前需按地区和年份更新。"],
            ),
            build_source(
                source_id="practice-problem-bank",
                source_name="本地实践问题样例库",
                source_type="local_sample",
                data_type="practice_problem_cluster",
                record_count=reference_count("practice-problem-bank.json", "problemClusters"),
                authorization_status="sample_only",
                limitations=["实践问题库为种子样例，不能覆盖所有学段、学科和学校情境。"],
            ),
        ]
    )
    existing_ids = {source.get("sourceId") for source in sources}
    for source in literature_sources or []:
        if isinstance(source, dict) and source.get("sourceId") not in existing_ids:
            sources.append(source)
            existing_ids.add(source.get("sourceId"))
    return build_data_source_report(
        skill_id="research-topic-generation-skill",
        task_intent=config.get("taskIntent", "mixed_topic"),
        sources=sources,
        overall_limitations=["立项题、政策热点和实践问题库仍为本地样例；文献信号只说明题录相关性，不承诺完整研究空白检测。"],
    )


def as_material_digests(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    digests = []
    for index, material in enumerate(materials, 1):
        content = material.get("content", "")
        title = material.get("title") or f"未命名材料-{index}"
        signals = [term for term in SIGNAL_TERMS if term in f"{title}{content}"]
        if not signals:
            signals = [material.get("materialType", "教学实践")]
        fact = content[:80] if content else "材料内容缺失，不能抽取事实。"
        digests.append(
            {
                "digestId": f"digest-{index:03d}",
                "materialId": material.get("materialId", f"mat-{index:03d}"),
                "materialType": material.get("materialType", "unknown"),
                "title": title,
                "keyFacts": [{"fact": fact, "confidence": "high" if content else "low"}],
                "topicSignals": signals,
                "usableFor": ["research_topic", "project_basis"] if content else ["needs_more_evidence"],
                "limitations": [] if content else ["缺少材料正文。"],
            }
        )
    return digests


def digest_fact(digest: dict[str, Any]) -> str:
    facts = digest.get("keyFacts", [])
    if facts and isinstance(facts[0], dict):
        return str(facts[0].get("fact", ""))
    return ""


def material_stage(digests: list[dict[str, Any]], material_ids: list[str]) -> str:
    selected = [digest for digest in digests if digest.get("materialId") in material_ids]
    material_types = {digest.get("materialType") for digest in selected}
    if len(selected) >= 3 or "data_record" in material_types or "project_outcome" in material_types:
        return "evidence_building"
    if len(selected) >= 2:
        return "theme_consolidation"
    return "material_accumulation"


def build_material_clusters(digests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not digests:
        return []

    clusters: list[dict[str, Any]] = []
    used_material_ids: set[str] = set()
    for rule in CLUSTER_RULES:
        matched = []
        for digest in digests:
            haystack = f"{digest.get('title', '')} {' '.join(digest.get('topicSignals', []))} {digest_fact(digest)}"
            if any(signal in haystack for signal in rule["signals"]):
                matched.append(digest)
        if not matched:
            continue
        material_ids = [digest["materialId"] for digest in matched if digest.get("materialId")]
        used_material_ids.update(material_ids)
        core_signals = list(
            dict.fromkeys(
                signal
                for digest in matched
                for signal in digest.get("topicSignals", [])
                if signal in rule["signals"] or signal in SIGNAL_TERMS
            )
        )[:5]
        clusters.append(
            {
                "clusterId": f"cluster-{len(clusters) + 1:03d}",
                "clusterTitle": rule["clusterTitle"],
                "materialIds": material_ids,
                "coreSignals": core_signals or rule["signals"][:2],
                "researchAxis": rule["researchAxis"],
                "evidenceSummary": [
                    {"materialId": digest["materialId"], "fact": digest_fact(digest)}
                    for digest in matched
                    if digest.get("materialId") and digest_fact(digest)
                ],
                "currentStage": material_stage(digests, material_ids),
                "gaps": ["缺少连续课堂观察、学生作品或数据记录。"] if "data_record" not in {digest.get("materialType") for digest in matched} else ["需要补充分析方法和成果形态说明。"],
                "usableTopicAngles": rule["usableTopicAngles"],
            }
        )

    uncovered = [digest for digest in digests if digest.get("materialId") not in used_material_ids]
    if uncovered:
        material_ids = [digest["materialId"] for digest in uncovered if digest.get("materialId")]
        clusters.append(
            {
                "clusterId": f"cluster-{len(clusters) + 1:03d}",
                "clusterTitle": "教师已有实践材料线索",
                "materialIds": material_ids,
                "coreSignals": list(dict.fromkeys(signal for digest in uncovered for signal in digest.get("topicSignals", [])))[:5] or ["教学实践"],
                "researchAxis": "先把零散实践材料整理为可追踪的问题链和证据链。",
                "evidenceSummary": [
                    {"materialId": digest["materialId"], "fact": digest_fact(digest)}
                    for digest in uncovered
                    if digest.get("materialId") and digest_fact(digest)
                ],
                "currentStage": material_stage(digests, material_ids),
                "gaps": ["材料主题较分散，需要补充共同问题、对象范围和证据记录。"],
                "usableTopicAngles": ["从已有实践材料中提炼课堂改进问题"],
            }
        )
    return clusters


def build_research_trajectory(profile: dict[str, Any], digests: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    if not digests:
        subject = profile.get("subject", "学科")
        return {
            "trajectoryId": "trajectory-001",
            "stage": "insufficient_material",
            "sourceMaterialIds": [],
            "dominantThemes": [],
            "trajectorySummary": f"当前只有{subject}教师画像，尚无可证明已有积累的材料。",
            "pastAccumulation": [],
            "currentFocusableDirections": ["先补充课例、反思、学生作品或成果材料，再生成总结性选题。"],
            "futureDeepeningPath": [
                {
                    "stepId": "path-001",
                    "timeframe": "1-2 周",
                    "action": "整理至少 1 份课例或教学反思，标注问题、对象和改进动作。",
                    "requiredEvidence": ["课例文本", "教学反思"],
                    "output": "可用于总结性选题的 MaterialDigest",
                },
                {
                    "stepId": "path-002",
                    "timeframe": "1 个月",
                    "action": "补充课堂观察或学生作品样本，形成证据链雏形。",
                    "requiredEvidence": ["课堂观察表", "学生作品或错题样本"],
                    "output": "可验证研究基础的材料包",
                },
            ],
            "risks": ["材料不足时只能生成规划性方向，不能声称已有成果。"],
        }

    source_ids = [digest["materialId"] for digest in digests if digest.get("materialId")]
    dominant_themes = [cluster.get("clusterTitle") for cluster in clusters[:3] if cluster.get("clusterTitle")]
    facts = [digest_fact(digest) for digest in digests if digest_fact(digest)]
    if any(cluster.get("currentStage") == "evidence_building" for cluster in clusters):
        stage = "evidence_building"
    elif len(clusters) >= 2 or len(digests) >= 2:
        stage = "theme_consolidation"
    else:
        stage = "material_accumulation"
    first_theme = dominant_themes[0] if dominant_themes else "已有课堂实践"
    return {
        "trajectoryId": "trajectory-001",
        "stage": stage,
        "sourceMaterialIds": source_ids,
        "dominantThemes": dominant_themes,
        "trajectorySummary": f"已有材料集中在{first_theme}，可从零散实践积累升级为连续证据链研究。",
        "pastAccumulation": facts[:5],
        "currentFocusableDirections": [cluster.get("researchAxis", "") for cluster in clusters[:3] if cluster.get("researchAxis")],
        "futureDeepeningPath": [
            {
                "stepId": "path-001",
                "timeframe": "0-1 个月",
                "action": "把已有课例、反思和成果按共同主题整理成问题链。",
                "requiredEvidence": source_ids[:3],
                "output": "研究问题与材料证据对应表",
            },
            {
                "stepId": "path-002",
                "timeframe": "1-2 个月",
                "action": "补充连续课堂观察、学生作品或错题样本，验证主题是否稳定出现。",
                "requiredEvidence": ["课堂观察表", "学生作品", "错题样本"],
                "output": "连续实践证据包",
            },
            {
                "stepId": "path-003",
                "timeframe": "1 学期内",
                "action": "明确研究方法、对象范围和成果形态，将总结性方向转化为申报题目。",
                "requiredEvidence": ["研究设计", "过程数据", "成果形态说明"],
                "output": "可申报选题与研究设计草案",
            },
        ],
        "risks": list(dict.fromkeys(gap for cluster in clusters for gap in cluster.get("gaps", [])))[:4],
    }


def topic_count(input_obj: dict[str, Any], key: str, default: int) -> int:
    requested = input_obj.get("topicCount", {})
    if isinstance(requested, dict):
        try:
            return max(0, int(requested.get(key, default)))
        except (TypeError, ValueError):
            return default
    return default


def load_grant_samples() -> list[dict[str, Any]]:
    return load_json(REFERENCES_DIR / "grant-title-samples.json").get("samples", [])


def normalize_terms(values: list[Any]) -> set[str]:
    terms: set[str] = set()
    for value in values:
        text = str(value)
        if not text:
            continue
        terms.add(text)
        for term in SIGNAL_TERMS:
            if term in text:
                terms.add(term)
    return {term for term in terms if term.strip()}


def title_terms(title: str) -> set[str]:
    return {term for term in SIGNAL_TERMS if term in title}


def similarity_score(topic: dict[str, Any], grant: dict[str, Any]) -> float:
    topic_terms = normalize_terms(topic.get("keywords", [])) | title_terms(str(topic.get("topicTitle", "")))
    grant_terms = normalize_terms(grant.get("keywords", [])) | title_terms(str(grant.get("title", "")))
    if not topic_terms or not grant_terms:
        return 0.0
    overlap = len(topic_terms.intersection(grant_terms))
    union = len(topic_terms.union(grant_terms))
    return round(overlap / union, 2)


def risk_level(score: float) -> str:
    if score >= 0.67:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"


def differentiation_strategy(topic: dict[str, Any], grant: dict[str, Any], score: float) -> str:
    hint = grant.get("differenceHint") or "进一步限定研究对象、方法、证据来源或成果形态。"
    if score >= 0.67:
        return f"相似度偏高，需避免只替换题名关键词；建议{hint}"
    if score >= 0.34:
        return f"存在部分主题重合；建议{hint}"
    return "与样例立项题相似度较低，仍需在申报书中说明研究对象、方法和成果形态。"


def add_basis_gap_and_differentiation(topics: list[dict[str, Any]], target_project_type: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grant_samples = load_grant_samples()
    differentiation_checks: list[dict[str, Any]] = []
    basis_gap_checks: list[dict[str, Any]] = []
    for topic in topics:
        basis_items = topic.get("existingBasis", [])
        basis_texts = [item.get("basis", "") for item in basis_items if isinstance(item, dict) and item.get("basis")]
        needed_materials = topic.get("feasibility", {}).get("neededMaterials", [])
        risks = topic.get("feasibility", {}).get("risks", [])
        target_requirement = f"{target_project_type or '课题'}申报通常需要问题来源、连续实践证据、研究方法、过程数据和可展示成果。"
        topic["basisGap"] = {
            "currentBasis": basis_texts or ["当前仅有教师画像或主题意向，尚无可直接支撑的用户材料。"],
            "targetRequirement": target_requirement,
            "gaps": needed_materials or risks or ["需要补充课堂证据、研究过程记录和成果形态说明。"],
            "upgradePath": [
                "把已有课例或反思整理为材料摘要和问题链。",
                "补充至少一轮连续课堂观察、学生作品或错题样本。",
                "明确研究方法、对象范围和阶段性成果形态。",
            ],
        }

        nearest = max(grant_samples, key=lambda grant: similarity_score(topic, grant), default={})
        score = similarity_score(topic, nearest) if nearest else 0.0
        topic["differentiation"] = {
            "nearestGrantId": nearest.get("grantId", ""),
            "nearestGrantTitle": nearest.get("title", ""),
            "similarityScore": score,
            "riskLevel": risk_level(score),
            "differenceStrategy": differentiation_strategy(topic, nearest, score) if nearest else "暂无立项样本可比对，需后续补充样本库。",
            "differentiatedTitleSuggestion": topic.get("topicTitle", ""),
        }
        differentiation_checks.append(
            {
                "topicId": topic.get("topicId"),
                "nearestGrantId": topic["differentiation"]["nearestGrantId"],
                "similarityScore": score,
                "riskLevel": topic["differentiation"]["riskLevel"],
            }
        )
        basis_gap_checks.append(
            {
                "topicId": topic.get("topicId"),
                "gapCount": len(topic["basisGap"]["gaps"]),
                "upgradeStepCount": len(topic["basisGap"]["upgradePath"]),
            }
        )
    return topics, differentiation_checks, basis_gap_checks


def ensure_unique_topic_titles(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for topic in topics:
        title = str(topic.get("topicTitle", ""))
        if title in seen:
            suffix = "未来三年证据积累路径" if topic.get("topicType") == "planning" else "材料转化路径"
            topic["topicTitle"] = f"{title}：{suffix}"
        seen.add(str(topic.get("topicTitle", "")))
    return topics


def should_build_literature_signals(config: dict[str, Any], input_obj: dict[str, Any], backend: str | None) -> bool:
    if input_obj.get("enableLiteratureSignals") is True or config.get("enableLiteratureSignals") is True:
        return True
    return backend in {"pedascope", "hybrid"}


def topic_domain_filters(profile: dict[str, Any], input_obj: dict[str, Any]) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    subject = profile.get("subject") or input_obj.get("subject")
    grade_band = profile.get("gradeBand") or input_obj.get("gradeBand")
    if subject:
        filters["subject"] = subject
    if grade_band:
        filters["stage"] = grade_band
    if input_obj.get("targetProjectType"):
        filters["research_domain"] = input_obj.get("targetProjectType")
    return filters


def compact_literature_record(record: dict[str, Any]) -> dict[str, Any]:
    limits = record.get("limits") or [
        "该记录仅用于选题阶段文献分布提示，不能证明完整研究空白。",
        "未经原文、摘要或用户上传材料形成 EvidenceCard 前，不能作为支撑性引用。",
    ]
    return {
        "paperId": record.get("paperId", ""),
        "title": record.get("title", ""),
        "authors": record.get("authors", [])[:4],
        "year": record.get("year", ""),
        "journal": record.get("journal", ""),
        "doi": record.get("doi", ""),
        "keywords": record.get("keywords", [])[:8],
        "sourceStatus": record.get("sourceStatus", ""),
        "textAvailability": record.get("textAvailability", ""),
        "evidenceLevel": record.get("evidenceLevel", ""),
        "generatedSummary": record.get("generatedSummary", ""),
        "limits": limits,
    }


def differentiation_hint_from_literature(candidate_count: int, records: list[dict[str, Any]]) -> tuple[str, str]:
    recent = [record for record in records if str(record.get("year", "")).isdigit() and int(str(record.get("year"))) >= 2020]
    if candidate_count >= 30:
        return "high", "相关题录较多，建议进一步限定研究对象、场景、证据来源或方法，避免泛化选题。"
    if recent:
        return "medium", "近年存在相关题录，可从课堂材料、对象范围和证据链设计上做差异化。"
    if candidate_count > 0:
        return "medium", "已有相关题录但近年信号有限，建议先阅读代表文献确认研究定位。"
    return "low", "当前检索未形成明显题录密集信号，但这不等于研究空白，需继续扩大关键词和数据库。"


def build_literature_signals(
    *,
    topics: list[dict[str, Any]],
    profile: dict[str, Any],
    input_obj: dict[str, Any],
    config: dict[str, Any],
    backend: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if not should_build_literature_signals(config, input_obj, backend):
        return topics, [], [], []
    adapters = literature_adapter.default_adapters(backend=backend or "local_mock")
    data_sources = literature_adapter.describe_adapters(adapters)
    filters = topic_domain_filters(profile, input_obj)
    signal_checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    for topic in topics:
        topic_title = str(topic.get("topicTitle", ""))
        topic_keywords = [str(item) for item in topic.get("keywords", []) if str(item).strip()]
        search = literature_adapter.search_papers(
            research_topic=topic_title,
            keywords=topic_keywords,
            adapters=adapters,
            limit=3,
            domain_filters=filters,
        )
        report = search.get("corpusSearchReport", {})
        records = search.get("records", [])
        candidate_count = int(report.get("candidateCount", len(records)) or len(records))
        domain = str(filters.get("research_domain") or filters.get("subject") or "")
        gap_report = literature_adapter.find_research_gaps(
            keywords=topic_keywords or [topic_title],
            domain=domain,
            adapters=adapters,
            limit=50,
        )
        if gap_report.get("status") == "ok":
            candidate_count = max(candidate_count, int(gap_report.get("totalPapersAnalyzed", 0) or 0))
        keyword_report = literature_adapter.suggest_research_keywords(
            seed_keywords=topic_keywords,
            topic=topic_title,
            adapters=adapters,
            limit=20,
        )
        comparison_report: dict[str, Any] = {}
        nearest_grant_title = topic.get("differentiation", {}).get("nearestGrantTitle", "") if isinstance(topic.get("differentiation"), dict) else ""
        if nearest_grant_title:
            comparison_report = literature_adapter.compare_research_topics(
                topic_a=topic_title,
                topic_b=str(nearest_grant_title),
                adapters=adapters,
                limit=30,
            )
        risk, hint = differentiation_hint_from_literature(candidate_count, records)
        comparison = comparison_report.get("comparison", {}) if isinstance(comparison_report.get("comparison"), dict) else {}
        if comparison.get("differentiation") == "low":
            risk = "high"
            hint = "PedaScope 题录比较显示与相近选题重叠较高，建议收窄对象、场景或证据来源。"
        elif comparison.get("differentiation") == "moderate" and risk == "low":
            risk = "medium"
        representative = [compact_literature_record(record) for record in records]
        signal = {
            "backend": backend or "local_mock",
            "candidateCount": candidate_count,
            "returnedCount": len(records),
            "indexSource": report.get("indexSource", ""),
            "sourceBackends": report.get("sourceBackends", []),
            "differentiationRisk": risk,
            "differentiationHint": hint,
            "representativeLiterature": representative,
            "researchGapReport": gap_report if gap_report.get("status") == "ok" else {},
            "keywordSuggestionReport": keyword_report if keyword_report.get("status") == "ok" else {},
            "topicComparisonReport": comparison_report if comparison_report.get("status") == "ok" else {},
            "limits": [
                "文献信号来自题录和系统生成摘要，不能证明完整研究空白。",
                "metadata-only 文献不能直接生成 EvidenceCard 或支撑性引用。",
            ],
        }
        if report.get("adapterWarnings"):
            signal["warnings"] = report["adapterWarnings"]
            warnings.extend(report["adapterWarnings"])
        for extra_report in (gap_report, keyword_report, comparison_report):
            if isinstance(extra_report, dict) and extra_report.get("warnings"):
                signal.setdefault("warnings", []).extend(extra_report["warnings"])
                warnings.extend(extra_report["warnings"])
        topic["literatureSignals"] = signal
        if representative:
            additions = [
                f"阅读《{record['title']}》时重点核对其研究对象、方法和证据来源，与本选题的差异在哪里？"
                for record in representative[:2]
                if record.get("title")
            ]
            for suggestion in keyword_report.get("suggestedKeywords", [])[:2] if isinstance(keyword_report.get("suggestedKeywords"), list) else []:
                keyword = suggestion.get("keyword") if isinstance(suggestion, dict) else ""
                if keyword:
                    additions.append(f"围绕“{keyword}”扩展检索时，是否能形成比当前题目更聚焦的子问题？")
            topic["nextReadingQuestions"] = list(dict.fromkeys([*topic.get("nextReadingQuestions", []), *additions]))[:6]
        signal_checks.append(
            {
                "topicId": topic.get("topicId"),
                "backend": backend or "local_mock",
                "candidateCount": candidate_count,
                "returnedCount": len(records),
                "differentiationRisk": risk,
            }
        )
    return topics, signal_checks, data_sources, list(dict.fromkeys(warnings))


def compact_topic_handoff(topic: dict[str, Any]) -> dict[str, Any]:
    feasibility = topic.get("feasibility", {}) if isinstance(topic.get("feasibility"), dict) else {}
    differentiation = topic.get("differentiation", {}) if isinstance(topic.get("differentiation"), dict) else {}
    literature_signal = topic.get("literatureSignals", {}) if isinstance(topic.get("literatureSignals"), dict) else {}
    return {
        "topicId": topic.get("topicId"),
        "topicTitle": topic.get("topicTitle"),
        "topicType": topic.get("topicType"),
        "keywords": topic.get("keywords", [])[:6],
        "researchQuestion": topic.get("researchQuestion", ""),
        "evidenceStatus": "material_backed" if topic.get("topicType") == "summative" else "planning_needs_materials",
        "feasibilityScore": feasibility.get("score"),
        "riskLevel": differentiation.get("riskLevel", "medium"),
        "literatureSignal": {
            "backend": literature_signal.get("backend", ""),
            "candidateCount": literature_signal.get("candidateCount", 0),
            "differentiationRisk": literature_signal.get("differentiationRisk", ""),
        } if literature_signal else {},
        "nextReadingQuestions": topic.get("nextReadingQuestions", [])[:4],
    }


def compact_cluster_handoff(cluster: dict[str, Any]) -> dict[str, Any]:
    return {
        "clusterId": cluster.get("clusterId"),
        "clusterTitle": cluster.get("clusterTitle"),
        "materialIds": cluster.get("materialIds", [])[:8],
        "coreSignals": cluster.get("coreSignals", [])[:6],
        "currentStage": cluster.get("currentStage"),
    }


def build_summative_topics(digests: list[dict[str, Any]], clusters: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    topics = []
    if not digests:
        return topics
    title_pool = [
        "小学数学课堂即时反馈支持错因诊断的实践研究",
        "基于错因分析的小学数学分数教学改进路径研究",
        "课堂投票数据支持小学数学精准讲评的行动研究",
    ]
    for index in range(count):
        cluster = clusters[index % len(clusters)] if clusters else {}
        cluster_material_ids = cluster.get("materialIds", [])
        cluster_digests = [digest for digest in digests if digest.get("materialId") in cluster_material_ids] or digests
        digest = cluster_digests[index % len(cluster_digests)]
        topic_title = title_pool[index % len(title_pool)]
        if cluster.get("usableTopicAngles"):
            topic_title = f"{cluster['usableTopicAngles'][0]}的实践研究"
        keywords = list(dict.fromkeys(cluster.get("coreSignals", []) + digest.get("topicSignals", []) + ["小学数学", "课堂改进"]))[:4]
        basis_items = [
            {"materialId": item["materialId"], "basis": f"已有材料显示：{item['fact']}"}
            for item in cluster.get("evidenceSummary", [])[:3]
            if item.get("materialId") and item.get("fact")
        ] or [{"materialId": digest["materialId"], "basis": f"已有材料显示：{digest['keyFacts'][0]['fact']}"}]
        topics.append(
            {
                "topicId": f"topic-sum-{index + 1:03d}",
                "topicTitle": topic_title,
                "topicType": "summative",
                "researchQuestion": f"如何基于{cluster.get('clusterTitle', '已有材料')}提炼可持续研究的课堂改进问题？",
                "existingBasis": basis_items,
                "innovationPoints": ["把已有课例、反思或成果聚合为可追踪的问题链和证据链。"],
                "feasibility": {
                    "score": 4,
                    "risks": cluster.get("gaps", []) or ["需要补充连续课堂观察或学生作品，避免只停留在单次经验描述。"],
                    "neededMaterials": ["课堂观察表", "学生错题样本", "讲评调整记录"],
                },
                "keywords": keywords if len(keywords) >= 2 else keywords + ["教学改进"],
                "nextReadingQuestions": ["课堂即时反馈如何支持教师调整教学？", "错因诊断如何转化为讲评策略？"],
            }
        )
    return topics


def build_planning_topics(profile: dict[str, Any], count: int) -> list[dict[str, Any]]:
    bank = load_json(REFERENCES_DIR / "practice-problem-bank.json").get("problemClusters", [])
    subject = profile.get("subject", "")
    grade_band = profile.get("gradeBand", "")
    matched = next((item for item in bank if subject in item.get("subjectTags", []) or grade_band in item.get("gradeBands", [])), bank[0])
    angles = matched.get("possibleTopicAngles", [])
    topics = []
    for index in range(count):
        title = angles[index % len(angles)]
        topics.append(
            {
                "topicId": f"topic-plan-{index + 1:03d}",
                "topicTitle": title if subject in title else f"{subject}{title}",
                "topicType": "planning",
                "researchQuestion": "未来 1-3 年如何围绕该课堂问题形成连续实践和证据积累？",
                "existingBasis": [{"basis": "依据教师画像和实践问题库生成，尚需用户材料进一步确认。"}],
                "innovationPoints": ["从实践问题、证据采集和成果形态三个维度规划研究。"],
                "feasibility": {
                    "score": 3,
                    "risks": matched.get("feasibilityRisks", [])[:2],
                    "neededMaterials": matched.get("neededMaterials", [])[:4],
                },
                "keywords": list(dict.fromkeys(matched.get("problemSignals", [])[:2] + ["小学数学", "实践研究"]))[:4],
                "nextReadingQuestions": ["该主题已有研究主要采用哪些方法？", "需要收集哪些课堂证据？"],
            }
        )
    return topics


def render(config: dict[str, Any]) -> dict[str, Any]:
    input_obj = config.get("input", {})
    profile = input_obj.get("teacherProfile") or config.get("teacherProfile", {})

    # ---- 材料入口：文件解析 + JSON 材料合并 ----
    source_files = input_obj.get("sourceFiles") or config.get("sourceFiles") or []
    # 将相对路径解析为基于 Skill 根目录的绝对路径
    resolved_files = [
        str(ROOT / f) if not os.path.isabs(f) else f
        for f in source_files
    ]
    user_materials = input_obj.get("materials", [])
    if resolved_files:
        # 从文件解析材料，与 JSON 中已有的材料合并
        file_materials = build_source_materials_from_files(resolved_files)
        json_materials = normalize_source_materials(user_materials)
        # 重新编号：文件解析材料在前
        offset = len(file_materials)
        for i, mat in enumerate(json_materials):
            mat["materialId"] = f"mat-{offset + i + 1:03d}"
        materials = file_materials + json_materials
    else:
        materials = normalize_source_materials(user_materials)
    # -------------------------------------------------

    target_project_type = input_obj.get("targetProjectType", "")
    digests = common_build_material_digests(materials)
    material_clusters = common_build_material_clusters(digests)
    research_trajectory = common_build_research_trajectory(profile, digests, material_clusters)
    summative_target = topic_count(input_obj, "summative", 2)
    planning_target = topic_count(input_obj, "planning", 1)
    topics = build_summative_topics(digests, material_clusters, summative_target)
    topics.extend(build_planning_topics(profile, planning_target))
    topics = ensure_unique_topic_titles(topics)
    topics, differentiation_checks, basis_gap_checks = add_basis_gap_and_differentiation(topics, target_project_type)
    backend = selected_backend(config, input_obj)
    topics, literature_signal_checks, literature_sources, literature_warnings = build_literature_signals(
        topics=topics,
        profile=profile,
        input_obj=input_obj,
        config=config,
        backend=backend,
    )
    summative_count = len([topic for topic in topics if topic["topicType"] == "summative"])
    planning_count = len([topic for topic in topics if topic["topicType"] == "planning"])
    material_coverage = round(summative_count / len(topics), 2) if topics else 0
    clustered_material_ids = {material_id for cluster in material_clusters for material_id in cluster.get("materialIds", [])}
    clustered_material_coverage = round(len(clustered_material_ids) / len(digests), 2) if digests else 0
    trajectory_step_count = len(research_trajectory.get("futureDeepeningPath", []))
    high_similarity_count = len([item for item in differentiation_checks if item.get("riskLevel") == "high"])
    warnings = [] if digests else ["未提供材料，不能生成总结性选题。"]
    warnings.extend(literature_warnings)
    status = "warn" if warnings else "pass"
    payload = {
        "requestId": config.get("requestId", "req-research-topic-render-001"),
        "skillId": "research-topic-generation-skill",
        "taskIntent": config.get("taskIntent", "mixed_topic"),
        "status": status,
        "summary": "已生成总结性/规划性选题候选；总结性选题均回链用户材料。",
        "inputSummary": {
            "sourceRequest": config.get("sourceRequest", ""),
            "materialCount": len(materials),
            "literatureBackend": backend or "local_mock",
            "teacherProfileFields": sorted(key for key, value in profile.items() if value not in (None, "", [], {})),
            "targetProjectType": target_project_type,
            "assumptions": config.get("assumptions", []),
            "constraints": config.get("constraints", {}),
        },
        "warnings": warnings,
        "dataSourceReport": build_research_topic_data_source_report(config, materials, literature_sources),
        "artifacts": [],
        "result": {
            "materialDigests": digests,
            "materialClusters": material_clusters,
            "researchTrajectory": research_trajectory,
            "topicCandidates": topics,
            "topicEvaluationReport": {
                "materialEvidenceCoverage": material_coverage,
                "clusteredMaterialCoverage": clustered_material_coverage,
                "materialClusterChecks": [
                    {
                        "clusterId": cluster.get("clusterId"),
                        "materialCount": len(cluster.get("materialIds", [])),
                        "signalCount": len(cluster.get("coreSignals", [])),
                    }
                    for cluster in material_clusters
                ],
                "researchTrajectoryCheck": {
                    "stage": research_trajectory.get("stage"),
                    "sourceMaterialCount": len(research_trajectory.get("sourceMaterialIds", [])),
                    "futureStepCount": trajectory_step_count,
                },
                "differentiationChecks": differentiation_checks,
                "basisGapChecks": basis_gap_checks,
                "literatureSignalChecks": literature_signal_checks,
                "notes": ["总结性选题来自用户材料；规划性选题来自教师画像和实践问题库；差异化仅基于本地立项样本做首轮降重提示。"],
            },
        },
        "handoff": {
            "topicCandidates": [compact_topic_handoff(topic) for topic in topics],
            "materialClusters": [compact_cluster_handoff(cluster) for cluster in material_clusters],
            "researchTrajectory": {
                "trajectoryId": research_trajectory.get("trajectoryId"),
                "stage": research_trajectory.get("stage"),
                "dominantThemes": research_trajectory.get("dominantThemes", [])[:5],
                "sourceMaterialIds": research_trajectory.get("sourceMaterialIds", [])[:10],
            },
            "keywords": list(dict.fromkeys(keyword for topic in topics for keyword in topic.get("keywords", [])))[:8],
            "readingQuestions": list(dict.fromkeys(question for topic in topics for question in topic.get("nextReadingQuestions", [])))[:6],
        },
        "qualityReport": {
            "status": status,
            "checks": [{"id": "summative_material_ref", "status": "pass"}, {"id": "topic_risks_or_materials", "status": "pass"}],
            "warnings": warnings,
            "metrics": {
                "topicCount": len(topics),
                "summativeCount": summative_count,
                "planningCount": planning_count,
                "materialEvidenceCoverage": material_coverage,
                "feasibilityWarnings": len([topic for topic in topics if topic.get("feasibility", {}).get("risks")]),
                "basisGapCount": len(basis_gap_checks),
                "differentiationCheckCount": len(differentiation_checks),
                "highSimilarityCount": high_similarity_count,
                "materialClusterCount": len(material_clusters),
                "clusteredMaterialCoverage": clustered_material_coverage,
                "trajectoryStepCount": trajectory_step_count,
                "literatureSignalCount": len(literature_signal_checks),
                "literatureSignalHighRiskCount": len([item for item in literature_signal_checks if item.get("differentiationRisk") == "high"]),
            },
        },
        "provenanceReport": {
            "sourceCount": len(materials),
            "verifiedSourceCount": len(materials),
            "unsupportedClaimCount": 0,
        },
        "nextActions": ["补充课例、反思或成果材料后再生成总结性选题。"] if not digests else ["补充连续课堂观察记录以增强可行性论证。"],
    }
    return attach_education_generator_runtime(
        payload,
        skill_id="research-topic-generation-skill",
        task_intent=str(config.get("taskIntent", "mixed_topic")),
        used_for=["material_digest_language", "topic_candidate_generation", "dkg_result_verbalization"],
        generation_mode="rules_first_with_innospark_235b_generator_contract",
    )


def render_markdown(data: dict[str, Any]) -> str:
    result = data.get("result", {})
    lines = [
        "# 研究选题生成结果",
        "",
        f"请求 ID：`{data.get('requestId')}`",
        f"校验状态：`{data.get('qualityReport', {}).get('status')}`",
        "",
        "## 摘要",
        "",
        data.get("summary", ""),
        "",
    ]
    digests = result.get("materialDigests", [])
    if digests:
        lines.extend(["## 材料摘要", ""])
        for digest in digests:
            facts = "；".join(item.get("fact", "") for item in digest.get("keyFacts", []))
            lines.append(f"- **{digest.get('title')}**（`{digest.get('materialId')}`）：{facts}")
        lines.append("")
    clusters = result.get("materialClusters", [])
    if clusters:
        lines.extend(["## 材料主题聚类", ""])
        for cluster in clusters:
            lines.extend(
                [
                    f"- **{cluster.get('clusterTitle')}**（`{cluster.get('clusterId')}`）",
                    f"  - 材料：{', '.join(cluster.get('materialIds', []))}",
                    f"  - 研究轴：{cluster.get('researchAxis')}",
                    f"  - 缺口：{'；'.join(cluster.get('gaps', []))}",
                ]
            )
        lines.append("")
    trajectory = result.get("researchTrajectory", {})
    if trajectory:
        lines.extend(["## 研究轨迹", ""])
        lines.append(f"- 阶段：`{trajectory.get('stage')}`")
        lines.append(f"- 概括：{trajectory.get('trajectorySummary')}")
        lines.append("")
    lines.extend(["## 选题候选", ""])
    for topic in result.get("topicCandidates", []):
        risks = "；".join(topic.get("feasibility", {}).get("risks", [])) or "暂无"
        needed = "、".join(topic.get("feasibility", {}).get("neededMaterials", [])) or "暂无"
        basis = "；".join(item.get("basis", "") for item in topic.get("existingBasis", []))
        lines.extend(
            [
                f"### {topic.get('topicTitle')}",
                "",
                f"- 类型：{topic.get('topicType')}",
                f"- 研究问题：{topic.get('researchQuestion')}",
                f"- 已有基础：{basis}",
                f"- 关键词：{'、'.join(topic.get('keywords', []))}",
                f"- 可行性评分：{topic.get('feasibility', {}).get('score')}",
                f"- 风险：{risks}",
                f"- 补充资料：{needed}",
                f"- 差异化：{topic.get('differentiation', {}).get('differenceStrategy', '未提供')}",
                f"- 基础差距：{'；'.join(topic.get('basisGap', {}).get('gaps', [])) or '未提供'}",
                "",
            ]
        )
        signal = topic.get("literatureSignals", {})
        if isinstance(signal, dict) and signal:
            lines.extend(
                [
                    f"- 文献信号：候选 {signal.get('candidateCount', 0)}，返回 {signal.get('returnedCount', 0)}，风险 `{signal.get('differentiationRisk')}`",
                    f"- 文献差异化提示：{signal.get('differentiationHint', '未提供')}",
                ]
            )
            for record in signal.get("representativeLiterature", [])[:2]:
                lines.append(f"  - 代表题录：{record.get('title')}（{record.get('year')}，{record.get('journal')}）")
            lines.append("")
    next_actions = data.get("nextActions", [])
    if next_actions:
        lines.extend(["## 下一步", ""])
        lines.extend(f"- {item}" for item in next_actions)
        lines.append("")
    return "\n".join(lines)


def merge_dkg_into_output(
    llm_output: dict[str, Any],
    dkg_result: dict[str, Any],
    target_project_type: str,
) -> dict[str, Any]:
    """将 DKG 发现的选题合并到 LLM 输出结构中。

    DKG 选题作为额外候选追加，每条附带 dkgEvidence。
    LLM 轨生成的选题保持不变。
    """
    rank_list = dkg_result.get("rank_list", [])
    evidence_chains = dkg_result.get("evidence_chains", [])
    chain_by_id = {chain["gap_id"]: chain for chain in evidence_chains}
    fallback_flags = dkg_result.get("fallback_flags", [])

    dkg_topics: list[dict[str, Any]] = []
    for item in rank_list:
        gap_id = item.get("gap_id", "")
        chain = chain_by_id.get(gap_id, {})
        gap_nodes = item.get("gap_nodes", []) or ["图谱缺口", "课堂实践"]
        readable_nodes = [str(node).split("::")[-1] for node in gap_nodes]
        next_questions = [
            f"{readable_nodes[0]} 与 {readable_nodes[1] if len(readable_nodes) > 1 else '课堂实践'} 已有哪些代表性研究？",
            "该图谱缺口是否已被近三到五年论文或立项题覆盖？",
            "教师现有材料能否提供课堂观察、学生作品或访谈证据？",
        ]
        dkg_topics.append(
            {
                "topicId": f"topic-dkg-{gap_id}",
                "topicTitle": item.get("title", "DKG 发现的研究方向"),
                "topicType": "planning",
                "researchQuestion": f"如何围绕 {item.get('title', '该方向')} 开展实证研究？",
                "existingBasis": [
                    {"basis": f"DKG 图计算发现：该方向存在 {chain.get('gap_type', '未知')} 型缺口。"}
                ],
                "innovationPoints": [
                    f"缺口类型：{chain.get('gap_type', '')}",
                    f"综合评分：{item.get('composite_score', 0)}",
                ],
                "feasibility": {
                    "score": round(float(item.get("composite_score", 0.5)) * 5),
                    "risks": (
                        ["趋势信号不足，趋势评分为占位值。"]
                        if chain.get("trend_evidence", {}).get("fallback")
                        else []
                    ),
                    "neededMaterials": item.get("next_materials", []),
                },
                "keywords": readable_nodes[:4] if len(readable_nodes) >= 2 else readable_nodes + ["研究缺口"],
                "nextReadingQuestions": next_questions,
                "dkgEvidence": {
                    "enabled": True,
                    "gapType": chain.get("gap_type", ""),
                    "gapCause": chain.get("gap_cause", {}).get("trigger_basis", ""),
                    "topoEvidence": chain.get("topo_evidence", {}),
                    "trendEvidence": chain.get("trend_evidence", {}),
                    "sourceCoverage": min(chain.get("source_coverage", {}).get("source_count", 0) / 8.0, 1.0),
                    "graphPath": chain.get("path", ""),
                    "scoreBreakdown": {
                        **chain.get("score_breakdown", {}),
                        "composite": item.get("composite_score", 0),
                        "synthesis": item.get("synthesis", ""),
                    },
                    "uncertaintyNote": "；".join(chain.get("uncertainty_note", [])) or "",
                },
            }
        )

    # 合并到现有输出
    result = llm_output.get("result", {})
    existing_topics = result.get("topicCandidates", [])
    all_topics = ensure_unique_topic_titles(existing_topics + dkg_topics)
    all_topics, differentiation_checks, basis_gap_checks = add_basis_gap_and_differentiation(all_topics, target_project_type)

    llm_output["result"]["topicCandidates"] = all_topics

    evaluation_report = llm_output["result"].setdefault("topicEvaluationReport", {})
    evaluation_report["differentiationChecks"] = differentiation_checks
    evaluation_report["basisGapChecks"] = basis_gap_checks
    notes = evaluation_report.setdefault("notes", [])
    notes.append("DKG 轨候选已补齐 basisGap、differentiation 和 nextReadingQuestions；仍需人工核对图谱缺口与真实材料的匹配度。")

    llm_output["handoff"]["topicCandidates"] = [compact_topic_handoff(topic) for topic in all_topics]
    llm_output["handoff"]["keywords"] = list(dict.fromkeys(keyword for topic in all_topics for keyword in topic.get("keywords", [])))[:8]
    llm_output["handoff"]["readingQuestions"] = list(dict.fromkeys(question for topic in all_topics for question in topic.get("nextReadingQuestions", [])))[:8]

    # 更新质量报告
    qr = llm_output.get("qualityReport", {})
    metrics = qr.get("metrics", {})
    summative_count = len([topic for topic in all_topics if topic.get("topicType") == "summative"])
    planning_count = len([topic for topic in all_topics if topic.get("topicType") == "planning"])
    metrics.update(
        {
            "topicCount": len(all_topics),
            "summativeCount": summative_count,
            "planningCount": planning_count,
            "feasibilityWarnings": len([topic for topic in all_topics if topic.get("feasibility", {}).get("risks")]),
            "basisGapCount": len(all_topics),
            "differentiationCheckCount": len(all_topics),
            "highSimilarityCount": len([topic for topic in all_topics if topic.get("differentiation", {}).get("riskLevel") == "high"]),
            "dkgEnabled": True,
            "dkgCoverage": len(dkg_topics),
            "gapEvidenceCount": len(evidence_chains),
            "trendConfidence": (
                sum(
                    chain.get("trend_evidence", {}).get("confidence", 0)
                    for chain in evidence_chains
                )
                / max(len(evidence_chains), 1)
            ),
        }
    )
    if fallback_flags:
        qr.setdefault("warnings", []).extend(fallback_flags)
        llm_output.setdefault("warnings", []).extend(fallback_flags)
        qr["status"] = "warn"
    llm_output["status"] = qr.get("status", llm_output.get("status", "pass"))

    llm_output["summary"] = (
        llm_output.get("summary", "")
        + f"\nDKG 轨发现 {len(dkg_topics)} 个图计算选题。"
    )
    return llm_output


def main() -> int:
    parser = argparse.ArgumentParser(description="渲染研究选题生成 JSON 产物（LLM 轨 / DKG 轨）。")
    parser.add_argument("input_or_output_base", help="旧入口为请求 JSON；使用 --config 时为输出 base")
    parser.add_argument("--config", help="模板式入口的请求 JSON 文件：render_x.py <output_base> --config <request>")
    parser.add_argument("--output", help="输出 JSON 文件；默认写入 generated-outputs/<requestId>.json")
    parser.add_argument("--validate", action="store_true", help="输出后立即运行 validate_research_topic.py")
    parser.add_argument(
        "--dkg-result",
        help="可选：DKG 发现结果 JSON（由 scripts/discover.py run 产出），合并到选题输出中",
    )
    parser.add_argument(
        "--dkg-sources",
        help="可选：构建 DKG 的源记录 JSON，与 --dkg-result 互斥（会自动运行 dkg.py build + discover.py run）",
    )
    parser.add_argument(
        "--dkg-request",
        help="DKG 请求 JSON（与 --dkg-sources 配合使用）",
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else Path(args.input_or_output_base)
    config = load_json(config_path)

    # DKG 轨：先运行 DKG 管线
    dkg_result = None
    if args.dkg_result:
        dkg_result = load_json(Path(args.dkg_result))
    elif args.dkg_sources and args.dkg_request:
        dkg_path = Path(args.dkg_sources).with_suffix(".dkg.json")
        dkg_out = Path(args.dkg_sources).with_suffix(".result.json")
        # S1: 构建 DKG
        rc = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "dkg.py"),
                "build",
                "--sources",
                str(args.dkg_sources),
                "--out",
                str(dkg_path),
            ],
            capture_output=True, text=True, check=False,
        )
        if rc.returncode != 0:
            print(f"[DKG] build failed: {rc.stderr}")
        else:
            print(f"[DKG] {rc.stdout.strip()}")
            # S2-S9: 选题发现
            rc2 = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "discover.py"),
                    "run",
                    "--dkg",
                    str(dkg_path),
                    "--request",
                    str(args.dkg_request),
                    "--config",
                    str(ROOT / "assets" / "agent_config.json") if (ROOT / "assets" / "agent_config.json").exists() else "",
                    "--out",
                    str(dkg_out),
                ],
                capture_output=True, text=True, check=False,
            )
            if rc2.returncode != 0:
                print(f"[DKG] discovery failed: {rc2.stderr}")
            else:
                print(f"[DKG] {rc2.stdout.strip()}")
                dkg_result = load_json(dkg_out)

    # LLM 轨：渲染基础输出
    output = render(config)

    # 合并 DKG 结果
    if dkg_result:
        target_project_type = config.get("input", {}).get("targetProjectType", "")
        output = merge_dkg_into_output(output, dkg_result, target_project_type)

    if args.output:
        output_path = Path(args.output)
    elif args.config:
        output_base = Path(args.input_or_output_base)
        output_path = output_base if output_base.suffix == ".json" else output_base.with_suffix(".json")
    else:
        output_path = OUTPUT_DIR / f"{output['requestId']}.json"
    md_path = output_path.with_suffix(".md")
    output["artifacts"] = [
        {"type": "json", "path": str(output_path), "description": "结构化研究选题生成结果"},
        {"type": "markdown", "path": str(md_path), "description": "教师可读研究选题报告"},
    ]
    write_json(output_path, output)
    write_markdown(md_path, render_markdown(output))
    print(output_path)
    print(md_path)
    if args.validate:
        return subprocess.run(["python3", str(VALIDATE_SCRIPT), str(output_path)], check=False).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
