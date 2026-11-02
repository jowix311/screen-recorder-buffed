"""Speech-to-text with faster-whisper, run locally. Rules: content-model.md (Recording review, Transcript).

Each speech segment becomes one Segment with start/end times in seconds. Silent
stretches produce no segment. The spoken language comes from the picker, so the
model does not guess it.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

MODEL_SIZE = "small"  # chosen by the user, 2026-11-02


@dataclass(frozen=True)
class Segment:
    start_seconds: float
    end_seconds: float
    text: str  # the words as spoken, in the spoken language


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path, language: str) -> list[Segment]: ...


def clean_segments(raw: Iterable[tuple[float, float, str]]) -> list[Segment]:
    """Round times to milliseconds and drop segments with no words (silence)."""
    segments: list[Segment] = []
    for start, end, text in raw:
        words = text.strip()
        if not words:
            continue
        segments.append(Segment(
            start_seconds=round(float(start), 3),
            end_seconds=round(float(end), 3),
            text=words,
        ))
    return segments


WORKER_SCRIPT = Path(__file__).with_name("transcribe_worker.py")
DEFAULT_TRANSCRIBER_PYTHON = Path.home() / ".venvs" / "srb-transcriber" / "bin" / "python"
TRANSCRIBE_TIMEOUT_S = 4 * 60 * 60  # a long meeting on a CPU can take a while


class TranscriptionError(Exception):
    """The transcriber could not run or failed."""


class SubprocessTranscriber:
    """Runs transcribe_worker.py under the Python 3.12 environment that has faster-whisper.

    faster-whisper 1.2.1 does not work with the PyAV version the app uses on Python 3.14,
    so the model runs in its own environment (see the Slice 3 notes in the roadmap).
    """

    def __init__(
        self,
        python: Path = DEFAULT_TRANSCRIBER_PYTHON,
        model_size: str = MODEL_SIZE,
        worker: Path = WORKER_SCRIPT,
    ) -> None:
        self._python = python
        self._model_size = model_size
        self._worker = worker

    def transcribe(self, audio_path: Path, language: str) -> list[Segment]:
        if not self._python.exists():
            raise TranscriptionError(f"Transcriber not found: {self._python}")
        try:
            result = subprocess.run(
                [str(self._python), "-I", str(self._worker), self._model_size, str(audio_path), language],
                capture_output=True,
                text=True,
                timeout=TRANSCRIBE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as error:
            raise TranscriptionError("Transcription took too long") from error
        if result.returncode != 0:
            raise TranscriptionError(result.stderr.strip() or "Transcription failed")
        try:
            rows = json.loads(result.stdout)
        except ValueError as error:
            raise TranscriptionError("Transcriber returned unreadable output") from error
        return clean_segments((float(start), float(end), str(text)) for start, end, text in rows)
