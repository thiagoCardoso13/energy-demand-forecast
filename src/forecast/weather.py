"""Day-ahead temperature forecasts, as they were known at the time (Open-Meteo previous runs)."""

import time
from collections.abc import Callable
from datetime import date

import pandas as pd

from forecast.http import get_json

# Approximate metropolitan population in millions, used only as relative weights.
CITIES = {
    "madrid": (40.42, -3.70, 6.8),
    "barcelona": (41.39, 2.17, 5.0),
    "valencia": (39.47, -0.38, 1.6),
    "sevilla": (37.39, -5.99, 1.5),
    "malaga": (36.72, -4.42, 1.0),
    "bilbao": (43.26, -2.93, 1.0),
    "zaragoza": (41.65, -0.89, 0.8),
}
FIRST_DAY = date(2021, 3, 25)
VARIABLE = "temperature_2m_previous_day2"
URL = (
    "https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&start_date={start}&end_date={end}&hourly=" + VARIABLE + "&timezone=GMT"
)


def parse_city(data: dict) -> pd.Series:
    hourly = data["hourly"]
    index = pd.to_datetime(hourly["time"], utc=True)
    return pd.Series(pd.array(hourly[VARIABLE], dtype="Float64"), index=index).astype(float)


def weighted_temperature(cities: pd.DataFrame) -> pd.Series:
    """Population-weighted mean. An hour with any city missing is NaN."""
    weights = pd.Series({name: CITIES[name][2] for name in cities.columns})
    total = cities.mul(weights, axis=1).sum(axis=1, skipna=False)
    return (total / weights.sum()).rename("temperature_c")


def year_ranges(first: date, last: date) -> list[tuple[date, date]]:
    return [
        (max(first, date(year, 1, 1)), min(last, date(year, 12, 31)))
        for year in range(first.year, last.year + 1)
    ]


def fetch_temperature(
    first: date,
    last: date,
    get: Callable[[str], dict] = get_json,
    pause: float = 1.0,
) -> pd.Series:
    columns = {}
    for name, (lat, lon, _) in CITIES.items():
        pieces = []
        for start, end in year_ranges(first, last):
            pieces.append(parse_city(get(URL.format(lat=lat, lon=lon, start=start, end=end))))
            time.sleep(pause)
        columns[name] = pd.concat(pieces)
    return weighted_temperature(pd.DataFrame(columns))
