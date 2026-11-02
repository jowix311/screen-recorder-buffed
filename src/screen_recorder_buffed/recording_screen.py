"""Recording control screen. Rules: site-contract.md §2 and content-model.md (Recording control).

The screen reads the start conditions from the saved settings and the keyring, and
shows whatever state the RecordingController reports. The Start button, and the
messages under it, are refreshed whenever a condition could have changed.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from screen_recorder_buffed import languages
from screen_recorder_buffed.key_store import KeyStore, SecureStoreUnavailable
from screen_recorder_buffed.recording_controller import RecordingController
from screen_recorder_buffed.recording_state import StartInputs, State, start_blockers
from screen_recorder_buffed.settings_store import SettingsStore
from screen_recorder_buffed.theme import px

MAX_WIDTH = 720
PLACEHOLDER_LANGUAGE = "Choose a language"
MSG_NOT_SAVED = "Settings could not be saved."
SOURCE_TEXT = "Primary monitor"
SHORTCUT_NOTICE = "Ctrl+Shift+R works only while this window is focused."


class RecordingScreen(QWidget):
    def __init__(self, store: SettingsStore, keys: KeyStore, controller: RecordingController) -> None:
        super().__init__()
        self._store = store
        self._keys = keys
        self._controller = controller

        self.setMaximumWidth(MAX_WIDTH)
        layout = QVBoxLayout(self)
        padding = px("space-3")
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(px("space-2"))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Recording control")
        heading.setObjectName("page-title")
        layout.addWidget(heading)

        self.language = QComboBox()
        self.language.setAccessibleName("Spoken language")
        self.language.addItem(PLACEHOLDER_LANGUAGE, None)
        for name, code in languages.LANGUAGES:
            self.language.addItem(languages.label(code), code)
        layout.addWidget(self.language)

        source_title = QLabel("Source")
        source_title.setObjectName("section-title")
        layout.addWidget(source_title)
        source = QLabel(SOURCE_TEXT)
        source.setObjectName("page-body")
        layout.addWidget(source)

        self.button = QPushButton()
        self.button.setObjectName("primary")
        self.button.clicked.connect(self._on_button)
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.messages = QLabel()
        self.messages.setObjectName("error-message")
        self.messages.setWordWrap(True)
        layout.addWidget(self.messages)

        self.timer = QLabel("00:00:00")
        self.timer.setObjectName("page-body")
        layout.addWidget(self.timer)

        self.shortcut_notice = QLabel(SHORTCUT_NOTICE)
        self.shortcut_notice.setObjectName("page-body")
        self.shortcut_notice.setWordWrap(True)
        self.shortcut_notice.hide()
        layout.addWidget(self.shortcut_notice)

        self.language.currentIndexChanged.connect(self._on_language_changed)
        controller.state_changed.connect(self._on_state)
        controller.messages_changed.connect(self._on_controller_messages)
        controller.elapsed_changed.connect(self.timer.setText)

        self._controller_messages: list[str] = []
        self._save_error: str | None = None
        self._preselect_language()
        self.refresh()

    # --- Start conditions --------------------------------------------------

    def inputs(self) -> StartInputs:
        settings = self._store.load()
        try:
            has_key = bool(self._keys.get_key())
        except SecureStoreUnavailable:
            has_key = False
        return StartInputs(
            privacy_accepted=settings.privacy_accepted,
            has_key=has_key,
            language_selected=self.language.currentData() is not None,
            retry_running=self._controller.retry_running,
        )

    def _preselect_language(self) -> None:
        """Settings default, else the last language chosen, else the placeholder (content-model.md)."""
        settings = self._store.load()
        code = settings.default_language or settings.last_language
        index = self.language.findData(code) if code else 0
        self.language.setCurrentIndex(max(index, 0))

    # --- Refresh -----------------------------------------------------------

    def refresh(self) -> None:
        """Recompute the button and the messages from the current conditions.

        Called on screen show, on language change, on every state change, and when the
        user comes back to this screen (Settings may have changed in between).
        """
        state = self._controller.state
        inputs = self.inputs()
        blockers = start_blockers(inputs) if state is State.IDLE else []

        self.button.setText(self._controller.control.button_label())
        self.button.setEnabled(self._controller.button_enabled(inputs))
        self.timer.setVisible(self._controller.control.timer_visible())
        if state is State.IDLE:
            self.timer.setText("00:00:00")
        self.language.setEnabled(state is State.IDLE and not self._controller.picking)
        messages = blockers or self._controller_messages
        if self._save_error:
            messages = [*messages, self._save_error]
        self._show_messages(messages)

    def _show_messages(self, messages: list[str]) -> None:
        self.messages.setText("\n".join(messages))
        self.messages.setVisible(bool(messages))

    # --- Actions -----------------------------------------------------------

    def _on_button(self) -> None:
        if self._controller.state is State.RECORDING:
            self._controller.stop()
            return
        self._controller.start(self.inputs(), self.language.currentData())

    def toggle_from_shortcut(self) -> None:
        """Ctrl+Shift+R. Ignored while Start is blocked (site-contract.md §2)."""
        if self._controller.state is State.IDLE and start_blockers(self.inputs()):
            return
        self._controller.toggle(self.inputs(), self.language.currentData())

    def show_shortcut_notice(self, visible: bool) -> None:
        self.shortcut_notice.setVisible(visible)

    # --- Signals -----------------------------------------------------------

    def _on_language_changed(self, _index: int) -> None:
        code = self.language.currentData()
        self._save_error = None
        if code is not None:
            # Saved as soon as it is chosen (content-model.md: the last language chosen).
            settings = self._store.load()
            settings.last_language = code
            try:
                self._store.save(settings)
            except OSError:
                self._save_error = MSG_NOT_SAVED
        self.refresh()

    def _on_state(self, _value: str) -> None:
        self.refresh()

    def _on_controller_messages(self, messages: list) -> None:
        self._controller_messages = list(messages)
        self.refresh()
