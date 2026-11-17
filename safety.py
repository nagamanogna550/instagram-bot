"""Rate-limit and timing safety helpers."""
import json
import os
import random
import time
from datetime import date, datetime

# Conservative default daily caps. Lower them if in doubt.
DEFAULT_LIMITS = {"like": 60, "comment": 10, "follow": 15, "upload": 2}
MIN_DELAY = 3.0            # never act faster than this (seconds)
LOG_FILE = "action_log.json"


class RateLimiter:
    """Counts actions per day, persists them to disk and blocks over-limit actions."""

    def __init__(self, limits=None, path=LOG_FILE, today=None):
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.path = path
        self._today = today or (lambda: date.today().isoformat())
        self._date = self._today()
        self.counts = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    saved = json.load(f)
                if saved.get("date") == self._date:
                    return dict(saved.get("counts", {}))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"date": self._date, "counts": self.counts}, f, indent=2)

    def _prepare(self, action):
        if action not in self.limits:
            raise ValueError(f"Unknown action '{action}'. Known: {sorted(self.limits)}")
        if self._today() != self._date:          # a new day started: reset counters
            self._date, self.counts = self._today(), {}

    def used(self, action):
        self._prepare(action)
        return self.counts.get(action, 0)

    def remaining(self, action):
        used = self.used(action)          # validates the action name first
        return max(0, self.limits[action] - used)

    def can_do(self, action):
        return self.remaining(action) > 0

    def record(self, action):
        if not self.can_do(action):
            raise RuntimeError(f"Daily limit reached for '{action}'.")
        self.counts[action] = self.counts.get(action, 0) + 1
        self._save()


def human_delay(low=4.0, high=12.0, sleep=time.sleep, rng=random):
    """Sleep for a random time; ~10% of the time add a longer 'distracted' pause."""
    if low < MIN_DELAY or high < low:
        raise ValueError(f"Delays must satisfy {MIN_DELAY} <= low <= high.")
    delay = rng.uniform(low, high)
    if rng.random() < 0.10:
        delay += rng.uniform(high, high * 3)
    sleep(delay)
    return delay


def type_like_human(element, text, sleep=time.sleep, rng=random):
    """Type one character at a time with small random pauses."""
    for ch in text:
        element.send_keys(ch)
        sleep(rng.uniform(0.05, 0.25))


def in_active_hours(start=9, end=22, now=None):
    """True if the current local hour is inside [start, end)."""
    now = now or datetime.now()
    return start <= now.hour < end
