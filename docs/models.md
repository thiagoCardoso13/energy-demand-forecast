# Model notes

Numbers are in [evaluation.md](evaluation.md).

## What is compared

| Name | Description |
|---|---|
| `seasonal_naive` | Same local hour one week earlier |
| `ridge` | One regularised linear regression per local hour |
| `boosting` | scikit-learn histogram gradient boosting, one model for all hours |
| `boosting_weekly_change` | Same, but learning the difference from one week earlier |

`_no_temperature` variants drop the temperature features. All settings were written down before the
comparison ran, and none was tuned afterwards.

LightGBM was planned, but its wheel needs the `libomp` system library, which is missing on the
development machine. scikit-learn's histogram gradient boosting uses the same technique.

## Findings

- All learned models beat the baseline (4.16% MAPE).
- Temperature helps boosting (2.94% to 2.55%) but not the linear model (2.93% without, 3.07% with).
  The cause has not been investigated.
- `boosting_weekly_change` has the lowest error (2.51%). Its margin over `boosting` is small and may not
  hold on other periods.
- On national holidays its MAPE is 5.20%, against 12.82% for the baseline. Holidays remain the hardest days.
- REE's `Prevista` had a 1.37% MAPE on 2025 5-minute data (see [DATA.md](DATA.md)). That is a different
  period and an unknown issue time, so it is not comparable, but this project does not claim to match it.

## Held-out test

Run once on 2026-11-27, see [final_test.md](final_test.md): 2.70% MAPE against 4.94% for the
baseline. No model setting was changed after seeing it.

## Tracking

```bash
pip install -r requirements-train.txt
```

```bash
PYTHONPATH=src python -m forecast.evaluate --mlflow
```

Runs are stored in a local `mlflow.db` (not committed). Browse them with
`mlflow ui --backend-store-uri sqlite:///mlflow.db`.

## Not done

- SARIMAX or Prophet (optional in the plan).
- Regional holidays.
