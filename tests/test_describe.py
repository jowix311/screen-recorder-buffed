"""Screen-description rules: content-model.md limits. No network.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from screen_recorder_buffed.describe import MAX_CHARS, NO_CONTENT, build_request, clean_description


class CleanDescriptionTests(unittest.TestCase):
    def test_keeps_at_most_two_sentences(self) -> None:
        text = "A slide about revenue. It shows a bar chart. A third sentence follows."
        self.assertEqual(clean_description(text), "A slide about revenue. It shows a bar chart.")

    def test_cuts_long_text_at_a_word_within_200_characters(self) -> None:
        text = "word " * 100
        result = clean_description(text)
        self.assertLessEqual(len(result), MAX_CHARS)
        self.assertFalse(result.endswith(" "))
        self.assertTrue(result.split()[-1] == "word")

    def test_empty_reply_is_no_shared_content(self) -> None:
        self.assertEqual(clean_description("   "), NO_CONTENT)

    def test_no_shared_content_reply_is_normalised(self) -> None:
        self.assertEqual(clean_description("No shared content."), NO_CONTENT)

    def test_whitespace_is_collapsed(self) -> None:
        self.assertEqual(clean_description("A  title\n\nslide."), "A title slide.")


class BuildRequestTests(unittest.TestCase):
    def test_image_is_sent_as_base64_jpeg(self) -> None:
        body = build_request(b"\xff\xd8fake")
        image = body["messages"][0]["content"][0]
        self.assertEqual(image["type"], "image")
        self.assertEqual(image["source"]["media_type"], "image/jpeg")
        self.assertEqual(image["source"]["data"], "/9hmYWtl")


if __name__ == "__main__":
    unittest.main()
