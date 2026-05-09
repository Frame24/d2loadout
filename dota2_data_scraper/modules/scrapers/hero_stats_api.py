"""
Сбор статистики героев через публичный API dota2protracker.com (без браузера).
"""

from __future__ import annotations

import json
import logging
import time
from http.cookiejar import CookieJar
from typing import Any, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pandas as pd

logger = logging.getLogger(__name__)

D2PT_HERO_STATS_URL = "https://dota2protracker.com/api/heroes/stats"

# Cloudflare: нужен полный набор заголовков как у браузера со страницы сайта.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_D2PT_ORIGIN = "https://dota2protracker.com"


def _api_request_headers() -> dict[str, str]:
    return {
        "User-Agent": _BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Referer": f"{_D2PT_ORIGIN}/meta",
        "Origin": _D2PT_ORIGIN,
    }


def _d2pt_opener_with_cookies():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def _warm_d2pt_session(opener, timeout: float) -> None:
    """Первый заход на /meta — часто нужен для cookies Cloudflare перед API."""
    req = Request(
        f"{_D2PT_ORIGIN}/meta",
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        },
    )
    with opener.open(req, timeout=timeout) as resp:
        resp.read()


def _row_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
    matches = int(entry.get("matches") or 0)
    wins = int(entry.get("wins") or 0)
    if matches > 0:
        wr = 100.0 * wins / matches
    else:
        wr = float("nan")
    d2pt = entry.get("d2pt_rating")
    try:
        d2pt_val = float(d2pt) if d2pt is not None else float("nan")
    except (TypeError, ValueError):
        d2pt_val = float("nan")
    raw_hid = entry.get("hero_id")
    try:
        hero_id_val = int(raw_hid) if raw_hid is not None else None
    except (TypeError, ValueError):
        hero_id_val = None
    return {
        "Hero": entry.get("hero_name"),
        "hero_id": hero_id_val,
        "Role": entry.get("position"),
        "Matches": matches,
        "WR": wr,
        "D2PT Rating": d2pt_val,
        "Facet": "No Facet",
    }


def _fetch_position_json(
    position_label: str,
    opener,
    *,
    mmr: int = 7000,
    order_by: str = "matches",
    min_matches: int = 20,
    period: str = "8",
    legacy: bool = False,
    timeout: float = 45.0,
) -> List[dict[str, Any]]:
    query = urlencode(
        {
            "mmr": mmr,
            "position": position_label,
            "order_by": order_by,
            "min_matches": min_matches,
            "period": period,
            "legacy": str(legacy).lower(),
        }
    )
    url = f"{D2PT_HERO_STATS_URL}?{query}"
    req = Request(url, headers=_api_request_headers())
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Ожидался JSON-массив, получено: {type(data).__name__}")
    return data


def fetch_heroes_stats_dataframe(
    *,
    mmr: int = 7000,
    order_by: str = "matches",
    min_matches: int = 20,
    period: str = "8",
    legacy: bool = False,
    timeout: float = 45.0,
) -> pd.DataFrame:
    """
    Загружает статистику для позиций pos 1 … pos 5 и возвращает один DataFrame.

    Колонки: Hero, Role, Matches, WR, D2PT Rating, Facet (No Facet).

    По умолчанию фильтры совпадают с D2PT Meta view:
    - period="8" (последние 8 дней)
    - min_matches=20
    """
    opener = _d2pt_opener_with_cookies()
    warm_timeout = min(timeout, 30.0)
    logger.info("Прогрев сессии D2PT (/meta, cookies)...")
    _warm_d2pt_session(opener, warm_timeout)
    time.sleep(0.4)

    frames: List[pd.DataFrame] = []
    for i in range(1, 6):
        if i > 1:
            time.sleep(0.35)
        label = f"pos {i}"
        logger.info("Запрос D2PT API: %s", label)
        entries = _fetch_position_json(
            label,
            opener,
            mmr=mmr,
            order_by=order_by,
            min_matches=min_matches,
            period=period,
            legacy=legacy,
            timeout=timeout,
        )
        rows = [_row_from_entry(e) for e in entries if isinstance(e, dict)]
        if rows:
            frames.append(pd.DataFrame(rows))
    if not frames:
        return pd.DataFrame(
            columns=[
                "Hero",
                "hero_id",
                "Role",
                "Matches",
                "WR",
                "D2PT Rating",
                "Facet",
            ]
        )
    df = pd.concat(frames, axis=0, ignore_index=True)
    df = df.dropna(how="all")
    return df


def fetch_heroes_stats_safe(
    **kwargs: Any,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Обёртка с перехватом сетевых ошибок. Возвращает (df, error_message).
    """
    try:
        return fetch_heroes_stats_dataframe(**kwargs), None
    except HTTPError as e:
        msg = f"HTTP {e.code} при запросе к D2PT API"
        logger.error("%s: %s", msg, e.reason)
        return pd.DataFrame(), msg
    except URLError as e:
        msg = f"Сеть / URL: {e.reason}"
        logger.error(msg)
        return pd.DataFrame(), msg
    except (json.JSONDecodeError, ValueError, OSError) as e:
        msg = str(e)
        logger.error("Ошибка разбора ответа D2PT API: %s", msg)
        return pd.DataFrame(), msg
