from datetime import date

import numpy as np
import pandas as pd
import pytest

from forecast.backtest import issue_moment, known_history, run_backtest
from forecast.evaluate import BACKTEST, FINAL_TEST
from forecast.metrics import breakdown, summarize
from forecast.models import SeasonalNaive, seasonal_naive, weeks_earlier
from forecast.timeutils import hours_of_local_day


def demand(first: str = "2026-01-01", last: str = "2026-12-01") -> pd.Series:
    index = pd.date_range(first, last, freq="1h", tz="UTC")
    return pd.Series(np.random.default_rng(0).uniform(20_000, 40_000, len(index)), index=index)


@pytest.mark.parametrize(
    ("day", "utc"),
    [(date(2026, 1, 15), "2026-01-14 09:00"), (date(2026, 7, 15), "2026-07-14 08:00")],
)
def test_forecast_is_issued_at_ten_madrid_time_the_day_before(day, utc):
    assert issue_moment(day) == pd.Timestamp(utc, tz="UTC")


def test_history_ends_with_the_last_hour_completed_at_issue_time():
    history = known_history(demand(), date(2026, 1, 15))
    assert history.index.max() == pd.Timestamp("2026-01-14 08:00", tz="UTC")


def test_baseline_repeats_the_same_local_hour_across_a_clock_change():
    # 2026-03-30 12:00 Madrid is UTC+2; one week earlier the offset was UTC+1.
    target = pd.DatetimeIndex(["2026-03-30 10:00"], tz="UTC")
    assert weeks_earlier(target, 1)[0] == pd.Timestamp("2026-03-23 11:00", tz="UTC")


def test_baseline_handles_the_skipped_and_repeated_hours():
    for day in (date(2026, 4, 5), date(2026, 11, 1), date(2026, 10, 25)):
        targets = pd.DatetimeIndex(hours_of_local_day(day))
        assert seasonal_naive(demand(), targets).notna().all()


def test_baseline_falls_back_to_two_weeks_earlier():
    history = demand()
    target = pd.DatetimeIndex(["2026-06-16 10:00"], tz="UTC")
    history[pd.Timestamp("2026-06-09 10:00", tz="UTC")] = np.nan
    expected = history[pd.Timestamp("2026-06-02 10:00", tz="UTC")]
    assert seasonal_naive(history, target).iloc[0] == expected


def test_metrics_ignore_and_count_missing_hours():
    index = pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC")
    results = pd.DataFrame(
        {"actual": [100.0, 200.0, np.nan], "predicted": [110.0, 180.0, 5.0]}, index=index
    )
    assert summarize(results) == {
        "hours": 2,
        "skipped": 1,
        "mae_mw": 15.0,
        "mape_pct": pytest.approx(10.0),
    }


def test_holiday_breakdown_uses_the_local_date():
    # 23:00 UTC on 31 December is already 1 January in Madrid.
    index = pd.DatetimeIndex(["2025-12-31 23:00", "2026-01-02 12:00"], tz="UTC")
    results = pd.DataFrame({"actual": [100.0, 100.0], "predicted": [90.0, 100.0]}, index=index)
    table = breakdown(results, "holiday")
    assert table.loc[True, "mae_mw"] == 10.0
    assert table.loc[False, "mae_mw"] == 0.0


def test_held_out_period_does_not_overlap_the_backtest():
    assert BACKTEST[1] < FINAL_TEST[0]


def test_models_are_refitted_monthly_with_only_the_data_known_then():
    class Spy(SeasonalNaive):
        def __init__(self):
            self.fitted = []

        def fit(self, history, temperature):
            self.fitted.append((history.index.max(), temperature.index.max()))

    spy = Spy()
    series = demand()
    run_backtest(series, series, spy, date(2026, 1, 30), date(2026, 3, 2))
    expected = [issue_moment(d) for d in (date(2026, 1, 30), date(2026, 2, 1), date(2026, 3, 1))]
    assert [h + pd.Timedelta(hours=1) for h, _ in spy.fitted] == expected
    assert all(t <= moment for (_, t), moment in zip(spy.fitted, expected))
