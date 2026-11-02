"""Recording library data. Rules: content-model.md (Recording library) and site-contract.md §4.

Each MKV in the output folder is one row. Its sidecar gives the title, times and status.
An MKV with no readable sidecar is shown as failed, so the video is never hidden (decided
2026-11-02). The recording in progress is shown with the status the controller reports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from screen_recorder_buffed.sidecar import FAILED, READY, read_sidecar

NAME_FORMAT = "%Y-%m-%d_%H-%M-%S"  # MKV file names (content-model.md, Output files)


class LibraryError(Exception):
    """The output folder cannot be read."""


@dataclass(frozen=True)
class LibraryRow:
    video: Path
    title: str
    started_at: datetime | None  # naive local time, for display and sorting
    duration_seconds: int | None
    spoken_language: str | None
    status: str  # 'recording', 'processing', 'ready' or 'failed'

    @property
    def opens_review(self) -> bool:
        return self.status in (READY, FAILED)


def _started_from_name(video: Path) -> datetime | None:
    try:
        return datetime.strptime(video.stem, NAME_FORMAT)
    except ValueError:
        return None


def _row_for(video: Path, active: dict[Path, str]) -> LibraryRow:
    if video in active:
        return LibraryRow(video, video.stem, _started_from_name(video), None, None, active[video])
    try:
        data = read_sidecar(video)
        # Naive local time, so it sorts with rows whose time comes from the file name.
        started = datetime.fromisoformat(data["started_at"]).astimezone().replace(tzinfo=None)
        duration = data.get("duration_seconds")
        return LibraryRow(
            video=video,
            title=str(data.get("title") or video.stem),
            started_at=started,
            duration_seconds=int(duration) if duration is not None else None,
            spoken_language=data.get("spoken_language") or None,
            status=data.get("status") if data.get("status") in (READY, FAILED) else FAILED,
        )
    except (OSError, ValueError, KeyError, TypeError):
        return LibraryRow(video, video.stem, _started_from_name(video), None, None, FAILED)


def scan_library(folder: Path, active: dict[Path, str] | None = None) -> list[LibraryRow]:
    """All recordings in `folder`, newest first. `active` maps in-progress files to their status."""
    active = active or {}
    try:
        videos = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mkv"]
    except FileNotFoundError:
        return []  # no folder yet means no recordings yet
    except OSError as error:
        raise LibraryError(f"Cannot read output folder: {folder}") from error
    rows = [_row_for(video, active) for video in videos]
    rows.sort(key=lambda row: row.started_at or datetime.min, reverse=True)
    return rows


def format_duration(seconds: int | None) -> str:
    """hh:mm:ss, or an em dash while the length is unknown (content-model.md)."""
    if seconds is None:
        return "—"
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_started(started: datetime | None) -> str:
    return started.strftime("%Y-%m-%d %H:%M") if started else "—"
