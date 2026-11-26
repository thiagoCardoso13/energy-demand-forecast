"""Rolling-origin backtest: one forecast per day, using only what was known when it was issued."""

from datetime import date, datetime, time, timedelta

import pandas as pd

from forecast.models import Model
from forecast.timeutils import MADRID, hours_of_local_day

ISSUE_TIME = time(10, 0)


def issue_moment(target_day: date) -> pd.Timestamp:
    """10:00 Madrid on the day before the target day, in UTC."""
    local = datetime.combine(target_day - timedelta(days=1), ISSUE_TIME, MADRID)
    return pd.Timestamp(local).tz_convert("UTC")


def known_history(demand: pd.Series, target_day: date) -> pd.Series:
    """Hourly values whose hour had already ended at issue time."""
    # The index marks the start of each hour.
    return demand[demand.index + pd.Timedelta(hours=1) <= issue_moment(target_day)]


def run_backtest(
    demand: pd.Series, temperature: pd.Series, model: Model, first: date, last: date
) -> pd.DataFrame:
    """Forecast every day in [first, last]. Returns `actual` and `predicted` per UTC hour.

    The model is refitted for the first day and for the first day of every month, with the data
    known when that day's forecast was issued.
    """
    days = []
    day = first
    while day <= last:
        targets = pd.DatetimeIndex(hours_of_local_day(day))
        history = known_history(demand, day)
        # Day-ahead forecasts up to the target day exist at issue time; later ones are hidden.
        forecast = temperature[temperature.index <= targets[-1]]
        if day == first or day.day == 1:
            model.fit(history, forecast[forecast.index <= issue_moment(day)])
        predicted = model.predict(history, forecast, targets)
        days.append(pd.DataFrame({"actual": demand.reindex(targets), "predicted": predicted}))
        day += timedelta(days=1)
    return pd.concat(days)
