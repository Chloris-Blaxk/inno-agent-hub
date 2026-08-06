from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = COMMON_ROOT.parents[1]


def run_cmd(args: list[str], *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if expect_success and result.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"args: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    if not expect_success and result.returncode == 0:
        raise AssertionError(
            "command unexpectedly succeeded\n"
            f"args: {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


class ResearchLineE2ETests(unittest.TestCase):
    def test_four_skill_template_cli_outputs_pass_guard_and_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="research-line-e2e-") as tmpdir:
            tmp = Path(tmpdir)
            outputs = {
                "topic": tmp / "research-topic",
                "literature": tmp / "literature",
                "paper": tmp / "paper",
                "project": tmp / "project",
            }
            render_specs = [
                (
                    "agent_cases/research-topic-generation-skill/scripts/render_research_topic.py",
                    outputs["topic"],
                    "agent_cases/research-topic-generation-skill/examples/sample-request.json",
                ),
                (
                    "agent_cases/literature-reading-skill/scripts/render_literature_reading.py",
                    outputs["literature"],
                    "agent_cases/literature-reading-skill/examples/sample-request.json",
                ),
                (
                    "agent_cases/paper-writing-skill/scripts/render_paper_writing.py",
                    outputs["paper"],
                    "agent_cases/paper-writing-skill/examples/sample-request.json",
                ),
                (
                    "agent_cases/project-proposal-skill/scripts/render_project_proposal.py",
                    outputs["project"],
                    "agent_cases/project-proposal-skill/examples/sample-request.json",
                ),
            ]

            json_outputs: list[Path] = []
            for script, output_base, request in render_specs:
                run_cmd([sys.executable, script, str(output_base), "--config", request, "--validate"])
                json_path = output_base.with_suffix(".json")
                md_path = output_base.with_suffix(".md")
                self.assertTrue(json_path.exists(), json_path)
                self.assertTrue(md_path.exists(), md_path)
                data = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertIn("dataSourceReport", data)
                self.assertTrue(data["dataSourceReport"]["dataSources"])
                self.assertTrue(data["dataSourceReport"]["overallLimitations"])
                self.assertEqual(
                    {artifact["type"] for artifact in data.get("artifacts", [])},
                    {"json", "markdown"},
                )
                json_outputs.append(json_path)

            guard = run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/model_output_guard.py",
                    *[str(path) for path in json_outputs],
                ]
            )
            guard_payload = json.loads(guard.stdout)
            self.assertEqual(guard_payload["summary"]["total"], 4)
            self.assertEqual(guard_payload["summary"]["rejected"], 0)
            self.assertEqual(guard_payload["summary"]["readyForRender"], 2)
            self.assertEqual(guard_payload["summary"]["needsReview"], 2)

            workspace_path = tmp / "workspace.json"
            run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/workspace_summary.py",
                    *[str(path) for path in json_outputs],
                    "--output",
                    str(workspace_path),
                ]
            )
            run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/workspace_summary.py",
                    str(workspace_path),
                    "--output",
                    str(workspace_path),
                    "--validate-only",
                ]
            )
            workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
            self.assertEqual(workspace["sourceOutputCount"], 4)
            self.assertEqual(len(workspace["topicCandidates"]), 5)
            self.assertGreaterEqual(len(workspace["literatureRecords"]), 5)
            self.assertEqual(workspace["contextBudget"]["status"], "ok")
            self.assertNotIn("sourceRefs", json.dumps(workspace.get("projectFactTables", []), ensure_ascii=False))

    def test_invalid_fixtures_remain_expected_failures(self) -> None:
        invalid_specs = [
            (
                "agent_cases/research-topic-generation-skill/scripts/validate_research_topic.py",
                "agent_cases/research-topic-generation-skill/generated-outputs/sample-invalid.json",
            ),
            (
                "agent_cases/literature-reading-skill/scripts/validate_literature_reading.py",
                "agent_cases/literature-reading-skill/generated-outputs/sample-invalid.json",
            ),
            (
                "agent_cases/paper-writing-skill/scripts/validate_paper_writing.py",
                "agent_cases/paper-writing-skill/generated-outputs/sample-invalid.json",
            ),
            (
                "agent_cases/project-proposal-skill/scripts/validate_project_proposal.py",
                "agent_cases/project-proposal-skill/generated-outputs/sample-invalid.json",
            ),
        ]
        for validator, fixture in invalid_specs:
            with self.subTest(fixture=fixture):
                result = run_cmd([sys.executable, validator, fixture], expect_success=False)
                combined_output = result.stdout + result.stderr
                self.assertIn("不通过", combined_output)
                self.assertIn("expected_invalid_fixture", combined_output)


if __name__ == "__main__":
    unittest.main()
