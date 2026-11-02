# Screen Recorder Buffed

A Linux desktop app that records the screen and system audio of a meeting, transcribes the speech, translates it to English, and describes the shared screen every 10 seconds. The result is an MKV file plus a JSON sidecar with timestamped text. Vibe: a screen recorder that listens to meetings, translates what it hears to English, and describes what it sees on the presentation.

## Constraints

- **Stack:** Python 3 with PySide6 (Qt) for the window; faster-whisper for speech-to-text, run locally; the Claude Messages API with `claude-haiku-5-5` for translation and screen descriptions, authenticated with an API key; the OS keyring (libsecret) for the key.
- **Python packages:** PySide6 6.12.0, keyring 25.7.0, jeepney 0.9.0 (pinned in `pyproject.toml`).
- **Transcriber environment (approved 2026-11-02):** faster-whisper 1.2.1 with the small model and PyAV 13.1.0, in a separate Python 3.12 environment at `~/.venvs/srb-transcriber`. It runs `src/screen_recorder_buffed/transcribe_worker.py` as a subprocess, because faster-whisper 1.2.1 does not work with PyAV 19 on Python 3.14.
- **System tools (approved 2026-11-02):** `gst-launch-1.0` with GStreamer plugins good and base (screen and audio capture, MKV muxing); `pactl` (PulseAudio/PipeWire, to find the default output's monitor). The desktop portals ScreenCast and GlobalShortcuts are used through D-Bus. `ffmpeg` and `ffprobe` (approved 2026-11-02) read video frames and durations for screen descriptions.
- **Platform:** Linux only in version 1.
- **Claude Code is the build tool only.** It is never part of the app's runtime.
- **No new dependencies without approval.**
- **Never log or write the API key, the transcript text or the screen images** outside the MKV and JSON sidecar in the output folder.
- **Privacy:** the app sends screen images and transcript text to Anthropic only after the user has checked the privacy box in Settings.
- **Primary screen only** in version 1. Language choice from a short list of 9.
- **Write no code** until the user approves the spec docs below and asks to start building.

## Where everything is

| Doc | Load when |
|-----|-----------|
| `PRD.md` | making product or scope decisions |
| `content-model.md` | building or reviewing screens, fields or the JSON sidecar |
| `site-contract.md` | implementing window layout, states, transitions or shortcuts |
| `design-standard.md` | any UI or styling work |
| `.claude/skills/project-spec-docs/` | planning changes to these docs |
| `.claude/agents/spec-*.md` | checking docs for vague wording, researching open items, auditing built code |

## Working rules

- Follow `content-model.md` and `site-contract.md` exactly. Do not invent screens, fields, states or colours not in those docs.
- Any value you need that the docs don't define: ask the user, or mark it as a default in the doc.
- Run `spec-auditor` against the docs after each build slice, and fix Critical and High findings before the next slice.
