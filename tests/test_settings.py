"""Slice 1 checks: Settings rules from content-model.md and site-contract.md §6.

Uses a fake key store, so the real OS keyring and config files are never touched.
Run with: .venv/bin/python -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from screen_recorder_buffed import languages  # noqa: E402
from screen_recorder_buffed.key_store import (  # noqa: E402
    MSG_BAD_PREFIX,
    MSG_TOO_SHORT,
    MSG_NO_STORE,
    SecureStoreUnavailable,
    mask_key,
    validate_key,
)
from screen_recorder_buffed.settings_screen import PRIVACY_TEXT, REMOVE_KEY_TEXT, SettingsScreen  # noqa: E402
from screen_recorder_buffed.settings_store import (  # noqa: E402
    MSG_FOLDER_REQUIRED,
    Settings,
    SettingsStore,
    validate_output_folder,
)

VALID_KEY = "sk-ant-api03-0123456789wxyz"  # 27 characters, ends in "wxyz"

_IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


class FakeKeyStore:
    def __init__(self, key: str | None = None, unavailable: bool = False) -> None:
        self.key = key
        self.unavailable = unavailable

    def _check(self) -> None:
        if self.unavailable:
            raise SecureStoreUnavailable(MSG_NO_STORE)

    def get_key(self) -> str | None:
        self._check()
        return self.key

    def set_key(self, key: str) -> None:
        self._check()
        self.key = key

    def delete_key(self) -> None:
        self._check()
        self.key = None


class SettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "config" / "settings.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_gives_defaults(self) -> None:
        settings = SettingsStore(self.path).load()
        self.assertEqual(settings, Settings())
        self.assertFalse(settings.privacy_accepted)
        self.assertEqual(settings.output_folder, "~/Videos/ScreenRecorderBuffed/")
        self.assertIsNone(settings.default_language)

    def test_save_and_load_round_trip(self) -> None:
        store = SettingsStore(self.path)
        store.save(Settings(privacy_accepted=True, output_folder="/tmp/x", default_language="es"))
        loaded = SettingsStore(self.path).load()
        self.assertTrue(loaded.privacy_accepted)
        self.assertEqual(loaded.output_folder, "/tmp/x")
        self.assertEqual(loaded.default_language, "es")

    def test_corrupt_file_gives_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(SettingsStore(self.path).load(), Settings())

    def test_unknown_language_becomes_none(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"default_language": "xx"}), encoding="utf-8")
        self.assertIsNone(SettingsStore(self.path).load().default_language)

    def test_saved_file_contains_no_api_key(self) -> None:
        SettingsStore(self.path).save(Settings(privacy_accepted=True))
        self.assertNotIn("sk-ant", self.path.read_text(encoding="utf-8"))


class KeyringKeyStoreTests(unittest.TestCase):
    def test_silent_backend_is_reported_as_unavailable(self) -> None:
        # A backend that discards writes (like keyring's null backend) must not look like success.
        from screen_recorder_buffed.key_store import KeyringKeyStore

        with mock.patch("keyring.set_password"), mock.patch("keyring.get_password", return_value=None):
            with self.assertRaises(SecureStoreUnavailable):
                KeyringKeyStore().set_key(VALID_KEY)

    def test_successful_round_trip_is_accepted(self) -> None:
        from screen_recorder_buffed.key_store import KeyringKeyStore

        stored: dict[str, str] = {}
        with mock.patch("keyring.set_password", side_effect=lambda s, u, p: stored.update({u: p})), \
                mock.patch("keyring.get_password", side_effect=lambda s, u: stored.get(u)):
            KeyringKeyStore().set_key(VALID_KEY)
        self.assertEqual(stored.get("claude-api-key"), VALID_KEY)


class KeyRuleTests(unittest.TestCase):
    def test_key_must_start_with_prefix(self) -> None:
        self.assertEqual(validate_key("abc123"), MSG_BAD_PREFIX)
        self.assertIsNone(validate_key(VALID_KEY))
        self.assertEqual(validate_key("sk-ant-x"), MSG_TOO_SHORT)

    def test_mask_shows_prefix_and_last_four(self) -> None:
        self.assertEqual(mask_key(VALID_KEY), "sk-ant-••••wxyz")


class OutputFolderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_value_is_rejected(self) -> None:
        folder, error = validate_output_folder("   ")
        self.assertIsNone(folder)
        self.assertEqual(error, MSG_FOLDER_REQUIRED)

    def test_missing_folder_is_created(self) -> None:
        target = self.root / "new" / "recordings"
        folder, error = validate_output_folder(str(target))
        self.assertIsNone(error)
        self.assertEqual(folder, target)
        self.assertTrue(target.is_dir())

    def test_file_in_place_of_folder_is_rejected(self) -> None:
        file_path = self.root / "a-file"
        file_path.write_text("x", encoding="utf-8")
        folder, error = validate_output_folder(str(file_path))
        self.assertIsNone(folder)
        self.assertEqual(error, f"Folder is not writable: {file_path}")

    @unittest.skipIf(_IS_ROOT, "root can write to read-only folders")
    def test_read_only_folder_is_rejected(self) -> None:
        locked = self.root / "locked"
        locked.mkdir()
        locked.chmod(0o500)
        try:
            folder, error = validate_output_folder(str(locked))
            self.assertIsNone(folder)
            self.assertEqual(error, f"Folder is not writable: {locked}")
        finally:
            locked.chmod(0o700)


class SettingsScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = SettingsStore(self.root / "settings.json")
        self.keys = FakeKeyStore()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _screen(self) -> SettingsScreen:
        screen = SettingsScreen(self.store, self.keys)
        screen.show()
        return screen

    def test_privacy_checkbox_applies_on_click_and_is_saved(self) -> None:
        screen = self._screen()
        self.assertFalse(screen.privacy.isChecked())
        self.assertEqual(screen.privacy.text(), PRIVACY_TEXT)
        screen.privacy.setChecked(True)
        self.assertTrue(self.store.load().privacy_accepted)
        screen.privacy.setChecked(False)
        self.assertFalse(self.store.load().privacy_accepted)

    def test_saving_a_valid_key_stores_it_and_shows_mask(self) -> None:
        screen = self._screen()
        screen.key_input.setText(VALID_KEY)
        screen._on_save_key()
        self.assertEqual(self.keys.key, VALID_KEY)
        self.assertIn("sk-ant-••••wxyz", screen.key_status.text())
        self.assertFalse(screen.key_input.isVisible())

    def test_bad_prefix_is_rejected_and_nothing_is_stored(self) -> None:
        screen = self._screen()
        screen.key_input.setText("not-a-key")
        screen._on_save_key()
        self.assertIsNone(self.keys.key)
        self.assertEqual(screen.key_error.text(), MSG_BAD_PREFIX)
        self.assertTrue(screen.key_error.isVisible())

    def test_keyring_unavailable_shows_message(self) -> None:
        self.keys = FakeKeyStore(unavailable=True)
        screen = self._screen()
        screen.key_input.setText(VALID_KEY)
        screen._on_save_key()
        self.assertEqual(screen.key_error.text(), MSG_NO_STORE)

    def test_unavailable_store_leaves_status_empty(self) -> None:
        self.keys = FakeKeyStore(unavailable=True)
        screen = self._screen()
        self.assertEqual(screen.key_status.text(), "")
        self.assertEqual(screen.key_error.text(), MSG_NO_STORE)

    def test_remove_key_needs_confirmation(self) -> None:
        self.keys.key = VALID_KEY
        screen = self._screen()
        with mock.patch.object(SettingsScreen, "_confirm_remove", return_value=False):
            screen._on_remove_key()
        self.assertEqual(self.keys.key, VALID_KEY)
        with mock.patch.object(SettingsScreen, "_confirm_remove", return_value=True) as ask:
            screen._on_remove_key()
        self.assertIsNone(self.keys.key)
        ask.assert_called_once()

    def test_remove_dialog_text_matches_spec(self) -> None:
        self.assertEqual(
            REMOVE_KEY_TEXT,
            "Remove the Claude API key? Recording will be disabled until a new key is saved.",
        )

    def test_folder_save_persists_a_valid_value(self) -> None:
        screen = self._screen()
        target = self.root / "out"
        screen.folder_input.setText(str(target))
        screen._on_save_folder()
        self.assertEqual(self.store.load().output_folder, str(target))
        self.assertTrue(target.is_dir())

    def test_invalid_folder_keeps_previous_value(self) -> None:
        self.store.save(Settings(output_folder=str(self.root / "good")))
        screen = self._screen()
        bad = self.root / "a-file"
        bad.write_text("x", encoding="utf-8")
        screen.folder_input.setText(str(bad))
        screen._on_save_folder()
        self.assertEqual(self.store.load().output_folder, str(self.root / "good"))
        self.assertEqual(screen.folder_input.text(), str(self.root / "good"))
        self.assertIn("Folder is not writable", screen.folder_error.text())

    def test_language_default_saves_code_or_none(self) -> None:
        screen = self._screen()
        index = screen.language.findData("ko")
        screen.language.setCurrentIndex(index)
        screen._on_save_language()
        self.assertEqual(self.store.load().default_language, "ko")
        screen.language.setCurrentIndex(screen.language.findData(None))
        screen._on_save_language()
        self.assertIsNone(self.store.load().default_language)

    def test_settings_file_write_failure_shows_inline_message(self) -> None:
        # Put the settings file under a regular file, so the folder cannot be created.
        blocker = self.root / "blocker"
        blocker.write_text("x", encoding="utf-8")
        self.store = SettingsStore(blocker / "settings.json")
        screen = self._screen()
        screen.privacy.setChecked(True)
        self.assertTrue(screen.privacy_error.isVisible())
        self.assertEqual(screen.privacy_error.text(), "Settings could not be saved.")

    def test_remove_button_is_styled_destructive(self) -> None:
        screen = self._screen()
        self.assertEqual(screen.key_remove.objectName(), "destructive")

    def test_fields_have_accessible_names(self) -> None:
        screen = self._screen()
        self.assertEqual(screen.key_input.accessibleName(), "Claude API key")
        self.assertEqual(screen.folder_input.accessibleName(), "Output folder")
        self.assertEqual(screen.language.accessibleName(), "Spoken-language default")

    def test_language_list_has_none_plus_nine_languages(self) -> None:
        screen = self._screen()
        self.assertEqual(screen.language.count(), 1 + len(languages.LANGUAGES))
        self.assertEqual(screen.language.itemText(0), "None")
        self.assertEqual(screen.language.itemText(1), "English (en)")


if __name__ == "__main__":
    unittest.main()
