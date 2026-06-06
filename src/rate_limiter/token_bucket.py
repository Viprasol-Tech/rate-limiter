"""Token-bucket rate limiter.

A token bucket holds up to ``capacity`` tokens and refills continuously at
``refill_rate`` tokens per second. Each acquire removes ``n`` tokens; if fewer
than ``n`` are available the acquire is denied. This permits short bursts up to
``capacity`` while bounding the long-run average rate to ``refill_rate``.

The clock is injected (``Callable[[], float]``) so refilling is computed from
elapsed time rather than real sleeping, making the limiter deterministic.

Part of Rate Limiter by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from rate_limiter.clock import Clock, monotonic_clock


class TokenBucket:
    """A classic token-bucket limiter with continuous, lazy refilling.

    Tokens are not refilled on a timer; instead the bucket records the last
    time it was touched and, on each call, adds ``elapsed * refill_rate`` tokens
    (capped at ``capacity``). This "lazy" approach is exact and allocation-free.

    Args:
        capacity: Maximum number of tokens the bucket can hold (the burst size).
            Must be positive.
        refill_rate: Tokens added per second. Must be positive.
        clock: Time source in seconds. Defaults to :func:`monotonic_clock`.
        initial_tokens: Starting token count. Defaults to ``capacity`` (a full
            bucket). Clamped to ``[0, capacity]``.

    Example:
        >>> from rate_limiter.clock import FakeClock
        >>> clock = FakeClock()
        >>> bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=clock)
        >>> bucket.try_acquire()
        True
        >>> bucket.try_acquire()
        True
        >>> bucket.try_acquire()
        False
        >>> _ = clock.advance(1.0)
        >>> bucket.try_acquire()
        True
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        clock: Clock = monotonic_clock,
        initial_tokens: float | None = None,
    ) -> None:
        """Initialise the bucket, validating ``capacity`` and ``refill_rate``."""
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._clock = clock
        start = self.capacity if initial_tokens is None else float(initial_tokens)
        self._tokens = max(0.0, min(self.capacity, start))
        self._last = clock()

    def _refill(self) -> None:
        """Add tokens accrued since the last update, capped at ``capacity``."""
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last = now

    @property
    def tokens(self) -> float:
        """Current available tokens (after bringing the bucket up to date)."""
        self._refill()
        return self._tokens

    def try_acquire(self, n: float = 1) -> bool:
        """Attempt to consume ``n`` tokens.

        Refills lazily based on elapsed time, then removes ``n`` tokens if at
        least that many are available.

        Args:
            n: Number of tokens to consume. Must be positive.

        Returns:
            ``True`` if the tokens were consumed (request allowed), otherwise
            ``False`` (request denied; no tokens are removed).
        """
        if n <= 0:
            raise ValueError("n must be positive")
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def time_until_available(self, n: float = 1) -> float:
        """Seconds until ``n`` tokens would be available.

        Returns ``0.0`` if ``n`` tokens are already available. Useful for
        deciding how long a caller should back off before retrying.

        Args:
            n: Number of tokens desired. Must be positive and not exceed
                ``capacity`` (more than capacity can never accumulate).
        """
        if n <= 0:
            raise ValueError("n must be positive")
        if n > self.capacity:
            raise ValueError("n cannot exceed capacity")
        self._refill()
        if self._tokens >= n:
            return 0.0
        deficit = n - self._tokens
        return deficit / self.refill_rate
