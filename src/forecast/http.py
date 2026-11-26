"""Small JSON-over-HTTP helper with retries."""

import json
import time
import urllib.error
import urllib.request


def get_json(url: str, attempts: int = 4, timeout: int = 90, wait: float = 5.0) -> dict:
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            if attempt == attempts:
                raise
            time.sleep(wait * attempt)
    raise ValueError("attempts must be at least 1")
