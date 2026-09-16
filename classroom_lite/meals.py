from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import neis
from .cache import read_cache, write_cache


def next_school_date(day: date) -> date:
    result = day
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def get_meal(
    settings: dict[str, Any],
    cache_dir: Path,
    target: date | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    target = next_school_date(target or date.today())
    config = settings["neis"]
    ymd = target.strftime("%Y%m%d")
    cache_file = cache_dir / f"meal-{config['school_code']}-{ymd}.json"
    if not refresh:
        cached = read_cache(cache_file)
        if cached is not None:
            return {**cached, "cached": True, "stale": False}

    try:
        data = neis._fetch(
            "mealServiceDietInfo",
            config["api_key"],
            {
                "ATPT_OFCDC_SC_CODE": config["office_code"],
                "SD_SCHUL_CODE": config["school_code"],
                "MLSV_YMD": ymd,
            },
        )
        rows = neis._rows(data, "mealServiceDietInfo")
        lunch = next(
            (row for row in rows if "중식" in str(row.get("MMEAL_SC_NM", ""))),
            None,
        )
        items: list[str] = []
        if lunch:
            for item in re.split(r"<br\s*/?>", str(lunch.get("DDISH_NM", ""))):
                cleaned = re.sub(r"\([0-9.]+\)", "", item).strip()
                if cleaned:
                    items.append(cleaned)
        result = {
            "date": target.isoformat(),
            "items": items,
            "calories": lunch.get("CAL_INFO") if lunch else None,
            "cached": False,
            "stale": False,
        }
        write_cache(cache_file, result)
        return result
    except neis.NeisError:
        stale = _latest_valid_meal(cache_dir, config["school_code"])
        if stale is not None:
            return {
                **stale,
                "cached": True,
                "stale": True,
                "warning": "네트워크 오류로 최근 저장된 급식을 표시합니다.",
            }
        raise


def _latest_valid_meal(cache_dir: Path, school_code: str) -> dict[str, Any] | None:
    for path in sorted(
        cache_dir.glob(f"meal-{school_code}-*.json"),
        key=lambda item: item.name,
        reverse=True,
    ):
        cached = read_cache(path)
        if isinstance(cached, dict) and cached.get("items"):
            return cached
    return None
