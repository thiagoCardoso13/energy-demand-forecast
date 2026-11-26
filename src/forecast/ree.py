"""Download 5-minute demand from the Red Eléctrica REData API."""

import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from forecast.http import get_json

URL = (
    "https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real"
    "?start_date={}T00:00&end_date={}T23:59&time_trunc=hour"
)
SETTLE_DAYS = 7  # a month is cached only once it has been over for this long


def month_ranges(first: date, last: date) -> list[tuple[date, date]]:
    """Split [first, last] into calendar-month pieces."""
    ranges = []
    start = first
    while start <= last:
        next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
        ranges.append((start, min(next_month - timedelta(days=1), last)))
        start = next_month
    return ranges


def fetch_month(
    start: date,
    end: date,
    today: date,
    cache_dir: Path | None = None,
    get: Callable[[str], dict] = get_json,
) -> dict:
    """Return the raw API answer for one month piece, using the cache for settled months."""
    month_is_whole = start.day == 1 and (end + timedelta(days=1)).day == 1
    settled = month_is_whole and (today - end).days > SETTLE_DAYS
    path = cache_dir / f"{start:%Y-%m}.json" if cache_dir and settled else None
    if path and path.exists():
        return json.loads(path.read_text())
    data = get(URL.format(start, end))
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    return data


def parse_series(data: dict, name: str = "Real") -> pd.Series:
    """Turn one series of an API answer into values indexed by UTC timestamp."""
    series = next((s for s in data["included"] if s["type"] == name), None)
    if series is None:
        raise ValueError(f"series {name!r} is not in the API answer")
    values = series["attributes"]["values"]
    index = pd.to_datetime([v["datetime"] for v in values], utc=True)
    return pd.Series([float(v["value"]) for v in values], index=index, name=name)
