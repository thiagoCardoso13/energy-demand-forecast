from datetime import date

import pytest

from forecast.timeutils import hours_of_local_day


@pytest.mark.parametrize(
    ("day", "expected"),
    [(date(2026, 3, 29), 23), (date(2026, 6, 15), 24), (date(2026, 10, 25), 25)],
)
def test_hours_of_local_day_handles_daylight_saving(day, expected):
    hours = hours_of_local_day(day)
    assert len(hours) == expected
    assert len(set(hours)) == expected
