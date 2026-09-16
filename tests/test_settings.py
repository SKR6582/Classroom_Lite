import tempfile
import unittest
from pathlib import Path

from classroom_lite.settings_store import (
    DEFAULT_SETTINGS,
    SettingsError,
    SettingsStore,
    public_settings,
)


class SettingsStoreTests(unittest.TestCase):
    def test_save_preserves_existing_secret_when_blank(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(directory)
            first = {**DEFAULT_SETTINGS, "classroom_name": "2-1"}
            first["neis"] = {
                **DEFAULT_SETTINGS["neis"],
                "api_key": "secret",
                "office_code": "N10",
                "school_code": "123",
            }
            store.save(first)
            second = store.load()
            second["neis"]["api_key"] = ""
            store.save(second)
            self.assertEqual(store.load()["neis"]["api_key"], "secret")

    def test_public_settings_never_exposes_secret(self):
        settings = {**DEFAULT_SETTINGS}
        settings["neis"] = {**DEFAULT_SETTINGS["neis"], "api_key": "secret"}
        public = public_settings(settings)
        self.assertEqual(public["neis"]["api_key"], "")
        self.assertTrue(public["neis"]["api_key_configured"])

    def test_rejects_overlapping_slots(self):
        settings = {**DEFAULT_SETTINGS}
        settings["slots"] = [
            {"label": "1교시", "start": "09:00", "end": "10:00"},
            {"label": "2교시", "start": "09:50", "end": "10:40"},
        ]
        settings["week_subjects"] = {
            day: ["", ""] for day in ("월", "화", "수", "목", "금")
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SettingsError):
                SettingsStore(Path(directory)).save(settings)


if __name__ == "__main__":
    unittest.main()
