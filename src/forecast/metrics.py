"""Error metrics over backtest results."""

from datetime import date

import holidays
import pandas as pd

from forecast.timeutils import MADRID


def summarize(results: pd.DataFrame) -> dict:
    """MAE (MW) and MAPE (%) over hours that have both an actual value and a prediction."""
    both = results.dropna()
    error = (both["predicted"] - both["actual"]).abs()
    return {
        "hours": len(both),
        "skipped": len(results) - len(both),
        "mae_mw": error.mean(),
        "mape_pct": 100 * (error / both["actual"]).mean(),
    }


def is_national_holiday(days: list[date]) -> list[bool]:
    calendar = holidays.country_holidays("ES", years=sorted({d.year for d in days}))
    return [d in calendar for d in days]


def breakdown(results: pd.DataFrame, by: str) -> pd.DataFrame:
    """Metrics grouped by local `hour`, `weekday`, `month` or `holiday`."""
    local = results.index.tz_convert(MADRID)
    if by == "hour":
        keys = local.hour
    elif by == "weekday":
        keys = local.day_of_week
    elif by == "month":
        keys = local.strftime("%Y-%m")
    elif by == "holiday":
        keys = pd.Index(is_national_holiday(list(local.date)))
    else:
        raise ValueError(f"unknown grouping {by!r}")
    rows = {key: summarize(group) for key, group in results.groupby(keys)}
    return pd.DataFrame.from_dict(rows, orient="index")
