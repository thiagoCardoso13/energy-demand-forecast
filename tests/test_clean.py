from datetime import date

import numpy as np
import pandas as pd
import pytest

from forecast.clean import merge_update, to_hourly
from forecast.timeutils import hours_of_local_day


def five_minutes(start: str, periods: int, value: float = 100.0) -> pd.Series:
    return pd.Series(value, index=pd.date_range(start, periods=periods, freq="5min", tz="UTC"))


def test_hour_is_the_mean_of_twelve_points():
    raw = five_minutes("2026-01-01 00:00", 12)
    raw.iloc[:6] = 200.0
    assert to_hourly(raw).tolist() == [150.0]


def test_incomplete_hour_and_hole_are_missing_not_interpolated():
    raw = pd.concat(
        [
            five_minutes("2026-01-01 00:00", 12),
            five_minutes("2026-01-01 01:00", 11),
            five_minutes("2026-01-01 03:00", 12),
        ]
    )
    hourly = to_hourly(raw)
    assert len(hourly) == 4
    assert hourly.isna().tolist() == [False, True, True, False]


def test_duplicated_points_do_not_complete_an_hour():
    raw = five_minutes("2026-01-01 00:00", 11)
    raw = pd.concat([raw, raw.iloc[-1:]])
    assert np.isnan(to_hourly(raw).iloc[0])


@pytest.mark.parametrize("day", [date(2026, 3, 29), date(2026, 10, 25)])
def test_daylight_saving_day_has_one_row_per_real_hour(day):
    hours = hours_of_local_day(day)
    # Same shape as the API: local timestamps carrying their own offset.
    stamps = pd.date_range(hours[0], periods=len(hours) * 12, freq="5min")
    local = [t.isoformat() for t in stamps.tz_convert("Europe/Madrid")]
    raw = pd.Series(1.0, index=pd.to_datetime(local, utc=True))
    hourly = to_hourly(raw)
    assert len(hourly) == len(hours)
    assert hourly.notna().all()


def table(start: str, values: list[float]) -> pd.DataFrame:
    index = pd.date_range(start, periods=len(values), freq="1h", tz="UTC")
    return pd.DataFrame({"demand_mw": values}, index=index)


def test_update_prefers_new_values_and_keeps_old_ones_over_holes():
    old = table("2026-01-01 00:00", [1.0, 2.0, 3.0])
    new = table("2026-01-01 01:00", [20.0, np.nan, 40.0])
    assert merge_update(old, new)["demand_mw"].tolist() == [1.0, 20.0, 3.0, 40.0]


def test_update_after_a_break_leaves_visible_missing_hours():
    merged = merge_update(table("2026-01-01 00:00", [1.0]), table("2026-01-01 03:00", [4.0]))
    assert merged["demand_mw"].isna().tolist() == [False, True, True, False]
