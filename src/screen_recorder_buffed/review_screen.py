"""Recording review screen. Rules: content-model.md (Recording review) and site-contract.md §5.

Opens one recording with status 'ready' or 'failed'. Clicking a transcript or
description entry seeks the video to its time. A failed recording shows only the
failure message and Retry; while a retry runs, "Processing…" replaces the message.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from screen_recorder_buffed.recording_state import format_elapsed
from screen_recorder_buffed.sidecar import READY, read_sidecar, update_title, validate_title
from screen_recorder_buffed.theme import px

FAILED_TEXT = "Processing failed. The video is kept."
PROCESSING_TEXT = "Processing…"
NO_SPEECH_TEXT = "No speech detected"
TITLE_NOT_SAVED = "Title could not be saved"
WIDE_WINDOW = 1280  # site-contract.md §1: side by side from this window width
TIME_ROLE = Qt.ItemDataRole.UserRole
LIST_MIN_HEIGHT = 160  # keeps the lists usable; the page scrolls instead of squeezing them


def video_error_text(video: Path) -> str:
    return f"Video cannot be played: {video}"


class ReviewScreen(QWidget):
    seek_requested = Signal(float)  # seconds into the video
    title_changed = Signal(str)  # the MKV path whose title was saved

    def __init__(
        self,
        retry: Callable[[Path], str | None],
        is_processing: Callable[[Path], bool],
        can_retry: Callable[[], bool] = lambda: True,
        with_video: bool = True,
    ) -> None:
        super().__init__()
        self._retry = retry
        self._is_processing = is_processing
        self._can_retry = can_retry
        self._has_sidecar = False
        self.controls: QWidget | None = None
        self._video: Path | None = None
        self._saved_title = ""
        self._status = READY
        self._player = None

        outer = QVBoxLayout(self)
        padding = px("space-3")
        outer.setContentsMargins(padding, padding, padding, padding)
        outer.setSpacing(px("space-2"))
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Recording review")
        heading.setObjectName("page-title")
        outer.addWidget(heading)

        # Title (content-model.md: edited here only; saved on Enter or when focus leaves).
        self.title = QLineEdit()
        self.title.setAccessibleName("Title")
        self.title.editingFinished.connect(self._on_title_edited)
        outer.addWidget(self.title)
        self.title_error = self._error_label()
        outer.addWidget(self.title_error)

        # Body: video on one side, transcript and descriptions on the other.
        self.body = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.body.setSpacing(px("space-3"))
        outer.addLayout(self.body, stretch=1)

        self.video_box = QWidget()
        video_layout = QVBoxLayout(self.video_box)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_message = QLabel()
        self.video_message.setObjectName("error-message")
        self.video_message.setWordWrap(True)
        self.video_message.hide()
        video_layout.addWidget(self.video_message)
        self.video_widget = self._build_player(video_layout) if with_video else None

        self.side_box = QWidget()
        side = QVBoxLayout(self.side_box)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(px("space-2"))

        self.failure_message = QLabel(FAILED_TEXT)
        self.failure_message.setObjectName("page-body")
        side.addWidget(self.failure_message)
        self.retry_button = QPushButton("Retry")
        self.retry_button.setObjectName("primary")
        self.retry_button.clicked.connect(self._on_retry)
        side.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.retry_error = self._error_label()
        side.addWidget(self.retry_error)

        self.transcript_title = self._section("Transcript")
        side.addWidget(self.transcript_title)
        self.no_speech = QLabel(NO_SPEECH_TEXT)
        self.no_speech.setObjectName("page-body")
        side.addWidget(self.no_speech)
        self.transcript = QListWidget()
        self.transcript.setWordWrap(True)
        self.transcript.setMinimumHeight(LIST_MIN_HEIGHT)
        self.transcript.itemClicked.connect(self._on_item_clicked)
        self.transcript.itemActivated.connect(self._on_item_clicked)
        side.addWidget(self.transcript, stretch=1)

        self.descriptions_title = self._section("Screen descriptions")
        side.addWidget(self.descriptions_title)
        self.descriptions = QListWidget()
        self.descriptions.setWordWrap(True)
        self.descriptions.setMinimumHeight(LIST_MIN_HEIGHT)
        self.descriptions.itemClicked.connect(self._on_item_clicked)
        self.descriptions.itemActivated.connect(self._on_item_clicked)
        side.addWidget(self.descriptions, stretch=1)

        self.body.addWidget(self.video_box, stretch=3)
        self.body.addWidget(self.side_box, stretch=2)
        self._apply_layout()

    # --- Building ----------------------------------------------------------

    @staticmethod
    def _error_label() -> QLabel:
        label = QLabel()
        label.setObjectName("error-message")
        label.setWordWrap(True)
        label.hide()
        return label

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section-title")
        return label

    def _build_player(self, layout: QVBoxLayout) -> QWidget:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget

        widget = QVideoWidget()
        widget.setMinimumHeight(240)
        layout.addWidget(widget, stretch=1)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(widget)
        self._player.errorOccurred.connect(self._on_player_error)

        self.controls = QWidget()
        controls = QHBoxLayout(self.controls)
        controls.setContentsMargins(0, 0, 0, 0)
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_button)
        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.setAccessibleName("Seek")
        self.position.sliderMoved.connect(lambda ms: self._player.setPosition(ms))
        # Clicking the track and the arrow keys move the handle; seek there as well.
        self.position.actionTriggered.connect(
            lambda _action: self._player.setPosition(self.position.sliderPosition()))
        controls.addWidget(self.position, stretch=1)
        layout.addWidget(self.controls)

        self._player.durationChanged.connect(lambda ms: self.position.setRange(0, ms))
        self._player.positionChanged.connect(self._on_position)
        self._player.playbackStateChanged.connect(self._on_playback_state)
        return widget

    # --- Opening a recording -----------------------------------------------

    def open(self, video: Path) -> None:
        """Show one recording. Rows without a readable sidecar are shown as failed."""
        self._video = video
        self.title_error.hide()
        self.retry_error.hide()
        try:
            data = read_sidecar(video)
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        self._has_sidecar = bool(data)
        self._status = data.get("status") if data.get("status") in (READY, "failed") else "failed"
        self._saved_title = str(data.get("title") or video.stem)
        self.title.setText(self._saved_title)

        self._fill(data.get("segments") or [], data.get("descriptions") or [])
        self._load_video(video)
        self.refresh_status()

    def _fill(self, segments: list, descriptions: list) -> None:
        self.transcript.clear()
        for line in segments:
            start = float(line.get("start_seconds", 0))
            text = f"{format_elapsed(start)}  {line.get('original_text', '')}\n{line.get('english_text', '')}"
            item = QListWidgetItem(text)
            item.setData(TIME_ROLE, start)
            self.transcript.addItem(item)
        self.descriptions.clear()
        for note in descriptions:
            seconds = float(note.get("time_seconds", 0))
            item = QListWidgetItem(f"{format_elapsed(seconds)}  {note.get('description', '')}")
            item.setData(TIME_ROLE, seconds)
            self.descriptions.addItem(item)

    def _load_video(self, video: Path) -> None:
        self.video_message.hide()
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())  # never keep the previous recording loaded
        if not video.exists():
            self._show_video_error()
            return
        if self._player is not None:
            self.video_widget.show()
            self.controls.show()
            self._player.setSource(QUrl.fromLocalFile(str(video)))

    def _show_video_error(self) -> None:
        """The message replaces the whole player, controls included (site-contract.md §5)."""
        if self._video is None:
            return
        self.video_message.setText(video_error_text(self._video))
        self.video_message.show()
        if self.video_widget is not None:
            self.video_widget.hide()
        if self.controls is not None:
            self.controls.hide()
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())

    # --- Status views (site-contract.md §5) --------------------------------

    def refresh_status(self) -> None:
        """Show the ready, failed or processing view for the open recording."""
        if self._video is None:
            return
        processing = self._is_processing(self._video)
        ready = self._status == READY and not processing

        self.failure_message.setVisible(not ready)
        self.failure_message.setText(PROCESSING_TEXT if processing else FAILED_TEXT)
        self.retry_button.setVisible(not ready)
        self.retry_button.setEnabled(not processing and self._can_retry())
        # A title edit during a retry would be overwritten when it finishes, so lock it.
        self.title.setEnabled(self._has_sidecar and not processing)

        for widget in (self.transcript_title, self.transcript, self.descriptions_title, self.descriptions):
            widget.setVisible(ready)
        self.no_speech.setVisible(ready and self.transcript.count() == 0)

    def on_recording_finished(self, path: str, _status: str) -> None:
        """A retry (or a new recording) finished; reload if it is the one on screen."""
        if self._video is not None and Path(path) == self._video:
            self.open(self._video)

    # --- Actions -----------------------------------------------------------

    def _on_retry(self) -> None:
        if self._video is None:
            return
        message = self._retry(self._video)
        if message:
            self.retry_error.setText(message)
            self.retry_error.show()
            return
        self.retry_error.hide()
        self.refresh_status()

    def _on_title_edited(self) -> None:
        if self._video is None:
            return
        text = self.title.text()
        if text == self._saved_title:
            self.title_error.hide()
            return
        error = validate_title(text)
        if error:
            self.title.setText(self._saved_title)
            self.title_error.setText(error)
            self.title_error.show()
            return
        try:
            update_title(self._video, text)
        except (OSError, ValueError, KeyError, TypeError):
            # The sidecar could not be rewritten: put the old title back (content-model.md).
            self.title.setText(self._saved_title)
            self.title_error.setText(TITLE_NOT_SAVED)
            self.title_error.show()
            return
        self._saved_title = text
        self.title_error.hide()
        self.title_changed.emit(str(self._video))

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.seek(float(item.data(TIME_ROLE)))

    def seek(self, seconds: float) -> None:
        self.seek_requested.emit(seconds)
        if self._player is not None:
            self._player.setPosition(int(seconds * 1000))

    # --- Player ------------------------------------------------------------

    def _toggle_play(self) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_playback_state(self, state) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setText("Pause" if playing else "Play")

    def _on_position(self, ms: int) -> None:
        if not self.position.isSliderDown():
            self.position.blockSignals(True)
            self.position.setValue(ms)
            self.position.blockSignals(False)

    def _on_player_error(self, *_args) -> None:
        self._show_video_error()

    def stop_playback(self) -> None:
        if self._player is not None:
            self._player.stop()

    # --- Layout (site-contract.md §1) --------------------------------------

    def _apply_layout(self) -> None:
        wide = self.window().width() >= WIDE_WINDOW
        direction = QBoxLayout.Direction.LeftToRight if wide else QBoxLayout.Direction.TopToBottom
        if self.body.direction() != direction:
            self.body.setDirection(direction)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().resizeEvent(event)
        self._apply_layout()
