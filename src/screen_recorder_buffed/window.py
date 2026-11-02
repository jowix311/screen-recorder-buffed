"""Main window: left sidebar with four screens, minimum size 1024x640.

Behaviour from site-contract.md, section 1. Recording control, library and review
are placeholders until their slices; Settings is built (Slice 1).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from screen_recorder_buffed.key_store import KeyringKeyStore, KeyStore
from screen_recorder_buffed.settings_screen import SettingsScreen
from screen_recorder_buffed.settings_store import SettingsStore
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
REVIEW_INDEX = 2
SETTINGS_INDEX = 3


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


class MainWindow(QWidget):
    def __init__(self, store: SettingsStore | None = None, keys: KeyStore | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Screen Recorder Buffed")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.stack = QStackedWidget()

        for index, name in enumerate(SCREEN_NAMES):
            self.sidebar.addItem(QListWidgetItem(name))
            if index == SETTINGS_INDEX:
                screen = SettingsScreen(store or SettingsStore(), keys or KeyringKeyStore())
                self.stack.addWidget(_in_scroll_area(screen))
            else:
                self.stack.addWidget(_placeholder_screen(name))

        # Recording review is hidden until a library row is opened (site-contract.md §1).
        self.sidebar.setRowHidden(REVIEW_INDEX, True)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, stretch=1)

    def show_recording_review(self) -> None:
        """Make the Recording review item visible. Called when a library row is opened (Slice 6)."""
        self.sidebar.setRowHidden(REVIEW_INDEX, False)
