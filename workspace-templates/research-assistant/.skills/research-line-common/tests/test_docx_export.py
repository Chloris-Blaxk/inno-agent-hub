from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


COMMON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = COMMON_ROOT.parents[1]
BUNDLED_PYTHON = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "bin" / "python3"


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


class DocxExportTests(unittest.TestCase):
    def test_docx_export_supports_all_four_research_skills(self) -> None:
        python = python_with_docx()
        if not python:
            self.skipTest("python-docx is not available in the current or bundled Python runtime")

        sample_outputs = [
            "agent_cases/research-topic-generation-skill/generated-outputs/sample-valid.json",
            "agent_cases/literature-reading-skill/generated-outputs/sample-valid.json",
            "agent_cases/paper-writing-skill/generated-outputs/sample-valid.json",
            "agent_cases/project-proposal-skill/generated-outputs/sample-valid.json",
        ]
        with tempfile.TemporaryDirectory(prefix="research-line-docx-") as tmpdir:
            result = subprocess.run(
                [
                    python,
                    "agent_cases/research-line-common/docx_export.py",
                    *sample_outputs,
                    "--output-dir",
                    tmpdir,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise AssertionError(f"docx_export failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")

            files = sorted(Path(tmpdir).glob("*.docx"))
            self.assertGreaterEqual(len(files), 4)
            titles = {
                "研究选题生成报告",
                "文献阅读助手报告",
                "论文写作助手查源与润色报告",
                "项目事实表",
            }
            document_xml = ""
            for path in files:
                self.assertGreater(path.stat().st_size, 1000, path)
                with zipfile.ZipFile(path) as archive:
                    document_xml += archive.read("word/document.xml").decode("utf-8")
            for title in titles:
                self.assertIn(title, document_xml)


if __name__ == "__main__":
    unittest.main()
