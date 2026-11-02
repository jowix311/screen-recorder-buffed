# PRD: Screen Recorder Buffed

> Status: APPROVED by the user on 2026-10-31. All open questions are closed as of 2026-11-02.

## Vision

A Linux desktop app that records the screen while listening to a meeting. It translates the spoken audio into English and describes what is shown on screen (slides, shared windows) alongside the translation, so the recording is understandable without knowing the spoken language.

**Vibe sentence:** A screen recorder desktop app that can record a screen while it listens to meetings, translates what it hears to English, and describes what it sees on the presentation.

## Users

1. **Multilingual attendee.** Joins a meeting in a language they don't fully follow. Needs English text next to the slides afterwards, and maybe during the meeting.
2. **Note-taker or reviewer.** Records a meeting for later review. Needs a single file with video, a readable transcript and slide descriptions.

## Features

### Must-Have
- Record the screen (video) on Linux.
- Show a visible recording indicator (a red badge) for as long as recording is active.
- Capture meeting audio from the system output (what the other participants say), not only the microphone.
- Choose the spoken language before each recording, from a short list: English, Spanish, French, German, Portuguese, Italian, Japanese, Chinese, Korean.
- Speech-to-text of the captured audio, with timestamps.
- Translate the transcript to English.
- Describe the shared screen at intervals, with timestamps.
- Save the result: an MKV video file plus a JSON sidecar holding the timestamped translated transcript and screen descriptions, in `~/Videos/ScreenRecorderBuffed/`.

### Should-Have (version 2)
- Live view of translated captions and screen descriptions while recording.
- Choose which screen or window to record.

### Nice-to-Have
- Export to a subtitle file (SRT/VTT).
- Search across a finished recording's transcript and descriptions.

## Constraints

- **Platform:** Linux only for version 1 (decided).
- **Processing location (hybrid):**
  - Speech-to-text runs locally with faster-whisper, using segment timestamps. Audio never leaves the machine.
  - Translation and screen descriptions use the Claude Messages API with `claude-haiku-5-5`, authenticated with an API key. Transcript text and screen images are sent to Anthropic.
  - Frames are sampled every 10 seconds, at most 1280x720.
  - Claude Code is the build tool only. It is not part of the app's runtime and does no transcription, translation or description.
  - The app needs internet access for translation and descriptions.
  - Estimated cost: about $0.10–0.15 per recorded hour.
- **Privacy:** the user accepts that screen images and transcript text are sent to Anthropic and retained for up to 30 days, the data-retention setting on the user's individual API plan (confirmed 2026-11-02). Zero data retention is not in use.
- **Scope:** built by a solo developer working with AI.
- **Non-goals:**
  - Windows and macOS support.
  - Joining meetings as a bot or sending audio or video into the meeting.
  - Editing the video.
  - Multi-user or cloud sync.

## Design standards

See `design-standard.md`.

## Success criteria

- A meeting in a non-English language, recorded for 10 minutes, produces an English transcript whose timestamps match the recording within 2 seconds.
- Every slide change visible on screen is reflected in a screen description within 10 seconds.
- The app runs for a 60-minute recording without crashing or losing the video file.
- The transcript and screen descriptions are ready within 10 minutes after a 60-minute recording ends (processing time to be confirmed by research).

## Open questions



## Decisions log

| Item | Choice | Date | Source |
|------|--------|------|--------|
| Platform | Linux only for version 1 | 2026-10-31 | User |
| Live view | Post-processing in version 1; live captions in version 2 | 2026-10-31 | User |
| Consent | Visible recording indicator while recording; no consent prompt | 2026-10-31 | User |
| Screen description interval | Every 10 seconds | 2026-10-31 | User |
| Output format | MKV video + JSON sidecar in ~/Videos/ScreenRecorderBuffed/ | 2026-10-31 | User |
| Processing location | Hybrid: local faster-whisper speech-to-text; Claude Haiku 5.5 via the Messages API for translation and screen descriptions (API key); Claude Code not used | 2026-10-31 | User choice; spec-researcher report (sources: platform.claude.com vision, pricing, models overview, data-retention pages; code.claude.com legal-and-compliance and headless pages; github.com/openai/whisper and SYSTRAN/faster-whisper) |
| Frame sampling | Every 10 seconds, max 1280x720 | 2026-10-31 | Researcher recommendation; cost and token figures from platform.claude.com vision and pricing pages |
| Privacy acceptance | User accepts sending screen images and transcript text to the Claude API (data-retention setting still to confirm) | 2026-10-31 | User |
| Recording source | Primary screen only in version 1; choosing a screen or window is version 2 | 2026-11-01 | User |
| Spoken language picker | In version 1, from a short list of 9 languages (en, es, fr, de, pt, it, ja, zh, ko); moved from version 2 | 2026-11-01 | User |
| Failed recordings | Can be opened in Recording review, with Retry | 2026-11-01 | User |
| Privacy acceptance placement | Unchecked checkbox in Settings; processing blocked until ticked | 2026-11-01 | User |
| Audio in recording | The MKV holds the screen video and the captured system-audio track in one file | 2026-11-01 | User |
| Data retention | Accepted: the individual API plan's 30-day retention setting (Console, Data retention page); no zero data retention | 2026-11-02 | User |
| Claude Code's role | Build tool only; the app's transcription, translation and descriptions do not use Claude Code | 2026-10-31 | User, after the terms and capability check (Claude Code cannot hear audio; Anthropic's legal page requires API-key auth for products) |
