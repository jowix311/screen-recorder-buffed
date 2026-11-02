"""Recording library rules: rows, statuses, ordering, unreadable folder. No Qt, no network.

Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from screen_recorder_buffed.recording_library import LibraryError, format_duration, scan_library


def write_pair(folder: Path, name: str, status: str, started: str, duration: int = 61) -> Path:
    video = folder / f"{name}.mkv"
    video.write_bytes(b"video")
    video.with_suffix(".json").write_text(json.dumps({
        "title": f"Meeting {name}",
        "started_at": started,
        "duration_seconds": duration,
        "spoken_language": "ja",
        "segments": [],
        "descriptions": [],
        "status": status,
    }), encoding="utf-8")
    return video


class LibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_rows_are_newest_first(self) -> None:
        write_pair(self.folder, "2026-11-01_09-00-00", "ready", "2026-11-01T09:00:00+00:00")
        write_pair(self.folder, "2026-11-02_09-00-00", "ready", "2026-11-02T09:00:00+00:00")
        titles = [row.title for row in scan_library(self.folder)]
        self.assertEqual(titles, ["Meeting 2026-11-02_09-00-00", "Meeting 2026-11-01_09-00-00"])

    def test_missing_sidecar_is_shown_as_failed(self) -> None:
        (self.folder / "2026-11-02_10-00-00.mkv").write_bytes(b"video")
        row = scan_library(self.folder)[0]
        self.assertEqual(row.status, "failed")
        self.assertTrue(row.opens_review)
        self.assertIsNone(row.duration_seconds)

    def test_in_progress_file_takes_the_controller_status(self) -> None:
        video = write_pair(self.folder, "2026-11-02_11-00-00", "failed", "2026-11-02T11:00:00+00:00")
        row = scan_library(self.folder, active={video: "processing"})[0]
        self.assertEqual(row.status, "processing")
        self.assertFalse(row.opens_review)

    def test_ready_and_failed_rows_open_review(self) -> None:
        write_pair(self.folder, "2026-11-02_12-00-00", "ready", "2026-11-02T12:00:00+00:00")
        write_pair(self.folder, "2026-11-02_13-00-00", "failed", "2026-11-02T13:00:00+00:00")
        self.assertTrue(all(row.opens_review for row in scan_library(self.folder)))

    def test_empty_folder_gives_no_rows(self) -> None:
        self.assertEqual(scan_library(self.folder), [])

    def test_missing_folder_gives_no_rows(self) -> None:
        self.assertEqual(scan_library(self.folder / "not-there"), [])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can read locked folders")
    def test_unreadable_folder_raises(self) -> None:
        locked = self.folder / "locked"
        locked.mkdir()
        locked.chmod(0)
        try:
            with self.assertRaises(LibraryError):
                scan_library(locked)
        finally:
            locked.chmod(0o700)


class FormatTests(unittest.TestCase):
    def test_duration_format(self) -> None:
        self.assertEqual(format_duration(3725), "01:02:05")
        self.assertEqual(format_duration(None), "—")


if __name__ == "__main__":
    unittest.main()
