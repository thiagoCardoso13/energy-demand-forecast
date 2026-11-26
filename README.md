# Energy Demand Forecast

Day-ahead forecast of Spain's hourly electricity demand, evaluated against simple baselines.

**Status:** early work. So far there is only the baseline (same hour one week earlier):
MAPE 4.16% over 2025-09 to 2026-08. See [Evaluation](docs/evaluation.md).

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
