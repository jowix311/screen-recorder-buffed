"""Reduced motion: read the desktop's animation setting (design-standard.md, Motion and Qt mapping).

Qt has no prefers-reduced-motion. The desktop portal's Settings interface exposes the
desktop's own switch, org.gnome.desktop.interface enable-animations, so we read that
over D-Bus with jeepney. If it cannot be read, animations stay on.
"""

from __future__ import annotations

from jeepney import DBusAddress, MessageType, new_method_call
from jeepney.io.blocking import open_dbus_connection

SETTINGS = DBusAddress(
    "/org/freedesktop/portal/desktop",
    bus_name="org.freedesktop.portal.Desktop",
    interface="org.freedesktop.portal.Settings",
)


def parse_reply(body: tuple) -> bool:
    """The portal answers with a variant, e.g. (('b', False),). Anything unexpected means on."""
    try:
        value = body[0]
        while isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
            value = value[1]  # unwrap nested variants
        return bool(value) if isinstance(value, bool) else True
    except (IndexError, TypeError):
        return True


def animations_enabled() -> bool:
    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception:  # noqa: BLE001 - no session bus: keep the default
        return True
    try:
        reply = conn.send_and_get_reply(
            new_method_call(SETTINGS, "ReadOne", "ss", ("org.gnome.desktop.interface", "enable-animations")),
            timeout=2,
        )
        if reply.header.message_type == MessageType.error:
            return True
        return parse_reply(reply.body)
    except Exception:  # noqa: BLE001 - any failure: keep the default
        return True
    finally:
        conn.close()
