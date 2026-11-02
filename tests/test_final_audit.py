"""Regression tests for the final (Slice 8) audit findings.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.describe import NoFrameError  # noqa: E402
from screen_recorder_buffed.library_screen import LibraryScreen  # noqa: E402
from screen_recorder_buffed.process_recording import ProcessingError, ProcessingResult, process_recording  # noqa: E402
from screen_recorder_buffed.recording_controller import RecordingController  # noqa: E402
from screen_recorder_buffed.recording_library import scan_library  # noqa: E402
from screen_recorder_buffed.recording_state import State  # noqa: E402
from screen_recorder_buffed.settings_screen import SettingsScreen  # noqa: E402
from screen_recorder_buffed.settings_store import Settings, SettingsStore  # noqa: E402
from screen_recorder_buffed.theme import build_stylesheet  # noqa: E402
from test_recording_controller import READY, FakeRecorder, FakeStream, sync_runner  # noqa: E402
from test_settings import FakeKeyStore  # noqa: E402


def write_sidecar_file(video: Path, language: str = "ja") -> None:
    video.write_bytes(b"video")
    video.with_suffix(".json").write_text(json.dumps({
        "title": "Meeting", "started_at": "2026-11-02T09:00:00+08:00", "duration_seconds": 61,
        "spoken_language": language, "segments": [], "descriptions": [], "status": "ready",
    }), encoding="utf-8")


class FinalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # High 1
    def test_rows_with_and_without_sidecar_sort_together(self) -> None:
        write_sidecar_file(self.root / "2026-11-02_09-00-00.mkv")
        (self.root / "2026-11-02_10-00-00.mkv").write_bytes(b"video")  # no sidecar
        (self.root / "odd-name.mkv").write_bytes(b"video")  # unparseable name
        rows = scan_library(self.root)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].video.name, "2026-11-02_10-00-00.mkv")

    # High 2
    def test_library_shows_language_name_and_code(self) -> None:
        write_sidecar_file(self.root / "2026-11-02_09-00-00.mkv", language="es")
        screen = LibraryScreen(lambda: self.root, lambda: {})
        screen.refresh()
        self.assertEqual(screen.table.item(0, 3).text(), "Spanish (es)")

    # High 3
    def test_primary_buttons_have_their_own_focus_ring(self) -> None:
        self.assertIn("QPushButton#primary:focus", build_stylesheet())

    # High 4
    def _controller(self, process=None) -> RecordingController:
        return RecordingController(
            pick_screen=lambda: FakeStream(), output_dir=lambda: self.root,
            process=process or (lambda v, l, d: ProcessingResult()),
            audio_monitor=lambda: "m", recorder=FakeRecorder(self.root), runner=sync_runner)

    def test_retry_is_refused_while_the_picker_is_open(self) -> None:
        video = self.root / "2026-11-02_09-00-00.mkv"
        write_sidecar_file(video)
        calls: list = []
        controller = self._controller(process=lambda v, l, d: calls.append(v) or ProcessingResult())
        controller._picking = True
        controller.retry(video)
        self.assertEqual(calls, [])
        self.assertFalse(controller.retry_running)

    def test_picker_result_is_dropped_when_a_retry_is_running(self) -> None:
        controller = self._controller()
        controller._retry_running = True
        stream = FakeStream()
        controller._on_picked(stream, READY)
        self.assertEqual(controller.state, State.IDLE)
        self.assertTrue(stream.closed)

    # Medium 5
    def test_stopping_shows_as_processing_in_the_library(self) -> None:
        controller = self._controller()
        controller.start(READY, "ja")
        controller.control.state = State.STOPPING
        self.assertEqual(list(controller.active_videos().values()), ["processing"])
        controller._timer.stop()

    # Medium 7
    def test_settings_does_not_overwrite_the_last_language(self) -> None:
        store = SettingsStore(self.root / "settings.json")
        screen = SettingsScreen(store, FakeKeyStore())
        settings = store.load()
        settings.last_language = "ko"  # saved meanwhile by Recording control
        store.save(settings)
        screen.privacy.setChecked(True)
        self.assertEqual(store.load().last_language, "ko")
        self.assertTrue(store.load().privacy_accepted)

    # Live risk: audio past the last video frame
    def test_missing_last_frame_does_not_fail_the_recording(self) -> None:
        def extract(video, seconds):
            if seconds >= 20:
                raise NoFrameError("no video frame")
            return b"jpeg"

        result = process_recording(
            Path("a.mkv"), "en", "sk-ant-x", privacy_accepted=True,
            transcribe=lambda p, lang: [], describe=lambda jpeg, key: "A slide.",
            extract=extract, times=[0, 10, 20])
        self.assertEqual([n.time_seconds for n in result.descriptions], [0, 10])

    def test_missing_middle_frame_still_fails(self) -> None:
        def extract(video, seconds):
            if seconds == 10:
                raise NoFrameError("no video frame")
            return b"jpeg"

        with self.assertRaises(ProcessingError):
            process_recording(
                Path("a.mkv"), "en", "sk-ant-x", privacy_accepted=True,
                transcribe=lambda p, lang: [], describe=lambda jpeg, key: "A slide.",
                extract=extract, times=[0, 10, 20])


if __name__ == "__main__":
    unittest.main()
