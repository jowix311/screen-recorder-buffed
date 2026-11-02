"""The Claude API key, kept in the OS keyring (libsecret). Rules: content-model.md, Settings.

The key is never written to a file, a log or a message. The UI only ever sees
the masked form from `mask_key`.
"""

from __future__ import annotations

from typing import Protocol

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE_NAME = "screen-recorder-buffed"
USERNAME = "claude-api-key"
KEY_PREFIX = "sk-ant-"

MIN_KEY_LENGTH = 20

MSG_NO_STORE = "No secure store available"
MSG_BAD_PREFIX = "API key must start with sk-ant-"
MSG_TOO_SHORT = "API key is too short"  # wording not yet in content-model.md; approve or change


class SecureStoreUnavailable(Exception):
    """Raised when no keyring backend can store the key."""


class KeyStore(Protocol):
    def get_key(self) -> str | None: ...
    def set_key(self, key: str) -> None: ...
    def delete_key(self) -> None: ...


class KeyringKeyStore:
    """KeyStore backed by the OS keyring."""

    def get_key(self) -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, USERNAME)
        except KeyringError as error:
            raise SecureStoreUnavailable(MSG_NO_STORE) from error

    def set_key(self, key: str) -> None:
        try:
            keyring.set_password(SERVICE_NAME, USERNAME, key)
            # Some backends (e.g. the null backend) discard the value silently.
            # Read it back so a failed save is never reported as saved.
            stored = keyring.get_password(SERVICE_NAME, USERNAME)
        except KeyringError as error:
            raise SecureStoreUnavailable(MSG_NO_STORE) from error
        if stored != key:
            raise SecureStoreUnavailable(MSG_NO_STORE)

    def delete_key(self) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, USERNAME)
        except PasswordDeleteError:
            pass  # nothing stored; removing it is already done
        except KeyringError as error:
            raise SecureStoreUnavailable(MSG_NO_STORE) from error


def validate_key(key: str) -> str | None:
    """Return the error message for a bad key, or None if it is acceptable."""
    if not key.startswith(KEY_PREFIX):
        return MSG_BAD_PREFIX
    if len(key) < MIN_KEY_LENGTH:
        return MSG_TOO_SHORT
    return None


def mask_key(key: str) -> str:
    """Masked form shown after saving: 'sk-ant-••••abcd' (last 4 characters)."""
    return f"{KEY_PREFIX}••••{key[-4:]}"
