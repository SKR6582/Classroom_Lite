from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_cache(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))["data"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return None


def write_cache(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(
            {"saved_at": datetime.now().isoformat(timespec="seconds"), "data": data},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temp.replace(path)
