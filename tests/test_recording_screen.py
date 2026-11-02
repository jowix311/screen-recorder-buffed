"""Recording control screen rules: messages without a click, Ctrl+Shift+R ignored when blocked,
language saved when chosen. Uses fakes; no portal, GStreamer or real keyring.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.process_recording import ProcessingResult  # noqa: E402
from screen_recorder_buffed.recording_controller import RecordingController  # noqa: E402
from screen_recorder_buffed.recording_screen import RecordingScreen  # noqa: E402
from screen_recorder_buffed.recording_state import MSG_KEY, MSG_PRIVACY  # noqa: E402
from screen_recorder_buffed.settings_store import Settings, SettingsStore  # noqa: E402
from test_recording_controller import FakeRecorder, FakeStream, sync_runner  # noqa: E402
from test_settings import FakeKeyStore  # noqa: E402


class RecordingScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = SettingsStore(self.root / "settings.json")
        self.keys = FakeKeyStore()
        self.recorder = FakeRecorder(self.root)
        self.picks = 0
        self.controller = RecordingController(
            pick_screen=self._pick,
            output_dir=lambda: self.root,
            process=lambda video, language, duration: ProcessingResult(),
            audio_monitor=lambda: "sink.monitor",
            recorder=self.recorder,
            runner=sync_runner,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _pick(self):
        self.picks += 1
        return FakeStream()

    def _screen(self) -> RecordingScreen:
        screen = RecordingScreen(self.store, self.keys, self.controller)
        screen.show()
        return screen

    def _pick_language(self, screen: RecordingScreen, code: str) -> None:
        screen.language.setCurrentIndex(screen.language.findData(code))

    def test_blocked_messages_show_without_a_click(self) -> None:
        screen = self._screen()
        self.assertFalse(screen.button.isEnabled())
        self.assertIn(MSG_PRIVACY, screen.messages.text())
        self.assertIn(MSG_KEY, screen.messages.text())

    def test_start_enables_when_settings_change_and_screen_is_shown_again(self) -> None:
        screen = self._screen()
        self._pick_language(screen, "es")
        self.assertFalse(screen.button.isEnabled())  # privacy and key still missing
        self.store.save(Settings(privacy_accepted=True))
        self.keys.key = "sk-ant-api03-0123456789wxyz"
        screen.refresh()  # what the window does when the user comes back to this screen
        self.assertTrue(screen.button.isEnabled())
        self.assertEqual(screen.messages.text(), "")

    def test_ctrl_shift_r_is_ignored_while_blocked(self) -> None:
        screen = self._screen()
        self._pick_language(screen, "fr")
        screen.toggle_from_shortcut()
        self.assertEqual(self.picks, 0)
        self.assertEqual(self.controller.state.value, "idle")

    def test_ctrl_shift_r_starts_when_all_conditions_hold(self) -> None:
        self.store.save(Settings(privacy_accepted=True))
        self.keys.key = "sk-ant-api03-0123456789wxyz"
        screen = self._screen()
        self._pick_language(screen, "de")
        screen.toggle_from_shortcut()
        self.assertEqual(self.picks, 1)
        self.assertEqual(self.controller.state.value, "recording")
        self.controller._timer.stop()

    def test_chosen_language_is_saved_immediately(self) -> None:
        screen = self._screen()
        self._pick_language(screen, "ko")
        self.assertEqual(self.store.load().last_language, "ko")

    def test_placeholder_does_not_overwrite_last_language(self) -> None:
        self.store.save(Settings(last_language="ja"))
        screen = self._screen()
        self.assertEqual(self.store.load().last_language, "ja")
        self.assertEqual(screen.language.currentData(), "ja")
        screen.language.setCurrentIndex(0)
        self.assertEqual(self.store.load().last_language, "ja")


if __name__ == "__main__":
    unittest.main()
