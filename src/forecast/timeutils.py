"""Calendar helpers for the Europe/Madrid market day."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def hours_of_local_day(day: date) -> list[datetime]:
    """Return the UTC start of every hour in a Madrid calendar day (23, 24 or 25)."""
    start = datetime.combine(day, time.min, MADRID).astimezone(ZoneInfo("UTC"))
    end = datetime.combine(day + timedelta(days=1), time.min, MADRID).astimezone(ZoneInfo("UTC"))
    count = int((end - start).total_seconds() // 3600)
    return [start + timedelta(hours=i) for i in range(count)]
