# Data notes

Checked on 2026-11-26. The demand figures come from `python scripts/explore.py` (2019-01-01 to 2026-11-25).
The geography, `Prevista` and weather checks were separate one-off requests.

## Demand (`demanda-tiempo-real`, series `Real`)

- 5-minute power values in MW. No token. One calendar month per request works.
- 828,496 points, no duplicate timestamps in any of the 95 monthly downloads.
- Earliest data: 2019 works. Single days tried in 2014, 2015 and 2018 returned HTTP 502 or 400.
- The API can be slow: the full download took more than 10 minutes.
- Daylight saving is correct: 276 points on 2026-03-29 and 300 on 2026-10-25, with offsets in each timestamp.

### Gaps

Of 69,264 expected hours, 210 have no data and 17 are incomplete.

- 11 days lack 17 hours each (04:00 to 20:59): 2019-06-17, 2020-01-28, 2020-07-15, 2020-11-09,
  2021-05-22, 2021-11-07, 2022-07-27, 2022-12-13, 2023-04-18, 2023-11-05 and 2024-01-07.
  Requesting 2023-11-05 and 2024-01-07 on their own gave the same hole.
- Smaller holes include 2026-06-11 (10 hours), 2025-06-06 (8), 2025-04-20 and 2025-06-05 (2 each).

Decision: do not interpolate targets. An incomplete hour is treated as missing.

### Outliers

- Median 29,158 MW, maximum 45,772 MW (July 2026).
- Minimum 1,769 MW on 2025-04-28, the day of the Iberian blackout. All 100 points below 15,000 MW are on that day.

Decision: exclude 2025-04-28 from training and report metrics with and without it.

## Geography

The default response is treated as **national** (the endpoint title says so). In 2025, on complete days,
its daily energy divided by the national daily series (`evolucion`) had a median of 0.993
(5th to 95th percentile: 0.974 to 1.008). Against the peninsular series the median was 1.057.

The two products do not match exactly. Asking `demanda-tiempo-real` for a specific region returned HTTP 502.

## REE's own forecast (`Prevista`)

Its mean absolute percentage error against `Real` over the 2025 5-minute points was 1.37%.

**This is not a day-ahead benchmark.** It is not known when each historical value was issued or whether it
was revised during the day. On 2026-11-26 the series reached only about 3 hours into the next day.
It is shown as an external reference only.

## Weather (Open-Meteo, tested for Madrid only)

| API | Finding |
|---|---|
| `historical-forecast-api` | Returned data for the days sampled from 2017. It is built from short-lead forecasts, so it is closer to observations than a day-ahead forecast. |
| `previous-runs-api`, `temperature_2m_previous_day2` | Starts on 2021-03-25. 516 hours missing, on 22 days between 2023-12-30 and 2024-01-20. |

Decision: use `previous_day2`. A forecast is issued at 10:00 on day D for day D+1. `previous_day1` is the
forecast made 24 hours before each hour, so for the afternoon of D+1 it would not exist yet at issue time.

## Consequences for modelling

- Training data with both demand and day-ahead temperature starts on 2021-03-25.
- Demand lags must respect the 10:00 cutoff: the most recent full day available is D-1.
- 2019-2020 demand can still be used for the baseline.

## Still open

- When `Prevista` is published and revised.
- Which cities and weights to use for temperature.
