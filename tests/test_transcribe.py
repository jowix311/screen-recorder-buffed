"""Slice 3 checks: segment cleaning rules. Uses no model, so it runs anywhere.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from screen_recorder_buffed.transcribe import MODEL_SIZE, Segment, clean_segments


class CleanSegmentsTests(unittest.TestCase):
    def test_times_are_rounded_to_milliseconds(self) -> None:
        segments = clean_segments([(1.23456, 4.98765, " Hola ")])
        self.assertEqual(segments, [Segment(1.235, 4.988, "Hola")])

    def test_silent_segments_are_dropped(self) -> None:
        segments = clean_segments([(0.0, 1.0, "   "), (1.0, 2.0, ""), (2.0, 3.0, "Hello")])
        self.assertEqual(segments, [Segment(2.0, 3.0, "Hello")])

    def test_order_is_kept(self) -> None:
        raw = [(5.0, 6.0, "second"), (1.0, 2.0, "first")]
        self.assertEqual([s.text for s in clean_segments(raw)], ["second", "first"])

    def test_model_size_is_small(self) -> None:
        self.assertEqual(MODEL_SIZE, "small")


if __name__ == "__main__":
    unittest.main()
