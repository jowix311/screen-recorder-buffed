# Content model: Screen Recorder Buffed

> Status: APPROVED by the user on 2026-11-01. The final clarity check reported remaining gaps; all suggested wording was applied and accepted. Every field lists its constraints. Items marked `<!-- default: -->` were proposed by the clarity checker and accepted by the user on 2026-11-01.

Screens for version 1: Recording control, Recording library, Recording review, Settings.

## Recording control

- **Source:** the monitor the desktop marks as primary. If none is marked, the monitor at position 0,0. Not selectable in version 1. (Choosing a screen or window is version 2.) <!-- default: accepted by user 2026-11-01 -->
- **Spoken language:** the language of the meeting audio. Required before Start. Closed list, shown as names with codes: English (`en`), Spanish (`es`), French (`fr`), German (`de`), Portuguese (`pt`), Italian (`it`), Japanese (`ja`), Chinese (`zh`), Korean (`ko`). Pre-selected value: the Settings default if set; otherwise the last language chosen, saved to disk and kept across app restarts; otherwise empty, and Start is disabled. <!-- default: accepted by user 2026-11-01 -->
- **Start / stop button:** one button. When processing ends with status `ready` or `failed`, the state returns to `idle`. Labels and enabled state:
  - `idle`: "Start recording". Enabled only when all of these are true: a spoken language is selected, privacy acceptance is checked, a Claude API key is saved, and no recording has `status` `processing` from a Retry. If the screen or system-audio source is missing when Start is pressed, Start is refused, the state stays `idle`, and "No screen or system-audio source found" is shown under the button. Under the button, show "Accept privacy in Settings to record" when privacy is unchecked, and "Add a Claude API key in Settings to record" when no key is saved. If both conditions fail, show both messages, one per line, privacy message first. <!-- default: accepted by user 2026-11-01 -->
  - `recording`: "Stop recording", enabled.
  - `stopping`: "Stopping…", disabled.
  - `processing`: "Processing…", disabled.
- **Timer:** elapsed time as `hh:mm:ss`, updated every second. Visible in `recording` and `stopping`. Hidden in `idle` and `processing`. <!-- default: accepted by user 2026-11-01 -->
- **Recording indicator:** a badge with the text "Recording", background `#d93025`, text `#ffffff`. Visible in `recording` and `stopping`. Cannot be hidden while visible. <!-- default: accepted by user 2026-11-01 -->
- **State:** one of `idle`, `recording`, `stopping`, `processing`. Only one recording can run at a time. A new recording can start only in `idle`. <!-- default: accepted by user 2026-11-01 -->
- **Capture error:** the video or system-audio source delivers no new data for 5 consecutive seconds, or the capture process exits before Stop is pressed. During `recording`, a capture error moves the state to `stopping`. The partial MKV file is kept and the recording is processed. <!-- default: accepted by user 2026-11-01 -->

## Recording library

Shows one row per recording, newest first. Clicking a row with status `ready` or `failed` opens Recording review. Clicking a row with status `recording` or `processing` does nothing. While the output folder is read, "Loading recordings…" is shown in place of the list. <!-- default: accepted by user 2026-11-01 -->

- **Title:** text, 1–80 Unicode code points. Required. Default: start date and time, `YYYY-MM-DD HH:mm`. Edited in Recording review only. An empty or over-length title is rejected with the message "Title must be 1–80 Unicode code points". <!-- default: accepted by user 2026-11-01 -->
- **Date:** start date and time, `YYYY-MM-DD HH:mm` (local time). Required.
- **Duration:** `hh:mm:ss` once the recording stops. Shows "—" while the status is `recording` or `processing`. <!-- default: accepted by user 2026-11-01 -->
- **Spoken language:** the language chosen for the recording, shown as name and code, e.g. "Spanish (es)", using the same names as Recording control. Required.
- **Status:** one of `recording`, `processing`, `ready`, `failed`. Required. Mapped from the Recording control state: `recording` while the state is `recording`; `processing` while the state is `stopping` or `processing`; then `ready` or `failed`. <!-- default: accepted by user 2026-11-01 -->
- **Empty state:** text "No recordings yet. Start one from Recording control." Shown when the list is empty.
- **Output folder unreadable:** show "Cannot read output folder: `<path>`" and a Retry button. Retry re-reads the output folder. On success, show the list. On failure, show the same message and button. <!-- default: accepted by user 2026-11-01 -->

## Recording review

Opens one recording with `status` `ready` or `failed`.

- **Video:** the MKV file, with play, pause and seek controls. If the file is missing or cannot play, show "Video cannot be played: `<path>`" in place of the player. <!-- default: accepted by user 2026-11-01 -->
- **Transcript** (one segment per speech segment from faster-whisper; silent intervals produce no segment):
  - When `status` is `failed`, hide the transcript and description sections. Show only the failure message and Retry.
  - When `status` is `ready` and there are zero segments, show "No speech detected". <!-- default: accepted by user 2026-11-01 -->
  - Start time: `hh:mm:ss`, required. Clicking it seeks the video to that time.
  - Original text: the words as spoken, required and non-empty.
  - English text: the translation, required. When the spoken language is `en`, it is the same string as the original text. <!-- default: accepted by user 2026-11-01 -->
- **Screen description** (one per frame; frames are captured at 00:00:00, 00:00:10, 00:00:20, and so on, until the recording stops):
  - Time: `hh:mm:ss`, required. Clicking it seeks the video to that time.
  - Description: English, 1–2 sentences (a sentence ends at `.`, `!` or `?`), at most 200 characters. If the reply has more than 2 sentences, keep the first 2. If the result is longer than 200 characters, cut it at the last whole word within 200 characters. Required. A frame with no shared content has the description "No shared content". <!-- default: accepted by user 2026-11-01 -->
- **Failed state:** when `status` is `failed`, show "Processing failed. The video is kept." with a Retry button. Pressing Retry sets `status` to `processing` and disables the button. Retry reruns the whole pipeline from the MKV file: faster-whisper, translation and all frame descriptions. While it runs, Start is disabled. While `status` is `processing`, show "Processing…" in place of the failure message. On success the status becomes `ready`. On failure it stays `failed`, and the same message and button are shown again. <!-- default: accepted by user 2026-11-01 -->
- **Title:** editable here. Same rule as the library title. If the sidecar rewrite fails, the title reverts to the previous value and "Title could not be saved" is shown. <!-- default: accepted by user 2026-11-01 -->

- **Labels** (approved 2026-11-02): page heading "Recording review"; section headings "Transcript" and "Screen descriptions"; player buttons "Play" and "Pause".
- **Recording without a readable sidecar:** shown as failed with its video; the title cannot be edited because there is no sidecar to rewrite.

## Settings

- **Privacy acceptance:** a checkbox, unchecked by default, with the text "Screen images and transcript text are sent to Anthropic." Processing is blocked while it is unchecked. Unchecking it blocks new processing only; a run already in progress finishes. <!-- default: accepted by user 2026-11-01 -->
- **Claude API key:** a secret string starting with `sk-ant-`. Required before any processing. Stored in the OS keyring (libsecret). If no keyring is available, saving fails with "No secure store available". If the value does not start with `sk-ant-`, saving is rejected, the previous key is kept, and "API key must start with sk-ant-" is shown. Shown masked after saving as `sk-ant-••••abcd` (last 4 characters). Buttons: "Replace key" (opens an empty field) and "Remove key" (deletes the key from the keyring, after confirmation). Confirmation text: "Remove the Claude API key? Recording will be disabled until a new key is saved." Buttons: "Remove" and "Cancel". A run in progress finishes using the key read when the run started. Removing the key takes effect for new runs. <!-- default: accepted by user 2026-11-01 -->
- **Output folder:** a folder path. Default: `~/Videos/ScreenRecorderBuffed/`. Each field has a "Save" button, and the value applies only after Save is pressed. On save, if the folder does not exist it is created. If it is not writable, the value is rejected, the previous value is kept, and "Folder is not writable: `<path>`" is shown. The library lists recordings in the current output folder only. <!-- default: accepted by user 2026-11-01 -->
- **Description interval:** 10 seconds. Fixed in version 1. Not editable.
- **Maximum frame size:** 1280×720. Frames are scaled to fit inside this size, keeping aspect ratio. Frames smaller than 1280×720 are not upscaled. Fixed in version 1. <!-- default: accepted by user 2026-11-01 -->
- **Spoken-language default:** one code from the Recording control list (`en`, `es`, `fr`, `de`, `pt`, `it`, `ja`, `zh`, `ko`), or none. Used to pre-select Recording control. Default: none. <!-- default: accepted by user 2026-11-01 -->

## Output files

Each recording writes two files to the output folder:

- **MKV video:** named `YYYY-MM-DD_HH-mm-ss.mkv` from the local start time. Contains the screen video and the captured system-audio track, muxed into one file. <!-- default: accepted by user 2026-11-01 -->
- **JSON sidecar:** the same base name with `.json`. Written when processing ends, and again when processing ends after each Retry, overwriting the previous file. Rewritten immediately when the title is edited. <!-- default: accepted by user 2026-11-01 -->

Editing the title does not rename either file. <!-- default: accepted by user 2026-11-01 -->

Sidecar fields:

- `title`: string, same as the library title.
- `started_at`: ISO 8601 timestamp with timezone, required.
- `duration_seconds`: integer, the recorded seconds rounded down, required.
- Time fields: `start_seconds` is a number with 3 decimal places (milliseconds). `time_seconds` is an integer, whole seconds rounded down.
- `spoken_language`: ISO 639-1 two-letter lowercase code, required (e.g. `es`). <!-- default: accepted by user 2026-11-01 -->
- `segments`: list of transcript segments, each with `start_seconds`, `original_text`, `english_text`. Empty array when `status` is `failed`. <!-- default: accepted by user 2026-11-01 -->
- `descriptions`: list of screen descriptions, each with `time_seconds` and `description`. Empty array when `status` is `failed`. <!-- default: accepted by user 2026-11-01 -->
- `status`: `ready` or `failed`, required. Set when processing ends: `failed` if faster-whisper, any Claude API call, or writing the sidecar returns an error; otherwise `ready`. If the sidecar write itself fails, the sidecar is not written, and `failed` is shown in the Recording library for the current session only. <!-- default: accepted by user 2026-11-01 -->
