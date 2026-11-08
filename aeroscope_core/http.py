"""HTTP helper with retries and Open-Meteo-friendly pacing."""

import time

import requests


class DailyLimitReached(RuntimeError):
    """Raised when the free API's daily quota is used up; re-run later to resume."""


class Pacer:
    """Keeps weighted API usage under a per-minute budget (Open-Meteo free tier: 600/min, 5000/h)."""

    def __init__(self, per_minute: float = 500.0, per_hour: float = 4500.0):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.events: list[tuple[float, float]] = []

    def wait(self, weight: float) -> None:
        while True:
            now = time.time()
            self.events = [(t, w) for t, w in self.events if now - t < 3600]
            minute = sum(w for t, w in self.events if now - t < 60)
            hour = sum(w for t, w in self.events)
            if minute + weight <= self.per_minute and hour + weight <= self.per_hour:
                self.events.append((now, weight))
                return
            if hour + weight > self.per_hour:
                oldest = min(t for t, _ in self.events)
                pause = max(5.0, 3600 - (now - oldest) + 1)
                print(f"    hourly budget reached, pausing {pause/60:.1f} min...", flush=True)
            else:
                pause = 5.0
            time.sleep(min(pause, 300))


def open_meteo_weight(n_locations: int, n_days: int, n_vars: int) -> float:
    """Open-Meteo counts long or wide requests as several calls."""
    return n_locations * max(1.0, n_days / 14.0) * max(1.0, n_vars / 10.0)


def get_json(url: str, params: dict, retries: int = 6, timeout: int = 180):
    delay = 10.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            print(f"    network error ({exc}); retry {attempt}/{retries} in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay *= 2
            continue
        if resp.status_code == 200:
            return resp.json()
        reason = resp.text[:300]
        if resp.status_code == 429:
            if "daily" in reason.lower():
                raise DailyLimitReached(reason)
            wait = 65 if "minut" in reason.lower() else delay
            print(f"    rate limited ({reason.strip()}); waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
            delay *= 2
            continue
        if resp.status_code >= 500:
            print(f"    server error {resp.status_code}; retry in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay *= 2
            continue
        raise RuntimeError(f"HTTP {resp.status_code} from {url}: {reason}")
    raise RuntimeError(f"Giving up on {url} after {retries} attempts")
