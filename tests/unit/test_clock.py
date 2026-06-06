from __future__ import annotations

import pytest

from rate_limiter.clock import FakeClock, monotonic_clock


def test_fake_clock_starts_at_given_value() -> None:
    assert FakeClock(start=3.5)() == 3.5


def test_fake_clock_advance_returns_new_time() -> None:
    clock = FakeClock()
    assert clock.advance(2.0) == 2.0
    assert clock.advance(0.5) == 2.5
    assert clock() == 2.5


def test_fake_clock_set_absolute() -> None:
    clock = FakeClock(start=1.0)
    assert clock.set(5.0) == 5.0
    assert clock() == 5.0


def test_fake_clock_rejects_negative_advance() -> None:
    clock = FakeClock()
    with pytest.raises(ValueError, match="negative"):
        clock.advance(-1.0)


def test_fake_clock_rejects_backwards_set() -> None:
    clock = FakeClock(start=5.0)
    with pytest.raises(ValueError, match="earlier"):
        clock.set(1.0)


def test_monotonic_clock_is_non_decreasing() -> None:
    first = monotonic_clock()
    second = monotonic_clock()
    assert second >= first
