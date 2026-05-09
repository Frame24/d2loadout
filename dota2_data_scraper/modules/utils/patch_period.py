"""
Определение актуального "period" для D2PT API.

Логика:
- Берём последний патч из официального списка Valve (datafeed/patchnoteslist).
- Если патч вышел < threshold_days дней назад — используем period="patch"
- Иначе — period="8" (8 days)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


PATCHNOTES_LIST_URL = "https://www.dota2.com/datafeed/patchnoteslist?language=english"

# Патчи вида 7.41, 7.35c. Под это не попадают "микро-обновления" без версии.
_PATCH_RE = re.compile(r"^\d+\.\d{2}[a-z]?$", re.IGNORECASE)


@dataclass(frozen=True)
class LatestPatchInfo:
    patch_number: str
    patch_timestamp: int

    @property
    def released_at_utc(self) -> datetime:
        return datetime.fromtimestamp(self.patch_timestamp, tz=timezone.utc)


def _fetch_patchnotes_list(timeout: float = 15.0) -> dict:
    req = Request(
        PATCHNOTES_LIST_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def get_latest_named_patch(timeout: float = 15.0) -> Optional[LatestPatchInfo]:
    """
    Возвращает самый свежий патч с версией вида 7.xx / 7.xx[a-z] и timestamp.
    """
    data = _fetch_patchnotes_list(timeout=timeout)
    patches = data.get("patches", [])
    if not isinstance(patches, list) or not patches:
        return None

    best: Optional[LatestPatchInfo] = None
    for p in patches:
        if not isinstance(p, dict):
            continue
        num = p.get("patch_number")
        ts = p.get("patch_timestamp")
        if not isinstance(num, str) or not _PATCH_RE.match(num.strip()):
            continue
        if not isinstance(ts, int):
            continue
        info = LatestPatchInfo(patch_number=num.strip(), patch_timestamp=ts)
        if best is None or info.patch_timestamp > best.patch_timestamp:
            best = info
    return best


def choose_d2pt_period(
    *,
    threshold_days: int = 8,
    now_utc: Optional[datetime] = None,
    timeout: float = 15.0,
) -> tuple[str, Optional[LatestPatchInfo], Optional[int]]:
    """
    Возвращает (period, latest_patch, age_days).

    period: "patch" или "8"
    age_days: целое число дней с выхода latest_patch (UTC), либо None если не удалось определить.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    try:
        latest = get_latest_named_patch(timeout=timeout)
        if latest is None:
            return "8", None, None
        age_days = int((now_utc - latest.released_at_utc).total_seconds() // 86400)
        period = "patch" if age_days < int(threshold_days) else "8"
        return period, latest, age_days
    except Exception as e:
        logger.warning("Не удалось определить дату последнего патча: %s", e)
        return "8", None, None

