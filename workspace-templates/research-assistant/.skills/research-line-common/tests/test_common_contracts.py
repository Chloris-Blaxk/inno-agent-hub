from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]


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


data_source_report = load_module("data_source_report_for_test", "data_source_report.py")
evidence_card_builder = load_module("evidence_card_builder_for_test", "evidence_card_builder.py")
evidence_policy = load_module("evidence_policy_for_test", "evidence_policy.py")
literature_adapter = load_module("literature_adapter_for_test", "literature_adapter.py")
material_adapter = load_module("material_adapter_for_test", "material_adapter.py")
material_trajectory = load_module("material_trajectory_for_test", "material_trajectory.py")
support_matcher = load_module("support_matcher_for_test", "support_matcher.py")
citation_verifier = load_module("citation_verifier_for_test", "citation_verifier.py")
model_output_guard = load_module("model_output_guard_for_test", "model_output_guard.py")
workspace_summary = load_module("workspace_summary_for_test", "workspace_summary.py")


class EvidencePolicyTests(unittest.TestCase):
    def test_metadata_cannot_become_supporting_evidence(self) -> None:
        self.assertFalse(evidence_policy.can_create_evidence_card("metadata"))
        self.assertFalse(evidence_policy.can_create_evidence_card("abstract", "metadata_verified"))
        self.assertTrue(evidence_policy.can_create_evidence_card("abstract", "abstract_verified"))
        self.assertTrue(evidence_policy.can_create_evidence_card("fulltext", "fulltext_verified"))

    def test_citation_insert_requires_authentic_source_support_locator_and_format(self) -> None:
        self.assertTrue(
            evidence_policy.can_insert_citation(
                evidence_level="abstract_verified",
                support_type="partial_support",
                source_status="whitelist",
                has_source_locator=True,
                has_formatted_citation=True,
            )
        )
        self.assertFalse(
            evidence_policy.can_insert_citation(
                evidence_level="metadata_verified",
                support_type="direct_support",
                source_status="whitelist",
                has_source_locator=True,
                has_formatted_citation=True,
            )
        )
        self.assertFalse(
            evidence_policy.can_insert_citation(
                evidence_level="fulltext_verified",
                support_type="direct_support",
                source_status="user_provided",
                has_source_locator=True,
                has_formatted_citation=True,
            )
        )

    def test_high_risk_actions_require_teacher_confirmation(self) -> None:
        self.assertTrue(evidence_policy.requires_teacher_confirmation("citation_insert"))
        self.assertTrue(evidence_policy.requires_teacher_confirmation("budget_amount_write"))
        self.assertTrue(evidence_policy.requires_teacher_confirmation("local_rewrite", "needs_user_confirmation"))
        self.assertFalse(evidence_policy.requires_teacher_confirmation("structure_diagnosis"))

    def test_text_availability_and_evidence_level_contract(self) -> None:
        self.assertFalse(evidence_policy.has_readable_text("metadata"))
        self.assertTrue(evidence_policy.has_readable_text("abstract"))
        self.assertTrue(evidence_policy.evidence_level_matches_availability("metadata_verified", "metadata"))
        self.assertTrue(evidence_policy.evidence_level_matches_availability("abstract_verified", "fulltext"))
        self.assertTrue(evidence_policy.evidence_level_matches_availability("fulltext_verified", "user_uploaded"))
        self.assertFalse(evidence_policy.evidence_level_matches_availability("fulltext_verified", "abstract"))
        self.assertFalse(evidence_policy.evidence_level_matches_availability("user_text_only", "fulltext"))

    def test_abstract_support_requires_limits(self) -> None:
        self.assertTrue(evidence_policy.requires_limits_for_abstract_support("abstract_verified", "partial_support", "abstract"))
        self.assertFalse(evidence_policy.requires_limits_for_abstract_support("abstract_verified", "background", "abstract"))
        self.assertFalse(evidence_policy.requires_limits_for_abstract_support("fulltext_verified", "direct_support", "fulltext"))

    def test_metadata_only_candidate_must_not_be_used_as_evidence(self) -> None:
        safe_candidate = {
            "paperId": "paper-001",
            "textAvailability": "metadata",
            "evidenceLevel": "metadata_verified",
            "relation": "topic_related",
            "limits": ["metadata only"],
        }
        unsafe_candidate = {
            **safe_candidate,
            "evidenceText": "该文证明了即时反馈显著提升成绩。",
            "supportStatus": "supports",
        }

        self.assertEqual(evidence_policy.metadata_as_evidence_violations(safe_candidate), [])
        self.assertTrue(evidence_policy.metadata_as_evidence_violations(unsafe_candidate))
        self.assertTrue(evidence_policy.forbid_metadata_as_evidence(safe_candidate))
        self.assertFalse(evidence_policy.forbid_metadata_as_evidence(unsafe_candidate))

    def test_synthetic_fixture_cannot_be_used_as_real_evidence(self) -> None:
        fixture = {
            "sourceStatus": "synthetic",
            "syntheticGeneratedBy": "InnoSpark-235B",
            "usableFor": ["fixture", "validator_test"],
            "notUsableFor": ["real_evidence", "citation_support", "project_fact_without_user_confirmation"],
        }

        self.assertEqual(evidence_policy.synthetic_source_violations(fixture, purpose="fixture"), [])
        self.assertTrue(evidence_policy.synthetic_source_violations(fixture, purpose="real_evidence"))
        self.assertTrue(evidence_policy.synthetic_source_violations(fixture, purpose="citation_support"))

    def test_object_aware_confirmation_helpers(self) -> None:
        insertion = {"decision": "suggest_insert"}
        draft = {"draftStatus": "draft_reference"}
        ordinary = {"targetType": "reading_list_item", "status": "candidate"}

        self.assertTrue(evidence_policy.requires_teacher_confirmation_for_item(insertion))
        self.assertTrue(evidence_policy.requires_teacher_confirmation_for_item(draft))
        self.assertFalse(evidence_policy.requires_teacher_confirmation_for_item(ordinary))
        self.assertEqual(
            evidence_policy.normalize_confirmation_status(None, requires_confirmation=True),
            "pending_teacher_confirmation",
        )


class LiteratureAdapterTests(unittest.TestCase):
    def test_search_papers_returns_unified_records_and_report(self) -> None:
        result = literature_adapter.search_papers(
            research_topic="小学数学即时反馈与错因诊断",
            keywords=["即时反馈", "错因诊断"],
            limit=3,
        )

        records = result["records"]
        report = result["corpusSearchReport"]

        self.assertTrue(records)
        self.assertEqual(report["adapterVersion"], literature_adapter.ADAPTER_VERSION)
        self.assertEqual(report["returnedCount"], len(records))
        self.assertEqual(len(report["topHits"]), len(records))
        self.assertGreaterEqual(report["candidateCount"], len(records))
        self.assertTrue(all(record.get("paperId") for record in records))
        self.assertTrue(all(record.get("evidenceLevel") for record in records))

    def test_source_trace_returns_paper_writing_candidate_contract(self) -> None:
        trace = literature_adapter.source_trace(query_text="即时反馈有助于教师调整教学决策")
        supporting = [candidate for candidate in trace["candidates"] if candidate.get("supportStatus") == "supports"]

        self.assertEqual(trace["decision"], "verified_source_found")
        self.assertTrue(trace["usableEvidenceCards"])
        self.assertTrue(trace["papers"])
        self.assertTrue(supporting)
        candidate = supporting[0]
        for field in ["paperId", "matchType", "matchSnippet", "confidence", "quoteLocation", "sourceLocator", "evidenceLevel", "citation"]:
            self.assertIn(field, candidate)
            self.assertTrue(candidate[field])
        self.assertEqual(candidate["matchType"], "evidence_card")
        self.assertIsInstance(candidate["sourceLocator"], dict)
        self.assertIn(candidate["evidenceLevel"], {"abstract_verified", "fulltext_verified", "user_text_only"})


class DataSourceReportTests(unittest.TestCase):
    def test_mock_source_requires_explicit_limitation(self) -> None:
        report = data_source_report.build_data_source_report(
            skill_id="demo-skill",
            task_intent="demo",
            sources=[
                data_source_report.build_source(
                    source_id="mock-index",
                    source_name="本地样例索引",
                    source_type="local_mock",
                    data_type="literature_metadata",
                    record_count=3,
                    authorization_status="mock_sample",
                )
            ],
        )

        self.assertTrue(report["mockDataUsed"])
        self.assertTrue(report["overallLimitations"])
        self.assertEqual(data_source_report.validate_data_source_report(report), [])

    def test_validator_rejects_missing_mock_limitation(self) -> None:
        report = {
            "dataSources": [
                {
                    "sourceId": "mock-index",
                    "sourceName": "本地样例索引",
                    "sourceType": "local_mock",
                    "dataType": "literature_metadata",
                    "recordCount": 3,
                    "authorizationStatus": "mock_sample",
                    "limitations": [],
                }
            ],
            "mockDataUsed": True,
            "overallLimitations": [],
        }

        self.assertTrue(data_source_report.validate_data_source_report(report))


class MaterialAdapterTests(unittest.TestCase):
    def test_normalize_source_materials_marks_synthetic_limits(self) -> None:
        materials = material_adapter.normalize_source_materials(
            [
                {
                    "materialId": "mat-001",
                    "materialType": "reflection",
                    "title": "即时反馈教学反思",
                    "content": "本节课用课堂投票进行即时反馈。",
                    "sourceStatus": "synthetic",
                    "syntheticGeneratedBy": "InnoSpark-235B",
                }
            ]
        )

        self.assertEqual(materials[0]["materialType"], "teaching_reflection")
        self.assertEqual(materials[0]["sourceStatus"], "synthetic")
        self.assertIn("real_evidence", materials[0]["notUsableFor"])
        self.assertTrue(materials[0]["permissions"]["canUseForGeneration"])

        project_material = material_adapter.normalize_source_materials(
            [{"materialId": "mat-002", "materialType": "proposal", "title": "申报材料", "content": "项目负责人 1 人"}],
            default_material_type="project_process_record",
        )[0]
        self.assertEqual(project_material["materialType"], "project_process_record")

    def test_build_material_digests_keeps_source_span_and_limits(self) -> None:
        digests = material_adapter.build_material_digests(
            [
                {
                    "materialId": "mat-001",
                    "materialType": "lesson_case",
                    "title": "分数错因诊断课例",
                    "content": "课堂观察发现学生在分数通分中存在典型错因，教师用即时反馈调整讲评。",
                }
            ]
        )

        self.assertEqual(digests[0]["materialId"], "mat-001")
        self.assertIn("错因诊断", digests[0]["topicSignals"])
        self.assertEqual(digests[0]["keyFacts"][0]["sourceSpan"], "content[:80]")
        self.assertEqual(digests[0]["limits"], [])

    def test_material_trajectory_clusters_and_stage(self) -> None:
        digests = material_adapter.build_material_digests(
            [
                {
                    "materialId": "mat-001",
                    "materialType": "lesson_case",
                    "title": "分数错因诊断课例",
                    "content": "学生分数教学错因诊断和讲评改进。",
                },
                {
                    "materialId": "mat-002",
                    "materialType": "project_process_record",
                    "title": "课堂观察记录",
                    "content": "连续课堂观察记录显示即时反馈影响讲评顺序。",
                },
            ]
        )
        clusters = material_trajectory.build_material_clusters(digests)
        trajectory = material_trajectory.build_research_trajectory({"subject": "小学数学"}, digests, clusters)

        self.assertTrue(clusters)
        self.assertEqual(trajectory["stage"], "evidence_building")
        self.assertEqual(set(trajectory["sourceMaterialIds"]), {"mat-001", "mat-002"})
        self.assertGreaterEqual(len(trajectory["futureDeepeningPath"]), 2)


class EvidenceCardBuilderTests(unittest.TestCase):
    def test_metadata_only_does_not_create_evidence_card(self) -> None:
        card = evidence_card_builder.build_evidence_card_from_paper(
            1,
            {
                "paperId": "paper-meta-001",
                "title": "题录候选",
                "textAvailability": "metadata",
                "evidenceLevel": "metadata_verified",
            },
        )
        self.assertIsNone(card)

    def test_user_uploaded_text_creates_limited_evidence_card(self) -> None:
        card = evidence_card_builder.build_evidence_card_from_paper(
            1,
            {
                "paperId": "paper-user-001",
                "title": "用户上传讲评课记录",
                "uploadedText": "课堂即时反馈帮助教师调整教学决策，但没有报告显著性。",
                "textAvailability": "user_uploaded",
                "evidenceLevel": "user_text_only",
                "sourceStatus": "user_provided",
            },
        )

        self.assertIsNotNone(card)
        assert card is not None
        self.assertEqual(card["evidenceLevel"], "user_text_only")
        self.assertEqual(card["sourceLocator"]["locationType"], "user_uploaded_text")
        self.assertIn("文献真实性需另行", "；".join(card["limits"]))

    def test_readable_abstract_overrides_legacy_metadata_level(self) -> None:
        card = evidence_card_builder.build_evidence_card_from_paper(
            2,
            {
                "paperId": "paper-abstract-001",
                "title": "摘要可读文献",
                "abstract": "课堂即时反馈可以作为教师调整教学决策的依据。",
                "textAvailability": "abstract",
                "evidenceLevel": "metadata_verified",
            },
        )

        self.assertIsNotNone(card)
        assert card is not None
        self.assertEqual(card["evidenceLevel"], "abstract_verified")


class SupportMatcherTests(unittest.TestCase):
    def test_claim_support_requires_supporting_evidence_card(self) -> None:
        card = {
            "cardId": "ec-001",
            "claim": "课堂即时反馈有助于教师调整教学决策。",
            "evidenceText": "课堂即时反馈有助于教师调整教学决策。",
            "paperId": "paper-001",
            "supportType": "direct_support",
            "evidenceLevel": "abstract_verified",
        }
        check = support_matcher.check_claim_support(
            "课堂即时反馈有助于教师调整教学决策。",
            [card],
            [{"paperId": "paper-001", "sourceStatus": "whitelist"}],
        )

        self.assertEqual(check["decision"], "suggest_insert")
        self.assertTrue(check["requiresTeacherConfirmation"])
        self.assertEqual(check["evidenceMatches"][0]["evidenceCardId"], "ec-001")

    def test_metadata_candidate_needs_more_evidence(self) -> None:
        check = support_matcher.check_claim_support(
            "即时反馈显著提升学生成绩。",
            [],
            [{"paperId": "paper-meta-001", "evidenceLevel": "metadata_verified", "sourceStatus": "external_verified"}],
        )

        self.assertEqual(check["decision"], "need_more_evidence")
        self.assertEqual(check["literatureVerification"]["status"], "verified")

    def test_background_card_only_supports_background_claims(self) -> None:
        card = {
            "cardId": "ec-bg-001",
            "claim": "小学数学课堂即时反馈与错因诊断的行动研究可为相关研究提供背景线索",
            "evidenceText": "本文讨论即时反馈信息如何帮助教师识别学生典型错因并调整讲评策略。",
            "paperId": "paper-001",
            "supportType": "background",
            "evidenceLevel": "abstract_verified",
        }

        background = support_matcher.check_claim_support(card["claim"], [card], [{"paperId": "paper-001", "sourceStatus": "whitelist"}])
        strong = support_matcher.check_claim_support("即时反馈显著提升学生数学成绩。", [card], [{"paperId": "paper-001", "sourceStatus": "whitelist"}])

        self.assertEqual(background["decision"], "suggest_insert")
        self.assertNotEqual(strong["decision"], "suggest_insert")


class CitationVerifierTests(unittest.TestCase):
    def test_batch_verifier_normalizes_adapter_output(self) -> None:
        class FakeAdapter:
            def verify_citation(self, citation: dict[str, object]) -> dict[str, object]:
                return {
                    "verified": True,
                    "confidence": "high",
                    "verificationStatus": "verified",
                    "verificationNote": "matched",
                    "bestMatch": {"paperId": citation.get("paperId")},
                }

        checks = citation_verifier.verify_citations_batch(
            [{"paperId": "paper-001", "title": "课堂即时反馈研究"}],
            adapters=[FakeAdapter()],
        )

        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["verificationStatus"], "verified")
        self.assertIn("不能证明其支撑", "；".join(checks[0]["limits"]))


class CommonContractTests(unittest.TestCase):
    def test_research_line_schema_uses_current_status_contract(self) -> None:
        schema = json.loads((COMMON_ROOT / "schemas" / "research_line.schema.json").read_text(encoding="utf-8"))
        self.assertIn("status", schema["required"])
        self.assertIn("warnings", schema["required"])
        self.assertIn("dataSourceReport", schema["required"])
        self.assertEqual(schema["properties"]["status"]["enum"], ["pass", "warn", "failed"])
        self.assertEqual(schema["properties"]["qualityReport"]["properties"]["status"]["enum"], ["pass", "warn", "failed"])
        self.assertIn("dataSourceReport", schema["properties"])

    def test_p0_schema_files_define_missing_capability_contracts(self) -> None:
        expected = {
            "source_material.schema.json": ["materialId", "materialType", "title", "sourceStatus", "permissions"],
            "material_digest.schema.json": ["digestId", "materialId", "materialType", "title", "keyFacts", "topicSignals", "sourceStatus", "limits"],
            "reference_resource.schema.json": ["resourceId", "resourceType", "version", "source", "license", "items"],
            "claim_support_check.schema.json": ["checkId", "claim", "literatureVerification", "evidenceMatches", "decision", "reasons"],
            "confirmation_action.schema.json": ["actionId", "targetType", "targetId", "action", "timestamp"],
        }
        for filename, required in expected.items():
            with self.subTest(filename=filename):
                schema = json.loads((COMMON_ROOT / "schemas" / filename).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["required"], required)
                self.assertEqual(schema["type"], "object")

    def test_claim_support_schema_keeps_suggest_insert_pending_confirmation(self) -> None:
        schema = json.loads((COMMON_ROOT / "schemas" / "claim_support_check.schema.json").read_text(encoding="utf-8"))
        self.assertIn("suggest_insert", schema["properties"]["decision"]["enum"])
        serialized = json.dumps(schema, ensure_ascii=False)
        self.assertIn('"requiresTeacherConfirmation": {"const": true}', serialized)

    def test_source_material_schema_marks_synthetic_required_fields(self) -> None:
        schema = json.loads((COMMON_ROOT / "schemas" / "source_material.schema.json").read_text(encoding="utf-8"))
        source_status_enum = schema["properties"]["sourceStatus"]["enum"]
        self.assertIn("synthetic", source_status_enum)
        serialized = json.dumps(schema, ensure_ascii=False)
        self.assertIn("syntheticGeneratedBy", serialized)
        self.assertIn("notUsableFor", serialized)

    def test_model_output_guard_maps_quality_statuses(self) -> None:
        self.assertEqual(model_output_guard.QUALITY_STATUS_TO_GATE["pass"], "ready_for_render")
        self.assertEqual(model_output_guard.QUALITY_STATUS_TO_GATE["warn"], "needs_review")
        self.assertEqual(model_output_guard.QUALITY_STATUS_TO_GATE["failed"], "rejected")
        self.assertEqual(model_output_guard.QUALITY_STATUS_TO_GATE["fail"], "rejected")

    def test_workspace_summary_compacts_project_fact_table_without_source_refs(self) -> None:
        output = {
            "skillId": "project-proposal-skill",
            "taskIntent": "project_application",
            "summary": "demo",
            "qualityReport": {"status": "pass", "warnings": [], "metrics": {}},
            "result": {
                "projectFactTable": {
                    "projectId": "proj-001",
                    "facts": [
                        {
                            "factId": "fact-001",
                            "field": "team.memberCount",
                            "value": "核心成员 4 人",
                            "sourceRefs": ["mat-001", "mat-002"],
                            "confidence": "high",
                            "status": "confirmed",
                        },
                        {
                            "factId": "fact-002",
                            "field": "budget.total",
                            "value": "2 万元",
                            "sourceRefs": ["mat-003"],
                            "confidence": "medium",
                            "status": "needs_user_confirmation",
                        },
                    ],
                    "missingFields": [{"field": "timeline.cycle"}],
                    "conflicts": [{"field": "budget.total"}],
                }
            },
            "handoff": {},
        }

        workspace = workspace_summary.collect_workspace([output], "rw-test")
        table = workspace["projectFactTables"][0]

        self.assertEqual(table["projectId"], "proj-001")
        self.assertEqual(table["confirmedFactCount"], 1)
        self.assertEqual(table["needsConfirmationCount"], 1)
        self.assertEqual(table["missingFields"], ["timeline.cycle"])
        self.assertEqual(table["conflictFields"], ["budget.total"])
        self.assertEqual(table["facts"][0]["sourceRefCount"], 2)
        self.assertNotIn("sourceRefs", table["facts"][0])
        workspace_summary.validate_workspace(workspace)


if __name__ == "__main__":
    unittest.main()
