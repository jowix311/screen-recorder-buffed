"""Reduced-motion reply parsing. No D-Bus.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from screen_recorder_buffed.motion import parse_reply


class ParseReplyTests(unittest.TestCase):
    def test_animations_off(self) -> None:
        self.assertFalse(parse_reply((("b", False),)))

    def test_animations_on(self) -> None:
        self.assertTrue(parse_reply((("b", True),)))

    def test_nested_variant(self) -> None:
        self.assertFalse(parse_reply((("v", ("b", False)),)))

    def test_unexpected_reply_keeps_animations_on(self) -> None:
        self.assertTrue(parse_reply(()))
        self.assertTrue(parse_reply((("s", "yes"),)))


if __name__ == "__main__":
    unittest.main()
