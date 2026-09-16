import tempfile
import unittest
from unittest.mock import patch

from app import _with_env_neis, create_app
from classroom_lite.settings_store import DEFAULT_SETTINGS


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {"TESTING": True, "DATA_DIR": self.temp.name}
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def test_unconfigured_dashboard_redirects_to_setup(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/setup"))

    def test_setup_page_links_to_neis_key_guide(self):
        response = self.client.get("/setup")
        self.assertEqual(response.status_code, 200)
        self.assertIn("NEIS API 키가 아직 없나요?", response.text)
        self.assertIn("암호 관리자", response.text)
        self.assertIn(
            "https://open.neis.go.kr/portal/guide/apiGuidePage.do",
            response.text,
        )

    def test_environment_neis_values_take_priority(self):
        with patch.dict(
            "os.environ",
            {
                "NEIS_API_KEY": "env-key",
                "NEIS_SCHOOL_CODE": "env-school",
                "NEIS_OFFICE_CODE": "env-office",
            },
        ):
            result = _with_env_neis(DEFAULT_SETTINGS)
        self.assertEqual(result["neis"]["api_key"], "env-key")
        self.assertEqual(result["neis"]["school_code"], "env-school")

    def test_settings_api_masks_key(self):
        payload = {**DEFAULT_SETTINGS, "classroom_name": "2-1"}
        payload["neis"] = {
            **DEFAULT_SETTINGS["neis"],
            "api_key": "secret",
            "office_code": "N10",
            "school_code": "123",
        }
        saved = self.client.post("/api/settings", json=payload)
        self.assertEqual(saved.status_code, 200)
        result = self.client.get("/api/settings").get_json()
        self.assertEqual(result["neis"]["api_key"], "")
        self.assertTrue(result["neis"]["api_key_configured"])

        safe_export = self.client.get("/api/settings/export").get_json()
        secret_export = self.client.get(
            "/api/settings/export?include_key=1"
        ).get_json()
        self.assertEqual(safe_export["neis"]["api_key"], "")
        self.assertEqual(secret_export["neis"]["api_key"], "secret")

    def test_timetable_endpoint_uses_manual_fallback(self):
        payload = {**DEFAULT_SETTINGS, "classroom_name": "2-1"}
        payload["timetable_source"] = "manual"
        payload["neis"] = {
            **DEFAULT_SETTINGS["neis"],
            "api_key": "secret",
            "office_code": "N10",
            "school_code": "123",
        }
        payload["week_subjects"] = {
            **DEFAULT_SETTINGS["week_subjects"],
            "수": ["국어"] * 7,
        }
        self.client.post("/api/settings", json=payload)
        response = self.client.get("/api/timetable?date=2026-09-16")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["entries"][0]["subject"], "국어")

    def test_notion_qr_is_disabled_without_help_url(self):
        payload = {**DEFAULT_SETTINGS, "help_url": ""}
        self.client.post("/api/settings", json=payload)
        response = self.client.get("/api/notion-qr?url=https://attacker.example")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.mimetype, "application/json")

    def test_notion_qr_returns_cached_svg_without_secrets(self):
        payload = {**DEFAULT_SETTINGS, "classroom_name": "2-1"}
        payload["help_url"] = "https://example.notion.site/classroom-guide"
        payload["neis"] = {
            **DEFAULT_SETTINGS["neis"],
            "api_key": "never-expose-this-key",
            "office_code": "N10",
            "school_code": "123",
        }
        self.client.post("/api/settings", json=payload)

        response = self.client.get(
            "/api/notion-qr?url=https://attacker.example"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/svg+xml")
        self.assertIn(b"<svg", response.data)
        self.assertNotIn(b"never-expose-this-key", response.data)
        self.assertNotIn(b"attacker.example", response.data)
        self.assertIn("private", response.headers["Cache-Control"])

        cached = self.client.get(
            "/api/notion-qr",
            headers={"If-None-Match": response.headers["ETag"]},
        )
        self.assertEqual(cached.status_code, 304)


if __name__ == "__main__":
    unittest.main()
