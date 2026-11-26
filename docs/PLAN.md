# Energy Demand Forecast: Plan

Day-ahead forecast of Spain's hourly electricity demand, evaluated honestly against simple baselines, published daily.

## Goal

Every day, forecast the 24 hourly demand values for tomorrow, and show how past forecasts compared with what really happened.

Skills it demonstrates: time series forecasting, feature engineering, backtesting without data leakage, experiment tracking (MLflow), a scheduled data pipeline, serving predictions.

**Constraint:** everything must be free, with no service that asks for a card.

## Data sources

### Electricity demand: Red Eléctrica (REData API)

`https://apidatos.ree.es/es/datos/demanda/...`, no token. Checked on 2026-11-26:

| Endpoint | Observed behaviour |
|---|---|
| `demanda-tiempo-real` | 5-minute values (even with `time_trunc=hour`). Series `Real`, `Prevista`, `Programada`. One month per request works. Data returned for 2019-03-01. |
| `evolucion` with `time_trunc=day` | Daily totals, one year per request. Data returned for 2014. A multi-year range returns HTTP 400. |
| `evolucion` with `time_trunc=hour` | HTTP 400 on the range tried. Do not rely on it. |

So the hourly series is built by averaging the 5-minute `Real` values, downloaded month by month.

### Weather: Open-Meteo

Temperature for a few large cities, combined with population weights. The archive endpoint answered without a key (free for non-commercial use).

Training and backtests must use **forecast** temperatures as they were known at the time (Open-Meteo previous runs, `previous_day2`, see [DATA.md](DATA.md)), not observed temperatures. Observed values would leak the future and make the error look better than it can be in production.

### Calendar

National holidays through the `holidays` Python package.

Phase 0 results are in [DATA.md](DATA.md).

## Forecast definition

- Issued on day D at 10:00 Europe/Madrid.
- Target: the 24 hourly values of day D+1.
- Only information available at issue time may be used. In particular, no demand values after 10:00 on D.
- Timestamps stored in UTC, calendar features computed in local time.

## Models, in order

1. **Baseline:** same hour one week earlier.
2. **Linear regression** with calendar, lag and temperature features.
3. **Gradient boosting** (LightGBM).
4. Optional: SARIMAX or Prophet for comparison.

A more complex model is kept only if it beats the simpler one in the backtest.

## Evaluation

- Rolling-origin backtest over the last 12 months, retraining monthly.
- A final untouched test period, used once.
- Metrics: MAPE and MAE (MW), also split by hour, weekday, month and holiday.
- REE's `Prevista` is shown as an external reference only, with the caveat above. No claim of beating it unless the comparison is on equal terms.

## Stack

| Part | Choice |
|---|---|
| Language | Python 3.12 |
| Data | pandas, Parquet files |
| Models | scikit-learn, LightGBM |
| Tracking | MLflow, local (results exported to `docs/evaluation.md`) |
| API | FastAPI |
| Dashboard | Streamlit, Streamlit Community Cloud |
| Automation | GitHub Actions, daily schedule |
| Quality | pytest, ruff, CI |

## Layout

```
src/forecast/    ingest, clean, features, models, backtest, predict
api/             FastAPI app
app.py           Streamlit dashboard
data/            small Parquet files and daily predictions
tests/
docs/
```

## Phases

Each phase ends with tests passing and a commit.

| # | Phase | Done when |
|---|---|---|
| 0 | Skeleton and data exploration | Open points above are answered in `docs/DATA.md`; CI green |
| 1 | Ingestion and cleaning | Rerunnable download of the hourly series and weather; gaps and DST tested |
| 2 | Baseline and backtest | Baseline error reported; a test proves no feature uses the future |
| 3 | Features and models | Models compared in MLflow; summary in `docs/evaluation.md` |
| 4 | Daily pipeline | Scheduled workflow fetches data, predicts D+1 and records the result |
| 5 | Dashboard and API | Forecast vs actual chart, error history, `GET /forecast` |
| 6 | Publish | Live demo, README with GIF, portfolio, CV and LinkedIn updated |

## Risks

- **REE API errors or changes:** retries, cached data, and the dashboard shows the date of the last update.
- **Late scheduled runs:** GitHub Actions schedules can be delayed. Each prediction stores when it was made, and any made after day D is excluded from the live error.
- **Unusual events** (for example a blackout) distort training: flag those days and report metrics with and without them.
- **Hosting sleeps:** the free demo takes a while to wake up; say so in the README.
