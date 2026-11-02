"""Design tokens from design-standard.md, applied as a Qt stylesheet.

Qt stylesheets have no CSS custom properties, so the tokens are kept here as
values and substituted into the stylesheet. Keep these values identical to the
`:root` block in design-standard.md.
"""

from __future__ import annotations

TOKENS: dict[str, str] = {
    "color-bg-app": "#0d1117",
    "color-bg-sidebar": "#161b22",
    "color-bg-surface": "#1c2430",
    "color-bg-active": "#1f2a37",
    "color-border": "#30363d",
    "color-border-input": "#6e7681",
    "color-text": "#e6edf3",
    "color-text-muted": "#8b949e",
    "color-text-active": "#ffffff",
    "color-accent": "#58a6ff",
    "color-accent-hover": "#5199eb",
    "color-button-primary-text": "#0d1117",
    "color-recording": "#d93025",
    "color-on-recording": "#ffffff",
    "color-status-recording": "#ff7b72",
    "color-status-ready": "#3fb950",
    "color-status-processing": "#d29922",
    "color-status-failed": "#f85149",
    "color-backdrop": "rgba(0, 0, 0, 0.6)",
    "font-family": "system-ui, sans-serif",
    "text-caption": "12px",
    "text-small": "14px",
    "text-body": "16px",
    "text-title": "20px",
    "text-page": "24px",
    "space-1": "8px",
    "space-2": "16px",
    "space-3": "24px",
    "space-4": "32px",
    "space-5": "48px",
    "radius-control": "6px",
    "radius-surface": "8px",
    "shadow-dialog": "0 8px 24px rgba(0, 0, 0, 0.5)",
}

_STYLESHEET = """
QWidget {{
    background-color: {color-bg-app};
    color: {color-text};
    font-family: {font-family};
    font-size: {text-body};
}}

QListWidget#sidebar {{
    background-color: {color-bg-sidebar};
    border: none;
    padding: {space-1} 0;
}}

QListWidget#sidebar::item {{
    height: 40px;
    padding-left: {space-2};
    color: {color-text-muted};
    border-left: 3px solid transparent;
}}

QListWidget#sidebar::item:hover {{
    background-color: {color-bg-surface};
}}

QListWidget#sidebar::item:selected {{
    background-color: {color-bg-active};
    color: {color-text-active};
    border-left: 3px solid {color-accent};
}}

/* Qt has no outline or :focus-visible. Approximate the 2px accent focus ring
   with a border, shown only while the sidebar has keyboard focus.
   Qt cannot animate background-color, so the 150 ms hover transition in
   design-standard.md is not implemented; see the Qt mapping open item. */
QListWidget#sidebar:focus {{
    border: 2px solid {color-accent};
}}

QLabel#page-title {{
    font-size: {text-page};
    font-weight: 600;
    color: {color-text};
}}

QLabel#page-body {{
    font-size: {text-body};
    color: {color-text-muted};
}}

"""


def build_stylesheet() -> str:
    """Return the application stylesheet with every token substituted."""
    return _STYLESHEET.format(**TOKENS)
