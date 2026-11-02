# Site contract: Screen Recorder Buffed

> Status: APPROVED by the user on 2026-11-01. Colour values are placeholders until `design-standard.md` is approved. Structure, states and content come from `PRD.md` and `content-model.md`. Items marked `<!-- default: -->` were chosen by the drafter and need confirmation. Items marked `<!-- user decision -->` were chosen by the user. Colour values are proposals until `design-standard.md` is written.

This is a desktop app, so "page" means the app window. Its behaviour is the contract that the build must follow.

## 1. Window structure

The app is one window, minimum size 1024×640.

- **Left sidebar** (200 px, fixed). Lists the four screens in this order: Recording control, Recording library, Recording review, Settings. The active screen has background `#1f2a37`, a 3 px left border `#58a6ff`, and text `#ffffff`. Recording review is listed after a row is opened from Recording library, and stays listed until the app closes. Clicking a sidebar item switches the content area. Sidebar item hover: background `#1c2430`, 150 ms ease-out. <!-- default: chosen by drafter, confirm -->
- **Content area.** Shows the active screen. Scrolls vertically when its content is taller than the window.
- **Recording indicator:** a badge with the text "Recording", background `#d93025`, text `#ffffff`. Shown at the top of the content area on every screen while the state is `recording` or `stopping`. <!-- default: chosen by drafter, confirm -->

Layout by window width:
- **Recording control and Settings:** one column, left-aligned, maximum width 720 px, at all widths. <!-- default: chosen by drafter, confirm -->
- **Recording library, 1024–1279 px:** the list above the detail. **1280 px and up:** the list takes the left 40%, the detail the right 60%. <!-- default: chosen by drafter, confirm -->
- **Recording review, under 1280 px:** video, then transcript, then descriptions, stacked. **1280 px and up:** the video takes 60% of the content width; the transcript and descriptions take the remaining 40%, side by side. <!-- default: chosen by drafter, confirm -->

## 2. Recording control

### States

| State | Start/stop button | Timer | Recording indicator | Spoken language | Source |
|-------|-------------------|-------|---------------------|-----------------|--------|
| `idle` | "Start recording" (enabled only when the start conditions hold) | hidden | hidden | editable | read-only text |
| `recording` | "Stop recording" | visible, counting | visible | locked | read-only text |
| `stopping` | "Stopping…" (disabled) | visible | visible | locked | read-only text |
| `processing` | "Processing…" (disabled) | hidden | hidden | locked | read-only text |

Source is shown as the read-only text "Primary monitor" in every state. It is not a control. <!-- default: chosen by drafter, confirm -->

Transitions:
- `idle` → `recording`: Start pressed, or Ctrl+Shift+R, while the start conditions hold.
- `recording` → `stopping`: Stop pressed, Ctrl+Shift+R, or a capture error.
- `stopping` → `processing`: the MKV file is finalised.
- `processing` → `idle`: processing ends with status `ready` or `failed`.

### Start conditions

Start is enabled only when all of these hold (from `content-model.md`): a spoken language is selected, privacy acceptance is checked, a Claude API key is saved, and no recording is in Retry.

### Messages

Shown under the button, one per unmet condition, in this order:
1. Privacy unchecked: "Accept privacy in Settings to record".
2. No Claude API key: "Add a Claude API key in Settings to record".
3. No spoken language selected: "Select a spoken language to record".
4. A Retry is running: "Wait for the retry to finish before recording". <!-- default: chosen by drafter, confirm -->

Other messages:
- "No screen or system-audio source found" under the button when Start is pressed and the source is missing.
- After a capture error: "Capture stopped. The partial recording is being processed." <!-- default: chosen by drafter, confirm -->

### Global shortcut

- **Ctrl+Shift+R** toggles recording from any app. It follows the same rules as the button: it is ignored when Start is disabled, and it cannot start a recording that the conditions would block. <!-- user decision -->

## 3. Closing the window

- Closing while `idle`: the app closes at once.
- Closing while `recording`: a dialog appears with the text "Stop the recording and process it?" and the buttons "Stop" and "Cancel". "Stop" moves the state to `stopping`. "Cancel" keeps the app open and recording. <!-- user decision -->
- Closing while `stopping` or `processing`: the window stays open until processing ends. The app then stays open, showing the result, until the user closes it. <!-- user decision -->

## 4. Recording library

### States

| State | Shows |
|-------|-------|
| Loading | "Loading recordings…" in place of the list |
| Empty | "No recordings yet. Start one from Recording control." |
| Unreadable folder | "Cannot read output folder: `<path>`" and a Retry button. Retry re-reads the folder; on success it shows the list, on failure the same message and button. |
| List | One row per recording, newest first |

Each row shows title, date, duration, spoken language and status, as defined in `content-model.md`.

### Interaction

- Clicking a row with status `ready` or `failed` opens Recording review.
- Clicking a row with status `recording` or `processing` does nothing.
- Row hover: background `#1c2430`, 150 ms ease-out. Row focus: outline 2px solid `#58a6ff`, outline-offset 2px. <!-- default: chosen by drafter, confirm -->

## 5. Recording review

### States

| State | Shows |
|-------|-------|
| `ready` | Video, transcript, descriptions. "No speech detected" if there are zero segments. |
| `failed` | Failure message "Processing failed. The video is kept." and a Retry button. Transcript and descriptions hidden. |
| `processing` (during Retry) | "Processing…" in place of the failure message; Retry disabled. |
| Video missing or cannot play | "Video cannot be played: `<path>`" in place of the player. |

### Interaction

- Clicking a transcript time or description time seeks the video to that time.
- Title is edited in place. Save on Enter or when focus leaves the field. An invalid title shows the message from `content-model.md` under the field. If the sidecar rewrite fails, the title reverts to the previous value and "Title could not be saved" shows under the field. <!-- default: chosen by drafter, confirm -->
- Retry reruns the whole pipeline from the MKV. While it runs, Start is disabled.

### Decisions (user, 2026-11-02)

- Playback keeps running when the user switches to another screen. It stops when the window closes.
- A failed recording keeps showing its video above the failure message and Retry. Only the transcript and descriptions are hidden.
- At 1280 px and up, the right-hand 40% column holds the transcript above the screen descriptions.
- Clicking or pressing Enter anywhere on a transcript or description entry seeks to its time.
- Retry is disabled while the app is recording, processing or running another retry. The title is locked while a retry runs.
- If Retry cannot run, the reason shows under the button: "Accept privacy in Settings before processing", "No Claude API key saved", or "The recording's details could not be read".

## 6. Settings

Messages show inline under the field.

- **Privacy acceptance:** checkbox, unchecked by default, with the text "Screen images and transcript text are sent to Anthropic." Applies on click; it has no Save button. <!-- user decision -->
- **Claude API key:** each field has its own Save button; the value applies only after Save. Shown after saving as `sk-ant-••••` followed by the last 4 characters, e.g. `sk-ant-••••abcd`. "Replace key" opens an empty field. "Remove key" asks for confirmation, then deletes the key. <!-- default: chosen by drafter, confirm -->
- **Output folder:** Save applies the value. Invalid values show their message and keep the previous value.
- **Spoken-language default:** dropdown with the 9 languages and "None", with its own Save button.
- **Fixed values:** description interval (10 seconds) and maximum frame size (1280×720) are shown as read-only text.

## 7. Feedback and messages

- Errors and status messages appear inline, next to the control they belong to. They stay until the problem is fixed. <!-- user decision -->
- No toast notifications in version 1.
- Destructive actions (Remove key) and the stop-on-close dialog are the only modal dialogs. <!-- default: chosen by drafter, confirm -->

## 8. Keyboard and focus

- Tab moves focus through the sidebar, then the content area, in visual order.
- Enter activates the focused button. Escape cancels a dialog. <!-- default: chosen by drafter, confirm -->
- Every interactive control has a focus outline: 2px solid `#58a6ff`, outline-offset 2px. <!-- default: chosen by drafter, confirm -->

## 9. Hover and transitions

- Buttons: hover colours are defined in `design-standard.md`, section Buttons (primary and secondary). Transition 150 ms ease-out. <!-- decision 2026-11-02: design-standard.md governs button hover -->
- Sidebar items: see section 1.
- The recording indicator blinks: opacity 1 → 0.4 → 1, one full cycle every 1000 ms, linear, repeating while visible. <!-- default: chosen by drafter, confirm -->
- No other animations in version 1.
