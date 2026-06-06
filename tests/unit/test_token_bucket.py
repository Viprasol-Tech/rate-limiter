from __future__ import annotations

import pytest

from rate_limiter.clock import FakeClock
from rate_limiter.token_bucket import TokenBucket


def test_allows_up_to_capacity_then_denies() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=3, refill_rate=1.0, clock=clock)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    # capacity exhausted, no time elapsed -> deny
    assert bucket.try_acquire() is False


def test_refills_after_time_advances() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=clock)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    # advance one second -> exactly one token back
    clock.advance(1.0)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_refill_capped_at_capacity() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_rate=10.0, clock=clock)
    # drain fully
    for _ in range(5):
        assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    # advance a long time; should not exceed capacity
    clock.advance(1000.0)
    assert bucket.tokens == pytest.approx(5.0)
    for _ in range(5):
        assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_multi_token_acquire() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=10, refill_rate=1.0, clock=clock)
    assert bucket.try_acquire(4) is True
    assert bucket.try_acquire(6) is True
    assert bucket.try_acquire(1) is False


def test_initial_tokens_clamped() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=5, refill_rate=1.0, clock=clock, initial_tokens=0)
    assert bucket.try_acquire() is False
    clock.advance(1.0)
    assert bucket.try_acquire() is True


def test_time_until_available() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=2.0, clock=clock)
    assert bucket.time_until_available() == 0.0
    bucket.try_acquire(2)
    # need 1 token at 2/s -> 0.5s
    assert bucket.time_until_available(1) == pytest.approx(0.5)


def test_invalid_construction() -> None:
    with pytest.raises(ValueError, match="capacity"):
        TokenBucket(capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError, match="refill_rate"):
        TokenBucket(capacity=1, refill_rate=0.0)


def test_invalid_acquire_amount() -> None:
    bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=FakeClock())
    with pytest.raises(ValueError, match="positive"):
        bucket.try_acquire(0)
    with pytest.raises(ValueError, match="exceed capacity"):
        bucket.time_until_available(99)


@pytest.mark.parametrize(
    ("rate", "wait", "expected"),
    [
        (1.0, 1.0, True),
        (2.0, 0.5, True),
        (1.0, 0.5, False),
        (4.0, 0.25, True),
    ],
)
def test_parametrized_refill_rates(rate: float, wait: float, expected: bool) -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=1, refill_rate=rate, clock=clock)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    clock.advance(wait)
    assert bucket.try_acquire() is expected
