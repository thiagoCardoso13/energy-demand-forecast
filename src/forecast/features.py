"""Features for each target hour, using only what is known when its forecast is issued."""

import numpy as np
import pandas as pd

from forecast.backtest import issue_moment
from forecast.metrics import is_national_holiday
from forecast.models import weeks_earlier
from forecast.timeutils import MADRID

BLACKOUT = pd.Timestamp("2025-04-28").date()
HEATING_BELOW_C = 15.0
COOLING_ABOVE_C = 21.0


def without_blackout(demand: pd.Series) -> pd.Series:
    """Hide the blackout day, so it is neither learned from nor repeated through lags."""
    return demand.mask(demand.index.tz_convert(MADRID).date == BLACKOUT)


def lag_in_weeks(demand: pd.Series, targets: pd.DatetimeIndex, weeks: int) -> np.ndarray:
    """Same local hour `weeks` earlier, falling back to the two weeks before that."""
    result = np.full(len(targets), np.nan)
    for back in range(weeks, weeks + 3):
        values = demand.reindex(weeks_earlier(targets, back)).to_numpy()
        result = np.where(np.isnan(result), values, result)
    return result


def recent_level(demand: pd.Series, targets: pd.DatetimeIndex) -> np.ndarray:
    """Mean demand over the 24 hours that had ended when each target day was issued."""
    # Entry t of the rolling mean covers the 24 hourly rows starting at t-23 up to t.
    full = demand.reindex(pd.date_range(demand.index.min(), targets.max(), freq="1h"))
    rolling = full.rolling(24, min_periods=12).mean()
    days = targets.tz_convert(MADRID).date
    last_hour = {d: issue_moment(d) - pd.Timedelta(hours=1) for d in set(days)}
    return rolling.reindex(pd.DatetimeIndex([last_hour[d] for d in days])).to_numpy()


def two_days_earlier(demand: pd.Series, targets: pd.DatetimeIndex) -> np.ndarray:
    """Same local hour on the last day that was complete at issue time (D-1 for target D+1)."""
    wall = targets.tz_convert(MADRID).tz_localize(None) - pd.Timedelta(days=2)
    earlier = wall.tz_localize(
        MADRID, ambiguous=np.ones(len(wall), dtype=bool), nonexistent="shift_forward"
    ).tz_convert("UTC")
    values = demand.reindex(earlier).to_numpy()
    return np.where(np.isnan(values), lag_in_weeks(demand, targets, 1), values)


def build_features(
    demand: pd.Series, temperature: pd.Series | None, targets: pd.DatetimeIndex
) -> pd.DataFrame:
    """One row per target hour. `temperature` is the day-ahead forecast, or None to omit it."""
    demand = without_blackout(demand)
    local = targets.tz_convert(MADRID)
    dates = list(local.date)
    year_angle = 2 * np.pi * local.day_of_year / 365.25
    day = pd.Timedelta(days=1)
    table = pd.DataFrame(
        {
            "hour": local.hour,
            "weekday": local.day_of_week,
            "year_sin": np.sin(year_angle),
            "year_cos": np.cos(year_angle),
            "holiday": is_national_holiday(dates),
            "day_before_holiday": is_national_holiday([(t + day).date() for t in local]),
            "day_after_holiday": is_national_holiday([(t - day).date() for t in local]),
            "week_ago_holiday": is_national_holiday([(t - 7 * day).date() for t in local]),
            "two_days_ago_holiday": is_national_holiday([(t - 2 * day).date() for t in local]),
            "lag_2d": two_days_earlier(demand, targets),
            "lag_1w": lag_in_weeks(demand, targets, 1),
            "lag_2w": lag_in_weeks(demand, targets, 2),
            "level_24h": recent_level(demand, targets),
        },
        index=targets,
    )
    if temperature is not None:
        temp = temperature.reindex(targets)
        daily = temp.groupby(local.date).transform("mean")
        table["temp"] = temp
        table["temp_day_mean"] = daily.to_numpy()
        table["heating"] = np.maximum(HEATING_BELOW_C - daily.to_numpy(), 0)
        table["cooling"] = np.maximum(daily.to_numpy() - COOLING_ABOVE_C, 0)
        week_before = temperature.reindex(weeks_earlier(targets, 1)).to_numpy()
        table["temp_change_1w"] = temp.to_numpy() - week_before
    return table.astype(float)
