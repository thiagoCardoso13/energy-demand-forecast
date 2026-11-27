"""Dashboard: forecast against actual demand, and the error history.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from forecast.serving import (  # noqa: E402
    daily_errors,
    day_view,
    load_backtest,
    load_live,
    scored_live,
)

# Colour follows the series in every chart.
COLORS = {"Actual": "#2a78d6", "Forecast": "#eb6834", "Baseline": "#1baf7a"}
LIVE, BACKTEST = "Live forecasts", "Backtest (past year, simulated)"


def lines(frame: pd.DataFrame, x: alt.X, y_title: str, series: list[str], value_format: str):
    long = frame.melt(
        id_vars=[c for c in frame.columns if c not in series],
        value_vars=series,
        var_name="series",
        value_name="value",
    ).dropna(subset=["value"])
    return (
        alt.Chart(long)
        .mark_line(strokeWidth=2, point=len(frame) <= 31)
        .encode(
            x=x,
            y=alt.Y("value:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(domain=series, range=[COLORS[s] for s in series]),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip(x.shorthand, title=""),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title=y_title, format=value_format),
            ],
        )
        .properties(height=320)
    )


@st.cache_data(ttl=600)
def load(source: str) -> pd.DataFrame:
    return load_live() if source == LIVE else load_backtest()


st.set_page_config(page_title="Spain electricity demand forecast", layout="wide")
st.title("Spain electricity demand: day-ahead forecast")
st.caption(
    "Each day, tomorrow's hourly demand is forecast with what is known at 10:00 Madrid time. "
    "Sources: Red Eléctrica (demand), Open-Meteo (temperature forecast, CC BY 4.0)."
)

# Until a live forecast exists, open on the backtest so the page has something to show.
source = st.radio("Data", [LIVE, BACKTEST], index=int(load(LIVE).empty), horizontal=True)
table = load(source)
if source == BACKTEST:
    st.info(
        "Simulation over 2025-09 to 2026-08. The model was chosen on this period, "
        "so these errors are slightly optimistic."
    )
if table.empty:
    st.warning("No live forecast has been recorded yet. The backtest shows past performance.")
    st.stop()

days = sorted(table["target_day"].unique(), reverse=True)
day = st.selectbox("Day", days)
view = day_view(table, day).rename(
    columns={"actual_mw": "Actual", "predicted_mw": "Forecast", "baseline_mw": "Baseline"}
)
view[["Actual", "Forecast", "Baseline"]] = view[["Actual", "Forecast", "Baseline"]].astype(float)
# The repeated hour of the October clock change needs its offset to stay distinct.
repeated = view["local_time"].duplicated(keep=False)
view.loc[repeated, "local_time"] += " (" + view.loc[repeated, "offset"].str[:3] + ")"

st.subheader(f"Demand on {day}")
if view["Actual"].isna().all():
    st.caption("Actual demand for this day is not available yet.")
hour_axis = alt.X("local_time:O", title="Madrid time", sort=None)
st.altair_chart(
    lines(
        view[["local_time", "Actual", "Forecast", "Baseline"]],
        hour_axis,
        "MW",
        ["Actual", "Forecast", "Baseline"],
        ",.0f",
    ),
    width="stretch",
)
with st.expander("Table"):
    st.dataframe(view[["local_time", "Forecast", "Baseline", "Actual"]], hide_index=True)

st.subheader("Error history")
errors = daily_errors(scored_live(table) if source == LIVE else table)
if errors.empty:
    st.caption("No forecast day has actual values yet.")
else:
    weights = errors["hours"] / errors["hours"].sum()
    left, middle, right = st.columns(3)
    left.metric("Forecast, mean error (MAPE)", f"{(errors['model'] * weights).sum():.2f}%")
    middle.metric("Baseline, mean error (MAPE)", f"{(errors['baseline'] * weights).sum():.2f}%")
    right.metric("Days scored", len(errors))
    errors = errors.rename(columns={"model": "Forecast", "baseline": "Baseline"})
    st.altair_chart(
        lines(
            errors[["day", "Forecast", "Baseline"]],
            alt.X("day:T", title=None),
            "Daily MAPE (%)",
            ["Forecast", "Baseline"],
            ".2f",
        ),
        width="stretch",
    )
    with st.expander("Table"):
        st.dataframe(errors, hide_index=True)
st.caption("Baseline: the same hour one week earlier.")
