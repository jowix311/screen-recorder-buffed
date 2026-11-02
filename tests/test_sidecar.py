"""Slice 5 rules: sidecar fields and types, failed status, Retry. No network.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.process_recording import ProcessingError, ProcessingResult, ScreenNote, TranscriptLine  # noqa: E402
from screen_recorder_buffed.sidecar import FAILED, READY, SidecarMeta, build_sidecar, default_title, read_sidecar, write_sidecar  # noqa: E402

META = SidecarMeta(
    title="2026-11-02 10:00",
    started_at=datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc),
    duration_seconds=61,
    spoken_language="ja",
)
RESULT = ProcessingResult(
    lines=[TranscriptLine(1.23456, 4.5, "こんにちは", "Hello")],
    descriptions=[ScreenNote(0, "A slide.")],
)


class SidecarTests(unittest.TestCase):
    def test_ready_sidecar_has_the_content_model_fields(self) -> None:
        data = build_sidecar(META, READY, RESULT)
        self.assertEqual(set(data), {"title", "started_at", "duration_seconds", "spoken_language",
                                     "segments", "descriptions", "status"})
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["duration_seconds"], 61)
        self.assertEqual(data["segments"], [{"start_seconds": 1.235, "original_text": "こんにちは",
                                             "english_text": "Hello"}])
        self.assertEqual(data["descriptions"], [{"time_seconds": 0, "description": "A slide."}])

    def test_failed_sidecar_has_empty_lists(self) -> None:
        data = build_sidecar(META, FAILED, None)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["segments"], [])
        self.assertEqual(data["descriptions"], [])

    def test_default_title_format(self) -> None:
        self.assertEqual(default_title(META.started_at), "2026-11-02 10:00")

    def test_write_then_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "2026-11-02_10-00-00.mkv"
            video.write_bytes(b"")
            write_sidecar(video, META, READY, RESULT)
            self.assertEqual(read_sidecar(video)["status"], "ready")
            self.assertTrue((Path(tmp) / "2026-11-02_10-00-00.json").exists())
            self.assertFalse(any(p.suffix == ".tmp" for p in Path(tmp).iterdir()))


class ValidatorTests(unittest.TestCase):
    def test_built_sidecars_are_valid(self) -> None:
        from screen_recorder_buffed.sidecar import validate_sidecar

        self.assertEqual(validate_sidecar(build_sidecar(META, READY, RESULT)), [])
        self.assertEqual(validate_sidecar(build_sidecar(META, FAILED, None)), [])

    def test_problems_are_reported(self) -> None:
        from screen_recorder_buffed.sidecar import validate_sidecar

        data = build_sidecar(META, READY, RESULT)
        data["started_at"] = "2026-11-02T10:00:00"
        data["duration_seconds"] = 61.5
        problems = validate_sidecar(data)
        self.assertIn("started_at has no timezone", problems)
        self.assertIn("duration_seconds is not an integer", problems)

    def test_missing_keys_are_reported(self) -> None:
        from screen_recorder_buffed.sidecar import validate_sidecar

        self.assertIn("missing status", validate_sidecar({"title": "x"}))


class RetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_retry_rewrites_status_and_blocks_start_while_running(self) -> None:
        from screen_recorder_buffed.recording_controller import RecordingController
        from screen_recorder_buffed.recording_state import StartInputs
        from test_recording_controller import FakeRecorder, FakeStream, sync_runner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "2026-11-02_10-00-00.mkv"
            video.write_bytes(b"")
            write_sidecar(video, META, FAILED, None)
            seen: dict = {}

            def process(path, language, duration):
                seen.update(language=language, duration=duration, running=controller.retry_running)
                return RESULT

            controller = RecordingController(
                pick_screen=lambda: FakeStream(), output_dir=lambda: root, process=process,
                audio_monitor=lambda: "m", recorder=FakeRecorder(root), runner=sync_runner)
            finished: list = []
            controller.recording_finished.connect(lambda p, s: finished.append(s))
            controller.retry(video)
            self.assertEqual(seen, {"language": "ja", "duration": 61, "running": True})
            self.assertFalse(controller.retry_running)
            self.assertEqual(finished, ["ready"])
            self.assertEqual(read_sidecar(video)["status"], "ready")
            self.assertEqual(len(read_sidecar(video)["segments"]), 1)

    def test_failed_processing_marks_the_recording_failed_and_keeps_video(self) -> None:
        from screen_recorder_buffed.recording_controller import RecordingController
        from test_recording_controller import FakeRecorder, FakeStream, sync_runner

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "2026-11-02_10-00-00.mkv"
            video.write_bytes(b"video")
            write_sidecar(video, META, READY, RESULT)

            def failing(path, language, duration):
                raise ProcessingError("Claude API returned HTTP 500")

            controller = RecordingController(
                pick_screen=lambda: FakeStream(), output_dir=lambda: root, process=failing,
                audio_monitor=lambda: "m", recorder=FakeRecorder(root), runner=sync_runner)
            controller.retry(video)
            self.assertEqual(read_sidecar(video)["status"], "failed")
            self.assertEqual(read_sidecar(video)["segments"], [])
            self.assertEqual(video.read_bytes(), b"video")


if __name__ == "__main__":
    unittest.main()
