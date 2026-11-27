"""Read the recorded forecasts for the dashboard and the API."""

from pathlib import Path

import pandas as pd

from forecast.daily import on_time, read_predictions
from forecast.timeutils import MADRID

DATA = Path(__file__).resolve().parents[2] / "data"


def load_live(data_dir: Path = DATA) -> pd.DataFrame:
    return read_predictions(data_dir / "predictions.csv")


def load_backtest(data_dir: Path = DATA) -> pd.DataFrame:
    table = pd.read_csv(data_dir / "backtest.csv")
    local = pd.to_datetime(table["target_utc"], utc=True).dt.tz_convert(MADRID)
    return table.assign(target_day=local.dt.strftime("%Y-%m-%d"))


def data_updated_until(table: pd.DataFrame) -> str:
    """Madrid time of the latest demand data behind a live or backtest table."""
    ends = []
    if "history_end_utc" in table:
        ends.append(pd.to_datetime(table["history_end_utc"], utc=True).max())
    with_actual = table.loc[table["actual_mw"].notna(), "target_utc"]
    if not with_actual.empty:
        # Hours are indexed by their start.
        ends.append(pd.to_datetime(with_actual, utc=True).max() + pd.Timedelta(hours=1))
    return max(ends).tz_convert(MADRID).strftime("%Y-%m-%d %H:%M")


def day_view(table: pd.DataFrame, day: str) -> pd.DataFrame:
    """Hours of one Madrid day, with local wall-clock time for plotting."""
    rows = table[table["target_day"] == day].sort_values("target_utc")
    local = pd.to_datetime(rows["target_utc"], utc=True).dt.tz_convert(MADRID)
    return rows.assign(local_time=local.dt.strftime("%H:%M"), offset=local.dt.strftime("%z"))


def daily_errors(table: pd.DataFrame) -> pd.DataFrame:
    """MAPE per day for the model and the baseline, over hours that have actual values."""
    scored = table.dropna(subset=["actual_mw", "predicted_mw", "baseline_mw"])
    actual = scored["actual_mw"].astype(float)
    errors = pd.DataFrame(
        {
            "day": scored["target_day"],
            "model": 100 * (scored["predicted_mw"] - actual).abs() / actual,
            "baseline": 100 * (scored["baseline_mw"] - actual).abs() / actual,
        }
    )
    grouped = errors.groupby("day")
    return grouped[["model", "baseline"]].mean().assign(hours=grouped.size()).reset_index()


def scored_live(table: pd.DataFrame) -> pd.DataFrame:
    """Only forecasts made in time count towards the live error."""
    return table[on_time(table)] if not table.empty else table
