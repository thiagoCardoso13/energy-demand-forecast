from datetime import date

import numpy as np
import pandas as pd
import pytest

from forecast import ree, weather
from forecast.ingest import update_demand, update_temperature


def answer(start: date, end: date, value: float = 100.0) -> dict:
    stamps = pd.date_range(start, periods=((end - start).days + 1) * 288, freq="5min", tz="UTC")
    values = [{"datetime": t.isoformat(), "value": value} for t in stamps]
    return {"included": [{"type": "Real", "attributes": {"values": values}}]}


def test_month_ranges_split_on_calendar_months():
    assert ree.month_ranges(date(2025, 12, 20), date(2026, 2, 3)) == [
        (date(2025, 12, 20), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 3)),
    ]


def test_missing_series_is_an_error():
    with pytest.raises(ValueError):
        ree.parse_series({"included": []})


def test_only_settled_whole_months_are_cached(tmp_path):
    calls = []

    def get(url):
        calls.append(url)
        return {"included": []}

    today = date(2026, 3, 3)
    for _ in range(2):
        ree.fetch_month(date(2026, 1, 1), date(2026, 1, 31), today, tmp_path, get)  # settled
        ree.fetch_month(date(2026, 2, 1), date(2026, 2, 28), today, tmp_path, get)  # too recent
    assert len(calls) == 3
    assert [p.name for p in tmp_path.iterdir()] == ["2026-01.json"]


def test_second_run_only_downloads_recent_days(tmp_path, monkeypatch):
    monkeypatch.setattr("forecast.ingest.DEMAND_START", date(2026, 1, 1))
    asked = []

    def fetch(start, end, today, cache_dir):
        asked.append((start, end))
        return answer(start, end)

    path = tmp_path / "demand.parquet"
    first = update_demand(path, date(2026, 2, 10), fetch=fetch)
    asked.clear()
    second = update_demand(path, date(2026, 2, 10), fetch=fetch)
    assert asked == [(date(2026, 2, 4), date(2026, 2, 10))]
    pd.testing.assert_frame_equal(first, second, check_freq=False)


def test_a_failed_download_keeps_the_stored_file(tmp_path, monkeypatch):
    monkeypatch.setattr("forecast.ingest.DEMAND_START", date(2026, 1, 1))
    path = tmp_path / "demand.parquet"
    update_demand(path, date(2026, 1, 3), fetch=lambda s, e, t, c: answer(s, e))
    before = path.read_bytes()

    def broken(*args):
        raise TimeoutError

    with pytest.raises(TimeoutError):
        update_demand(path, date(2026, 1, 5), fetch=broken)
    assert path.read_bytes() == before


def test_temperature_is_weighted_and_needs_every_city():
    index = pd.date_range("2026-01-01", periods=2, freq="1h", tz="UTC")
    cities = pd.DataFrame({"madrid": [10.0, 10.0], "barcelona": [20.0, np.nan]}, index=index)
    result = weather.weighted_temperature(cities)
    assert result.iloc[0] == pytest.approx((10 * 6.8 + 20 * 5.0) / 11.8)
    assert np.isnan(result.iloc[1])


def test_temperature_asks_for_the_two_day_ahead_forecast():
    urls = []

    def get(url):
        urls.append(url)
        return {"hourly": {"time": ["2026-01-01T00:00"], weather.VARIABLE: [None]}}

    result = weather.fetch_temperature(date(2026, 1, 1), date(2026, 1, 1), get=get, pause=0)
    assert len(urls) == len(weather.CITIES)
    assert all("temperature_2m_previous_day2" in url for url in urls)
    assert result.isna().all()


def test_temperature_file_drops_the_empty_tail(tmp_path):
    def fetch(first, last):
        index = pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC")
        return pd.Series([1.0, 2.0, np.nan], index=index, name="temperature_c")

    stored = update_temperature(tmp_path / "t.parquet", date(2026, 1, 1), fetch=fetch)
    assert len(stored) == 2
