"""Translation rules with a fake HTTP function: no network, no API key.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from screen_recorder_buffed.translate import (
    MODEL,
    ClaudeTranslator,
    TranslationError,
    build_request,
    parse_response,
)


def reply(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


class TranslateTests(unittest.TestCase):
    def test_long_recordings_are_batched(self) -> None:
        calls: list[int] = []

        def fake_post(body: dict, api_key: str) -> dict:
            content = body["messages"][0]["content"]
            count = sum(1 for line in content.splitlines() if line[:1].isdigit())
            calls.append(count)
            return reply("[" + ", ".join(f'"e{i}"' for i in range(count)) + "]")

        translator = ClaudeTranslator("sk-ant-x", post=fake_post)
        result = translator.translate([f"t{i}" for i in range(120)], "ja")
        self.assertEqual(len(result), 120)
        self.assertEqual(calls, [50, 50, 20])

    def test_truncated_reply_is_an_error(self) -> None:
        with self.assertRaises(TranslationError):
            parse_response({"stop_reason": "max_tokens", "content": []}, expected=1)

    def test_english_is_passed_through_without_a_call(self) -> None:
        calls: list = []
        translator = ClaudeTranslator("sk-ant-x", post=lambda b, k: calls.append(b) or {})
        self.assertEqual(translator.translate(["Hello", "World"], "en"), ["Hello", "World"])
        self.assertEqual(calls, [])

    def test_translates_all_segments_in_one_request(self) -> None:
        seen: dict = {}

        def fake_post(body: dict, api_key: str) -> dict:
            seen["body"], seen["key"] = body, api_key
            return reply('["Hello there.", "Thank you."]')

        translator = ClaudeTranslator("sk-ant-key-123", post=fake_post)
        result = translator.translate(["こんにちは", "ありがとう"], "ja")
        self.assertEqual(result, ["Hello there.", "Thank you."])
        self.assertEqual(seen["body"]["model"], MODEL)
        self.assertEqual(seen["key"], "sk-ant-key-123")
        self.assertIn("Japanese", seen["body"]["messages"][0]["content"])

    def test_reply_with_wrong_count_is_rejected(self) -> None:
        with self.assertRaises(TranslationError):
            parse_response(reply('["only one"]'), expected=2)

    def test_reply_without_json_is_rejected(self) -> None:
        with self.assertRaises(TranslationError):
            parse_response(reply("Sorry, I cannot help."), expected=1)

    def test_request_numbers_the_lines(self) -> None:
        body = build_request(["a", "b"], "es")
        content = body["messages"][0]["content"]
        self.assertIn("1. a", content)
        self.assertIn("2. b", content)

    def test_errors_do_not_contain_the_key(self) -> None:
        def failing(body: dict, api_key: str) -> dict:
            raise TranslationError("Claude API returned HTTP 401")

        translator = ClaudeTranslator("sk-ant-secret-key-value", post=failing)
        with self.assertRaises(TranslationError) as raised:
            translator.translate(["こんにちは"], "ja")
        self.assertNotIn("sk-ant", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
