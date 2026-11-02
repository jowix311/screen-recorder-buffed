"""Translation to English with the Claude Messages API (claude-haiku-5-5).

All segments of one recording go in one request, as a numbered list, and come back
as a JSON array with one English line per segment. English input is passed through
unchanged (content-model.md, Recording review). The API key is never logged or shown.

Uses only the standard library, so no new package is needed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = "claude-haiku-5-5"
TIMEOUT_S = 120
MAX_OUTPUT_TOKENS = 8192

LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
    "it": "Italian", "ja": "Japanese", "zh": "Chinese", "ko": "Korean",
}

Post = Callable[[dict, str], dict]  # (body, api_key) -> parsed JSON response


class TranslationError(Exception):
    """The translation could not be done. The message never contains the API key."""


def _post(body: dict, api_key: str) -> dict:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise TranslationError(f"Claude API returned HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TranslationError("Could not reach the Claude API") from error


def build_request(texts: Sequence[str], source_language: str) -> dict:
    name = LANGUAGE_NAMES.get(source_language, source_language)
    numbered = "\n".join(f"{i + 1}. {text}" for i, text in enumerate(texts))
    instruction = (
        f"Translate each numbered line from {name} into English. "
        "Keep the meaning. Do not add or drop lines. "
        f"Reply with only a JSON array of {len(texts)} strings, in the same order."
    )
    return {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": f"{instruction}\n\n{numbered}"}],
    }


def parse_response(response: dict, expected: int) -> list[str]:
    try:
        text = "".join(block["text"] for block in response["content"] if block.get("type") == "text")
    except (KeyError, TypeError) as error:
        raise TranslationError("Claude API returned an unexpected reply") from error
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise TranslationError("Translation reply was not a JSON list")
    try:
        lines = json.loads(text[start:end + 1])
    except ValueError as error:
        raise TranslationError("Translation reply was not valid JSON") from error
    if not isinstance(lines, list) or len(lines) != expected or not all(isinstance(x, str) for x in lines):
        raise TranslationError("Translation reply did not match the number of segments")
    return [line.strip() for line in lines]


class ClaudeTranslator:
    def __init__(self, api_key: str, post: Post = _post) -> None:
        self._api_key = api_key
        self._post = post

    def translate(self, texts: Sequence[str], source_language: str) -> list[str]:
        if source_language == "en" or not texts:
            return list(texts)
        body = build_request(texts, source_language)
        response = self._post(body, self._api_key)
        return parse_response(response, expected=len(texts))
