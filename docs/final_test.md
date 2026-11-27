# Held-out test

Period 2026-09-01 to 2026-11-25, not used to choose or tune anything.
The model (`boosting_weekly_change`) was chosen on 2025-09-01 to 2026-08-31.
Run once with `python -m forecast.final_test`.

| Model | Hours | Skipped | MAE (MW) | MAPE (%) |
|---|---|---|---|---|
| boosting_weekly_change | 2,065 | 0 | 856 | 2.70 |
| seasonal_naive | 2,065 | 0 | 1,558 | 4.94 |

## boosting_weekly_change

| Month | Hours | MAE (MW) | MAPE (%) |
|---|---|---|---|
| 2026-09 | 720 | 1,096 | 3.17 |
| 2026-10 | 745 | 674 | 2.28 |
| 2026-11 | 600 | 794 | 2.66 |

| National holiday | Hours | MAE (MW) | MAPE (%) |
|---|---|---|---|
| No | 2,041 | 860 | 2.71 |
| Yes | 24 | 513 | 2.17 |
