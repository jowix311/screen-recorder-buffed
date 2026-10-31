# Design standard: Screen Recorder Buffed

> Status: APPROVED by the user on 2026-11-01. Every value is a CSS value and every token is a CSS custom property name. Items marked `<!-- default: -->` were chosen by the drafter and need confirmation. Items marked `<!-- user decision -->` were chosen by the user.

## Theme

Dark only in version 1. <!-- user decision -->

## Colour

Tokens go on `:root`. Contrast ratios are WCAG ratios, computed against the background each token is used on.

| Token | Value | Use | Contrast |
|-------|-------|-----|----------|
| `--color-bg-app` | `#0d1117` | window background | — |
| `--color-bg-sidebar` | `#161b22` | sidebar background | — |
| `--color-bg-surface` | `#1c2430` | row and card background; hover | — |
| `--color-bg-active` | `#1f2a37` | active sidebar item | — |
| `--color-border` | `#30363d` | dividers, card borders | — |
| `--color-border-input` | `#6e7681` | input borders, checkbox and select borders | 4.12:1 on `--color-bg-app`; 3.4:1 on `--color-bg-surface` |
| `--color-text` | `#e6edf3` | body and headings on app background | 16.0:1 on `--color-bg-app` |
| `--color-text-muted` | `#8b949e` | captions, timestamps, hints, inactive sidebar text | 6.15:1 on `--color-bg-app`; 5.1:1 on `--color-bg-surface` |
| `--color-text-active` | `#ffffff` | active sidebar text | 14.5:1 on `--color-bg-active` |
| `--color-accent` | `#58a6ff` | active sidebar border, focus outline, links, primary button background | 7.5:1 on `--color-bg-app`; 5.75:1 on `--color-bg-active` |
| `--color-accent-hover` | `#5199eb` | primary button background on hover | 6.4:1 with `--color-button-primary-text` |
| `--color-button-primary-text` | `#0d1117` | text on the primary button | 7.5:1 on `--color-accent` |
| `--color-recording` | `#d93025` | recording indicator background | — |
| `--color-on-recording` | `#ffffff` | text on the recording indicator | 4.77:1 on `--color-recording` |
| `--color-status-recording` | `#ff7b72` | status text "recording" | 7.5:1 on `--color-bg-app` |
| `--color-status-ready` | `#3fb950` | status text "ready" | 7.45:1 on `--color-bg-app` |
| `--color-status-processing` | `#d29922` | status text "processing" | 7.5:1 on `--color-bg-app` |
| `--color-status-failed` | `#f85149` | status text "failed", error messages | 5.65:1 on `--color-bg-app` |
| `--color-backdrop` | `rgba(0, 0, 0, 0.6)` | dialog backdrop | — |

Rules:
- Status is never shown by colour alone. Every status has its text label next to it.
- `--color-recording` is used only for the recording indicator.

<!-- default: palette chosen by drafter, confirm -->

## Typography

- **Family:** `--font-family: system-ui, sans-serif`. The desktop's own font. <!-- user decision -->
- **Scale:**

| Token | Size | Line height | Weight | Use |
|-------|------|-------------|--------|-----|
| `--text-caption` | 12 px | 16 px | 400 | timestamps, captions |
| `--text-small` | 14 px | 20 px | 400 | secondary labels, hints |
| `--text-body` | 16 px | 24 px | 400 | body text, row text |
| `--text-title` | 20 px | 28 px | 600 | section headings |
| `--text-page` | 24 px | 32 px | 600 | screen heading |

- **Letter spacing:** `0` everywhere.
- **Button text:** `--text-body`, weight 600.

<!-- default: type scale chosen by drafter, confirm -->

## Spacing

- **Base unit:** 8 px. <!-- user decision: comfortable density -->
- **Tokens:**

| Token | Value | Use |
|-------|-------|-----|
| `--space-1` | 8 px | gap between inline items |
| `--space-2` | 16 px | gap between form fields; content gutter; button horizontal padding |
| `--space-3` | 24 px | content area padding; column gap; dialog padding |
| `--space-4` | 32 px | gap between sections |
| `--space-5` | 48 px | minimum row height |

- **Layout:** sidebar `200px` fixed. Content area padding `--space-3`. Content maximum width `720px` on Recording control and Settings. Two-column screens use a `--space-3` gap between columns.
- **Touch and click targets:** minimum height 40 px for buttons, inputs, selects, checkboxes and sidebar items. Minimum width 40 px for icon buttons.
- **Button padding:** `8px 16px` (`--space-1 --space-2`).
- **Sidebar item height:** 40 px.
- **Recording badge padding:** `4px 8px`.

<!-- default: spacing values chosen by drafter, confirm -->

## Buttons

- **Primary** (Start recording, Save, Retry in the failed state): background `--color-accent`, text `--color-button-primary-text`, no border. Hover: background `--color-accent-hover`. Disabled: `opacity: 0.5`.
- **Secondary** (Cancel, Replace key, Retry in the library): background transparent, text `--color-text`, 1 px solid `--color-border`. Hover: background `--color-bg-surface`. Disabled: `opacity: 0.5`.
- **Destructive** (Remove key, confirmed in its dialog): same as Secondary, text `--color-status-failed`.
- **Stop recording** uses the Primary style.

<!-- default: button variants chosen by drafter, confirm -->

## Form controls

- **Inputs** (text, API key, folder path): background `--color-bg-surface`, 1 px solid `--color-border-input`, text `--color-text`, radius `--radius-control`, min-height 40 px.
- **Checkbox and select:** native controls with `accent-color: var(--color-accent)`, border `--color-border-input`, min-height 40 px.

<!-- default: form controls chosen by drafter, confirm -->

## Shape and elevation

- **Radius:** `--radius-control: 6px` for buttons, inputs and the recording badge; `--radius-surface: 8px` for rows and cards.
- **Shadow:** `--shadow-dialog: 0 8px 24px rgba(0, 0, 0, 0.5)`, used only on dialogs. No other shadows.
- **Dialogs:** width `400px`, padding `--space-3`, background `--color-bg-sidebar`, backdrop `--color-backdrop`.

<!-- default: shape and elevation chosen by drafter, confirm -->

## Texture

- **None.** No gradients, no grain, no blur, no background images. Flat colour only. <!-- user decision: dark theme, plain surfaces -->

## Focus

- **Focus ring:** on every interactive control, for keyboard focus only:

```css
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

- The stylesheet must not contain `outline: none` or `outline: 0`.

## Motion

- **Hover and focus transitions:** 150 ms, `ease-out`. Only on `background-color` and `border-color`.
- **Recording indicator blink:** `opacity` 1 → 0.4 → 1, one cycle per 1000 ms, `linear`, while visible.
- **Reduced motion:** with `@media (prefers-reduced-motion: reduce)`, the blink animation is removed and the indicator stays at `opacity: 1`.

<!-- default: motion chosen by drafter, confirm -->

## CSS custom properties (copy into the app's stylesheet)

```css
:root {
  --color-bg-app: #0d1117;
  --color-bg-sidebar: #161b22;
  --color-bg-surface: #1c2430;
  --color-bg-active: #1f2a37;
  --color-border: #30363d;
  --color-border-input: #6e7681;
  --color-text: #e6edf3;
  --color-text-muted: #8b949e;
  --color-text-active: #ffffff;
  --color-accent: #58a6ff;
  --color-accent-hover: #5199eb;
  --color-button-primary-text: #0d1117;
  --color-recording: #d93025;
  --color-on-recording: #ffffff;
  --color-status-recording: #ff7b72;
  --color-status-ready: #3fb950;
  --color-status-processing: #d29922;
  --color-status-failed: #f85149;
  --color-backdrop: rgba(0, 0, 0, 0.6);

  --font-family: system-ui, sans-serif;
  --text-caption: 12px;
  --text-small: 14px;
  --text-body: 16px;
  --text-title: 20px;
  --text-page: 24px;

  --space-1: 8px;
  --space-2: 16px;
  --space-3: 24px;
  --space-4: 32px;
  --space-5: 48px;

  --radius-control: 6px;
  --radius-surface: 8px;
  --shadow-dialog: 0 8px 24px rgba(0, 0, 0, 0.5);
}
```

## Verification

- [ ] Every line in this file passes the CSS value test: each rule names a specific value.
- [ ] Every colour pair used for text meets WCAG AA (4.5:1 for body text, 3:1 for large text and UI).
- [ ] Every status shows its text label as well as its colour.
- [ ] The focus ring is visible on every control in the sidebar, the content area and every dialog.
- [ ] The stylesheet contains no `outline: none` or `outline: 0`.
