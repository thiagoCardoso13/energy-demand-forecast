from datetime import date

import numpy as np
import pandas as pd
import pytest

from forecast.backtest import issue_moment, run_backtest
from forecast.evaluate import MODELS
from forecast.features import BLACKOUT, build_features, without_blackout
from forecast.timeutils import MADRID, hours_of_local_day


def series(low: float, high: float, seed: int) -> pd.Series:
    index = pd.date_range("2021-03-25", "2021-08-01", freq="1h", tz="UTC")
    return pd.Series(np.random.default_rng(seed).uniform(low, high, len(index)), index=index)


DEMAND = series(20_000, 40_000, 0)
TEMPERATURE = series(5, 30, 1)


def small(cls, params):
    if "Boosting" in cls.__name__:
        params = params | {"max_iter": 10}
    return cls(**params)


@pytest.mark.parametrize("name", MODELS)
def test_predictions_do_not_depend_on_the_future(name):
    day = date(2021, 7, 14)
    demand, temperature = DEMAND.copy(), TEMPERATURE.copy()
    demand[demand.index + pd.Timedelta(hours=1) > issue_moment(day)] = -1e9
    temperature[temperature.index > hours_of_local_day(day)[-1]] = -1e9
    expected = run_backtest(DEMAND, TEMPERATURE, small(*MODELS[name]), day, day)["predicted"]
    got = run_backtest(demand, temperature, small(*MODELS[name]), day, day)["predicted"]
    pd.testing.assert_series_equal(expected, got)
    assert expected.notna().all()


def test_features_of_a_day_are_the_same_with_or_without_later_data():
    # Training builds many days at once, so each row must respect its own issue time.
    targets = pd.DatetimeIndex(hours_of_local_day(date(2021, 6, 10)))
    all_at_once = build_features(DEMAND, TEMPERATURE, DEMAND.index[500:])
    known = DEMAND[DEMAND.index + pd.Timedelta(hours=1) <= issue_moment(date(2021, 6, 10))]
    alone = build_features(known, TEMPERATURE[: targets[-1]], targets)
    pd.testing.assert_frame_equal(all_at_once.loc[targets], alone, check_freq=False)


def test_blackout_day_is_hidden():
    index = pd.date_range("2025-04-27", "2025-04-30", freq="1h", tz="UTC")
    hidden = without_blackout(pd.Series(1.0, index=index))
    assert hidden.isna().sum() == 24
    assert set(hidden[hidden.isna()].index.tz_convert(MADRID).date) == {BLACKOUT}
