"""Main window: left sidebar with four screens, minimum size 1024x640.

Behaviour from site-contract.md, section 1. Recording control and Settings are built;
library and review are placeholders until their slices.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from screen_recorder_buffed.key_store import KeyringKeyStore, KeyStore, SecureStoreUnavailable
from screen_recorder_buffed.library_screen import LibraryScreen
from screen_recorder_buffed.process_recording import ProcessingError, frame_times, media_duration, process_recording
from screen_recorder_buffed.portal import PortalClient, ScreenStream
from screen_recorder_buffed.recording_controller import RecordingController
from screen_recorder_buffed.recording_screen import RecordingScreen
from screen_recorder_buffed.recording_state import State
from screen_recorder_buffed.review_screen import ReviewScreen
from screen_recorder_buffed.settings_screen import SettingsScreen
from screen_recorder_buffed.settings_store import SettingsStore
from screen_recorder_buffed.shortcut import ShortcutListener
from screen_recorder_buffed.transcribe import SubprocessTranscriber
from screen_recorder_buffed.theme import px

SIDEBAR_WIDTH = 200
MIN_WIDTH = 1024
MIN_HEIGHT = 640

# Order and labels from site-contract.md, section 1.
SCREEN_NAMES = [
    "Recording control",
    "Recording library",
    "Recording review",
    "Settings",
]
RECORDING_INDEX = 0
LIBRARY_INDEX = 1
REVIEW_INDEX = 2
SETTINGS_INDEX = 3

CLOSE_DIALOG_TEXT = "Stop the recording and process it?"
DIALOG_WIDTH = 400  # design-standard.md, Shape and elevation
BLINK_MS = 1000  # one full cycle, linear (design-standard.md, Motion)


def _in_scroll_area(page: QWidget) -> QScrollArea:
    """Content taller than the window scrolls (site-contract.md §1)."""
    scroll = QScrollArea()
    scroll.setWidget(page)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    return scroll


def _placeholder_screen(name: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    padding = px("space-3")
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    title = QLabel(name)
    title.setObjectName("page-title")
    body = QLabel("Not built yet.")
    body.setObjectName("page-body")

    layout.addWidget(title)
    layout.addWidget(body)
    return _in_scroll_area(page)


def _pick_primary_monitor() -> ScreenStream:
    """Ask the desktop for a monitor. The client stays open on the stream until the recording ends."""
    client = PortalClient()
    try:
        return client.screen_stream()
    except BaseException:
        client.close()  # a refused or cancelled picker must not leave the connection open
        raise


class MainWindow(QWidget):
    def __init__(
        self,
        store: SettingsStore | None = None,
        keys: KeyStore | None = None,
        controller: RecordingController | None = None,
        global_shortcut: bool = True,
        review_video: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Screen Recorder Buffed")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self._store = store or SettingsStore()
        self._keys = keys or KeyringKeyStore()
        self._controller = controller or RecordingController(
            pick_screen=_pick_primary_monitor,
            output_dir=self._output_dir,
            process=self._process_recording,
        )

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.stack = QStackedWidget()
        self.recording_screen: RecordingScreen | None = None
        self.library_screen: LibraryScreen | None = None
        self.review_screen: ReviewScreen | None = None

        for index, name in enumerate(SCREEN_NAMES):
            self.sidebar.addItem(QListWidgetItem(name))
            if index == RECORDING_INDEX:
                self.recording_screen = RecordingScreen(self._store, self._keys, self._controller)
                self.stack.addWidget(_in_scroll_area(self.recording_screen))
            elif index == LIBRARY_INDEX:
                self.library_screen = LibraryScreen(self._output_dir, self._controller.active_videos)
                self.library_screen.review_requested.connect(self.open_review)
                self.stack.addWidget(_in_scroll_area(self.library_screen))
            elif index == REVIEW_INDEX:
                self.review_screen = ReviewScreen(
                    retry=self.retry_recording,
                    is_processing=lambda video: video in self._controller.active_videos(),
                    can_retry=lambda: self._controller.state is State.IDLE and not self._controller.retry_running,
                    with_video=review_video,
                )
                self.review_screen.title_changed.connect(lambda _path: self._refresh_library())
                self.stack.addWidget(_in_scroll_area(self.review_screen))
            elif index == SETTINGS_INDEX:
                screen = SettingsScreen(self._store, self._keys)
                self.stack.addWidget(_in_scroll_area(screen))
            else:
                self.stack.addWidget(_placeholder_screen(name))

        # Recording review is hidden until a library row is opened (site-contract.md §1).
        self.sidebar.setRowHidden(REVIEW_INDEX, True)

        self.sidebar.currentRowChanged.connect(self._on_screen_changed)
        self.sidebar.setCurrentRow(0)

        self.badge = self._build_badge()
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.badge)
        content_layout.addWidget(self.stack, stretch=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(content, stretch=1)

        self._controller.state_changed.connect(self._on_state)
        self._controller.recording_finished.connect(lambda _path, _status: self._refresh_library())
        if self.review_screen is not None:
            self._controller.recording_finished.connect(self.review_screen.on_recording_finished)
            self._controller.state_changed.connect(lambda _state: self.review_screen.refresh_status())
        self._on_state(self._controller.state.value)

        self._shortcut_listener: ShortcutListener | None = None
        self._focus_shortcut: QShortcut | None = None
        if global_shortcut:
            self._start_global_shortcut()
        else:
            self._enable_focus_shortcut()

    # --- Output folder -----------------------------------------------------

    def _output_dir(self) -> Path:
        return Path(os.path.expanduser(self._store.load().output_folder))

    def _processing_blocker(self) -> str | None:
        """Why processing cannot run now, or None. Checked before any Retry writes anything."""
        if not self._store.load().privacy_accepted:
            return "Accept privacy in Settings before processing"
        try:
            has_key = bool(self._keys.get_key())
        except SecureStoreUnavailable:
            has_key = False
        return None if has_key else "No Claude API key saved"

    def retry_recording(self, video: Path) -> str | None:
        """Retry processing for a recording. Returns a message when Retry cannot run, else None."""
        blocker = self._processing_blocker()
        if blocker:
            return blocker
        try:
            self._controller.retry(video)
        except ValueError:
            return "The recording's details could not be read"
        return None

    def _process_recording(self, video: Path, language: str, duration: int):
        """Transcribe, translate and describe a finished recording. Runs on a worker thread.

        Frame times come from the MKV's own length, so a fraction of a second is not lost.
        """
        settings = self._store.load()
        try:
            key = self._keys.get_key()
        except SecureStoreUnavailable as error:
            raise ProcessingError(str(error)) from error
        if not key:
            raise ProcessingError("No Claude API key saved")
        return process_recording(
            video,
            language,
            key,
            privacy_accepted=settings.privacy_accepted,
            transcribe=SubprocessTranscriber().transcribe,
            times=frame_times(media_duration(video)),
        )

    # --- Recording badge (site-contract.md §2) -----------------------------

    def _build_badge(self) -> QLabel:
        badge = QLabel("Recording")
        badge.setObjectName("recording-badge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.hide()
        self._badge_effect = QGraphicsOpacityEffect(badge)
        badge.setGraphicsEffect(self._badge_effect)
        self._blink = QPropertyAnimation(self._badge_effect, b"opacity", self)
        self._blink.setDuration(BLINK_MS)
        self._blink.setStartValue(1.0)
        self._blink.setKeyValueAt(0.5, 0.4)
        self._blink.setEndValue(1.0)
        self._blink.setLoopCount(-1)
        return badge

    def _on_state(self, value: str) -> None:
        visible = State(value) in (State.RECORDING, State.STOPPING)
        self.badge.setVisible(visible)
        if visible:
            self._blink.start()
        else:
            self._blink.stop()
            self._badge_effect.setOpacity(1.0)

    # --- Shortcut ----------------------------------------------------------

    def _start_global_shortcut(self) -> None:
        listener = ShortcutListener()
        listener.activated.connect(self._on_shortcut)
        listener.unavailable.connect(self._on_shortcut_unavailable)
        listener.start()
        self._shortcut_listener = listener

    def _on_shortcut_unavailable(self, _reason: str) -> None:
        self._enable_focus_shortcut()

    def _enable_focus_shortcut(self) -> None:
        """Fallback: Ctrl+Shift+R works only while this window has focus."""
        if self._focus_shortcut is None:
            self._focus_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
            self._focus_shortcut.activated.connect(self._on_shortcut)
        if self.recording_screen is not None:
            self.recording_screen.show_shortcut_notice(True)

    def _on_shortcut(self) -> None:
        if self.recording_screen is not None:
            self.recording_screen.toggle_from_shortcut()

    # --- Close (site-contract.md §3) ---------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt name
        state = self._controller.state
        if state is State.IDLE:
            self._shutdown()
            event.accept()
            return
        if state is State.RECORDING:
            answer = QMessageBox(self)
            answer.setWindowTitle("Recording")
            answer.setText(CLOSE_DIALOG_TEXT)
            answer.setMinimumWidth(DIALOG_WIDTH)
            stop = answer.addButton("Stop", QMessageBox.ButtonRole.AcceptRole)
            answer.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            answer.exec()
            if answer.clickedButton() is stop:
                self._controller.stop()
        # Stopping or processing: the window stays open until processing ends.
        event.ignore()

    def _shutdown(self) -> None:
        if self.review_screen is not None:
            self.review_screen.stop_playback()
        if self._shortcut_listener is not None:
            self._shortcut_listener.request_stop()
            self._shortcut_listener.wait(3000)

    def _on_screen_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == RECORDING_INDEX and self.recording_screen is not None:
            # Settings may have changed while another screen was open.
            self.recording_screen.refresh()
        if index == LIBRARY_INDEX:
            self._refresh_library()

    def _refresh_library(self) -> None:
        if self.library_screen is not None:
            self.library_screen.refresh()

    def open_review(self, video: str) -> None:
        """Open a recording in Recording review, and list Review in the sidebar (site-contract.md §1)."""
        if self.review_screen is not None:
            self.review_screen.open(Path(video))
        self.show_recording_review()
        self.sidebar.setCurrentRow(REVIEW_INDEX)

    def show_recording_review(self) -> None:
        """Make the Recording review item visible. Called when a library row is opened (Slice 6)."""
        self.sidebar.setRowHidden(REVIEW_INDEX, False)
