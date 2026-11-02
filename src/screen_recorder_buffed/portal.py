"""Desktop portal client over D-Bus (jeepney): ScreenCast and GlobalShortcuts.

A portal call returns a Request object at once, and its result arrives later as a
Response signal. To avoid missing it, we subscribe to the expected Request path
before making the call. Each operation opens its own D-Bus connection, so work
can run on a background thread without sharing a connection.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from jeepney import DBusAddress, MatchRule, MessageType, message_bus, new_method_call
from jeepney.fds import FileDescriptor
from jeepney.io.blocking import open_dbus_connection

PORTAL_SERVICE = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
SHORTCUTS_IFACE = "org.freedesktop.portal.GlobalShortcuts"

RESPONSE_TIMEOUT_S = 120.0  # the user may take time in the picker
SHORTCUT_ID = "toggle-recording"
SHORTCUT_TRIGGER = "CTRL+SHIFT+r"
SHORTCUT_DESCRIPTION = "Start or stop recording"


class PortalError(Exception):
    """A portal call failed, was cancelled, or timed out."""


@dataclass
class ScreenStream:
    node_id: int
    fd: int  # PipeWire remote file descriptor, owned by the caller
    # The portal session lives on the client's connection, so keep the client
    # open until the recording ends (see close()).
    client: PortalClient | None = None

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None


def _unwrap(value: Any) -> Any:
    """Turn a D-Bus variant (sig, value) into its plain value."""
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return value[1]
    return value


def _unwrap_map(values: dict) -> dict:
    return {key: _unwrap(value) for key, value in values.items()}


def _address(path: str, iface: str) -> DBusAddress:
    return DBusAddress(path, bus_name=PORTAL_SERVICE, interface=iface)


class PortalClient:
    """Blocking portal calls. Use one instance per thread."""

    def __init__(self) -> None:
        self.conn = open_dbus_connection(bus="SESSION", enable_fds=True)
        self._activation_subscribed = False
        # The sender name as the portal writes it into request paths.
        self._sender = self.conn.unique_name.lstrip(":").replace(".", "_")

    def close(self) -> None:
        self.conn.close()

    # --- Request/response --------------------------------------------------

    def _request(self, iface: str, method: str, signature: str, body: tuple) -> dict:
        """Call a portal method, wait for its Response, return the results map.

        `body` must already contain the options dict with a 'handle_token' entry
        equal to the token used to predict the Request path, so the caller builds
        it through `_options`.
        """
        token = body[-1]["handle_token"][1]
        request_path = f"{PORTAL_PATH}/request/{self._sender}/{token}"

        self.conn.send_and_get_reply(message_bus.AddMatch(
            MatchRule(type="signal", interface=REQUEST_IFACE, member="Response", path=request_path)
        ))
        reply = self._send(new_method_call(_address(PORTAL_PATH, iface), method, signature, body))
        if reply.body and str(reply.body[0]) != request_path:
            # The portal may pick its own path; subscribe to it too.
            self.conn.send_and_get_reply(message_bus.AddMatch(
                MatchRule(type="signal", interface=REQUEST_IFACE, member="Response",
                          path=str(reply.body[0]))
            ))
            request_path = str(reply.body[0])

        return self._wait_response(request_path)

    def _send(self, message):
        """Send a method call and return its reply. An error reply raises PortalError."""
        reply = self.conn.send_and_get_reply(message)
        if reply.header.message_type == MessageType.error:
            raise PortalError(str(reply.body[0]) if reply.body else "The desktop refused the request")
        return reply

    def _wait_response(self, request_path: str) -> dict:
        deadline = time.monotonic() + RESPONSE_TIMEOUT_S
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PortalError("The desktop did not answer in time")
            try:
                message = self.conn.receive(timeout=remaining)
            except TimeoutError as error:
                raise PortalError("The desktop did not answer in time") from error
            header = message.header
            if header.fields.get(3) == "Response" and header.fields.get(1) == request_path:
                code, results = message.body
                if code == 1:
                    raise PortalError("cancelled")
                if code != 0:
                    raise PortalError("The desktop refused the request")
                return _unwrap_map(results)

    @staticmethod
    def _options(extra: dict[str, tuple[str, Any]]) -> dict:
        token = "srb_" + uuid.uuid4().hex[:12]
        options = {"handle_token": ("s", token)}
        options.update(extra)
        return options

    # --- ScreenCast --------------------------------------------------------

    def screen_stream(self) -> ScreenStream:
        """Ask the desktop for one monitor. This shows the desktop's picker.

        Returns the PipeWire node to record and the PipeWire remote fd.
        """
        created = self._request(SCREENCAST_IFACE, "CreateSession", "a{sv}", (self._options({
            "session_handle_token": ("s", "srb_session_" + uuid.uuid4().hex[:8]),
        }),))
        session = str(created["session_handle"])

        self._request(SCREENCAST_IFACE, "SelectSources", "oa{sv}", (session, self._options({
            "types": ("u", 1),          # 1 = monitor
            "multiple": ("b", False),
            "cursor_mode": ("u", 2),    # 2 = cursor embedded in the video
        })))

        started = self._request(SCREENCAST_IFACE, "Start", "osa{sv}", (session, "", self._options({})))
        streams = started.get("streams") or []
        if not streams:
            raise PortalError("No monitor was selected")
        node_id = int(streams[0][0])
        return ScreenStream(node_id=node_id, fd=self._open_pipewire_remote(session), client=self)

    def _open_pipewire_remote(self, session: str) -> int:
        reply = self._send(new_method_call(
            _address(PORTAL_PATH, SCREENCAST_IFACE), "OpenPipeWireRemote", "oa{sv}", (session, {})
        ))
        # jeepney wraps the received descriptor; to_raw_fd() hands over the integer and ownership.
        received = reply.body[0]
        return received.to_raw_fd() if isinstance(received, FileDescriptor) else int(received)

    # --- GlobalShortcuts ---------------------------------------------------

    def bind_toggle_shortcut(self) -> str:
        """Register Ctrl+Shift+R with the desktop. Returns the session handle.

        The desktop may ask the user to confirm the binding the first time.
        Raises PortalError if the desktop has no GlobalShortcuts portal.
        """
        created = self._request(SHORTCUTS_IFACE, "CreateSession", "a{sv}", (self._options({
            "session_handle_token": ("s", "srb_shortcuts_" + uuid.uuid4().hex[:8]),
        }),))
        session = str(created["session_handle"])
        self._request(SHORTCUTS_IFACE, "BindShortcuts", "oa(sa{sv})sa{sv}", (
            session,
            [(SHORTCUT_ID, {
                "description": ("s", SHORTCUT_DESCRIPTION),
                "preferred_trigger": ("s", SHORTCUT_TRIGGER),
            })],
            "",
            self._options({}),
        ))
        return session

    def wait_for_activation(self, session: str, should_stop) -> bool:
        """Block until the toggle shortcut fires for `session`. Returns False if `should_stop()` turns true.

        Call from a background thread with its own PortalClient.
        """
        if not self._activation_subscribed:
            self.conn.send_and_get_reply(message_bus.AddMatch(
                MatchRule(type="signal", interface=SHORTCUTS_IFACE, member="Activated", path=PORTAL_PATH)
            ))
            self._activation_subscribed = True
        while not should_stop():
            try:
                message = self.conn.receive(timeout=0.5)
            except TimeoutError:
                continue
            header = message.header
            if header.fields.get(3) != "Activated":
                continue
            activated_session, shortcut_id = message.body[0], message.body[1]
            if str(activated_session) == session and shortcut_id == SHORTCUT_ID:
                return True
        return False


__all__ = [
    "PortalClient",
    "PortalError",
    "ScreenStream",
    "SHORTCUT_DESCRIPTION",
    "SHORTCUT_ID",
    "SHORTCUT_TRIGGER",
]
