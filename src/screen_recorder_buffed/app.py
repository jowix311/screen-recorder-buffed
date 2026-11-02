"""Application start-up: create the Qt application, apply the theme, show the window."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from screen_recorder_buffed.theme import build_stylesheet
from screen_recorder_buffed.window import MainWindow


def run(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()
