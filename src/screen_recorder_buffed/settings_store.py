"""Non-secret settings, saved as JSON in the user's config folder.

The Claude API key is not stored here; it goes to the OS keyring (key_store.py).
Rules: content-model.md, Settings.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from screen_recorder_buffed.languages import LANGUAGE_CODES

DEFAULT_OUTPUT_FOLDER = "~/Videos/ScreenRecorderBuffed/"


@dataclass
class Settings:
    privacy_accepted: bool = False
    output_folder: str = DEFAULT_OUTPUT_FOLDER
    default_language: str | None = None  # one of LANGUAGE_CODES, or None for "None"
    last_language: str | None = None  # the language of the last recording (content-model.md)

    def __post_init__(self) -> None:
        if self.default_language is not None and self.default_language not in LANGUAGE_CODES:
            self.default_language = None
        if self.last_language is not None and self.last_language not in LANGUAGE_CODES:
            self.last_language = None


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "screen-recorder-buffed" / "settings.json"


MSG_FOLDER_REQUIRED = "Output folder is required."


def validate_output_folder(value: str) -> tuple[Path | None, str | None]:
    """Check a typed output folder. Returns (folder, None) or (None, message).

    Rules from content-model.md, Settings: the folder is created if missing;
    if it is not writable the value is rejected and the previous one is kept.
    """
    text = value.strip()
    if not text:
        return None, MSG_FOLDER_REQUIRED
    folder = Path(text).expanduser()
    not_writable = f"Folder is not writable: {text}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None, not_writable
    if not folder.is_dir() or not os.access(folder, os.W_OK):
        return None, not_writable
    return folder, None


class SettingsStore:
    """Loads and saves Settings. A missing or unreadable file gives the defaults."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> Settings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return Settings()
        if not isinstance(data, dict):
            return Settings()
        known = {key: data[key] for key in Settings.__dataclass_fields__ if key in data}
        try:
            return Settings(**known)
        except TypeError:
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
