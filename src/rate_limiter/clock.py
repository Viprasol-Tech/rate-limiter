"""Clock abstraction for deterministic rate limiting.

A ``Clock`` is simply a ``Callable[[], float]`` returning seconds. The default
production clock is :func:`time.monotonic`, which never goes backwards. Tests
inject a :class:`FakeClock` so time can be advanced explicitly with no real
sleeping, making every limiter fully deterministic.

Part of Rate Limiter by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import time
from collections.abc import Callable

Clock = Callable[[], float]
"""A zero-argument callable returning the current time in seconds (float)."""


def monotonic_clock() -> float:
    """Return a monotonically increasing time in seconds.

    Wraps :func:`time.monotonic`. Use this as the default clock in production;
    it is immune to wall-clock adjustments (NTP steps, DST) that could make a
    naive limiter briefly grant or deny requests incorrectly.
    """
    return time.monotonic()


class FakeClock:
    """A manually advanced clock for deterministic tests.

    The clock starts at ``start`` and only moves when :meth:`advance` or
    :meth:`set` is called, so limiter behaviour can be asserted exactly without
    waiting on real time.

    Example:
        >>> clock = FakeClock(start=0.0)
        >>> clock()
        0.0
        >>> clock.advance(2.5)
        2.5
        >>> clock()
        2.5
    """

    def __init__(self, start: float = 0.0) -> None:
        """Create a clock fixed at ``start`` seconds."""
        self._now = float(start)

    def __call__(self) -> float:
        """Return the current (frozen) time in seconds."""
        return self._now

    def advance(self, seconds: float) -> float:
        """Advance the clock by ``seconds`` and return the new time.

        Raises:
            ValueError: if ``seconds`` is negative (a clock must not rewind).
        """
        if seconds < 0:
            raise ValueError("cannot advance a clock by a negative amount")
        self._now += float(seconds)
        return self._now

    def set(self, now: float) -> float:
        """Set the clock to an absolute ``now`` and return it.

        Raises:
            ValueError: if ``now`` is earlier than the current time.
        """
        value = float(now)
        if value < self._now:
            raise ValueError("cannot set a clock to an earlier time")
        self._now = value
        return self._now
