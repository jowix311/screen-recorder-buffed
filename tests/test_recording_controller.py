"""Controller checks with fakes: no portal, no GStreamer, no threads.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.capture import RunningRecording  # noqa: E402
from screen_recorder_buffed.portal import PortalError, ScreenStream  # noqa: E402
from screen_recorder_buffed.recording_controller import RecordingController  # noqa: E402
from screen_recorder_buffed.recording_state import (  # noqa: E402
    MSG_CAPTURE_ERROR,
    MSG_KEY,
    MSG_NO_SOURCE,
    MSG_PRIVACY,
    StartInputs,
    State,
)

READY = StartInputs(privacy_accepted=True, has_key=True, language_selected=True, retry_running=False)


def sync_runner(work, on_ok, on_error):
    """Runs the work immediately, on the calling thread."""
    try:
        result = work()
    except PortalError as error:
        on_error(str(error))
    else:
        on_ok(result)


class FakeStream(ScreenStream):
    def __init__(self) -> None:
        super().__init__(node_id=42, fd=-1)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeProcess:
    def __init__(self) -> None:
        self.returncode = None
        self.signalled = False

    def poll(self):
        return self.returncode

    def send_signal(self, _sig) -> None:
        self.signalled = True
        self.returncode = 0

    def wait(self, timeout=None) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.returncode = -9


class FakeRecorder:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.started = 0
        self.stopped = 0
        self.process = FakeProcess()
        self.size = 0

    def start(self, stream, audio_monitor, output_dir):
        self.started += 1
        path = self.output_dir / "2026-11-02_10-00-00.mkv"
        path.write_bytes(b"")
        return RunningRecording(
            process=self.process,
            output_path=path,
            started_at=datetime(2026, 11, 2, 10, 0, 0),
            started_monotonic=0.0,
            stream=stream,
        )

    def stop(self, recording):
        self.stopped += 1
        return self.process.wait()


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.stream = FakeStream()
        self.picks = 0
        self.pick_error: str | None = None
        self.recorder = FakeRecorder(self.root)
        self.audio: str | None = "sink.monitor"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _pick(self) -> ScreenStream:
        self.picks += 1
        if self.pick_error:
            raise PortalError(self.pick_error)
        return self.stream

    def _controller(self) -> RecordingController:
        return RecordingController(
            pick_screen=self._pick,
            output_dir=lambda: self.root,
            audio_monitor=lambda: self.audio,
            recorder=self.recorder,
            runner=sync_runner,
        )

    def test_blocked_start_shows_messages_and_does_not_pick(self) -> None:
        controller = self._controller()
        controller.start(replace(READY, privacy_accepted=False, has_key=False))
        self.assertEqual(self.picks, 0)
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [MSG_PRIVACY, MSG_KEY])

    def test_successful_start_records_and_shows_recording_state(self) -> None:
        controller = self._controller()
        controller.start(READY)
        self.assertEqual(self.picks, 1)
        self.assertEqual(self.recorder.started, 1)
        self.assertEqual(controller.state, State.RECORDING)
        controller._timer.stop()

    def test_picker_cancelled_stays_idle_without_message(self) -> None:
        self.pick_error = "cancelled"
        controller = self._controller()
        controller.start(READY)
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [])
        self.assertEqual(self.recorder.started, 0)

    def test_picker_failure_shows_no_source_message(self) -> None:
        self.pick_error = "The desktop refused the request"
        controller = self._controller()
        controller.start(READY)
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [MSG_NO_SOURCE])

    def test_missing_audio_monitor_refuses_start(self) -> None:
        self.audio = None
        controller = self._controller()
        controller.start(READY)
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [MSG_NO_SOURCE])
        self.assertTrue(self.stream.closed)

    def test_stop_finalises_and_returns_to_idle(self) -> None:
        controller = self._controller()
        finished: list[str] = []
        controller.recording_finished.connect(finished.append)
        controller.start(READY)
        controller.stop()
        self.assertEqual(self.recorder.stopped, 1)
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0].endswith(".mkv"))
        self.assertTrue(self.stream.closed)

    def test_toggle_stops_while_recording(self) -> None:
        controller = self._controller()
        controller.start(READY)
        controller.toggle(READY)
        self.assertEqual(self.recorder.stopped, 1)
        self.assertEqual(controller.state, State.IDLE)

    def test_process_exit_during_recording_is_a_capture_error(self) -> None:
        controller = self._controller()
        controller.start(READY)
        self.recorder.process.returncode = 1
        controller._tick()
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [MSG_CAPTURE_ERROR])

    def test_no_new_data_for_five_seconds_is_a_capture_error(self) -> None:
        controller = self._controller()
        controller.start(READY)
        clock = {"now": 100.0}
        controller._now = staticmethod(lambda: clock["now"])
        controller._last_growth = 100.0
        controller._last_size = 0
        clock["now"] = 104.0
        controller._tick()
        self.assertEqual(controller.state, State.RECORDING)
        clock["now"] = 105.0
        controller._tick()
        self.assertEqual(controller.state, State.IDLE)
        self.assertEqual(controller.control.messages, [MSG_CAPTURE_ERROR])

    def test_growing_file_is_not_a_stall(self) -> None:
        controller = self._controller()
        controller.start(READY)
        clock = {"now": 100.0}
        controller._now = staticmethod(lambda: clock["now"])
        controller._last_growth = 100.0
        controller._last_size = 0
        for step in range(1, 10):
            clock["now"] = 100.0 + step
            self.recorder_file().write_bytes(b"x" * step)
            controller._tick()
        self.assertEqual(controller.state, State.RECORDING)
        controller._timer.stop()

    def recorder_file(self) -> Path:
        return self.root / "2026-11-02_10-00-00.mkv"

    def test_button_disabled_while_picking(self) -> None:
        controller = self._controller()
        controller._picking = True
        self.assertFalse(controller.button_enabled(READY))


if __name__ == "__main__":
    unittest.main()
