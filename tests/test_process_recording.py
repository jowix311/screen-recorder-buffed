"""Processing rules with fakes: failures become ProcessingError; frames every 10 s. No network.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from screen_recorder_buffed.process_recording import (
    ProcessingError,
    frame_times,
    process_recording,
)
from screen_recorder_buffed.transcribe import Segment
from screen_recorder_buffed.translate import ClaudeTranslator, TranslationError


def fake_extract(video: Path, seconds: float) -> bytes:
    return b"jpeg"


class ProcessRecordingTests(unittest.TestCase):
    def test_frames_every_ten_seconds_up_to_the_end(self) -> None:
        self.assertEqual(frame_times(25.0), [0, 10, 20])
        self.assertEqual(frame_times(10.0), [0])

    def test_fractional_duration_keeps_the_last_frame(self) -> None:
        self.assertEqual(frame_times(20.5), [0, 10, 20])
        self.assertEqual(frame_times(3600.4)[-1], 3600)

    def test_processing_is_refused_without_privacy(self) -> None:
        with self.assertRaises(ProcessingError):
            process_recording(Path("a.mkv"), "ja", "sk-ant-x", privacy_accepted=False,
                              transcribe=lambda p, lang: [], times=[])

    def test_transcript_is_translated_and_described(self) -> None:
        segments = [Segment(0.0, 2.0, "こんにちは")]
        translator = ClaudeTranslator("sk-ant-x", post=lambda b, k: {"content": [{"type": "text", "text": '["Hello"]'}]})
        result = process_recording(
            Path("a.mkv"), "ja", "sk-ant-x", privacy_accepted=True,
            transcribe=lambda p, lang: segments,
            translator=translator,
            describe=lambda jpeg, key: "A slide.",
            extract=fake_extract,
            times=[0, 10],
        )
        self.assertEqual(result.lines[0].english_text, "Hello")
        self.assertEqual([n.time_seconds for n in result.descriptions], [0, 10])

    def test_transcription_failure_is_a_processing_error(self) -> None:
        def broken(path: Path, language: str) -> list[Segment]:
            raise RuntimeError("model missing")

        with self.assertRaises(ProcessingError):
            process_recording(Path("a.mkv"), "ja", "sk-ant-x", privacy_accepted=True, transcribe=broken, times=[])

    def test_claude_failure_is_a_processing_error(self) -> None:
        def failing_post(body: dict, key: str) -> dict:
            raise TranslationError("Claude API returned HTTP 500")

        with self.assertRaises(ProcessingError):
            process_recording(
                Path("a.mkv"), "ja", "sk-ant-x", privacy_accepted=True,
                transcribe=lambda p, lang: [Segment(0.0, 1.0, "はい")],
                translator=ClaudeTranslator("sk-ant-x", post=failing_post),
                times=[],
            )


if __name__ == "__main__":
    unittest.main()
