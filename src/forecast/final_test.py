"""Evaluate the chosen model on the held-out period. Meant to be run once.

Usage: python -m forecast.final_test
"""

from pathlib import Path

import pandas as pd

from forecast.backtest import run_backtest
from forecast.daily import MODEL_NAME, make_model
from forecast.evaluate import BACKTEST, FINAL_TEST, markdown_table
from forecast.metrics import breakdown, summarize
from forecast.models import SeasonalNaive

REPORT = Path("docs/final_test.md")


def report(model: pd.DataFrame, baseline: pd.DataFrame) -> str:
    parts = [
        "# Held-out test",
        "",
        f"Period {FINAL_TEST[0]} to {FINAL_TEST[1]}, not used to choose or tune anything.",
        f"The model (`{MODEL_NAME}`) was chosen on {BACKTEST[0]} to {BACKTEST[1]}.",
        "Run once with `python -m forecast.final_test`.",
        "",
        "| Model | Hours | Skipped | MAE (MW) | MAPE (%) |",
        "|---|---|---|---|---|",
    ]
    for name, table in ((MODEL_NAME, model), ("seasonal_naive", baseline)):
        total = summarize(table)
        parts.append(
            f"| {name} | {total['hours']:,} | {total['skipped']} | "
            f"{total['mae_mw']:,.0f} | {total['mape_pct']:.2f} |"
        )
    parts += [
        "",
        f"## {MODEL_NAME}",
        "",
        markdown_table(breakdown(model, "month"), "Month"),
        "",
        markdown_table(
            breakdown(model, "holiday"), "National holiday", {False: "No", True: "Yes"}
        ),
    ]
    return "\n".join(parts) + "\n"


def main() -> None:
    if REPORT.exists():
        raise SystemExit(f"{REPORT} exists: the held-out period has already been used")
    demand = pd.read_parquet("data/demand.parquet")["demand_mw"]
    temperature = pd.read_parquet("data/temperature.parquet")["temperature_c"]
    if demand.last_valid_index().date() <= FINAL_TEST[1]:
        raise SystemExit("the demand data does not cover the whole held-out period yet")
    model = run_backtest(demand, temperature, make_model(), *FINAL_TEST)
    baseline = run_backtest(demand, temperature, SeasonalNaive(), *FINAL_TEST)
    text = report(model, baseline)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
