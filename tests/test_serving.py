import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app, data_dir
from forecast.daily import COLUMNS
from forecast.serving import daily_errors, data_updated_until, day_view


def predictions(day: str = "2026-02-11", actual: float | None = 100.0) -> pd.DataFrame:
    stamps = pd.date_range(f"{day} 00:00", periods=24, freq="1h", tz="Europe/Madrid")
    return pd.DataFrame(
        {
            "target_utc": [t.isoformat() for t in stamps.tz_convert("UTC")],
            "target_day": day,
            "predicted_mw": 110.0,
            "baseline_mw": 120.0,
            "actual_mw": actual,
            "made_at_utc": "2026-02-10T09:30:00+00:00",
            "history_end_utc": "2026-02-10T09:00:00+00:00",
            "model": "boosting_weekly_change",
        }
    )[COLUMNS]


def test_data_date_is_the_latest_of_history_and_actuals():
    # Actuals run to the end of 11 February; without them only the history before issue is known.
    assert data_updated_until(predictions()) == "2026-02-12 00:00"
    assert data_updated_until(predictions(actual=None)) == "2026-02-10 10:00"


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[data_dir] = lambda: tmp_path
    yield TestClient(app), tmp_path
    app.dependency_overrides.clear()


def test_day_view_uses_madrid_time():
    view = day_view(predictions(), "2026-02-11")
    assert view["local_time"].iloc[0] == "00:00"
    assert len(view) == 24


def test_daily_errors_ignore_days_without_actuals():
    table = pd.concat([predictions(), predictions("2026-02-12", actual=None)])
    errors = daily_errors(table)
    assert errors.to_dict("records") == [
        {"day": "2026-02-11", "model": 10.0, "baseline": 20.0, "hours": 24}
    ]


def test_api_returns_the_latest_day_by_default(client):
    api, folder = client
    pd.concat([predictions(), predictions("2026-02-12", actual=None)]).to_csv(
        folder / "predictions.csv", index=False
    )
    body = api.get("/forecast").json()
    assert body["day"] == "2026-02-12"
    assert body["demand_source"] == "Red Eléctrica"
    assert len(body["hours"]) == 24
    assert body["hours"][0]["actual_mw"] is None
    assert api.get("/forecast", params={"day": "2026-02-11"}).json()["hours"][0]["actual_mw"] == 100


def test_api_errors(client):
    api, folder = client
    assert api.get("/forecast").status_code == 404
    predictions().to_csv(folder / "predictions.csv", index=False)
    assert api.get("/forecast", params={"day": "2020-01-01"}).status_code == 404
    assert api.get("/forecast", params={"day": "tomorrow"}).status_code == 422
    assert api.get("/health").json() == {"status": "ok"}
