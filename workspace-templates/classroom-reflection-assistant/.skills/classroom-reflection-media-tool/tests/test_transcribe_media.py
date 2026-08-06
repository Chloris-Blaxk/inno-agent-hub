from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


TOOL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = TOOL_ROOT / "transcribe_media.py"

spec = importlib.util.spec_from_file_location("transcribe_media", SCRIPT)
transcribe_media = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["transcribe_media"] = transcribe_media
spec.loader.exec_module(transcribe_media)


class TranscribeMediaTest(unittest.TestCase):
    def test_convert_tingwu_sentences_to_reflection_request(self):
        raw = {
            "Data": {
                "Result": {
                    "Transcription": {
                        "Sentences": [
                            {
                                "SpeakerId": "spk-1",
                                "BeginTime": 0,
                                "EndTime": 4200,
                                "Text": "同学们，今天我们先观察这道题，你发现了什么？",
                            },
                            {
                                "SpeakerId": "spk-2",
                                "BeginTime": 4300,
                                "EndTime": 6500,
                                "Text": "我发现分母不一样。",
                            },
                        ]
                    }
                }
            }
        }

        request = transcribe_media.convert_tingwu_to_request(
            raw,
            teacher_speaker=None,
            student_speaker=None,
            time_unit="ms",
        )

        self.assertEqual(request["transcriptionProvider"], "tongyi-tingwu")
        self.assertEqual(request["transcription"][0]["speaker"], "教师")
        self.assertEqual(request["transcription"][1]["speaker"], "学生")
        self.assertEqual(request["transcription"][0]["start"], 0.0)
        self.assertEqual(request["transcription"][0]["end"], 4.2)
        self.assertIn("分母不一样", request["transcription"][1]["content"])

    def test_explicit_speaker_mapping_overrides_heuristic(self):
        raw = {
            "Transcription": {
                "sentences": [
                    {"speakerId": "A", "beginTime": 0, "endTime": 1000, "text": "老师好。"},
                    {"speakerId": "B", "beginTime": 1000, "endTime": 3000, "text": "请大家打开课本。"},
                ]
            }
        }

        request = transcribe_media.convert_tingwu_to_request(
            raw,
            teacher_speaker="B",
            student_speaker="A",
            time_unit="ms",
        )

        self.assertEqual(request["transcription"][0]["speaker"], "学生")
        self.assertEqual(request["transcription"][1]["speaker"], "教师")

    def test_convert_paragraph_words_to_reflection_request(self):
        raw = {
            "Transcription": {
                "Paragraphs": [
                    {
                        "SpeakerId": "teacher",
                        "Words": [
                            {"BeginTime": 0, "EndTime": 500, "Text": "同学们"},
                            {"BeginTime": 500, "EndTime": 900, "Text": "好"},
                        ],
                    },
                    {
                        "SpeakerId": "student",
                        "Words": [
                            {"BeginTime": 1000, "EndTime": 1300, "Text": "老师"},
                            {"BeginTime": 1300, "EndTime": 1600, "Text": "好"},
                        ],
                    },
                ]
            }
        }

        request = transcribe_media.convert_tingwu_to_request(
            raw,
            teacher_speaker="teacher",
            student_speaker="student",
            time_unit="ms",
        )

        self.assertEqual(len(request["transcription"]), 2)
        self.assertEqual(request["transcription"][0]["content"], "同学们好")
        self.assertEqual(request["transcription"][0]["start"], 0.0)
        self.assertEqual(request["transcription"][0]["end"], 0.9)
        self.assertEqual(request["transcription"][1]["speaker"], "学生")

    def test_convert_raises_when_sentence_items_have_no_readable_text(self):
        raw = {"Transcription": {"Sentences": [{"Foo": "bar"}]}}

        with self.assertRaisesRegex(ValueError, "none had readable text"):
            transcribe_media.convert_tingwu_to_request(
                raw,
                teacher_speaker=None,
                student_speaker=None,
                time_unit="ms",
            )

    def test_convert_cli_writes_request_json(self):
        raw = {
            "Sentences": [
                {"SpeakerId": "1", "BeginTime": 0, "EndTime": 1500, "Text": "请你读第一段。"},
                {"SpeakerId": "2", "BeginTime": 1600, "EndTime": 2500, "Text": "我来读。"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "tingwu.json"
            output_path = Path(tmp) / "request.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "convert",
                    "--tingwu-result",
                    str(raw_path),
                    "--output",
                    str(output_path),
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn(str(output_path), proc.stdout)
            request = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(request["transcription"]), 2)
        self.assertNotIn("topic", request)
        self.assertNotIn("subject", request)
        self.assertNotIn("grade", request)

    def test_default_raw_output_path_uses_output_stem(self):
        output = Path("/tmp/pan-request.json")

        raw_output = transcribe_media.default_raw_output_path(output)

        self.assertEqual(raw_output, Path("/tmp/pan-request.tingwu-raw.json"))

    def test_transcribe_command_writes_direct_raw_artifact(self):
        raw_transcription = {
            "Sentences": [
                {"SpeakerId": "1", "BeginTime": 0, "EndTime": 1500, "Text": "请你读第一段。"},
                {"SpeakerId": "2", "BeginTime": 1600, "EndTime": 2500, "Text": "我来读。"},
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "request.json"
            raw_output_path = Path(tmp) / "direct-tingwu.json"
            args = SimpleNamespace(
                media_url="https://example.com/lesson.mp4",
                endpoint="tingwu.example.com",
                language="cn",
                task_key="task-1",
                speaker_count=2,
                raw_dir=None,
                wait=True,
                poll_interval=1,
                timeout=10,
                raw_output=raw_output_path,
                output=output_path,
                teacher_speaker=None,
                student_speaker=None,
                time_unit="ms",
                default_speaker="教师",
            )

            original_resolve = transcribe_media.resolve_credentials
            original_submit = transcribe_media.submit_tingwu_task
            original_poll = transcribe_media.poll_until_complete
            try:
                transcribe_media.resolve_credentials = lambda: transcribe_media.Credentials("ak", "secret", "app")
                transcribe_media.submit_tingwu_task = lambda **_kwargs: {"TaskId": "task-id"}
                transcribe_media.poll_until_complete = lambda **_kwargs: {
                    "body": {"Data": {"Result": {"Transcription": raw_transcription}}}
                }

                transcribe_media.command_transcribe(args)
            finally:
                transcribe_media.resolve_credentials = original_resolve
                transcribe_media.submit_tingwu_task = original_submit
                transcribe_media.poll_until_complete = original_poll

            saved_raw = json.loads(raw_output_path.read_text(encoding="utf-8"))
            request = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved_raw, raw_transcription)
        self.assertEqual(len(request["transcription"]), 2)

    def test_transcription_result_accepts_tea_lowercase_body_envelope(self):
        raw_transcription = {"Sentences": [{"Text": "可以读取。"}]}

        result = transcribe_media.transcription_result_from_task_info(
            {"body": {"Data": {"Result": {"Transcription": raw_transcription}}}}
        )

        self.assertEqual(result, raw_transcription)

    def test_transcription_result_rejects_lowercase_internal_fields(self):
        raw_transcription = {"Sentences": [{"Text": "这不应该被宽松读取。"}]}

        with self.assertRaisesRegex(ValueError, "Body/body.Data.Result.Transcription"):
            transcribe_media.transcription_result_from_task_info(
                {"data": {"result": {"transcription": raw_transcription}}}
            )

    def test_parse_env_file_supports_tingwu_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "TINGWU_ACCESS_KEY_ID=ak-id",
                        "TINGWU_ACCESS_KEY_SECRET='ak-secret'",
                        'TINGWU_APP_KEY="app-key"',
                    ]
                ),
                encoding="utf-8",
            )

            values = transcribe_media.load_env_values([env_path])
            credentials = transcribe_media.credentials_from_mapping(values)

        self.assertIsNotNone(credentials)
        assert credentials is not None
        self.assertEqual(credentials.access_key_id, "ak-id")
        self.assertEqual(credentials.access_key_secret, "ak-secret")
        self.assertEqual(credentials.app_key, "app-key")

    def test_load_env_values_keeps_shell_environment_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "TINGWU_ACCESS_KEY_ID=file-id",
                        "TINGWU_ACCESS_KEY_SECRET=file-secret",
                        "TINGWU_APP_KEY=file-app",
                    ]
                ),
                encoding="utf-8",
            )

            original = transcribe_media.os.environ.get("TINGWU_ACCESS_KEY_ID")
            try:
                transcribe_media.os.environ["TINGWU_ACCESS_KEY_ID"] = "shell-id"
                values = transcribe_media.load_env_values([env_path])
            finally:
                if original is None:
                    transcribe_media.os.environ.pop("TINGWU_ACCESS_KEY_ID", None)
                else:
                    transcribe_media.os.environ["TINGWU_ACCESS_KEY_ID"] = original

        self.assertEqual(values["TINGWU_ACCESS_KEY_ID"], "shell-id")
        self.assertEqual(values["TINGWU_ACCESS_KEY_SECRET"], "file-secret")
        self.assertEqual(values["TINGWU_APP_KEY"], "file-app")

    def test_realtime_events_to_transcription(self):
        events = [
            {"header": {"name": "TranscriptionStarted"}, "payload": {}},
            {"header": {"name": "SentenceBegin"}, "payload": {"index": 1, "time": 0}},
            {
                "header": {"name": "SentenceEnd"},
                "payload": {
                    "index": 1,
                    "begin_time": 0,
                    "time": 2800,
                    "result": "同学们，请观察这句话。",
                    "speaker_id": "teacher-1",
                },
            },
            {"header": {"name": "TranscriptionCompleted"}, "payload": {}},
        ]

        transcription = transcribe_media.realtime_events_to_transcription(events)

        self.assertEqual(len(transcription["Sentences"]), 1)
        sentence = transcription["Sentences"][0]
        self.assertEqual(sentence["Text"], "同学们，请观察这句话。")
        self.assertEqual(sentence["BeginTime"], 0)
        self.assertEqual(sentence["EndTime"], 2800)
        self.assertEqual(sentence["SpeakerId"], "teacher-1")

    def test_missing_speaker_id_uses_default_speaker(self):
        raw = {
            "Sentences": [
                {"BeginTime": 0, "EndTime": 1500, "Text": "今天我们学习第一段。"},
            ]
        }

        request = transcribe_media.convert_tingwu_to_request(
            raw,
            teacher_speaker=None,
            student_speaker=None,
            time_unit="ms",
            default_speaker="教师",
        )

        self.assertEqual(request["transcription"][0]["speaker"], "教师")


if __name__ == "__main__":
    unittest.main()
