"""Settings screen. Rules: content-model.md (Settings) and site-contract.md (section 6).

Each field has its own Save action, except the privacy checkbox, which applies on
click. Messages show inline under the field.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screen_recorder_buffed import languages
from screen_recorder_buffed.key_store import (
    KeyStore,
    SecureStoreUnavailable,
    mask_key,
    validate_key,
)
from screen_recorder_buffed.settings_store import (
    Settings,
    SettingsStore,
    validate_output_folder,
)
from screen_recorder_buffed.theme import px

PRIVACY_TEXT = "Screen images and transcript text are sent to Anthropic."
REMOVE_KEY_TEXT = "Remove the Claude API key? Recording will be disabled until a new key is saved."
MSG_NOT_SAVED = "Settings could not be saved."
MAX_WIDTH = 720
NONE_LABEL = "None"
DIALOG_WIDTH = 400
FIELD_GAP = px("space-2")
SECTION_GAP = px("space-4")
CHECKBOX_MIN_HEIGHT = 40


def _error_label() -> QLabel:
    label = QLabel()
    label.setObjectName("error-message")
    label.setWordWrap(True)
    label.hide()
    return label


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section-title")
    return label


def _field_column(parent: QWidget | None = None) -> QVBoxLayout:
    layout = QVBoxLayout(parent)
    layout.setSpacing(FIELD_GAP)
    layout.setContentsMargins(0, 0, 0, 0)
    return layout


class SettingsScreen(QWidget):
    def __init__(self, store: SettingsStore, keys: KeyStore) -> None:
        super().__init__()
        self._store = store
        self._keys = keys
        self._settings: Settings = store.load()

        self.setMaximumWidth(MAX_WIDTH)
        layout = QVBoxLayout(self)
        padding = px("space-3")
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(SECTION_GAP)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Settings")
        heading.setObjectName("page-title")
        layout.addWidget(heading)
        layout.addWidget(self._build_privacy())
        layout.addWidget(self._build_key())
        layout.addWidget(self._build_folder())
        layout.addWidget(self._build_language())
        layout.addWidget(self._build_fixed())

        self._refresh_key_view()

    # --- Persistence -------------------------------------------------------

    def _persist(self, error_label: QLabel, **changes) -> bool:
        """Apply `changes` to the settings on disk and save. On failure, show the message.

        Reloads first, so a value saved by another screen (e.g. the last language chosen
        in Recording control) is never overwritten by an old copy.
        """
        fresh = self._store.load()
        for name, value in changes.items():
            setattr(fresh, name, value)
        self._settings = fresh
        try:
            self._store.save(self._settings)
        except OSError:
            self._show_error(error_label, MSG_NOT_SAVED)
            return False
        return True

    # --- Privacy -----------------------------------------------------------

    def _build_privacy(self) -> QWidget:
        box = QWidget()
        layout = _field_column(box)
        self.privacy = QCheckBox(PRIVACY_TEXT)
        self.privacy.setMinimumHeight(CHECKBOX_MIN_HEIGHT)
        self.privacy.setChecked(self._settings.privacy_accepted)
        self.privacy.toggled.connect(self._on_privacy_toggled)
        self.privacy_error = _error_label()
        layout.addWidget(self.privacy)
        layout.addWidget(self.privacy_error)
        return box

    def _on_privacy_toggled(self, checked: bool) -> None:
        self._persist(self.privacy_error, privacy_accepted=checked)

    # --- Claude API key ----------------------------------------------------

    def _build_key(self) -> QWidget:
        box = QWidget()
        layout = _field_column(box)
        layout.addWidget(_section_title("Claude API key"))

        self.key_status = QLabel()
        layout.addWidget(self.key_status)

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-ant-…")
        self.key_input.setAccessibleName("Claude API key")
        layout.addWidget(self.key_input)

        self.key_error = _error_label()
        layout.addWidget(self.key_error)

        row = QHBoxLayout()
        row.setSpacing(FIELD_GAP)
        self.key_save = QPushButton("Save")
        self.key_save.setObjectName("primary")
        self.key_save.clicked.connect(self._on_save_key)
        self.key_replace = QPushButton("Replace key")
        self.key_replace.clicked.connect(self._on_replace_key)
        self.key_cancel = QPushButton("Cancel")
        self.key_cancel.clicked.connect(self._refresh_key_view)
        self.key_remove = QPushButton("Remove key")
        self.key_remove.setObjectName("destructive")
        self.key_remove.clicked.connect(self._on_remove_key)
        for button in (self.key_save, self.key_replace, self.key_cancel, self.key_remove):
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        return box

    def _stored_key(self) -> str | None:
        try:
            return self._keys.get_key()
        except SecureStoreUnavailable as error:
            self._show_error(self.key_error, str(error))
            self._store_unavailable = True
            return None

    def _refresh_key_view(self) -> None:
        """Show either the masked key (with Replace and Remove) or the empty entry field."""
        self.key_error.hide()
        self._store_unavailable = False
        stored = self._stored_key()
        self.key_input.clear()
        if stored:
            self.key_status.setText(f"Saved: {mask_key(stored)}")
            self.key_input.hide()
            self.key_save.hide()
            self.key_cancel.hide()
            self.key_replace.show()
            self.key_remove.show()
        else:
            # With no secure store, the error line says why; the status line stays empty.
            self.key_status.setText("" if self._store_unavailable else "No key saved.")
            self.key_input.show()
            self.key_save.show()
            self.key_cancel.hide()
            self.key_replace.hide()
            self.key_remove.hide()

    def _on_replace_key(self) -> None:
        self.key_error.hide()
        self.key_status.setText("Enter the new key.")
        self.key_input.clear()
        self.key_input.show()
        self.key_save.show()
        self.key_cancel.show()
        self.key_replace.hide()
        self.key_remove.hide()

    def _on_save_key(self) -> None:
        key = self.key_input.text().strip()
        error = validate_key(key)
        if error:
            self._show_error(self.key_error, error)
            return
        try:
            self._keys.set_key(key)
        except SecureStoreUnavailable as error:
            self._show_error(self.key_error, str(error))
            return
        self._refresh_key_view()

    def _confirm_remove(self) -> bool:
        """Ask before removing the key. Buttons: 'Remove' and 'Cancel' (site-contract.md §6)."""
        box = QMessageBox(self)
        box.setWindowTitle("Remove key")
        box.setText(REMOVE_KEY_TEXT)
        box.setMinimumWidth(DIALOG_WIDTH)
        remove = box.addButton("Remove", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(QMessageBox.StandardButton.NoButton)
        box.exec()
        return box.clickedButton() is remove

    def _on_remove_key(self) -> None:
        if not self._confirm_remove():
            return
        try:
            self._keys.delete_key()
        except SecureStoreUnavailable as error:
            self._show_error(self.key_error, str(error))
            return
        self._refresh_key_view()

    # --- Output folder -----------------------------------------------------

    def _build_folder(self) -> QWidget:
        box = QWidget()
        layout = _field_column(box)
        layout.addWidget(_section_title("Output folder"))

        self.folder_input = QLineEdit(self._settings.output_folder)
        self.folder_input.setAccessibleName("Output folder")
        layout.addWidget(self.folder_input)

        self.folder_error = _error_label()
        layout.addWidget(self.folder_error)

        save = QPushButton("Save")
        save.setObjectName("primary")
        save.clicked.connect(self._on_save_folder)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        return box

    def _on_save_folder(self) -> None:
        folder, error = validate_output_folder(self.folder_input.text())
        if error or folder is None:
            # Keep the previous value and show the message under the field.
            self.folder_input.setText(self._settings.output_folder)
            self._show_error(self.folder_error, error or "")
            return
        self.folder_error.hide()
        self._persist(self.folder_error, output_folder=self.folder_input.text().strip())

    # --- Spoken-language default -------------------------------------------

    def _build_language(self) -> QWidget:
        box = QWidget()
        layout = _field_column(box)
        layout.addWidget(_section_title("Spoken-language default"))

        self.language = QComboBox()
        self.language.setAccessibleName("Spoken-language default")
        self.language.addItem(NONE_LABEL, None)
        for name, code in languages.LANGUAGES:
            self.language.addItem(languages.label(code), code)
        index = self.language.findData(self._settings.default_language)
        self.language.setCurrentIndex(max(index, 0))
        layout.addWidget(self.language)

        self.language_error = _error_label()
        layout.addWidget(self.language_error)

        save = QPushButton("Save")
        save.setObjectName("primary")
        save.clicked.connect(self._on_save_language)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        return box

    def _on_save_language(self) -> None:
        self._persist(self.language_error, default_language=self.language.currentData())

    # --- Fixed values ------------------------------------------------------

    def _build_fixed(self) -> QWidget:
        box = QWidget()
        layout = _field_column(box)
        layout.addWidget(_section_title("Fixed in version 1"))
        layout.addWidget(QLabel("Description interval: 10 seconds"))
        layout.addWidget(QLabel("Maximum frame size: 1280×720"))
        return box

    # --- Helpers -----------------------------------------------------------

    @staticmethod
    def _show_error(label: QLabel, text: str) -> None:
        label.setText(text)
        label.show()
