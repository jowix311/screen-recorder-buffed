"""The spoken-language list for version 1 (content-model.md, Recording control)."""

from __future__ import annotations

# (name, ISO 639-1 code), in the order shown in the picker.
LANGUAGES: list[tuple[str, str]] = [
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Portuguese", "pt"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Chinese", "zh"),
    ("Korean", "ko"),
]

LANGUAGE_CODES: frozenset[str] = frozenset(code for _, code in LANGUAGES)


def label(code: str) -> str:
    """Name and code, e.g. 'Spanish (es)' (content-model.md, Recording library)."""
    for name, language_code in LANGUAGES:
        if language_code == code:
            return f"{name} ({code})"
    raise KeyError(code)
