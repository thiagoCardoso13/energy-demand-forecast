# Energy Demand Forecast

Day-ahead forecast of Spain's hourly electricity demand, evaluated against simple baselines.

**Status:** a [daily pipeline](docs/pipeline.md) records tomorrow's forecast in
`data/predictions.csv`. A dashboard and an API run locally; there is no public demo yet. Backtest over 2025-09 to 2026-08:

| Model | MAPE |
|---|---|
| Baseline (same hour one week earlier) | 4.16% |
| Linear regression per hour | 3.07% |
| Gradient boosting | 2.55% |
| Gradient boosting on the weekly change | 2.51% |

See [Evaluation](docs/evaluation.md) and [Model notes](docs/models.md).

- [Plan](docs/PLAN.md)
- [Data notes](docs/DATA.md)

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## Dashboard

```bash
.venv/bin/streamlit run app.py
```

Forecast against actual demand for any day, and the error history, for live forecasts or the backtest.

## API

```bash
PYTHONPATH=src .venv/bin/uvicorn api.main:app
```

`GET /forecast` returns the latest recorded forecast, `GET /forecast?day=2026-11-28` a given day.
Interactive documentation is at `/docs`.

## Backtest

```bash
PYTHONPATH=src .venv/bin/python -m forecast.evaluate
```

## Data

```bash
PYTHONPATH=src .venv/bin/python -m forecast.ingest
```

Writes two hourly tables indexed in UTC, and on later runs downloads only recent days:

| File | Column | Source |
|---|---|---|
| `data/demand.parquet` | `demand_mw` | [Red Eléctrica](https://www.ree.es/en/datos/apidata), REData API |
| `data/temperature.parquet` | `temperature_c` | [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), two-day-ahead forecast, population-weighted |

A missing hour is stored as an empty value. Nothing is interpolated.
