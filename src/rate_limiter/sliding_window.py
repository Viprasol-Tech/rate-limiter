"""Sliding-window rate limiter.

Allows at most ``max_requests`` events within any rolling window of
``window_seconds``. Unlike a fixed window (which resets on a boundary and lets
through 2x the limit straddling the boundary), the sliding log tracks the
timestamp of every recent hit and expires those older than the window, giving
an exact rolling count.

The clock is injected (``Callable[[], float]``) so the window slides by elapsed
time rather than real sleeping, making the limiter deterministic.

Part of Rate Limiter by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections import deque

from rate_limiter.clock import Clock, monotonic_clock


class SlidingWindowLimiter:
    """A sliding-log rate limiter.

    Each allowed request appends the current time to a deque; expired entries
    (older than ``window_seconds``) are evicted from the left on every call.
    A request is allowed only if fewer than ``max_requests`` live entries
    remain.

    Args:
        max_requests: Maximum allowed requests within any window. Must be a
            positive integer.
        window_seconds: Length of the rolling window in seconds. Must be
            positive.
        clock: Time source in seconds. Defaults to :func:`monotonic_clock`.

    Example:
        >>> from rate_limiter.clock import FakeClock
        >>> clock = FakeClock()
        >>> limiter = SlidingWindowLimiter(max_requests=2, window_seconds=10, clock=clock)
        >>> limiter.try_acquire()
        True
        >>> limiter.try_acquire()
        True
        >>> limiter.try_acquire()
        False
        >>> _ = clock.advance(10.0)
        >>> limiter.try_acquire()
        True
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Clock = monotonic_clock,
    ) -> None:
        """Initialise the limiter, validating ``max_requests`` and window."""
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = int(max_requests)
        self.window_seconds = float(window_seconds)
        self._clock = clock
        self._hits: deque[float] = deque()

    def _evict(self, now: float) -> None:
        """Drop timestamps that have slid out of the current window."""
        cutoff = now - self.window_seconds
        hits = self._hits
        while hits and hits[0] <= cutoff:
            hits.popleft()

    @property
    def current_count(self) -> int:
        """Number of live requests in the window right now."""
        self._evict(self._clock())
        return len(self._hits)

    def try_acquire(self) -> bool:
        """Attempt to record one request against the window.

        Evicts expired timestamps, then allows the request (recording its
        timestamp) only if the live count is below ``max_requests``.

        Returns:
            ``True`` if the request is allowed, otherwise ``False`` (nothing is
            recorded on denial).
        """
        now = self._clock()
        self._evict(now)
        if len(self._hits) < self.max_requests:
            self._hits.append(now)
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until the next request would be allowed.

        Returns ``0.0`` if a request is allowed right now; otherwise the time
        until the oldest live timestamp expires out of the window.
        """
        now = self._clock()
        self._evict(now)
        if len(self._hits) < self.max_requests:
            return 0.0
        oldest = self._hits[0]
        return (oldest + self.window_seconds) - now
