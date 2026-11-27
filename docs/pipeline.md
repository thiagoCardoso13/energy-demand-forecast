# Daily pipeline

`.github/workflows/daily.yml` runs `python -m forecast.daily` at 09:17 UTC, with further attempts at 10:37, 12:47, 15:23 and 18:53 UTC.
It can also be started by hand from the Actions tab.

Each run:

1. downloads recent demand and temperature;
2. fills in actual values for earlier forecasts;
3. forecasts the 24 hours (23 or 25 on clock changes) of tomorrow;
4. commits `data/predictions.csv`.

## Rules

- Same procedure as the backtest: demand up to 10:00 Madrid, model fitted with the data known for the
  first forecast of the month.
- The first forecast recorded for a day is never replaced.
- A forecast made on or after its target day (Madrid time) is not counted in the live error.
- No forecast is made if demand data ends more than 6 hours before the 10:00 cutoff, or if the
  temperature forecast for the day is incomplete. The run fails, and a later run tries again.
- If every run of a day fails or is skipped by GitHub, that day has no forecast. It is not filled in afterwards by
  the schedule.

## Repository size

The Parquet files are committed only on the 1st of each month; between those commits each run
downloads the days since the last snapshot. Actual values for the forecast hours are in
`data/predictions.csv`.

## Limits

- GitHub Actions schedules can be delayed.
- GitHub disables schedules in public repositories after a long period without activity.
