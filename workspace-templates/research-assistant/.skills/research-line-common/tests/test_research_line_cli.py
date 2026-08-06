from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = COMMON_ROOT.parents[1]
BUNDLED_PYTHON = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "bin" / "python3"

SAMPLE_OUTPUTS = [
    "agent_cases/research-topic-generation-skill/generated-outputs/sample-valid.json",
    "agent_cases/literature-reading-skill/generated-outputs/sample-valid.json",
    "agent_cases/paper-writing-skill/generated-outputs/sample-valid.json",
    "agent_cases/project-proposal-skill/generated-outputs/sample-valid.json",
]


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


def python_with_docx() -> str | None:
    candidates = [os.environ.get("DOCX_EXPORT_PYTHON"), str(BUNDLED_PYTHON), sys.executable]
    for candidate in candidates:
        if not candidate:
            continue
        result = subprocess.run(
            [candidate, "-c", "import docx"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return None


class ResearchLineCliTests(unittest.TestCase):
    def test_guard_subcommand_matches_common_gate_summary(self) -> None:
        result = run_cmd(
            [
                sys.executable,
                "agent_cases/research-line-common/research_line_cli.py",
                "guard",
                *SAMPLE_OUTPUTS,
            ]
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["command"], "guard")
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(payload["summary"]["total"], 4)
        self.assertEqual(payload["summary"]["readyForRender"], 3)
        self.assertEqual(payload["summary"]["needsReview"], 1)
        self.assertEqual(payload["summary"]["rejected"], 0)

    def test_workspace_subcommand_generates_and_validates_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="research-line-cli-") as tmpdir:
            workspace_path = Path(tmpdir) / "workspace.json"
            result = run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/research_line_cli.py",
                    "workspace",
                    *SAMPLE_OUTPUTS,
                    "--output",
                    str(workspace_path),
                    "--workspace-id",
                    "rw-cli-test",
                ]
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["command"], "workspace")
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["workspaceId"], "rw-cli-test")
            self.assertTrue(workspace_path.exists())

            validate = run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/research_line_cli.py",
                    "workspace",
                    "--output",
                    str(workspace_path),
                    "--validate-only",
                ]
            )
            self.assertEqual(json.loads(validate.stdout)["status"], "passed")

    def test_workspace_subcommand_requires_outputs_when_generating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="research-line-cli-empty-") as tmpdir:
            result = run_cmd(
                [
                    sys.executable,
                    "agent_cases/research-line-common/research_line_cli.py",
                    "workspace",
                    "--output",
                    str(Path(tmpdir) / "workspace.json"),
                ],
                expect_success=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["command"], "workspace")
            self.assertEqual(payload["status"], "failed")

    def test_docx_subcommand_exports_all_four_reports(self) -> None:
        python = python_with_docx()
        if not python:
            self.skipTest("python-docx is not available in the current or bundled Python runtime")

        with tempfile.TemporaryDirectory(prefix="research-line-cli-docx-") as tmpdir:
            result = run_cmd(
                [
                    python,
                    "agent_cases/research-line-common/research_line_cli.py",
                    "docx",
                    *SAMPLE_OUTPUTS,
                    "--output-dir",
                    tmpdir,
                ]
            )
            payload = json.loads(result.stdout)

            self.assertEqual(payload["command"], "docx")
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(len(payload["files"]), 4)
            for item in payload["files"]:
                self.assertGreater(item["bytes"], 1000)
                self.assertTrue(Path(item["path"]).exists())


if __name__ == "__main__":
    unittest.main()
