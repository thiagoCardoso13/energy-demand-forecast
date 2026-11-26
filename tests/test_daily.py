from datetime import date

import numpy as np
import pandas as pd
import pytest

from forecast.daily import forecast_day, live_summary, read_predictions, run
from forecast.models import SeasonalNaive

INDEX = pd.date_range("2026-01-01", "2026-03-01", freq="1h", tz="UTC")
DEMAND = pd.DataFrame({"demand_mw": np.linspace(20_000, 30_000, len(INDEX))}, index=INDEX)
TEMPERATURE = pd.DataFrame({"temperature_c": 12.0}, index=INDEX)


def at(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def data_until(moment: str):
    return lambda today: (DEMAND[DEMAND.index < at(moment)], TEMPERATURE)


def daily(tmp_path, now: str, known: str | None = None) -> str:
    return run(tmp_path, at(now), model=SeasonalNaive(), update=data_until(known or now))


def test_a_run_records_the_24_hours_of_tomorrow(tmp_path):
    daily(tmp_path, "2026-02-10 09:30")
    table = read_predictions(tmp_path / "predictions.csv")
    assert len(table) == 24
    assert set(table["target_day"]) == {"2026-02-11"}
    assert table["actual_mw"].isna().all()


def test_the_first_forecast_stands_and_actuals_are_filled_later(tmp_path):
    daily(tmp_path, "2026-02-10 09:30")
    first = read_predictions(tmp_path / "predictions.csv")
    assert "already" in daily(tmp_path, "2026-02-10 12:00")
    daily(tmp_path, "2026-02-12 09:30")
    table = read_predictions(tmp_path / "predictions.csv")
    old = table[table["target_day"] == "2026-02-11"].reset_index(drop=True)
    assert old["predicted_mw"].tolist() == first["predicted_mw"].tolist()
    assert old["made_at_utc"].tolist() == first["made_at_utc"].tolist()
    assert old["actual_mw"].notna().all()
    assert live_summary(table)["model"]["hours"] == 24


def test_data_after_issue_time_does_not_change_the_forecast():
    day = date(2026, 2, 11)
    changed = DEMAND["demand_mw"].copy()
    changed[changed.index >= at("2026-02-10 09:00")] = -1e9
    results = [
        forecast_day(
            demand, TEMPERATURE["temperature_c"], day, at("2026-02-10 20:00"), SeasonalNaive()
        )
        for demand in (DEMAND["demand_mw"], changed)
    ]
    pd.testing.assert_frame_equal(*results)


def test_refuses_to_forecast_before_issue_time(tmp_path):
    with pytest.raises(ValueError, match="too early"):
        daily(tmp_path, "2026-02-10 08:00")
    assert not (tmp_path / "predictions.csv").exists()


def test_stale_data_fails_but_keeps_what_was_recorded(tmp_path):
    daily(tmp_path, "2026-02-10 09:30")
    with pytest.raises(ValueError, match="stale"):
        daily(tmp_path, "2026-02-13 09:30", known="2026-02-12 00:00")
    table = read_predictions(tmp_path / "predictions.csv")
    assert set(table["target_day"]) == {"2026-02-11"}
    assert table["actual_mw"].notna().all()


def test_late_forecasts_are_left_out_of_the_live_error():
    row = {"actual_mw": 100.0, "predicted_mw": 90.0, "baseline_mw": 80.0}
    table = pd.DataFrame(
        [
            row | {"target_day": "2026-02-11", "made_at_utc": "2026-02-10T09:30:00+00:00"},
            # 23:30 UTC is already the target day in Madrid.
            row | {"target_day": "2026-02-11", "made_at_utc": "2026-02-10T23:30:00+00:00"},
        ]
    )
    assert live_summary(table)["model"]["hours"] == 1
