"""Recording library screen. Rules: content-model.md (Recording library) and site-contract.md §4.

States: loading, empty, unreadable folder (with Retry), and the list. Clicking a row with
status 'ready' or 'failed' opens Recording review; other rows do nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from screen_recorder_buffed import languages
from screen_recorder_buffed.recording_library import (
    LibraryError,
    LibraryRow,
    format_duration,
    format_started,
    scan_library,
)
from screen_recorder_buffed.theme import TOKENS, px

HEADERS = ["Title", "Date", "Duration", "Language", "Status"]
STATUS_COLUMN = 4
EMPTY_TEXT = "No recordings yet. Start one from Recording control."
LOADING_TEXT = "Loading recordings…"
MAX_WIDTH = 1200


class LibraryScreen(QWidget):
    review_requested = Signal(str)  # the MKV path to open in Recording review

    def __init__(self, output_dir: Callable[[], Path], active: Callable[[], dict[Path, str]]) -> None:
        super().__init__()
        self._output_dir = output_dir
        self._active = active
        self._rows: list[LibraryRow] = []

        self.setMaximumWidth(MAX_WIDTH)
        layout = QVBoxLayout(self)
        padding = px("space-3")
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(px("space-2"))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Recording library")
        heading.setObjectName("page-title")
        layout.addWidget(heading)

        self.message = QLabel(LOADING_TEXT)
        self.message.setObjectName("page-body")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.retry_button = QPushButton("Retry")
        self.retry_button.setObjectName("secondary")
        self.retry_button.clicked.connect(self.refresh)
        self.retry_button.hide()
        layout.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.cellActivated.connect(self._on_cell_clicked)
        self.table.hide()
        layout.addWidget(self.table, stretch=1)

    # --- Data --------------------------------------------------------------

    def refresh(self) -> None:
        """Rescan the output folder. Called when the screen is shown and when a recording ends."""
        self.message.setText(LOADING_TEXT)
        self.message.show()
        self.retry_button.hide()
        try:
            self._rows = scan_library(self._output_dir(), self._active())
        except LibraryError as error:
            self._rows = []
            self.table.hide()
            self.message.setText(str(error))
            self.retry_button.show()
            return
        self._fill()

    def _fill(self) -> None:
        if not self._rows:
            self.table.hide()
            self.message.setText(EMPTY_TEXT)
            self.message.show()
            return
        self.message.hide()
        self.table.setRowCount(len(self._rows))
        for row_index, row in enumerate(self._rows):
            code = row.spoken_language
            cells = [
                row.title,
                format_started(row.started_at),
                format_duration(row.duration_seconds),
                languages.label(code) if code in languages.LANGUAGE_CODES else "—",
                row.status,
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == STATUS_COLUMN:
                    # Status colour plus its text label (design-standard.md, Colour).
                    item.setForeground(QColor(TOKENS[f"color-status-{row.status}"]))
                self.table.setItem(row_index, column, item)
        self.table.show()

    # --- Interaction -------------------------------------------------------

    def _on_cell_clicked(self, row_index: int, _column: int) -> None:
        if not (0 <= row_index < len(self._rows)):
            return
        row = self._rows[row_index]
        if row.opens_review:
            self.review_requested.emit(str(row.video))

    def rows(self) -> list[LibraryRow]:
        return list(self._rows)
