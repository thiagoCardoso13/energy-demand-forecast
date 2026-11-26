"""Update the data, forecast tomorrow and record it.

Usage: python -m forecast.daily [--data data] [--cache .cache/ree]

The first forecast recorded for a day is never replaced. Actual values are filled in later runs.
"""

import argparse
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from forecast.backtest import issue_moment, known_history
from forecast.ingest import update_demand, update_temperature
from forecast.learned import GradientBoosting
from forecast.metrics import summarize
from forecast.models import Model, seasonal_naive
from forecast.timeutils import MADRID, hours_of_local_day

# The model with the lowest backtest error, see docs/evaluation.md.
MODEL_NAME = "boosting_weekly_change"
MAX_HISTORY_AGE = pd.Timedelta(hours=6)
COLUMNS = [
    "target_utc",
    "target_day",
    "predicted_mw",
    "baseline_mw",
    "actual_mw",
    "made_at_utc",
    "history_end_utc",
    "model",
]


def make_model() -> Model:
    return GradientBoosting(predict_change=True)


def read_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, dtype={"target_day": str, "model": str})


def forecast_day(
    demand: pd.Series,
    temperature: pd.Series,
    target_day: date,
    made_at: pd.Timestamp,
    model: Model,
) -> pd.DataFrame:
    """Forecast one day the same way the backtest does."""
    if made_at < issue_moment(target_day):
        raise ValueError(f"too early to forecast {target_day}: issue time is 10:00 the day before")
    targets = pd.DatetimeIndex(hours_of_local_day(target_day))
    history = known_history(demand, target_day)
    end = history.last_valid_index() + pd.Timedelta(hours=1)
    if issue_moment(target_day) - end > MAX_HISTORY_AGE:
        raise ValueError(f"demand data is stale: it ends at {end}")
    forecast = temperature[temperature.index <= targets[-1]]
    if forecast.reindex(targets).isna().any():
        raise ValueError(f"temperature forecast for {target_day} is incomplete")
    # Fitted with what was known for the first forecast of the month, as in the backtest.
    month_start = target_day.replace(day=1)
    model.fit(
        known_history(demand, month_start), forecast[forecast.index <= issue_moment(month_start)]
    )
    return pd.DataFrame(
        {
            "target_utc": [t.isoformat() for t in targets],
            "target_day": target_day.isoformat(),
            "predicted_mw": model.predict(history, forecast, targets).round(1).to_numpy(),
            "baseline_mw": seasonal_naive(history, targets).round(1).to_numpy(),
            "actual_mw": float("nan"),
            "made_at_utc": made_at.isoformat(timespec="seconds"),
            "history_end_utc": end.isoformat(),
            "model": MODEL_NAME,
        }
    )[COLUMNS]


def fill_actuals(predictions: pd.DataFrame, demand: pd.Series) -> pd.DataFrame:
    if predictions.empty:
        return predictions
    stamps = pd.to_datetime(predictions["target_utc"], utc=True)
    latest = pd.Series(demand.reindex(stamps).round(1).to_numpy(), index=predictions.index)
    return predictions.assign(actual_mw=latest.fillna(predictions["actual_mw"].astype(float)))


def on_time(predictions: pd.DataFrame) -> pd.Series:
    """True for forecasts made before their target day started in Madrid."""
    made = pd.to_datetime(predictions["made_at_utc"], utc=True).dt.tz_convert(MADRID)
    return made.dt.strftime("%Y-%m-%d") < predictions["target_day"]


def live_summary(predictions: pd.DataFrame) -> dict | None:
    """Errors of the on-time forecasts that already have actual values."""
    scored = predictions[on_time(predictions) & predictions["actual_mw"].notna()]
    if scored.empty:
        return None
    actual = scored["actual_mw"].astype(float)
    return {
        name: summarize(pd.DataFrame({"actual": actual, "predicted": scored[column]}))
        for name, column in (("model", "predicted_mw"), ("baseline", "baseline_mw"))
    }


def run(
    data_dir: Path,
    now: pd.Timestamp,
    cache_dir: Path | None = None,
    model: Model | None = None,
    update: Callable | None = None,
) -> str:
    today = now.tz_convert(MADRID).date()
    if update is None:
        demand = update_demand(data_dir / "demand.parquet", today, cache_dir)
        temperature = update_temperature(data_dir / "temperature.parquet", today)
    else:
        demand, temperature = update(today)
    demand, temperature = demand["demand_mw"], temperature["temperature_c"]

    path = data_dir / "predictions.csv"
    predictions = fill_actuals(read_predictions(path), demand)
    target = today + timedelta(days=1)

    def save() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(path, index=False)

    if target.isoformat() in set(predictions["target_day"]):
        save()
        return f"{target} was already forecast"
    # Actual values are saved even if today's forecast cannot be made.
    save()
    new = forecast_day(demand, temperature, target, now, model or make_model())
    predictions = new if predictions.empty else pd.concat([predictions, new], ignore_index=True)
    save()
    return f"forecast recorded for {target}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/ree"))
    args = parser.parse_args()
    print(run(args.data, pd.Timestamp(datetime.now(UTC)), args.cache))
    summary = live_summary(read_predictions(args.data / "predictions.csv"))
    if summary:
        for name, total in summary.items():
            print(f"live {name}: MAPE {total['mape_pct']:.2f}% over {total['hours']} hours")


if __name__ == "__main__":
    main()
