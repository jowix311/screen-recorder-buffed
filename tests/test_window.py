"""Slice 0 checks: window size, sidebar order, navigation, sidebar width.

Run with: .venv/bin/python -m unittest discover -s tests -v
Uses Qt's offscreen platform so no display is needed.
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed.theme import build_stylesheet  # noqa: E402
from screen_recorder_buffed.window import (  # noqa: E402
    MIN_HEIGHT,
    MIN_WIDTH,
    REVIEW_INDEX,
    SCREEN_NAMES,
    SIDEBAR_WIDTH,
    MainWindow,
)


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(build_stylesheet())

    def setUp(self) -> None:
        self.window = MainWindow()
        self.window.show()

    def tearDown(self) -> None:
        self.window.close()

    def test_minimum_size_is_1024_by_640(self) -> None:
        self.assertEqual(self.window.minimumWidth(), MIN_WIDTH)
        self.assertEqual(self.window.minimumHeight(), MIN_HEIGHT)
        self.window.resize(100, 100)
        self.app.processEvents()
        self.assertGreaterEqual(self.window.width(), MIN_WIDTH)
        self.assertGreaterEqual(self.window.height(), MIN_HEIGHT)

    def test_sidebar_lists_four_screens_in_order(self) -> None:
        labels = [self.window.sidebar.item(i).text() for i in range(self.window.sidebar.count())]
        self.assertEqual(labels, SCREEN_NAMES)
        self.assertEqual(
            labels,
            ["Recording control", "Recording library", "Recording review", "Settings"],
        )

    def test_recording_review_is_hidden_until_opened(self) -> None:
        self.assertTrue(self.window.sidebar.isRowHidden(REVIEW_INDEX))
        visible = [
            self.window.sidebar.item(i).text()
            for i in range(self.window.sidebar.count())
            if not self.window.sidebar.isRowHidden(i)
        ]
        self.assertEqual(visible, ["Recording control", "Recording library", "Settings"])

    def test_show_recording_review_reveals_the_item(self) -> None:
        self.window.show_recording_review()
        self.assertFalse(self.window.sidebar.isRowHidden(REVIEW_INDEX))

    def test_sidebar_width_is_fixed_at_200(self) -> None:
        self.assertEqual(self.window.sidebar.width(), SIDEBAR_WIDTH)
        self.assertEqual(self.window.sidebar.minimumWidth(), SIDEBAR_WIDTH)
        self.assertEqual(self.window.sidebar.maximumWidth(), SIDEBAR_WIDTH)

    def test_first_screen_is_selected_at_start(self) -> None:
        self.assertEqual(self.window.sidebar.currentRow(), 0)
        self.assertEqual(self.window.stack.currentIndex(), 0)

    def test_clicking_a_sidebar_item_switches_the_screen(self) -> None:
        self.window.show_recording_review()
        for index in range(len(SCREEN_NAMES)):
            self.window.sidebar.setCurrentRow(index)
            self.assertEqual(self.window.stack.currentIndex(), index)


if __name__ == "__main__":
    unittest.main()
