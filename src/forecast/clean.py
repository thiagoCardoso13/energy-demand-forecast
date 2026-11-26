"""Turn raw series into a regular hourly table."""

import pandas as pd

POINTS_PER_HOUR = 12


def to_hourly(raw: pd.Series) -> pd.Series:
    """Average 5-minute values by hour.

    The result has one row per hour between the first and last point. An hour without all
    twelve 5-minute values is NaN: targets are never interpolated.
    """
    if raw.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    unique = raw[~raw.index.duplicated(keep="last")].sort_index()
    groups = unique.resample("1h")
    return groups.mean().where(groups.count() == POINTS_PER_HOUR)


def merge_update(old: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Add `new` to `old` and keep a gap-free hourly index.

    New values win, but a hole in a new download never erases a value already stored.
    """
    merged = new if old is None else new.combine_first(old)
    if merged.empty:
        return merged
    full = pd.date_range(merged.index.min(), merged.index.max(), freq="1h")
    return merged.sort_index().reindex(full)
