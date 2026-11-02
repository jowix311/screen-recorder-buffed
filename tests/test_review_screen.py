"""Slice 7 rules: Recording review views, Retry, title editing, seeking. No player, no network.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.process_recording import ProcessingResult, ScreenNote, TranscriptLine  # noqa: E402
from screen_recorder_buffed.review_screen import (  # noqa: E402
    FAILED_TEXT,
    NO_SPEECH_TEXT,
    PROCESSING_TEXT,
    TITLE_NOT_SAVED,
    ReviewScreen,
    video_error_text,
)
from screen_recorder_buffed.sidecar import (  # noqa: E402
    FAILED,
    MSG_TITLE_LENGTH,
    READY,
    SidecarMeta,
    read_sidecar,
    write_sidecar,
)

META = SidecarMeta("2026-11-02 10:00", datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc), 61, "ja")
RESULT = ProcessingResult(
    lines=[TranscriptLine(12.5, 15.0, "こんにちは", "Hello")],
    descriptions=[ScreenNote(0, "A slide."), ScreenNote(10, "A chart.")],
)


def shown(widget) -> bool:
    return not widget.isHidden()


class ReviewScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.video = self.root / "2026-11-02_10-00-00.mkv"
        self.video.write_bytes(b"video")
        self.processing: set[Path] = set()
        self.retry_reply: str | None = None
        self.retried: list[Path] = []

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _retry(self, video: Path) -> str | None:
        self.retried.append(video)
        if self.retry_reply is None:
            self.processing.add(video)
        return self.retry_reply

    def _screen(self) -> ReviewScreen:
        return ReviewScreen(retry=self._retry, is_processing=lambda v: v in self.processing, with_video=False)

    def test_ready_recording_shows_transcript_and_descriptions(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        self.assertEqual(screen.title.text(), "2026-11-02 10:00")
        self.assertEqual(screen.transcript.count(), 1)
        self.assertIn("00:00:12", screen.transcript.item(0).text())
        self.assertIn("Hello", screen.transcript.item(0).text())
        self.assertEqual(screen.descriptions.count(), 2)
        self.assertFalse(shown(screen.failure_message))
        self.assertFalse(shown(screen.retry_button))
        self.assertFalse(shown(screen.no_speech))

    def test_ready_recording_without_speech_says_so(self) -> None:
        write_sidecar(self.video, META, READY, ProcessingResult(lines=[], descriptions=[]))
        screen = self._screen()
        screen.open(self.video)
        self.assertTrue(shown(screen.no_speech))
        self.assertEqual(screen.no_speech.text(), NO_SPEECH_TEXT)

    def test_failed_recording_shows_only_message_and_retry(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        screen = self._screen()
        screen.open(self.video)
        self.assertTrue(shown(screen.failure_message))
        self.assertEqual(screen.failure_message.text(), FAILED_TEXT)
        self.assertTrue(shown(screen.retry_button))
        self.assertTrue(screen.retry_button.isEnabled())
        self.assertFalse(shown(screen.transcript))
        self.assertFalse(shown(screen.descriptions))

    def test_retry_shows_processing_and_disables_the_button(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        screen = self._screen()
        screen.open(self.video)
        screen.retry_button.click()
        self.assertEqual(self.retried, [self.video])
        self.assertEqual(screen.failure_message.text(), PROCESSING_TEXT)
        self.assertFalse(screen.retry_button.isEnabled())

    def test_refused_retry_shows_the_reason_and_changes_nothing(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        self.retry_reply = "Accept privacy in Settings before processing"
        screen = self._screen()
        screen.open(self.video)
        screen.retry_button.click()
        self.assertEqual(screen.retry_error.text(), "Accept privacy in Settings before processing")
        self.assertEqual(screen.failure_message.text(), FAILED_TEXT)
        self.assertTrue(screen.retry_button.isEnabled())

    def test_finished_retry_reloads_the_recording(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        screen = self._screen()
        screen.open(self.video)
        screen.retry_button.click()
        write_sidecar(self.video, META, READY, RESULT)
        self.processing.clear()
        screen.on_recording_finished(str(self.video), READY)
        self.assertFalse(shown(screen.failure_message))
        self.assertEqual(screen.transcript.count(), 1)

    def test_valid_title_is_saved_to_the_sidecar(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        saved: list[str] = []
        screen.title_changed.connect(saved.append)
        screen.title.setText("Quarterly review")
        screen.title.editingFinished.emit()
        self.assertEqual(read_sidecar(self.video)["title"], "Quarterly review")
        self.assertEqual(saved, [str(self.video)])
        self.assertTrue(self.video.exists())  # the video is never renamed

    def test_empty_or_long_title_is_rejected(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        for bad in ("", "x" * 81):
            screen.title.setText(bad)
            screen.title.editingFinished.emit()
            self.assertEqual(screen.title.text(), "2026-11-02 10:00")
            self.assertEqual(screen.title_error.text(), MSG_TITLE_LENGTH)
        self.assertEqual(read_sidecar(self.video)["title"], "2026-11-02 10:00")

    def test_eighty_code_points_is_accepted(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        title = "会" * 80
        screen.title.setText(title)
        screen.title.editingFinished.emit()
        self.assertEqual(read_sidecar(self.video)["title"], title)

    def test_title_reverts_when_the_sidecar_cannot_be_written(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        with mock.patch("screen_recorder_buffed.review_screen.update_title", side_effect=OSError("disk full")):
            screen.title.setText("New name")
            screen.title.editingFinished.emit()
        self.assertEqual(screen.title.text(), "2026-11-02 10:00")
        self.assertEqual(screen.title_error.text(), TITLE_NOT_SAVED)

    def test_recording_without_sidecar_is_failed_and_title_is_locked(self) -> None:
        screen = self._screen()
        screen.open(self.video)
        self.assertEqual(screen.failure_message.text(), FAILED_TEXT)
        self.assertFalse(screen.title.isEnabled())
        self.assertEqual(screen.title.text(), "2026-11-02_10-00-00")

    def test_missing_video_shows_its_path(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        self.video.unlink()
        screen = self._screen()
        screen.open(self.video)
        self.assertTrue(shown(screen.video_message))
        self.assertEqual(screen.video_message.text(), video_error_text(self.video))

    def test_clicking_an_entry_seeks_to_its_time(self) -> None:
        write_sidecar(self.video, META, READY, RESULT)
        screen = self._screen()
        screen.open(self.video)
        seeks: list[float] = []
        screen.seek_requested.connect(seeks.append)
        screen.transcript.itemClicked.emit(screen.transcript.item(0))
        screen.descriptions.itemClicked.emit(screen.descriptions.item(1))
        self.assertEqual(seeks, [12.5, 10.0])


    def test_retry_is_disabled_while_the_app_is_busy(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        screen = ReviewScreen(retry=self._retry, is_processing=lambda v: False,
                              can_retry=lambda: False, with_video=False)
        screen.open(self.video)
        self.assertTrue(shown(screen.retry_button))
        self.assertFalse(screen.retry_button.isEnabled())

    def test_title_is_locked_while_a_retry_runs(self) -> None:
        write_sidecar(self.video, META, FAILED, None)
        screen = self._screen()
        screen.open(self.video)
        self.assertTrue(screen.title.isEnabled())
        screen.retry_button.click()
        self.assertFalse(screen.title.isEnabled())

    def test_missing_video_hides_the_player_and_unloads_the_previous_one(self) -> None:
        other = self.root / "2026-11-02_09-00-00.mkv"
        other.write_bytes(b"video")
        write_sidecar(other, META, READY, RESULT)
        write_sidecar(self.video, META, READY, RESULT)
        self.video.unlink()
        screen = ReviewScreen(retry=self._retry, is_processing=lambda v: False)
        screen.open(other)
        self.assertFalse(screen._player.source().isEmpty())
        screen.open(self.video)
        self.assertTrue(screen._player.source().isEmpty())
        self.assertTrue(screen.controls.isHidden())
        self.assertTrue(screen.video_widget.isHidden())
        self.assertTrue(shown(screen.video_message))


class AtomicWriteTests(unittest.TestCase):
    def test_failed_write_leaves_no_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "2026-11-02_10-00-00.mkv"
            video.write_bytes(b"video")
            with mock.patch("screen_recorder_buffed.sidecar.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    write_sidecar(video, META, READY, RESULT)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["2026-11-02_10-00-00.mkv"])


if __name__ == "__main__":
    unittest.main()
