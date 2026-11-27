from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_dashboard_runs_for_both_data_sources():
    # Uses the committed data files, as the hosted app does.
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    for source in app.radio[0].options:
        app.radio[0].set_value(source).run()
        assert not app.exception
    assert app.metric[2].value == "365"
