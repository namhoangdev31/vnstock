"""Minimal monotonic rate limiter for outbound vnstock requests.

AGENTS.md §7.2 mandates a 0.2–0.5s minimum spacing between batch requests to
external data providers to avoid IP blacklisting. The limiter enforces that
spacing across all calls that pass through it. ``clock`` and ``sleep`` are
injectable so tests can assert throttle behavior without real delays.
"""

import threading
import time
from collections.abc import Callable


class RateLimiter:
    """Thread-safe minimum-interval throttle."""

    def __init__(
        self,
        min_delay: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_delay = min_delay
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_call: float | None = None

    def wait(self) -> float:
        """Block until ``min_delay`` has elapsed since the previous call.

        Returns the number of seconds actually slept (0.0 if no wait was needed).
        """
        with self._lock:
            now = self._clock()
            if self._last_call is None:
                self._last_call = now
                return 0.0
            elapsed = now - self._last_call
            remaining = self.min_delay - elapsed
            if remaining > 0:
                self._sleep(remaining)
                slept = remaining
            else:
                slept = 0.0
            self._last_call = self._clock()
            return slept
