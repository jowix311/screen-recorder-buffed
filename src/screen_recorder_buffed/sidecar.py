"""The JSON sidecar written next to each MKV. Rules: content-model.md (Output files).

Status is 'ready' when processing succeeded and the sidecar was written, and 'failed'
otherwise. A failed recording keeps its video, with empty segment and description lists.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from screen_recorder_buffed.process_recording import ProcessingResult

READY = "ready"
FAILED = "failed"
PROCESSING = "processing"


@dataclass(frozen=True)
class SidecarMeta:
    title: str
    started_at: datetime  # timezone-aware
    duration_seconds: int  # rounded down
    spoken_language: str  # ISO 639-1, lowercase


def default_title(started_at: datetime) -> str:
    """Default title: start date and time, YYYY-MM-DD HH:mm (content-model.md)."""
    return started_at.strftime("%Y-%m-%d %H:%M")


def sidecar_path(video: Path) -> Path:
    return video.with_suffix(".json")


def build_sidecar(meta: SidecarMeta, status: str, result: ProcessingResult | None) -> dict:
    failed = status != READY or result is None
    return {
        "title": meta.title,
        "started_at": meta.started_at.isoformat(timespec="seconds"),
        "duration_seconds": int(meta.duration_seconds),
        "spoken_language": meta.spoken_language,
        "segments": [] if failed else [
            {"start_seconds": round(line.start_seconds, 3),
             "original_text": line.original_text,
             "english_text": line.english_text}
            for line in result.lines
        ],
        "descriptions": [] if failed else [
            {"time_seconds": note.time_seconds, "description": note.description}
            for note in result.descriptions
        ],
        "status": status,
    }


def write_sidecar(video: Path, meta: SidecarMeta, status: str, result: ProcessingResult | None) -> Path:
    """Write the sidecar atomically (temp file, then rename). Raises OSError if that fails."""
    target = sidecar_path(video)
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(build_sidecar(meta, status, result), ensure_ascii=False, indent=2),
                    encoding="utf-8")
    os.replace(temp, target)
    return target


def read_sidecar(video: Path) -> dict:
    return json.loads(sidecar_path(video).read_text(encoding="utf-8"))


def read_meta(video: Path) -> SidecarMeta:
    """The metadata Retry needs. Raises ValueError if the sidecar is missing or malformed."""
    try:
        data = read_sidecar(video)
        return SidecarMeta(
            title=str(data["title"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            duration_seconds=int(data["duration_seconds"]),
            spoken_language=str(data["spoken_language"]),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError("The recording's details could not be read") from error


REQUIRED_KEYS = {"title", "started_at", "duration_seconds", "spoken_language", "segments", "descriptions", "status"}


def validate_sidecar(data: dict) -> list[str]:
    """Return the problems found in a sidecar (empty list when it is valid)."""
    problems = [f"missing {key}" for key in sorted(REQUIRED_KEYS - set(data))]
    if problems:
        return problems
    try:
        started = datetime.fromisoformat(data["started_at"])
        if started.tzinfo is None:
            problems.append("started_at has no timezone")
    except (TypeError, ValueError):
        problems.append("started_at is not an ISO timestamp")
    if not isinstance(data["duration_seconds"], int):
        problems.append("duration_seconds is not an integer")
    if data["status"] not in (READY, FAILED):
        problems.append("status is not ready or failed")
    if data["status"] == FAILED and (data["segments"] or data["descriptions"]):
        problems.append("failed recording has segments or descriptions")
    for line in data["segments"]:
        if not isinstance(line.get("start_seconds"), (int, float)):
            problems.append("segment start_seconds is not a number")
    for note in data["descriptions"]:
        if not isinstance(note.get("time_seconds"), int):
            problems.append("description time_seconds is not an integer")
    return problems
