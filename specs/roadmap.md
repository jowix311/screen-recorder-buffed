# Roadmap: Screen Recorder Buffed, version 1

> Status: APPROVED by the user on 2026-11-02. Each slice is built, then checked with `spec-auditor` before the next one starts. Items marked `<!-- default: -->` were chosen by the drafter.

Sources: `PRD.md` (scope), `content-model.md` (fields and states), `site-contract.md` (behaviour), `design-standard.md` (look).

## Slice 0: Scaffold

- Python 3 project, PySide6 window, minimum size 1024×640.
- Left sidebar (200 px) with the four screens, navigation between them. Recording review is hidden until a library row is opened (site-contract.md §1, decided 2026-11-02). Empty placeholder content.
- Design tokens from `design-standard.md` loaded as the stylesheet.
- Done when: the app starts, the sidebar switches screens, and the window cannot be made smaller than 1024×640.

## Slice 1: Settings

Depends on: 0.

- Privacy checkbox, applied on click.
- Claude API key: save to the OS keyring, mask as `sk-ant-••••abcd`, replace and remove with confirmation.
- Output folder with Save, created if missing, rejected if not writable.
- Spoken-language default.
- Fixed values shown read-only: 10-second interval, 1280×720 maximum frame.
- Done when: every Settings rule in `content-model.md` and `site-contract.md` passes by hand, and the key is never written to a log or file.

## Slice 2: Recording control, capture only

Depends on: 1 (Start is gated by Settings).

- Start conditions and their messages (privacy, key, language, retry).
- Primary monitor capture and system-audio capture, written to one MKV file in the output folder with the name `YYYY-MM-DD_HH-mm-ss.mkv`.
- States `idle`, `recording`, `stopping`, `processing` (processing is a placeholder here), timer, recording indicator with blink, and the 5-second capture-error rule.
- Global shortcut Ctrl+Shift+R.
- Closing the window while recording shows the stop dialog.
- Done when: a 10-minute test recording produces an MKV with video and audio tracks, and the state moves correctly through every transition.

<!-- default: capture library and method chosen at build time; research needed on Wayland support for global shortcuts and PipeWire capture -->

## Slice 3: Speech-to-text

Depends on: 2.

- faster-whisper, run locally, with segment timestamps.
- The spoken language from the picker is passed to the model.
- Done when: a 10-minute recording in a known language produces segments whose start times match the audio within 2 seconds.

## Slice 4: Translation and screen descriptions

Depends on: 3.

- Frames taken every 10 seconds at 00:00:00, 00:00:10, and so on, at most 1280×720, aspect ratio kept.
- Claude Messages API with `claude-haiku-5-5`: translation of each transcript segment (English passed through unchanged); one description per frame, rules from `content-model.md` (1–2 sentences, 200 characters, "No shared content" when nothing is shared).
- API errors are recorded so that `failed` can be set.
- Done when: a 60-minute test recording is fully processed within 10 minutes, and a simulated API error sets the recording to `failed`.

## Slice 5: Output and status

Depends on: 4.

- JSON sidecar written when processing ends, with the fields and types in `content-model.md`.
- Status rules: `failed` on any faster-whisper, Claude API, or sidecar error; otherwise `ready`.
- Retry reruns the whole pipeline from the MKV and disables Start while it runs.
- Done when: a valid sidecar opens and validates, and Retry changes the status as specified.

## Slice 6: Recording library

Depends on: 5.

- List newest first, columns and status labels from `content-model.md`.
- Loading, empty and unreadable-folder states with Retry.
- Row click rules; library status mapping from the Recording control state.
- Done when: every library state in `site-contract.md` can be reached by hand.

## Slice 7: Recording review

Depends on: 6.

- Video player with seek; transcript and description times seek the video.
- Transcript and description layouts; "No speech detected"; hidden sections for `failed`.
- Failed state with Retry; title edit with save and revert.
- Done when: every review state in `site-contract.md` can be reached, and a missing video shows its message.

## Slice 8: Hardening and audit

Depends on: 7.

- `spec-auditor` run against all five docs and the full code; Critical and High findings fixed.
- Test on a real meeting in a non-English language: transcript and descriptions checked by hand.
- Check the reduced-motion rule and the focus ring on every control.

## Risks

- **Global shortcut on Wayland:** Ctrl+Shift+R may need the desktop portal. If it doesn't work on the user's desktop, slice 2 needs a decision.
- **Local speech-to-text speed:** the 10-minute target was estimated, not measured. Measure in slice 3, and change the model size if needed.
- **Screen capture on Wayland:** capture needs the desktop's portal and PipeWire. Check before slice 2 starts.
