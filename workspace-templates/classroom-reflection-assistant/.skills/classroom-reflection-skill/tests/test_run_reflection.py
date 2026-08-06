import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "run_reflection.py"


spec = importlib.util.spec_from_file_location("run_reflection", SCRIPT)
run_reflection = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["run_reflection"] = run_reflection
spec.loader.exec_module(run_reflection)


class RunReflectionTest(unittest.TestCase):
    def test_select_rubric_prefers_custom_rubric(self):
        selection = run_reflection.select_rubric(
            {
                "subject": "语文",
                "customRubric": "一级指标 | 评价要点\n课堂互动 | 学生有真实表达和回应",
                "transcription": [{"content": "同学们读课文", "start": 0, "end": 1, "speaker": "教师"}],
            }
        )

        self.assertEqual(selection.source, "用户自定义评价量规")
        self.assertIsNone(selection.rubric_file)
        self.assertIn("课堂互动", selection.rubric_text)

    def test_select_rubric_matches_subject_alias(self):
        selection = run_reflection.select_rubric(
            {
                "subject": "小学语文",
                "transcription": [{"content": "同学们读课文", "start": 0, "end": 1, "speaker": "教师"}],
            }
        )

        self.assertEqual(selection.rubric_file, "01_语文.md")
        self.assertEqual(selection.matched_subject, "语文")

    def test_next_conversation_id_allocates_new_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "generated-outputs"
            existing = root / "sample-lesson" / "case-sample-lesson-001"
            existing.mkdir(parents=True)

            self.assertEqual(
                run_reflection.next_conversation_id(root, "sample-lesson", None),
                "case-sample-lesson-002",
            )
            self.assertEqual(
                run_reflection.next_conversation_id(root, "sample-lesson", None, reuse_existing=True),
                "case-sample-lesson-002",
            )

    def test_next_conversation_id_reuses_only_explicit_requested_id(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "generated-outputs"
            existing = root / "sample-lesson" / "named-run"
            existing.mkdir(parents=True)

            self.assertEqual(
                run_reflection.next_conversation_id(root, "sample-lesson", "named-run", reuse_existing=True),
                "named-run",
            )

            with self.assertRaises(ValueError):
                run_reflection.next_conversation_id(root, "sample-lesson", "missing-run", reuse_existing=True)

    def test_prepare_creates_output_dir_state_and_prompt_payload(self):
        import tempfile

        request = {
            "subject": "数学",
            "grade": "五年级",
            "topic": "异分母分数加减法",
            "transcription": [
                {"id": 1, "content": "计算 1/2 加 1/3，大家觉得第一步应该做什么？", "start": 0, "end": 8, "speaker": "教师"},
                {"id": 2, "content": "要先通分。", "start": 9, "end": 11, "speaker": "学生"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "request.json"
            input_file.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(input_file),
                    "--conversation-id",
                    "case-test",
                    "--lesson-slug",
                    "unit-test-lesson",
                    "--output-root",
                    str(Path(tmp) / "generated-outputs"),
                ],
                cwd=SKILL_ROOT.parents[1],
                text=True,
                capture_output=True,
                check=True,
            )
            state = json.loads(proc.stdout)
            output_dir = Path(state["outputDir"])
            prompt_payload = Path(state["promptPayloadPath"]).read_text(encoding="utf-8")

            self.assertEqual(output_dir.name, "case-test")
            self.assertEqual(output_dir.parent.name, "unit-test-lesson")
            self.assertTrue((output_dir / "run-state.json").exists())
            self.assertTrue((output_dir / ".internal" / "normalized-input.json").exists())
            self.assertTrue((output_dir / ".internal" / "prompt-payload.md").exists())
            self.assertIn("完整逐字稿", prompt_payload)
            self.assertIn("计算 1/2 加 1/3", prompt_payload)
            self.assertEqual(state["matchedRubric"], "02_数学.md")
            self.assertEqual(Path(state["normalizedInputPath"]).parent.name, ".internal")
            self.assertEqual(Path(state["promptPayloadPath"]).parent.name, ".internal")
            self.assertIn("generated-outputs/unit-test-lesson/case-test/reflection-report.md", state["reportPath"])

    def test_prepare_transcribes_media_input_and_archives_artifacts(self):
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            media_file = Path(tmp) / "lesson.mp4"
            media_file.write_bytes(b"fake media")
            output_root = Path(tmp) / "generated-outputs"

            def fake_transcribe_media_input(media_path: Path, work_dir: Path):
                request_path = work_dir / run_reflection.MEDIA_REQUEST_NAME
                raw_artifact_path = work_dir / run_reflection.MEDIA_RAW_ARTIFACT_NAME
                raw_dir = work_dir / run_reflection.MEDIA_RAW_DIR_NAME
                raw_dir.mkdir(parents=True)
                request_path.write_text(
                    json.dumps(
                        {
                            "mediaFile": str(media_path),
                            "transcriptionProvider": "tongyi-tingwu",
                            "transcription": [
                                {"id": 1, "content": "同学们，请看这段视频。", "start": 0, "end": 4, "speaker": "教师"},
                                {"id": 2, "content": "我们看到了。", "start": 5, "end": 7, "speaker": "学生"},
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                raw_artifact_path.write_text("[{\"event\":\"raw\"}]\n", encoding="utf-8")
                (raw_dir / "tingwu-realtime-events.json").write_text("[]\n", encoding="utf-8")
                return run_reflection.MediaTranscriptionArtifacts(
                    source=str(media_path),
                    source_type="local-file",
                    request_path=request_path,
                    raw_artifact_path=raw_artifact_path,
                    raw_dir=raw_dir,
                )

            original_transcribe = run_reflection.transcribe_media_input
            try:
                run_reflection.transcribe_media_input = fake_transcribe_media_input
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    run_reflection.prepare(
                        SimpleNamespace(
                            input=media_file,
                            media_url=None,
                            conversation_id=None,
                            lesson_slug=None,
                            inferred_subject=None,
                            output_root=output_root,
                            reuse_existing=False,
                            transcript_preview_chars=0,
                        )
                    )
            finally:
                run_reflection.transcribe_media_input = original_transcribe

            state = json.loads(stdout.getvalue())
            internal_dir = Path(state["internalDir"])
            normalized = json.loads(Path(state["normalizedInputPath"]).read_text(encoding="utf-8"))

            self.assertEqual(state["inputFile"], str(media_file))
            self.assertEqual(state["lessonSlug"], "lesson")
            self.assertIn("mediaTranscription", state)
            self.assertTrue((internal_dir / run_reflection.MEDIA_REQUEST_NAME).exists())
            self.assertTrue((internal_dir / run_reflection.MEDIA_RAW_ARTIFACT_NAME).exists())
            self.assertTrue((internal_dir / run_reflection.MEDIA_RAW_DIR_NAME / "tingwu-realtime-events.json").exists())
            self.assertEqual(normalized["request"]["mediaFile"], str(media_file))
            self.assertEqual(len(normalized["request"]["transcription"]), 2)

    def test_prepare_transcribes_media_url_and_archives_artifacts(self):
        import contextlib
        import io
        import tempfile

        media_url = "https://example.com/lesson.mp4"
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "generated-outputs"

            def fake_transcribe_media_url(url: str, work_dir: Path):
                request_path = work_dir / run_reflection.MEDIA_REQUEST_NAME
                raw_artifact_path = work_dir / run_reflection.MEDIA_RAW_ARTIFACT_NAME
                raw_dir = work_dir / run_reflection.MEDIA_RAW_DIR_NAME
                raw_dir.mkdir(parents=True)
                request_path.write_text(
                    json.dumps(
                        {
                            "mediaUrl": url,
                            "transcriptionProvider": "tongyi-tingwu",
                            "transcription": [
                                {"id": 1, "content": "同学们，今天开始上课。", "start": 0, "end": 4, "speaker": "教师"},
                                {"id": 2, "content": "老师好。", "start": 5, "end": 6, "speaker": "学生"},
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                raw_artifact_path.write_text("{\"Sentences\": []}\n", encoding="utf-8")
                (raw_dir / "tingwu-transcription-raw.json").write_text("{}\n", encoding="utf-8")
                return run_reflection.MediaTranscriptionArtifacts(
                    source=url,
                    source_type="media-url",
                    request_path=request_path,
                    raw_artifact_path=raw_artifact_path,
                    raw_dir=raw_dir,
                )

            original_transcribe_url = run_reflection.transcribe_media_url
            try:
                run_reflection.transcribe_media_url = fake_transcribe_media_url
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    run_reflection.prepare(
                        SimpleNamespace(
                            input=None,
                            media_url=media_url,
                            conversation_id=None,
                            lesson_slug="url-lesson",
                            inferred_subject=None,
                            output_root=output_root,
                            reuse_existing=False,
                            transcript_preview_chars=0,
                        )
                    )
            finally:
                run_reflection.transcribe_media_url = original_transcribe_url

            state = json.loads(stdout.getvalue())
            normalized = json.loads(Path(state["normalizedInputPath"]).read_text(encoding="utf-8"))

            self.assertEqual(state["inputFile"], media_url)
            self.assertEqual(state["mediaTranscription"]["sourceType"], "media-url")
            self.assertEqual(state["mediaTranscription"]["source"], media_url)
            self.assertEqual(normalized["request"]["mediaUrl"], media_url)
            self.assertEqual(len(normalized["request"]["transcription"]), 2)

    def test_normalize_request_reports_empty_media_transcription(self):
        with self.assertRaisesRegex(ValueError, "Media transcription output has no non-empty transcription"):
            run_reflection.normalize_request(
                {
                    "mediaUrl": "https://example.com/lesson.mp4",
                    "transcriptionProvider": "tongyi-tingwu",
                    "transcription": [],
                }
            )

    def test_prepare_can_build_compact_prompt_payload_when_explicitly_requested(self):
        import tempfile

        long_text = "同学们观察这个数学问题，先说说你们发现了什么。" * 20
        request = {
            "subject": "数学",
            "topic": "长逐字稿示例",
            "transcription": [
                {"id": 1, "content": long_text, "start": 0, "end": 20, "speaker": "教师"},
                {"id": 2, "content": "我们发现要先比较。", "start": 21, "end": 25, "speaker": "学生"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "request.json"
            input_file.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(input_file),
                    "--output-root",
                    str(Path(tmp) / "generated-outputs"),
                    "--transcript-preview-chars",
                    "120",
                ],
                cwd=SKILL_ROOT.parents[1],
                text=True,
                capture_output=True,
                check=True,
            )
            state = json.loads(proc.stdout)
            prompt_payload = Path(state["promptPayloadPath"]).read_text(encoding="utf-8")

        self.assertIn("逐字稿节选", prompt_payload)
        self.assertIn("已截断", prompt_payload)
        self.assertIn("必须读取", prompt_payload)
        self.assertIn(state["normalizedInputPath"], prompt_payload)

    def test_prepare_allocates_next_id_when_default_exists(self):
        import tempfile

        request = {
            "subject": "语文",
            "topic": "示例课",
            "transcription": [
                {"id": 1, "content": "同学们，今天我们学习课文。", "start": 0, "end": 3, "speaker": "教师"},
                {"id": 2, "content": "学生读课文。", "start": 4, "end": 6, "speaker": "学生"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "generated-outputs"
            (output_root / "示例课" / "case-示例课-001").mkdir(parents=True)
            input_file = Path(tmp) / "request.json"
            input_file.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prepare",
                    str(input_file),
                    "--output-root",
                    str(output_root),
                    "--reuse-existing",
                ],
                cwd=SKILL_ROOT.parents[1],
                text=True,
                capture_output=True,
                check=True,
            )
            state = json.loads(proc.stdout)

        self.assertEqual(state["lessonSlug"], "示例课")
        self.assertEqual(state["conversationId"], "case-示例课-002")

    def test_validate_report_rejects_missing_required_sections(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "rubricSource": "用户自定义评价量规",
            }
            markdown = "# 课堂教学反思与公开课点评报告\n\n生成时间：2026-06-02 10:00:00\n\n总分：80 / 100\n"

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("Missing required section" in failure for failure in result["failures"]))

    def test_validate_report_accepts_subject_and_rubric_line(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "用户自定义评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。
学科与量规：推断学科为语文；量规来源为用户自定义评价量规。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
| 一级指标 | 二级观察点 | 表现判断 | 判断依据 |
|---|---|---|---|
| 教学过程 | 课堂互动 | 基本有效 | 有明确课堂任务，但学生表达还可以更充分。 |
整体表现：良好

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "ok")

    def test_validate_report_rejects_quantitative_scores(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "内置评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。
学科与量规：推断学科为语文；量规来源为 `01_语文.md`。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
| 一级指标 | 二级观察点 | 分值 | 得分 | 评分理由 |
|---|---|---:|---:|---|
| 教学过程 | 课堂互动 | 20 | 16 | 有互动。 |
总分：80 / 100

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("quantitative total score" in failure for failure in result["failures"]))
        self.assertTrue(any("quantitative score columns" in failure for failure in result["failures"]))

    def test_validate_report_rejects_generic_basis_note(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "内置评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。
依据说明：基于课堂逐字稿和本次适用的评价量规，仅评价材料中有证据支持的内容。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
整体表现：良好

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("学科与量规" in failure for failure in result["failures"]))

    def test_validate_report_rejects_standalone_evaluation_basis_section(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "内置评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。

## 二、评价依据
评价量规：通用评价量规。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
整体表现：良好

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("standalone ## 二、评价依据" in failure for failure in result["failures"]))

    def test_validate_report_rejects_followup_suggestions_section(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "内置评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。
学科与量规：推断学科为语文；量规来源为 `01_语文.md`。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
整体表现：良好

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……

## 八、后续优化建议
可继续优化教案。
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("standalone ## 八、后续优化建议" in failure for failure in result["failures"]))

    def test_validate_report_rejects_audio_unsupported_evaluation_items(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = {
                "outputDir": str(Path(tmp) / "generated-outputs" / "lesson" / "case"),
                "reportPath": str(Path(tmp) / "generated-outputs" / "lesson" / "case" / "reflection-report.md"),
                "generatedRoot": str(Path(tmp) / "generated-outputs"),
                "rubricSource": "内置评价量规",
            }
            markdown = """# 课堂教学反思与公开课点评报告

生成时间：2026-06-02 10:00:00

## 一、基本判断
本节课整体属于：良好。
学科与量规：推断学科为语文；量规来源为 `01_语文.md`。

## 二、课堂流程复盘
| 环节 | 时间 | 教师行为 | 学生行为 | 主要问题 / 亮点 |

## 三、定性评价结果
| 一级指标 | 二级观察点 | 表现判断 | 判断依据 |
|---|---|---|---|
| 教师素养 | 板书/课件 | 证据不足 | 逐字稿无法判断。 |
整体表现：良好

## 四、主要优点
1. 有明确课堂任务。

## 五、关键问题
### 问题 1：学生表达不足
- 证据：
- 影响：
- 修改方向：

## 六、具体修改建议
| 问题位置 | 原课堂表现 | 修改建议 | 预期效果 |

## 七、可直接替换的课堂语言
导入语：……
提问语：……
评价语：……
"""

            result = run_reflection.validate_report(state, markdown)

        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("audio-unsupported" in failure for failure in result["failures"]))

    def test_builtin_rubrics_avoid_audio_unsupported_items(self):
        forbidden_terms = [
            "板书",
            "教态",
            "课堂纪律",
            "学生表情",
            "眼神",
            "站位",
            "巡视",
            "动作质量",
            "体能表现",
            "队形",
            "场地",
            "器材组织",
            "作品质量",
            "视觉美感",
            "实验操作质量",
            "课件",
        ]
        rubric_files = sorted((SKILL_ROOT / "assets" / "rubric").glob("*.md"))
        self.assertTrue(rubric_files)

        for rubric_file in rubric_files:
            text = rubric_file.read_text(encoding="utf-8")
            for term in forbidden_terms:
                self.assertIsNone(
                    re.search(re.escape(term), text),
                    f"{rubric_file.name} should not contain audio-unsupported term: {term}",
                )


if __name__ == "__main__":
    unittest.main()
