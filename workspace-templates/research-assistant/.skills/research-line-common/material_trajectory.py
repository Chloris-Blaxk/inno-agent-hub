#!/usr/bin/env python3
"""Shared material clustering and research trajectory helpers."""
from __future__ import annotations

from typing import Any

from material_adapter import SIGNAL_TERMS, digest_fact


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
        "signals": ["过程性评价", "学习证据", "课堂观察", "学生作品"],
        "researchAxis": "围绕学习证据采集、分析和转化为教学改进依据。",
        "usableTopicAngles": ["学习证据支持课堂改进", "过程性评价数据的课堂应用"],
    },
]


def material_stage(digests: list[dict[str, Any]], material_ids: list[str]) -> str:
    selected = [digest for digest in digests if digest.get("materialId") in material_ids]
    material_types = {digest.get("materialType") for digest in selected}
    if len(selected) >= 3 or {"project_process_record", "project_result", "data_record"}.intersection(material_types):
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
                "gaps": ["缺少连续课堂观察、学生作品或数据记录。"]
                if "project_process_record" not in {digest.get("materialType") for digest in matched}
                else ["需要补充分析方法和成果形态说明。"],
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
                "coreSignals": list(dict.fromkeys(signal for digest in uncovered for signal in digest.get("topicSignals", [])))[:5]
                or ["教学实践"],
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


def build_research_trajectory(
    profile: dict[str, Any],
    digests: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
) -> dict[str, Any]:
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
