import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from classroom_lite.meals import get_meal, next_school_date
from classroom_lite.neis import NeisError, search_schools
from classroom_lite.settings_store import DEFAULT_SETTINGS
from classroom_lite.timetable import get_timetable


def settings():
    value = {
        **DEFAULT_SETTINGS,
        "classroom_name": "2-1",
        "neis": {
            **DEFAULT_SETTINGS["neis"],
            "api_key": "key",
            "office_code": "N10",
            "school_code": "123",
            "school_kind": "고등학교",
            "grade": "2",
            "class_name": "1",
        },
        "week_subjects": {
            day: [f"{day}{i}" for i in range(1, 8)]
            for day in ("월", "화", "수", "목", "금")
        },
    }
    return value


class NeisTests(unittest.TestCase):
    def test_weekend_uses_next_monday(self):
        self.assertEqual(next_school_date(date(2026, 9, 19)), date(2026, 9, 21))

    @patch("classroom_lite.neis._fetch")
    def test_meal_is_cached_by_date(self, fetch):
        fetch.return_value = {
            "mealServiceDietInfo": [
                {},
                {
                    "row": [
                        {
                            "MMEAL_SC_NM": "중식",
                            "DDISH_NM": "밥(1.2)<br/>국(5.6)",
                            "CAL_INFO": "700 Kcal",
                        }
                    ]
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            first = get_meal(settings(), cache, date(2026, 9, 16))
            second = get_meal(settings(), cache, date(2026, 9, 16))
            self.assertEqual(first["items"], ["밥", "국"])
            self.assertTrue(second["cached"])
            self.assertEqual(fetch.call_count, 1)

    @patch("classroom_lite.neis._fetch")
    def test_timetable_precedence_override_then_neis(self, fetch):
        current = settings()
        current["date_overrides"] = {"2026-09-16": ["보정"] * 7}
        with tempfile.TemporaryDirectory() as directory:
            result = get_timetable(
                current, Path(directory), date(2026, 9, 16)
            )
            self.assertEqual(result["source"], "override")
            self.assertEqual(result["entries"][0]["subject"], "보정")
            fetch.assert_not_called()

        current["date_overrides"] = {}
        fetch.return_value = {
            "hisTimetable": [
                {},
                {"row": [{"PERIO": "1", "ITRT_CNTNT": "수학"}]},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            result = get_timetable(
                current, Path(directory), date(2026, 9, 16)
            )
            self.assertEqual(result["source"], "neis")
            self.assertEqual(result["entries"][0]["subject"], "수학")

    @patch("classroom_lite.neis._fetch")
    def test_timetable_displays_elective_markers_as_selection(self, fetch):
        fetch.return_value = {
            "hisTimetable": [
                {},
                {
                    "row": [
                        {"PERIO": "1", "ITRT_CNTNT": "--"},
                        {"PERIO": "3", "ITRT_CNTNT": "미적분Ⅰ"},
                    ]
                },
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            result = get_timetable(
                settings(), Path(directory), date(2026, 9, 16)
            )
        self.assertEqual(result["entries"][0]["subject"], "선택")
        self.assertEqual(result["entries"][1]["subject"], "선택")
        self.assertEqual(result["entries"][2]["subject"], "미적분Ⅰ")
        self.assertEqual(result["entries"][3]["subject"], "")

    @patch("classroom_lite.neis._fetch")
    def test_school_search_maps_codes(self, fetch):
        fetch.return_value = {
            "schoolInfo": [
                {},
                {
                    "row": [
                        {
                            "SCHUL_NM": "테스트고",
                            "SCHUL_KND_SC_NM": "고등학교",
                            "ORG_RDNMA": "테스트로 1",
                            "ATPT_OFCDC_SC_NM": "테스트교육청",
                            "ATPT_OFCDC_SC_CODE": "T10",
                            "SD_SCHUL_CODE": "123",
                        }
                    ]
                },
            ]
        }
        result = search_schools("key", "테스트")
        self.assertEqual(result[0]["office_code"], "T10")
        self.assertEqual(result[0]["school_code"], "123")

    @patch("classroom_lite.neis._fetch")
    def test_meal_uses_recent_cache_on_network_error(self, fetch):
        fetch.return_value = {
            "mealServiceDietInfo": [
                {},
                {"row": [{"MMEAL_SC_NM": "중식", "DDISH_NM": "밥"}]},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            get_meal(settings(), cache, date(2026, 9, 15))
            fetch.side_effect = NeisError("offline")
            result = get_meal(settings(), cache, date(2026, 9, 16))
            self.assertTrue(result["stale"])
            self.assertEqual(result["items"], ["밥"])


if __name__ == "__main__":
    unittest.main()
