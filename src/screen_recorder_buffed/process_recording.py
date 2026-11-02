"""Processing after a recording: transcribe, translate, describe. Rules: content-model.md.

Input is the finished MKV file. Output is the timestamped data the JSON sidecar needs
(sidecar.py writes it). Any failure raises ProcessingError, so the caller can set status
'failed'. Processing sends screen images and transcript text to Anthropic, so it refuses
to run unless the user has checked the privacy box in Settings (PRD.md, Constraints).
"""

from __future__ import annotations

import math
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from screen_recorder_buffed.describe import NoFrameError, describe_jpeg, extract_frame
from screen_recorder_buffed.transcribe import Segment
from screen_recorder_buffed.translate import ClaudeTranslator

DESCRIPTION_INTERVAL_S = 10  # fixed in version 1 (content-model.md, Settings)


class ProcessingError(Exception):
    """Processing failed or was refused. The recording's status becomes 'failed'."""


@dataclass(frozen=True)
class TranscriptLine:
    start_seconds: float
    end_seconds: float
    original_text: str
    english_text: str


@dataclass(frozen=True)
class ScreenNote:
    time_seconds: int
    description: str


@dataclass
class ProcessingResult:
    lines: list[TranscriptLine] = field(default_factory=list)
    descriptions: list[ScreenNote] = field(default_factory=list)


def media_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return float(out.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        # Covers a partial MKV whose duration is "N/A" (content-model.md, capture error).
        raise ProcessingError("Could not read the recording's length") from error


def frame_times(duration: float, interval: int = DESCRIPTION_INTERVAL_S) -> list[int]:
    """0, 10, 20, ... seconds, up to and including the last frame before the end (content-model.md)."""
    return list(range(0, math.ceil(duration), interval))


def process_recording(
    video: Path,
    language: str,
    api_key: str,
    privacy_accepted: bool,
    transcribe: Callable[[Path, str], list[Segment]],
    translator: ClaudeTranslator | None = None,
    describe: Callable[[bytes, str], str] = describe_jpeg,
    extract: Callable[[Path, float], bytes] = extract_frame,
    times: Sequence[int] | None = None,
) -> ProcessingResult:
    if not privacy_accepted:
        raise ProcessingError("Accept privacy in Settings before processing")

    try:
        segments = transcribe(video, language)
    except Exception as error:  # noqa: BLE001 - any transcription failure is a 'failed' status
        raise ProcessingError(f"Transcription failed: {error}") from error

    translator = translator or ClaudeTranslator(api_key)
    try:
        english = translator.translate([s.text for s in segments], language)
    except Exception as error:  # noqa: BLE001 - any Claude failure is a 'failed' status
        raise ProcessingError(str(error)) from error

    result = ProcessingResult(lines=[
        TranscriptLine(s.start_seconds, s.end_seconds, s.text, en)
        for s, en in zip(segments, english)
    ])

    if times is None:
        times = frame_times(media_duration(video))
    last = times[-1] if times else None
    for seconds in times:
        try:
            jpeg = extract(video, float(seconds))  # kept in memory, never written to disk
        except NoFrameError:
            if seconds == last:
                break  # audio ran past the last video frame; the recording is still fine
            raise ProcessingError(f"Screen description failed at {seconds}s: no video frame") from None
        except Exception as error:  # noqa: BLE001 - frame failure is a 'failed' status
            raise ProcessingError(f"Screen description failed at {seconds}s: {error}") from error
        try:
            text = describe(jpeg, api_key)
        except ProcessingError:
            raise
        except Exception as error:  # noqa: BLE001 - frame or Claude failure is a 'failed' status
            raise ProcessingError(f"Screen description failed at {seconds}s: {error}") from error
        result.descriptions.append(ScreenNote(time_seconds=seconds, description=text))
    return result

