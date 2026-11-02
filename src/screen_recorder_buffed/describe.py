"""Screen descriptions with the Claude Messages API (claude-haiku-5-5). Rules: content-model.md.

One request per frame. The frame is scaled to at most 1280x720, keeping its aspect ratio.
The reply is cleaned to at most two sentences and 200 characters. A frame with no shared
content gets "No shared content". Uses only the standard library, like translate.py.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from screen_recorder_buffed.translate import MODEL, MAX_OUTPUT_TOKENS, TranslationError, post_message

MAX_WIDTH = 1280
MAX_HEIGHT = 720
MAX_CHARS = 200
MAX_SENTENCES = 2
NO_CONTENT = "No shared content"

INSTRUCTION = (
    "This is one frame from a screen share in a meeting. In English, describe the slide or "
    "shared content in one or two sentences. If nothing is shared (blank, desktop, or no "
    "presentation), reply exactly: No shared content. Reply with the description only."
)

Post = Callable[[dict, str], dict]


def extract_frame(video: Path, seconds: float) -> bytes:
    """One frame at `seconds` as JPEG bytes, scaled to fit 1280x720. Never written to disk."""
    scale = (
        f"scale=w='min({MAX_WIDTH},iw)':h='min({MAX_HEIGHT},ih)':"
        "force_original_aspect_ratio=decrease"
    )
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf", scale, "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "3", "pipe:1"],
        capture_output=True,
        timeout=120,
        check=True,
    )
    if not result.stdout:
        raise ValueError("no frame at this time")
    return result.stdout


def build_request(jpeg: bytes) -> dict:
    return {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(jpeg).decode("ascii"),
                }},
                {"type": "text", "text": INSTRUCTION},
            ],
        }],
    }


def clean_description(text: str) -> str:
    """Apply the content-model limits: no more than two sentences, at most 200 characters."""
    text = " ".join(text.split())
    if not text:
        return NO_CONTENT
    if text.rstrip(".!?").lower() == NO_CONTENT.lower():
        return NO_CONTENT
    sentences = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text)
    kept = "".join(sentences[:MAX_SENTENCES]).strip() or text
    if len(kept) > MAX_CHARS:
        # Keep whole words only: cut at the last space at or before position 200.
        if kept[MAX_CHARS] == " ":
            kept = kept[:MAX_CHARS]
        else:
            space = kept.rfind(" ", 0, MAX_CHARS)
            kept = kept[:space] if space > 0 else kept[:MAX_CHARS]
    return kept.strip()


def describe_jpeg(jpeg: bytes, api_key: str, post: Post = post_message) -> str:
    response = post(build_request(jpeg), api_key)
    try:
        text = "".join(block["text"] for block in response["content"] if block.get("type") == "text")
    except (KeyError, TypeError) as error:
        raise TranslationError("Claude API returned an unexpected reply") from error
    return clean_description(text)
