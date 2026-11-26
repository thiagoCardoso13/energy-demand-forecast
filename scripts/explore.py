"""One-off data checks behind docs/DATA.md. Downloads are cached in .cache/ (not committed)."""

import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from forecast.timeutils import hours_of_local_day  # noqa: E402

CACHE = Path(".cache/ree")
URL = (
    "https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real"
    "?start_date={}T00:00&end_date={}T23:59&time_trunc=hour"
)


def month_starts(first: date, last: date):
    day = first
    while day <= last:
        yield day
        day = (day + timedelta(days=32)).replace(day=1)


def fetch(start: date, end: date, today: date) -> dict | None:
    path = CACHE / f"{start:%Y-%m}.json"
    if path.exists():
        return json.loads(path.read_text())
    for attempt in range(4):
        try:
            with urllib.request.urlopen(URL.format(start, end), timeout=90) as response:
                data = json.load(response)
            if end < today:
                path.write_text(json.dumps(data))
            time.sleep(1)
            return data
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"{start:%Y-%m} attempt {attempt + 1}: {error}")
            time.sleep(5 * (attempt + 1))
    return None


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    today = date.today()
    last_full_day = today - timedelta(days=1)
    real: dict[datetime, float] = {}
    failed, duplicates, conflicting = [], 0, 0
    for start in month_starts(date(2019, 1, 1), last_full_day):
        end = min((start + timedelta(days=32)).replace(day=1) - timedelta(days=1), last_full_day)
        data = fetch(start, end, today)
        if data is None:
            failed.append(f"{start:%Y-%m}")
            continue
        series = next(i for i in data["included"] if i["type"] == "Real")
        for point in series["attributes"]["values"]:
            stamp = datetime.fromisoformat(point["datetime"]).astimezone(UTC)
            if stamp in real:
                duplicates += 1
                conflicting += real[stamp] != point["value"]
            real[stamp] = point["value"]

    per_hour = Counter(stamp.replace(minute=0) for stamp in real)
    day, missing, partial, total = date(2019, 1, 1), [], [], 0
    while day <= last_full_day:
        for hour in hours_of_local_day(day):
            total += 1
            if per_hour[hour] == 0:
                missing.append(hour)
            elif per_hour[hour] < 12:
                partial.append(hour)
        day += timedelta(days=1)

    values = sorted(real.values())
    print("failed months:", failed)
    print("points:", len(real), "duplicates:", duplicates, "conflicting:", conflicting)
    print("hours expected:", total, "missing:", len(missing), "partial:", len(partial))
    print("missing by day:", Counter(str(h.date()) for h in missing).most_common(15))
    print("partial by day:", Counter(str(h.date()) for h in partial).most_common(10))
    print("min/median/max:", values[0], values[len(values) // 2], values[-1])
    print("lowest days:", Counter(str(s.date()) for s, v in real.items() if v < 15000))
    print("highest days:", Counter(str(s.date()) for s, v in real.items() if v > 45000))


if __name__ == "__main__":
    main()
