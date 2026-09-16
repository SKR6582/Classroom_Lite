from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


NEIS_BASE = "https://open.neis.go.kr/hub"


class NeisError(RuntimeError):
    pass


def _fetch(endpoint: str, api_key: str, params: dict[str, str]) -> dict[str, Any]:
    query = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": "1",
        "pSize": "100",
        **params,
    }
    url = f"{NEIS_BASE}/{endpoint}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "Classroom-TV-Lite/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise NeisError("NEIS 서버에 연결하지 못했습니다.") from exc


def _rows(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    block = data.get(key)
    if isinstance(block, list):
        for item in block:
            if isinstance(item, dict) and isinstance(item.get("row"), list):
                return item["row"]
    result = data.get("RESULT")
    if isinstance(result, dict):
        code = result.get("CODE")
        if code == "INFO-200":
            return []
        message = result.get("MESSAGE") or "NEIS 요청에 실패했습니다."
        raise NeisError(str(message))
    return []


def search_schools(api_key: str, name: str) -> list[dict[str, str]]:
    if len(name.strip()) < 2:
        raise NeisError("학교명을 두 글자 이상 입력하세요.")
    data = _fetch("schoolInfo", api_key, {"SCHUL_NM": name.strip()})
    rows = _rows(data, "schoolInfo")
    return [
        {
            "school_name": str(row.get("SCHUL_NM", "")),
            "school_kind": str(row.get("SCHUL_KND_SC_NM", "")),
            "address": str(row.get("ORG_RDNMA", "")),
            "office_name": str(row.get("ATPT_OFCDC_SC_NM", "")),
            "office_code": str(row.get("ATPT_OFCDC_SC_CODE", "")),
            "school_code": str(row.get("SD_SCHUL_CODE", "")),
        }
        for row in rows[:20]
    ]
