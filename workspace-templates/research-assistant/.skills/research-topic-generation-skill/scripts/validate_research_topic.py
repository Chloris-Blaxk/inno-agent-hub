#!/usr/bin/env python3
"""校验研究选题生成 Skill 的 JSON 产物。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

COMMON_ROOT = Path(__file__).resolve().parents[1].parent / "research-line-common"
sys.path.insert(0, str(COMMON_ROOT))
from data_source_report import validate_data_source_report  # noqa: E402


SKILL_ID = "research-topic-generation-skill"
ALLOWED_INTENTS = {"summative_topic", "planning_topic", "mixed_topic", "topic_refine"}
ROOT_REQUIRED = [
    "requestId",
    "skillId",
    "taskIntent",
    "status",
    "summary",
    "warnings",
    "dataSourceReport",
    "result",
    "handoff",
    "qualityReport",
    "provenanceReport",
    "nextActions",
]
GENERIC_TITLE_PATTERNS = [
    re.compile(r"^核心素养下.+教学研究$"),
    re.compile(r"^.+教学研究$"),
    re.compile(r"^.+课堂教学研究$"),
    re.compile(r"^.+有效性研究$"),
]
DIFFERENTIATION_RISKS = {"low", "medium", "high"}
TRAJECTORY_STAGES = {"insufficient_material", "material_accumulation", "theme_consolidation", "evidence_building"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def require_fields(obj: dict[str, Any], fields: list[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj or not non_empty(obj[field]):
            errors.append(f"{label} 缺少或为空：{field}")


def require_keys(obj: dict[str, Any], fields: list[str], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in obj:
            errors.append(f"{label} 缺少字段：{field}")


def validate_quality_report(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    quality = data.get("qualityReport", {})
    if not isinstance(quality, dict):
        errors.append("qualityReport 必须是对象。")
        return
    failed = [item.get("id") for item in quality.get("checks", []) if item.get("status") == "fail"]
    if failed:
        errors.append(f"qualityReport 存在失败检查：{failed}")
    if quality.get("status") in {"fail", "failed"}:
        errors.append(f"qualityReport.status 为 {quality.get('status')}。")
    if quality.get("status") == "warn":
        warnings.append("qualityReport.status 为 warn，请查看 warnings。")


def validate_literature_signal(signal: Any, topic_label: str, errors: list[str]) -> bool:
    if not signal:
        return False
    if not isinstance(signal, dict):
        errors.append(f"{topic_label}.literatureSignals 必须是对象。")
        return False
    require_keys(
        signal,
        ["backend", "candidateCount", "returnedCount", "indexSource", "sourceBackends", "differentiationRisk", "differentiationHint", "representativeLiterature", "limits"],
        f"{topic_label}.literatureSignals",
        errors,
    )
    candidate_count = signal.get("candidateCount")
    returned_count = signal.get("returnedCount")
    if not isinstance(candidate_count, int) or candidate_count < 0:
        errors.append(f"{topic_label}.literatureSignals.candidateCount 必须是非负整数。")
    if not isinstance(returned_count, int) or returned_count < 0:
        errors.append(f"{topic_label}.literatureSignals.returnedCount 必须是非负整数。")
    if signal.get("differentiationRisk") not in DIFFERENTIATION_RISKS:
        errors.append(f"{topic_label}.literatureSignals.differentiationRisk 不合法：{signal.get('differentiationRisk')}")
    limits = signal.get("limits", [])
    limits_text = "；".join(str(item) for item in limits) if isinstance(limits, list) else str(limits)
    if "研究空白" not in limits_text or "不能" not in limits_text:
        errors.append(f"{topic_label}.literatureSignals.limits 必须说明题录信号不能证明完整研究空白。")
    representative = signal.get("representativeLiterature", [])
    if not isinstance(representative, list):
        errors.append(f"{topic_label}.literatureSignals.representativeLiterature 必须是数组。")
        representative = []
    source_backends = signal.get("sourceBackends", [])
    uses_pedascope = isinstance(source_backends, list) and "pedascope_mcp" in source_backends
    for record_index, record in enumerate(representative, 1):
        record_label = f"{topic_label}.literatureSignals.representativeLiterature[{record_index}]"
        if not isinstance(record, dict):
            errors.append(f"{record_label} 必须是对象。")
            continue
        require_fields(record, ["paperId", "title", "textAvailability", "evidenceLevel", "limits"], record_label, errors)
        if uses_pedascope or record.get("textAvailability") == "metadata":
            if record.get("textAvailability") != "metadata" or record.get("evidenceLevel") != "metadata_verified":
                errors.append(f"{record_label} 来自 PedaScope/metadata-only 时必须保持 metadata / metadata_verified。")
            if "evidenceText" in record or "quoteLocation" in record:
                errors.append(f"{record_label} 不得携带 EvidenceCard 级 evidenceText 或 quoteLocation。")
    return True


def validate(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    require_keys(data, ROOT_REQUIRED, "根对象", errors)
    require_fields(data, [field for field in ROOT_REQUIRED if field not in {"nextActions", "warnings"}], "根对象", errors)
    if errors:
        return errors, warnings

    if data.get("skillId") != SKILL_ID:
        errors.append(f"skillId 不一致：期望 {SKILL_ID}，实际 {data.get('skillId')}")
    if data.get("taskIntent") not in ALLOWED_INTENTS:
        errors.append(f"未知 taskIntent：{data.get('taskIntent')}")
    if data.get("status") not in {"pass", "warn", "failed"}:
        errors.append(f"根对象 status 不合法：{data.get('status')}")
    if data.get("status") != data.get("qualityReport", {}).get("status"):
        errors.append("根对象 status 必须与 qualityReport.status 一致。")
    if not isinstance(data.get("warnings"), list):
        errors.append("根对象 warnings 必须是数组。")
    elif data.get("warnings") != data.get("qualityReport", {}).get("warnings", []):
        errors.append("根对象 warnings 必须与 qualityReport.warnings 一致。")
    errors.extend(validate_data_source_report(data.get("dataSourceReport")))

    result = data.get("result", {})
    if not isinstance(result, dict):
        errors.append("result 必须是对象。")
        return errors, warnings

    digests = result.get("materialDigests", [])
    material_clusters = result.get("materialClusters", [])
    research_trajectory = result.get("researchTrajectory", {})
    topics = result.get("topicCandidates", [])
    evaluation_report = result.get("topicEvaluationReport")
    if "topicEvaluationReport" not in result or not isinstance(evaluation_report, dict):
        errors.append("result.topicEvaluationReport 必须存在且为对象。")
        evaluation_report = {}
    if not isinstance(digests, list):
        errors.append("result.materialDigests 必须是数组。")
        digests = []
    if not isinstance(material_clusters, list):
        errors.append("result.materialClusters 必须是数组。")
        material_clusters = []
    if not isinstance(research_trajectory, dict):
        errors.append("result.researchTrajectory 必须是对象。")
        research_trajectory = {}
    if not isinstance(topics, list) or not topics:
        errors.append("result.topicCandidates 必须是非空数组。")
        topics = []

    material_ids = set()
    material_signals: set[str] = set()
    for index, digest in enumerate(digests, 1):
        if not isinstance(digest, dict):
            errors.append(f"materialDigests[{index}] 必须是对象。")
            continue
        require_fields(digest, ["digestId", "materialId", "materialType", "title", "keyFacts", "topicSignals"], f"materialDigests[{index}]", errors)
        material_ids.add(digest.get("materialId"))
        signals = digest.get("topicSignals", [])
        if isinstance(signals, list):
            material_signals.update(str(signal) for signal in signals if non_empty(signal))

    cluster_ids: set[str] = set()
    clustered_material_ids: set[str] = set()
    if digests and not material_clusters:
        errors.append("存在 materialDigests 时必须输出 materialClusters。")
    for index, cluster in enumerate(material_clusters, 1):
        label = f"materialClusters[{index}]"
        if not isinstance(cluster, dict):
            errors.append(f"{label} 必须是对象。")
            continue
        require_fields(cluster, ["clusterId", "clusterTitle", "materialIds", "coreSignals", "researchAxis", "evidenceSummary", "currentStage", "gaps", "usableTopicAngles"], label, errors)
        if cluster.get("clusterId"):
            if cluster.get("clusterId") in cluster_ids:
                errors.append(f"{label}.clusterId 重复：{cluster.get('clusterId')}")
            cluster_ids.add(cluster.get("clusterId"))
        material_id_list = cluster.get("materialIds", [])
        if not isinstance(material_id_list, list) or not material_id_list:
            errors.append(f"{label}.materialIds 必须是非空数组。")
            material_id_list = []
        for material_id in material_id_list:
            if material_id not in material_ids:
                errors.append(f"{label} 引用了不存在的 materialId：{material_id}")
            else:
                clustered_material_ids.add(material_id)
        if not isinstance(cluster.get("coreSignals", []), list) or not cluster.get("coreSignals"):
            errors.append(f"{label}.coreSignals 必须是非空数组。")
        if cluster.get("currentStage") not in TRAJECTORY_STAGES - {"insufficient_material"}:
            errors.append(f"{label}.currentStage 不合法：{cluster.get('currentStage')}")
        evidence_summary = cluster.get("evidenceSummary", [])
        if not isinstance(evidence_summary, list):
            errors.append(f"{label}.evidenceSummary 必须是数组。")
            evidence_summary = []
        for evidence_index, evidence in enumerate(evidence_summary, 1):
            evidence_label = f"{label}.evidenceSummary[{evidence_index}]"
            if not isinstance(evidence, dict):
                errors.append(f"{evidence_label} 必须是对象。")
                continue
            require_fields(evidence, ["materialId", "fact"], evidence_label, errors)
            if evidence.get("materialId") not in material_id_list:
                errors.append(f"{evidence_label} 必须引用本聚类 materialIds 中的材料。")
        if not non_empty(cluster.get("gaps")):
            errors.append(f"{label}.gaps 必须说明该主题簇距离申报选题的缺口。")
        if not non_empty(cluster.get("usableTopicAngles")):
            errors.append(f"{label}.usableTopicAngles 必须提供可转化选题角度。")

    if research_trajectory:
        require_fields(
            research_trajectory,
            ["trajectoryId", "stage", "trajectorySummary", "currentFocusableDirections", "futureDeepeningPath", "risks"],
            "researchTrajectory",
            errors,
        )
        require_keys(research_trajectory, ["sourceMaterialIds", "dominantThemes"], "researchTrajectory", errors)
        if research_trajectory.get("stage") not in TRAJECTORY_STAGES:
            errors.append(f"researchTrajectory.stage 不合法：{research_trajectory.get('stage')}")
        trajectory_material_ids = research_trajectory.get("sourceMaterialIds", [])
        if not isinstance(trajectory_material_ids, list):
            errors.append("researchTrajectory.sourceMaterialIds 必须是数组。")
            trajectory_material_ids = []
        for material_id in trajectory_material_ids:
            if material_id not in material_ids:
                errors.append(f"researchTrajectory 引用了不存在的 materialId：{material_id}")
        if digests and not trajectory_material_ids:
            errors.append("存在材料时 researchTrajectory.sourceMaterialIds 不能为空。")
        if not digests and research_trajectory.get("stage") != "insufficient_material":
            errors.append("无材料时 researchTrajectory.stage 应为 insufficient_material。")
        future_steps = research_trajectory.get("futureDeepeningPath", [])
        if not isinstance(future_steps, list) or len(future_steps) < 2:
            errors.append("researchTrajectory.futureDeepeningPath 至少需要 2 步。")
            future_steps = []
        for step_index, step in enumerate(future_steps, 1):
            step_label = f"researchTrajectory.futureDeepeningPath[{step_index}]"
            if not isinstance(step, dict):
                errors.append(f"{step_label} 必须是对象。")
                continue
            require_fields(step, ["stepId", "timeframe", "action", "requiredEvidence", "output"], step_label, errors)
            if not isinstance(step.get("requiredEvidence", []), list) or not step.get("requiredEvidence"):
                errors.append(f"{step_label}.requiredEvidence 必须是非空数组。")
    else:
        errors.append("result.researchTrajectory 必须存在。")

    summative_count = 0
    planning_count = 0
    feasibility_warning_count = 0
    high_similarity_count = 0
    literature_signal_count = 0
    literature_signal_high_risk_count = 0
    topic_ids: set[str] = set()
    topic_titles: set[str] = set()
    for index, topic in enumerate(topics, 1):
        if not isinstance(topic, dict):
            errors.append(f"topicCandidates[{index}] 必须是对象。")
            continue
        require_fields(topic, ["topicId", "topicTitle", "topicType", "existingBasis", "feasibility", "keywords", "nextReadingQuestions", "basisGap", "differentiation"], f"topicCandidates[{index}]", errors)
        if topic.get("topicId"):
            topic_ids.add(topic.get("topicId"))
        title = str(topic.get("topicTitle", ""))
        if title in topic_titles:
            errors.append(f"topicCandidates[{index}] topicTitle 重复：{title}")
        if title:
            topic_titles.add(title)
        keywords = topic.get("keywords", [])
        if not isinstance(keywords, list) or len([item for item in keywords if non_empty(item)]) < 2:
            errors.append(f"topicCandidates[{index}] keywords 至少需要 2 个具体关键词。")
        if any(pattern.match(title) for pattern in GENERIC_TITLE_PATTERNS):
            title_signals = {str(keyword) for keyword in keywords if non_empty(keyword)}
            if not title_signals.intersection(material_signals):
                errors.append(f"topicCandidates[{index}] 选题过于空泛，缺少来自用户材料的具体研究对象或问题。")
        topic_type = topic.get("topicType")
        if topic_type == "summative":
            summative_count += 1
            existing_basis = topic.get("existingBasis", [])
            if not isinstance(existing_basis, list) or not existing_basis:
                errors.append(f"topicCandidates[{index}] 总结性选题必须有 existingBasis。")
            else:
                for basis_index, basis in enumerate(existing_basis, 1):
                    if not isinstance(basis, dict):
                        errors.append(f"topicCandidates[{index}].existingBasis[{basis_index}] 必须是对象并引用 materialId。")
                        continue
                    if basis.get("materialId") not in material_ids:
                        errors.append(f"topicCandidates[{index}] 引用了不存在的 materialId：{basis.get('materialId')}")
        elif topic_type == "planning":
            planning_count += 1
        else:
            errors.append(f"topicCandidates[{index}] topicType 必须是 summative 或 planning。")

        feasibility = topic.get("feasibility", {})
        if isinstance(feasibility, dict):
            score = feasibility.get("score")
            if not isinstance(score, (int, float)) or score < 1 or score > 5:
                errors.append(f"topicCandidates[{index}].feasibility.score 必须是 1-5。")
            if non_empty(feasibility.get("risks")):
                feasibility_warning_count += 1
            if not non_empty(feasibility.get("risks")) and not non_empty(feasibility.get("neededMaterials")):
                errors.append(f"topicCandidates[{index}] 每个选题必须给出风险或补资料清单。")
        else:
            errors.append(f"topicCandidates[{index}].feasibility 必须是对象。")

        basis_gap = topic.get("basisGap", {})
        if not isinstance(basis_gap, dict):
            errors.append(f"topicCandidates[{index}].basisGap 必须是对象。")
        else:
            require_fields(basis_gap, ["currentBasis", "targetRequirement", "gaps", "upgradePath"], f"topicCandidates[{index}].basisGap", errors)
            if not isinstance(basis_gap.get("currentBasis"), list) or not basis_gap.get("currentBasis"):
                errors.append(f"topicCandidates[{index}].basisGap.currentBasis 必须是非空数组。")
            if not isinstance(basis_gap.get("gaps"), list) or not basis_gap.get("gaps"):
                errors.append(f"topicCandidates[{index}].basisGap.gaps 必须是非空数组。")
            if not isinstance(basis_gap.get("upgradePath"), list) or len(basis_gap.get("upgradePath", [])) < 2:
                errors.append(f"topicCandidates[{index}].basisGap.upgradePath 至少需要 2 步。")

        differentiation = topic.get("differentiation", {})
        if not isinstance(differentiation, dict):
            errors.append(f"topicCandidates[{index}].differentiation 必须是对象。")
        else:
            require_fields(
                differentiation,
                ["nearestGrantId", "nearestGrantTitle", "similarityScore", "riskLevel", "differenceStrategy", "differentiatedTitleSuggestion"],
                f"topicCandidates[{index}].differentiation",
                errors,
            )
            score = differentiation.get("similarityScore")
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                errors.append(f"topicCandidates[{index}].differentiation.similarityScore 必须是 0-1。")
            risk = differentiation.get("riskLevel")
            if risk not in DIFFERENTIATION_RISKS:
                errors.append(f"topicCandidates[{index}].differentiation.riskLevel 不合法：{risk}")
            if risk == "high":
                high_similarity_count += 1
                if "差异" not in str(differentiation.get("differenceStrategy", "")) and "避免" not in str(differentiation.get("differenceStrategy", "")):
                    errors.append(f"topicCandidates[{index}].differentiation 高相似风险必须说明差异化策略。")

        if validate_literature_signal(topic.get("literatureSignals"), f"topicCandidates[{index}]", errors):
            literature_signal_count += 1
            if topic.get("literatureSignals", {}).get("differentiationRisk") == "high":
                literature_signal_high_risk_count += 1

    if isinstance(evaluation_report, dict):
        differentiation_checks = evaluation_report.get("differentiationChecks", [])
        basis_gap_checks = evaluation_report.get("basisGapChecks", [])
        literature_signal_checks = evaluation_report.get("literatureSignalChecks", [])
        cluster_checks = evaluation_report.get("materialClusterChecks", [])
        trajectory_check = evaluation_report.get("researchTrajectoryCheck", {})
        clustered_material_coverage = evaluation_report.get("clusteredMaterialCoverage")
        if not isinstance(differentiation_checks, list) or len(differentiation_checks) != len(topics):
            errors.append("topicEvaluationReport.differentiationChecks 数量必须与 topicCandidates 一致。")
            differentiation_checks = []
        if not isinstance(basis_gap_checks, list) or len(basis_gap_checks) != len(topics):
            errors.append("topicEvaluationReport.basisGapChecks 数量必须与 topicCandidates 一致。")
            basis_gap_checks = []
        if not isinstance(cluster_checks, list) or len(cluster_checks) != len(material_clusters):
            errors.append("topicEvaluationReport.materialClusterChecks 数量必须与 materialClusters 一致。")
            cluster_checks = []
        if not isinstance(literature_signal_checks, list):
            errors.append("topicEvaluationReport.literatureSignalChecks 必须是数组。")
            literature_signal_checks = []
        if literature_signal_count and len(literature_signal_checks) != literature_signal_count:
            errors.append("topicEvaluationReport.literatureSignalChecks 数量必须与含 literatureSignals 的 topicCandidates 一致。")
        expected_clustered_coverage = round(len(clustered_material_ids) / len(material_ids), 2) if material_ids else 0
        if clustered_material_coverage not in (None, expected_clustered_coverage):
            errors.append("topicEvaluationReport.clusteredMaterialCoverage 与实际不一致。")
        for check_index, check in enumerate(differentiation_checks, 1):
            if not isinstance(check, dict):
                errors.append(f"topicEvaluationReport.differentiationChecks[{check_index}] 必须是对象。")
                continue
            require_fields(check, ["topicId", "similarityScore", "riskLevel"], f"topicEvaluationReport.differentiationChecks[{check_index}]", errors)
            if check.get("topicId") not in topic_ids:
                errors.append(f"topicEvaluationReport.differentiationChecks[{check_index}] 引用了不存在的 topicId：{check.get('topicId')}")
            if check.get("riskLevel") not in DIFFERENTIATION_RISKS:
                errors.append(f"topicEvaluationReport.differentiationChecks[{check_index}] riskLevel 不合法：{check.get('riskLevel')}")
        for check_index, check in enumerate(basis_gap_checks, 1):
            if not isinstance(check, dict):
                errors.append(f"topicEvaluationReport.basisGapChecks[{check_index}] 必须是对象。")
                continue
            require_fields(check, ["topicId", "gapCount", "upgradeStepCount"], f"topicEvaluationReport.basisGapChecks[{check_index}]", errors)
            if check.get("topicId") not in topic_ids:
                errors.append(f"topicEvaluationReport.basisGapChecks[{check_index}] 引用了不存在的 topicId：{check.get('topicId')}")
            if not isinstance(check.get("gapCount"), int) or check.get("gapCount") < 1:
                errors.append(f"topicEvaluationReport.basisGapChecks[{check_index}].gapCount 必须大于 0。")
            if not isinstance(check.get("upgradeStepCount"), int) or check.get("upgradeStepCount") < 2:
                errors.append(f"topicEvaluationReport.basisGapChecks[{check_index}].upgradeStepCount 至少为 2。")
        for check_index, check in enumerate(literature_signal_checks, 1):
            if not isinstance(check, dict):
                errors.append(f"topicEvaluationReport.literatureSignalChecks[{check_index}] 必须是对象。")
                continue
            require_fields(check, ["topicId", "backend", "candidateCount", "returnedCount", "differentiationRisk"], f"topicEvaluationReport.literatureSignalChecks[{check_index}]", errors)
            if check.get("topicId") not in topic_ids:
                errors.append(f"topicEvaluationReport.literatureSignalChecks[{check_index}] 引用了不存在的 topicId：{check.get('topicId')}")
            if check.get("differentiationRisk") not in DIFFERENTIATION_RISKS:
                errors.append(f"topicEvaluationReport.literatureSignalChecks[{check_index}] differentiationRisk 不合法：{check.get('differentiationRisk')}")
        for check_index, check in enumerate(cluster_checks, 1):
            if not isinstance(check, dict):
                errors.append(f"topicEvaluationReport.materialClusterChecks[{check_index}] 必须是对象。")
                continue
            require_fields(check, ["clusterId", "materialCount", "signalCount"], f"topicEvaluationReport.materialClusterChecks[{check_index}]", errors)
            if check.get("clusterId") not in cluster_ids:
                errors.append(f"topicEvaluationReport.materialClusterChecks[{check_index}] 引用了不存在的 clusterId：{check.get('clusterId')}")
            if not isinstance(check.get("materialCount"), int) or check.get("materialCount") < 1:
                errors.append(f"topicEvaluationReport.materialClusterChecks[{check_index}].materialCount 必须大于 0。")
            if not isinstance(check.get("signalCount"), int) or check.get("signalCount") < 1:
                errors.append(f"topicEvaluationReport.materialClusterChecks[{check_index}].signalCount 必须大于 0。")
        if not isinstance(trajectory_check, dict):
            errors.append("topicEvaluationReport.researchTrajectoryCheck 必须是对象。")
        else:
            require_fields(trajectory_check, ["stage", "sourceMaterialCount", "futureStepCount"], "topicEvaluationReport.researchTrajectoryCheck", errors)
            if trajectory_check.get("stage") != research_trajectory.get("stage"):
                errors.append("topicEvaluationReport.researchTrajectoryCheck.stage 与 researchTrajectory 不一致。")
            if trajectory_check.get("sourceMaterialCount") != len(research_trajectory.get("sourceMaterialIds", [])):
                errors.append("topicEvaluationReport.researchTrajectoryCheck.sourceMaterialCount 与实际不一致。")
            if trajectory_check.get("futureStepCount") != len(research_trajectory.get("futureDeepeningPath", [])):
                errors.append("topicEvaluationReport.researchTrajectoryCheck.futureStepCount 与实际不一致。")

    metrics = data.get("qualityReport", {}).get("metrics", {})
    if isinstance(metrics, dict):
        if metrics.get("topicCount") not in (None, len(topics)):
            errors.append(f"qualityReport.metrics.topicCount 与实际选题数不一致：{metrics.get('topicCount')} != {len(topics)}")
        if metrics.get("summativeCount") not in (None, summative_count):
            errors.append("qualityReport.metrics.summativeCount 与实际不一致。")
        if metrics.get("planningCount") not in (None, planning_count):
            errors.append("qualityReport.metrics.planningCount 与实际不一致。")
        if metrics.get("feasibilityWarnings") not in (None, feasibility_warning_count):
            errors.append("qualityReport.metrics.feasibilityWarnings 与实际不一致。")
        if metrics.get("basisGapCount") not in (None, len(topics)):
            errors.append("qualityReport.metrics.basisGapCount 与实际不一致。")
        if metrics.get("differentiationCheckCount") not in (None, len(topics)):
            errors.append("qualityReport.metrics.differentiationCheckCount 与实际不一致。")
        if metrics.get("highSimilarityCount") not in (None, high_similarity_count):
            errors.append("qualityReport.metrics.highSimilarityCount 与实际不一致。")
        if metrics.get("materialClusterCount") not in (None, len(material_clusters)):
            errors.append("qualityReport.metrics.materialClusterCount 与实际不一致。")
        expected_clustered_coverage = round(len(clustered_material_ids) / len(material_ids), 2) if material_ids else 0
        if metrics.get("clusteredMaterialCoverage") not in (None, expected_clustered_coverage):
            errors.append("qualityReport.metrics.clusteredMaterialCoverage 与实际不一致。")
        if metrics.get("trajectoryStepCount") not in (None, len(research_trajectory.get("futureDeepeningPath", []))):
            errors.append("qualityReport.metrics.trajectoryStepCount 与实际不一致。")
        if metrics.get("literatureSignalCount") not in (None, literature_signal_count):
            errors.append("qualityReport.metrics.literatureSignalCount 与实际不一致。")
        if metrics.get("literatureSignalHighRiskCount") not in (None, literature_signal_high_risk_count):
            errors.append("qualityReport.metrics.literatureSignalHighRiskCount 与实际不一致。")

    validate_quality_report(data, errors, warnings)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验研究选题生成 JSON 产物。")
    parser.add_argument("output_json", help="待校验 JSON 文件")
    args = parser.parse_args()

    data = load_json(Path(args.output_json))
    errors, warnings = validate(data)
    if errors:
        print("不通过")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"- 警告：{warning}")
        return 1

    print("通过")
    print(f"- 已检查 {args.output_json}")
    print(f"- 选题数：{len(data.get('result', {}).get('topicCandidates', []))}")
    for warning in warnings:
        print(f"- 警告：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
