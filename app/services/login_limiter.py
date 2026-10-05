"""Remember failed logins per email so passwords cannot be guessed quickly.

The counters live in memory: they reset when the service restarts, and this
assumes a single worker process. A blocked email is rejected without even
checking the password, so the answer does not reveal whether the account exists.
"""

import time
from collections import deque

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60
MAX_TRACKED = 10_000

_failures: dict[str, deque[float]] = {}


def _recent(key: str, now: float) -> deque[float] | None:
    attempts = _failures.get(key)
    if attempts is None:
        return None
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        del _failures[key]
        return None
    return attempts


def is_blocked(key: str, now: float | None = None) -> bool:
    now = time.monotonic() if now is None else now
    attempts = _recent(key, now)
    return attempts is not None and len(attempts) >= MAX_FAILURES


def retry_after(key: str, now: float | None = None) -> int:
    now = time.monotonic() if now is None else now
    attempts = _recent(key, now)
    if not attempts:
        return 0
    return max(1, int(attempts[0] + WINDOW_SECONDS - now) + 1)


def record_failure(key: str, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    if key not in _failures and len(_failures) >= MAX_TRACKED:
        _failures.clear()  # crude safety valve so memory cannot grow without limit
    _failures.setdefault(key, deque()).append(now)


def reset(key: str) -> None:
    _failures.pop(key, None)


def clear_all() -> None:
    _failures.clear()
