from __future__ import annotations

import pytest

from rate_limiter.clock import FakeClock
from rate_limiter.sliding_window import SlidingWindowLimiter


def test_denies_n_plus_first_within_window() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=3, window_seconds=10.0, clock=clock)
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    # 4th within the window is denied
    assert limiter.try_acquire() is False


def test_allows_after_window_slides() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=5.0, clock=clock)
    assert limiter.try_acquire() is True  # t=0
    assert limiter.try_acquire() is True  # t=0
    assert limiter.try_acquire() is False
    # advance past the window so both timestamps expire
    clock.advance(5.0)
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


def test_partial_slide_frees_one_slot() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=10.0, clock=clock)
    assert limiter.try_acquire() is True  # t=0
    clock.advance(4.0)
    assert limiter.try_acquire() is True  # t=4
    assert limiter.try_acquire() is False
    # advance so only the first (t=0) expires (t=0 + 10 = 10)
    clock.advance(6.0)  # now t=10, cutoff=0 -> t=0 evicted, t=4 stays
    assert limiter.current_count == 1
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


def test_current_count_tracks_live_entries() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=5, window_seconds=2.0, clock=clock)
    limiter.try_acquire()
    limiter.try_acquire()
    assert limiter.current_count == 2
    clock.advance(2.0)
    assert limiter.current_count == 0


def test_time_until_available() -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=3.0, clock=clock)
    assert limiter.time_until_available() == 0.0
    limiter.try_acquire()  # t=0
    clock.advance(1.0)  # t=1
    # oldest at 0 expires at 3, now is 1 -> 2s left
    assert limiter.time_until_available() == pytest.approx(2.0)


def test_invalid_construction() -> None:
    with pytest.raises(ValueError, match="max_requests"):
        SlidingWindowLimiter(max_requests=0, window_seconds=1.0)
    with pytest.raises(ValueError, match="window_seconds"):
        SlidingWindowLimiter(max_requests=1, window_seconds=0.0)


@pytest.mark.parametrize(
    ("max_requests", "window"),
    [(1, 1.0), (5, 10.0), (10, 0.5)],
)
def test_parametrized_capacity(max_requests: int, window: float) -> None:
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_requests=max_requests, window_seconds=window, clock=clock)
    for _ in range(max_requests):
        assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False
    clock.advance(window)
    assert limiter.try_acquire() is True
