from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_SLOTS = [
    {"label": f"{period}교시", "start": start, "end": end}
    for period, start, end in [
        (1, "08:45", "09:35"),
        (2, "09:45", "10:35"),
        (3, "10:45", "11:35"),
        (4, "12:35", "13:25"),
        (5, "13:35", "14:25"),
        (6, "14:35", "15:25"),
        (7, "15:35", "16:25"),
    ]
]
WEEKDAYS = ("월", "화", "수", "목", "금")
FONT_SCALE_KEYS = ("clock", "status", "notice", "meal", "timetable")
DEFAULT_FONT_SCALES = {key: 100 for key in FONT_SCALE_KEYS}
DEFAULT_HELP_URL = (
    "https://app.notion.com/p/"
    "Classroom-TV-Lite-3dd54b03965e8047b272df3015806757?source=copy_link"
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "version": 1,
    "classroom_name": "",
    "notice": "",
    "help_url": DEFAULT_HELP_URL,
    "timetable_source": "neis",
    "display": {"font_scales": DEFAULT_FONT_SCALES},
    "neis": {
        "api_key": "",
        "office_code": "",
        "school_code": "",
        "school_name": "",
        "school_kind": "",
        "grade": "",
        "class_name": "",
    },
    "slots": DEFAULT_SLOTS,
    "week_subjects": {day: [""] * 7 for day in WEEKDAYS},
    "date_overrides": {},
}


class SettingsError(ValueError):
    pass


def _valid_time(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return False
    try:
        hour, minute = map(int, value.split(":"))
    except ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _clean_optional_url(value: Any) -> str:
    cleaned = _clean_text(value, 500)
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SettingsError("Notion 주소는 http:// 또는 https://로 시작해야 합니다.")
    return cleaned


def _font_scales(payload: dict[str, Any]) -> dict[str, int]:
    display = payload.get("display") or {}
    if not isinstance(display, dict):
        raise SettingsError("화면 설정 형식이 올바르지 않습니다.")
    scales = display.get("font_scales") or {}
    if not isinstance(scales, dict):
        raise SettingsError("글씨 크기 설정 형식이 올바르지 않습니다.")

    result: dict[str, int] = {}
    for key in FONT_SCALE_KEYS:
        try:
            value = int(scales.get(key, 100))
        except (TypeError, ValueError):
            raise SettingsError("글씨 크기는 숫자로 입력하세요.") from None
        if value < 75 or value > 150:
            raise SettingsError("글씨 크기는 75%에서 150% 사이로 설정하세요.")
        result[key] = value
    return result


def public_settings(settings: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(settings)
    neis = result["neis"]
    neis["api_key"] = ""
    neis["api_key_configured"] = bool(settings["neis"].get("api_key"))
    return result


def validate_settings(
    payload: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SettingsError("설정 형식이 올바르지 않습니다.")

    current = deepcopy(existing or DEFAULT_SETTINGS)
    neis_input = payload.get("neis") or {}
    if not isinstance(neis_input, dict):
        raise SettingsError("NEIS 설정 형식이 올바르지 않습니다.")

    previous_key = current["neis"].get("api_key", "")
    submitted_key = _clean_text(neis_input.get("api_key"), 200)
    neis = {
        "api_key": submitted_key or previous_key,
        "office_code": _clean_text(neis_input.get("office_code"), 20),
        "school_code": _clean_text(neis_input.get("school_code"), 20),
        "school_name": _clean_text(neis_input.get("school_name"), 100),
        "school_kind": _clean_text(neis_input.get("school_kind"), 20),
        "grade": _clean_text(neis_input.get("grade"), 10),
        "class_name": _clean_text(neis_input.get("class_name"), 20),
    }

    source = payload.get("timetable_source", "neis")
    if source not in {"neis", "manual"}:
        raise SettingsError("시간표 방식이 올바르지 않습니다.")

    slots_input = payload.get("slots")
    if not isinstance(slots_input, list) or not 1 <= len(slots_input) <= 12:
        raise SettingsError("교시는 1개 이상 12개 이하로 입력하세요.")
    slots: list[dict[str, str]] = []
    previous_end = -1
    for index, raw in enumerate(slots_input, 1):
        if not isinstance(raw, dict):
            raise SettingsError(f"{index}교시 형식이 올바르지 않습니다.")
        start = _clean_text(raw.get("start"), 5)
        end = _clean_text(raw.get("end"), 5)
        if not _valid_time(start) or not _valid_time(end):
            raise SettingsError(f"{index}교시 시각을 HH:mm 형식으로 입력하세요.")
        start_min = int(start[:2]) * 60 + int(start[3:])
        end_min = int(end[:2]) * 60 + int(end[3:])
        if start_min >= end_min or start_min < previous_end:
            raise SettingsError("교시 시각은 겹치지 않게 순서대로 입력하세요.")
        previous_end = end_min
        slots.append(
            {
                "label": _clean_text(raw.get("label"), 20) or f"{index}교시",
                "start": start,
                "end": end,
            }
        )

    week_input = payload.get("week_subjects") or {}
    if not isinstance(week_input, dict):
        raise SettingsError("주간 시간표 형식이 올바르지 않습니다.")
    week_subjects: dict[str, list[str]] = {}
    for day in WEEKDAYS:
        subjects = week_input.get(day, [])
        if not isinstance(subjects, list):
            raise SettingsError(f"{day}요일 시간표 형식이 올바르지 않습니다.")
        week_subjects[day] = [
            _clean_text(subjects[i] if i < len(subjects) else "", 50)
            for i in range(len(slots))
        ]

    overrides_input = payload.get("date_overrides") or {}
    if not isinstance(overrides_input, dict):
        raise SettingsError("날짜별 시간표 형식이 올바르지 않습니다.")
    date_overrides: dict[str, list[str]] = {}
    for date_key, subjects in list(overrides_input.items())[-60:]:
        if (
            isinstance(date_key, str)
            and len(date_key) == 10
            and isinstance(subjects, list)
        ):
            date_overrides[date_key] = [
                _clean_text(subjects[i] if i < len(subjects) else "", 50)
                for i in range(len(slots))
            ]

    result = {
        "version": 1,
        "classroom_name": _clean_text(payload.get("classroom_name"), 60),
        "notice": _clean_text(payload.get("notice"), 240),
        "help_url": _clean_optional_url(payload.get("help_url")),
        "timetable_source": source,
        "display": {"font_scales": _font_scales(payload)},
        "neis": neis,
        "slots": slots,
        "week_subjects": week_subjects,
        "date_overrides": date_overrides,
    }
    return result


class SettingsStore:
    def __init__(self, data_dir: str | Path | None = None):
        configured = data_dir or os.environ.get("CLASSROOM_DATA_DIR")
        self.data_dir = (
            Path(configured).expanduser()
            if configured
            else Path.home() / ".classroom-tv-lite"
        )
        self.path = self.data_dir / "settings.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return deepcopy(DEFAULT_SETTINGS)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return validate_settings(raw)
        except (OSError, json.JSONDecodeError, SettingsError):
            return deepcopy(DEFAULT_SETTINGS)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load()
        settings = validate_settings(payload, current)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=".settings-", suffix=".json", dir=self.data_dir
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(settings, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return settings

    def is_configured(self) -> bool:
        settings = self.load()
        neis = settings["neis"]
        return all(
            (
                neis.get("api_key"),
                neis.get("office_code"),
                neis.get("school_code"),
                settings.get("classroom_name"),
            )
        )
