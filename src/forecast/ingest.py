"""Download or update the hourly demand and temperature files.

Usage: python -m forecast.ingest [--data data] [--cache .cache/ree]
"""

import argparse
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from forecast import ree, weather
from forecast.clean import merge_update, to_hourly
from forecast.timeutils import MADRID

DEMAND_START = date(2019, 1, 1)
REFRESH_DAYS = 7  # recent days are downloaded again in case they were completed or corrected


def read_table(path: Path) -> pd.DataFrame | None:
    return pd.read_parquet(path) if path.exists() else None


def write_table(table: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    table.to_parquet(temporary)
    temporary.replace(path)


def resume_day(old: pd.DataFrame | None, default: date) -> date:
    if old is None or old.empty:
        return default
    last = old.index.max().tz_convert(MADRID).date()
    return max(default, last - timedelta(days=REFRESH_DAYS))


def update_demand(
    path: Path,
    today: date,
    cache_dir: Path | None = None,
    fetch: Callable = ree.fetch_month,
) -> pd.DataFrame:
    old = read_table(path)
    pieces = []
    for start, end in ree.month_ranges(resume_day(old, DEMAND_START), today):
        data = fetch(start, end, today, cache_dir)
        pieces.append(ree.parse_series(data, "Real"))
        print(f"demand {start} to {end}: {len(pieces[-1])} points", flush=True)
    raw = pd.concat(pieces)
    # The current hour is still filling up, so it is not stored yet.
    hourly = to_hourly(raw)
    hourly = hourly.loc[: hourly.last_valid_index()]
    table = merge_update(old, hourly.to_frame("demand_mw"))
    write_table(table, path)
    return table


def update_temperature(
    path: Path,
    today: date,
    fetch: Callable = weather.fetch_temperature,
) -> pd.DataFrame:
    old = read_table(path)
    # Day-ahead forecasts exist for tomorrow, which is the day to predict.
    new = fetch(resume_day(old, weather.FIRST_DAY), today + timedelta(days=1)).to_frame()
    new = new.loc[new.first_valid_index() : new.last_valid_index()]
    table = merge_update(old, new)
    write_table(table, path)
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/ree"))
    args = parser.parse_args()
    today = datetime.now(UTC).astimezone(MADRID).date()
    for name, table in (
        ("demand", update_demand(args.data / "demand.parquet", today, args.cache)),
        ("temperature", update_temperature(args.data / "temperature.parquet", today)),
    ):
        missing = int(table.iloc[:, 0].isna().sum())
        print(f"{name}: {len(table)} hours, {missing} missing, {table.index.min()} to "
              f"{table.index.max()}")


if __name__ == "__main__":
    main()
