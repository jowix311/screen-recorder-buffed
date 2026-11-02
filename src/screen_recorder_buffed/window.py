"""Main window: left sidebar with four screens, minimum size 1024x640.

Behaviour from site-contract.md, section 1. The screens are placeholders in
Slice 0; their content comes in later slices.
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

from screen_recorder_buffed.theme import TOKENS

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


def _px(token: str) -> int:
    """Read a pixel token such as "24px" from theme.TOKENS as an int."""
    return int(TOKENS[token].removesuffix("px"))


def _placeholder_screen(name: str) -> QWidget:
    """A screen in a scroll area, so content taller than the window scrolls (site-contract.md §1)."""
    page = QWidget()
    layout = QVBoxLayout(page)
    padding = _px("space-3")
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    title = QLabel(name)
    title.setObjectName("page-title")
    body = QLabel("Not built yet.")
    body.setObjectName("page-body")

    layout.addWidget(title)
    layout.addWidget(body)

    scroll = QScrollArea()
    scroll.setWidget(page)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    return scroll


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Screen Recorder Buffed")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.stack = QStackedWidget()

        for name in SCREEN_NAMES:
            self.sidebar.addItem(QListWidgetItem(name))
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
