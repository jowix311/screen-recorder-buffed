"""Connects the Recording control state machine to the portal, the recorder and a timer.

Slow steps run on background threads: the desktop picker, and stopping the pipeline,
which waits for the MKV file to be finalised. Tests pass a synchronous runner instead.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from screen_recorder_buffed.capture import Recorder, RunningRecording, default_audio_monitor
from screen_recorder_buffed.portal import PortalError, ScreenStream
from screen_recorder_buffed.recording_state import (
    MSG_CAPTURE_ERROR,
    MSG_NO_SOURCE,
    MSG_STOP_FAILED,
    RecordingControl,
    StartInputs,
    State,
    format_elapsed,
    is_stalled,
    start_blockers,
)

TICK_MS = 1000

Runner = Callable[[Callable[[], Any], Callable[[Any], None], Callable[[str], None]], None]


class _Worker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, work: Callable[[], Any]) -> None:
        super().__init__()
        self._work = work

    def run(self) -> None:
        try:
            result = self._work()
        except PortalError as error:
            self.failed.emit(str(error))
        except Exception as error:  # noqa: BLE001 - surfaced as a message, never a crash
            self.failed.emit(f"Unexpected error: {error}")
        else:
            self.succeeded.emit(result)


def threaded_runner(work, on_ok, on_error) -> None:
    """Run `work` on a worker thread, then call on_ok or on_error on the UI thread."""
    worker = _Worker(work)
    worker.succeeded.connect(on_ok)
    worker.failed.connect(on_error)
    worker.finished.connect(worker.deleteLater)
    worker.start()
    # Keep a reference until the thread ends.
    _keep_alive.append(worker)
    worker.finished.connect(lambda: _keep_alive.remove(worker) if worker in _keep_alive else None)


_keep_alive: list[QThread] = []


class RecordingController(QObject):
    state_changed = Signal(str)
    messages_changed = Signal(list)
    elapsed_changed = Signal(str)
    recording_finished = Signal(str)  # MKV path, once the file is finalised

    def __init__(
        self,
        pick_screen: Callable[[], ScreenStream],
        output_dir: Callable[[], Path],
        audio_monitor: Callable[[], str | None] = default_audio_monitor,
        recorder: Recorder | None = None,
        runner: Runner = threaded_runner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.control = RecordingControl()
        self._pick_screen = pick_screen
        self._output_dir = output_dir
        self._audio_monitor = audio_monitor
        self._recorder = recorder or Recorder()
        self._runner = runner
        self._recording: RunningRecording | None = None
        self._picking = False
        self._last_size = -1
        self._last_growth = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    # --- Queries used by the UI -------------------------------------------

    @property
    def state(self) -> State:
        return self.control.state

    @property
    def picking(self) -> bool:
        return self._picking

    def button_enabled(self, inputs: StartInputs) -> bool:
        if self._picking:
            return False
        return self.control.button_enabled(inputs)

    # --- Commands ---------------------------------------------------------

    def start(self, inputs: StartInputs) -> None:
        """Start button or Ctrl+Shift+R while idle."""
        if self.control.state is not State.IDLE or self._picking:
            return
        blockers = start_blockers(inputs)
        if blockers:
            self._set_messages(blockers)
            return
        self._set_messages([])
        self._picking = True
        self._emit_state()
        self._runner(self._pick_screen, lambda stream: self._on_picked(stream, inputs), self._on_pick_failed)

    def toggle(self, inputs: StartInputs) -> None:
        """Ctrl+Shift+R: start when idle, stop when recording."""
        if self.control.state is State.RECORDING:
            self.stop()
        else:
            self.start(inputs)

    def stop(self) -> None:
        if not self.control.request_stop():
            return
        self._timer.stop()
        self._emit_state()
        self._finish_in_background()

    def on_close_requested(self) -> bool:
        """Returns True when the window may close now."""
        return self.control.state is State.IDLE

    # --- Start: picker, then recorder ------------------------------------

    def _on_pick_failed(self, message: str) -> None:
        self._picking = False
        if message == "cancelled":
            # The user closed the picker: stay idle with no message.
            self._set_messages([])
        else:
            self._set_messages([MSG_NO_SOURCE])
        self._emit_state()

    def _on_picked(self, stream: ScreenStream, inputs: StartInputs) -> None:
        self._picking = False
        audio = self._audio_monitor()
        if audio is None:
            self._close_fd(stream)
            self._set_messages([MSG_NO_SOURCE])
            self._emit_state()
            return
        self.control.request_start(inputs, source_available=True)
        try:
            self._recording = self._recorder.start(stream, audio, self._output_dir())
        except OSError:
            # Popen or the output folder failed: release the stream and go back to idle.
            self.control.state = State.IDLE
            self._close_fd(stream)
            self._set_messages([MSG_NO_SOURCE])
            self._emit_state()
            return
        self._last_size = -1
        self._last_growth = self._now()
        self._timer.start()
        self._emit_state()

    # --- While recording --------------------------------------------------

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _tick(self) -> None:
        recording = self._recording
        if recording is None or self.control.state is not State.RECORDING:
            return
        self.elapsed_changed.emit(format_elapsed(recording.elapsed()))

        if recording.process.poll() is not None:
            self._capture_failed()
            return

        size = recording.file_size()
        now = self._now()
        if size != self._last_size:
            self._last_size = size
            self._last_growth = now
        elif is_stalled(self._last_growth, now):
            self._capture_failed()

    def _capture_failed(self) -> None:
        if not self.control.on_capture_error():
            return
        self._timer.stop()
        self._set_messages([MSG_CAPTURE_ERROR])
        self._emit_state()
        self._finish_in_background()

    # --- Stop: finalise the file, then processing (placeholder until Slice 4) ---

    def _finish_in_background(self) -> None:
        recording = self._recording
        if recording is None:
            self.control.state = State.IDLE
            self._emit_state()
            return
        self._runner(
            lambda: self._recorder.stop(recording),
            lambda _code: self._on_file_finalised(recording),
            self._on_stop_failed,
        )

    def _on_stop_failed(self, message: str) -> None:
        self._set_messages([MSG_STOP_FAILED])
        if recording := self._recording:
            self._on_file_finalised(recording)

    def _on_file_finalised(self, recording: RunningRecording) -> None:
        self._recording = None
        recording.stream.close()  # the portal session ends with its connection
        self.control.on_file_finalised()
        self._emit_state()
        # Processing is a placeholder until Slices 3–5 add transcription and descriptions.
        self.control.on_processing_done()
        self.recording_finished.emit(str(recording.output_path))
        self._emit_state()

    # --- Helpers ----------------------------------------------------------

    @staticmethod
    def _close_fd(stream: ScreenStream) -> None:
        try:
            os.close(stream.fd)
        except OSError:
            pass
        stream.close()

    def _set_messages(self, messages: list[str]) -> None:
        self.control.messages = list(messages)
        self.messages_changed.emit(list(messages))

    def _emit_state(self) -> None:
        self.state_changed.emit(self.control.state.value)
