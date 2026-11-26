# Energy Demand Forecast

Day-ahead forecast of Spain's hourly electricity demand, evaluated against simple baselines.

**Status:** a [daily pipeline](docs/pipeline.md) records tomorrow's forecast in
`data/predictions.csv`; no demo yet. Backtest over 2025-09 to 2026-08:

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
