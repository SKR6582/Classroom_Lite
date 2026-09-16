from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from . import neis
from .cache import read_cache, write_cache


TIMETABLE_ENDPOINTS = {
    "초등학교": "elsTimetable",
    "중학교": "misTimetable",
    "고등학교": "hisTimetable",
    "특수학교": "spsTimetable",
}


def get_timetable(
    settings: dict[str, Any],
    cache_dir: Path,
    target: date | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    target = target or date.today()
    slots = settings["slots"]
    manual = _manual_subjects(settings, target)
    if target.isoformat() in settings.get("date_overrides", {}):
        return _combine_slots(slots, manual, "override")
    if settings.get("timetable_source") != "neis" or target.weekday() >= 5:
        return _combine_slots(slots, manual, "manual")

    config = settings["neis"]
    endpoint = TIMETABLE_ENDPOINTS.get(config.get("school_kind", ""))
    if not endpoint:
        return _combine_slots(slots, manual, "manual")

    ymd = target.strftime("%Y%m%d")
    identity = "-".join(
        (
            config["school_code"],
            config.get("grade") or "0",
            config.get("class_name") or "0",
            ymd,
        )
    )
    cache_file = cache_dir / f"timetable-{identity}.json"
    cached = None if refresh else read_cache(cache_file)
    try:
        if cached is None:
            params = {
                "ATPT_OFCDC_SC_CODE": config["office_code"],
                "SD_SCHUL_CODE": config["school_code"],
                "ALL_TI_YMD": ymd,
            }
            if config.get("grade"):
                params["GRADE"] = config["grade"]
            if config.get("class_name"):
                params["CLASS_NM"] = config["class_name"]
            data = neis._fetch(endpoint, config["api_key"], params)
            rows = neis._rows(data, endpoint)
            by_period = {
                int(row["PERIO"]): str(row.get("ITRT_CNTNT", "")).strip()
                for row in rows
                if str(row.get("PERIO", "")).isdigit()
            }
            cached = [by_period.get(i, "") for i in range(1, len(slots) + 1)]
            write_cache(cache_file, cached)
        if any(cached):
            return _combine_slots(slots, cached, "neis")
    except neis.NeisError:
        pass
    return _combine_slots(slots, manual, "manual")


def _manual_subjects(settings: dict[str, Any], target: date) -> list[str]:
    override = settings.get("date_overrides", {}).get(target.isoformat())
    if isinstance(override, list):
        return override
    day_names = ("월", "화", "수", "목", "금", "토", "일")
    return settings.get("week_subjects", {}).get(day_names[target.weekday()], [])


def _combine_slots(
    slots: list[dict[str, str]], subjects: list[str], source: str
) -> dict[str, Any]:
    return {
        "entries": [
            {
                **slot,
                "subject": subjects[index] if index < len(subjects) else "",
            }
            for index, slot in enumerate(slots)
        ],
        "source": source,
    }
