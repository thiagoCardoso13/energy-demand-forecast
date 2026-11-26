"""Forecasting models.

A model has `fit(history, temperature)` and `predict(history, temperature, targets)`. `history` is
the hourly demand known at that moment, `temperature` the day-ahead temperature forecast and
`targets` the UTC hours to predict.
"""

from typing import Protocol

import pandas as pd

from forecast.timeutils import MADRID


class Model(Protocol):
    def fit(self, history: pd.Series, temperature: pd.Series) -> None: ...

    def predict(
        self, history: pd.Series, temperature: pd.Series, targets: pd.DatetimeIndex
    ) -> pd.Series: ...


def weeks_earlier(targets: pd.DatetimeIndex, weeks: int) -> pd.DatetimeIndex:
    """The same Madrid wall-clock hour some weeks earlier, as UTC.

    A repeated hour (October) maps to its first occurrence and a skipped one (March) to the
    next existing hour.
    """
    wall = targets.tz_convert(MADRID).tz_localize(None) - pd.Timedelta(weeks=weeks)
    local = wall.tz_localize(MADRID, ambiguous=[True] * len(wall), nonexistent="shift_forward")
    return local.tz_convert("UTC")


def seasonal_naive(history: pd.Series, targets: pd.DatetimeIndex) -> pd.Series:
    """Baseline: the same hour one week earlier, or older weeks if that hour is missing."""
    result = pd.Series(float("nan"), index=targets)
    for weeks in (1, 2, 3):
        earlier = pd.Series(history.reindex(weeks_earlier(targets, weeks)).to_numpy(), targets)
        result = result.fillna(earlier)
    return result


class SeasonalNaive:
    def fit(self, history: pd.Series, temperature: pd.Series) -> None:
        pass

    def predict(
        self, history: pd.Series, temperature: pd.Series, targets: pd.DatetimeIndex
    ) -> pd.Series:
        return seasonal_naive(history, targets)
