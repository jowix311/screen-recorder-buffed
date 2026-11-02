"""Ctrl+Shift+R through the desktop's GlobalShortcuts portal, on a background thread.

If the desktop refuses the binding, the window falls back to a shortcut that works
only while the app has focus (site-contract.md §2, decided 2026-11-01).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from screen_recorder_buffed.portal import PortalClient


class ShortcutListener(QThread):
    activated = Signal()
    unavailable = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        # Any failure here means "no desktop shortcut": the window falls back to the focus-only key.
        try:
            client = PortalClient()
        except Exception as error:  # noqa: BLE001 - no session bus, jeepney errors, etc.
            self.unavailable.emit(str(error))
            return
        try:
            session = client.bind_toggle_shortcut()
        except Exception as error:  # noqa: BLE001 - PortalError, or any connection failure
            self.unavailable.emit(str(error))
            client.close()
            return
        try:
            while not self._stop_requested:
                if client.wait_for_activation(session, lambda: self._stop_requested):
                    self.activated.emit()
        except Exception:  # noqa: BLE001 - the listener must not die silently
            self.unavailable.emit("The desktop shortcut stopped working")
        finally:
            client.close()
