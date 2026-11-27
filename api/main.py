"""Read-only API over the recorded forecasts.

Run with: PYTHONPATH=src uvicorn api.main:app
"""

from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException

from forecast.daily import on_time
from forecast.serving import DATA, data_updated_until, day_view, load_live

app = FastAPI(
    title="Energy Demand Forecast",
    description="Day-ahead forecasts of Spain's hourly electricity demand.",
)


def data_dir() -> Path:
    return DATA


def number(value) -> float | None:
    return None if pd.isna(value) else float(value)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/forecast")
def forecast(day: date | None = None, folder: Path = Depends(data_dir)) -> dict:
    """The recorded forecast for a day, or the most recent one."""
    table = load_live(folder)
    if table.empty:
        raise HTTPException(404, "no forecast has been recorded yet")
    wanted = day.isoformat() if day else table["target_day"].max()
    rows = day_view(table, wanted)
    if rows.empty:
        raise HTTPException(404, f"no forecast recorded for {wanted}")
    first = rows.iloc[0]
    return {
        "day": wanted,
        "demand_source": "Red Eléctrica",
        "demand_data_until_madrid": data_updated_until(table),
        "model": first["model"],
        "made_at_utc": first["made_at_utc"],
        "made_before_target_day": bool(on_time(rows).all()),
        "hours": [
            {
                "start_utc": row.target_utc,
                "predicted_mw": number(row.predicted_mw),
                "baseline_mw": number(row.baseline_mw),
                "actual_mw": number(row.actual_mw),
            }
            for row in rows.itertuples()
        ],
    }
