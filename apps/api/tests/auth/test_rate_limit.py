"""Unit tests for the login rate limiter — fixed window, configurable (10 §1.3). T-103.

Driven with a tiny in-memory fake Redis so the limiter logic (counting, window, per-key isolation)
is covered without a live Redis, proving the limiter is injectable/configurable for tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.auth.rate_limit import (
    DEFAULT_LOGIN_LIMIT,
    DEFAULT_LOGIN_WINDOW_SECONDS,
    LoginRateLimiter,
)


class _FakePipeline:
    def __init__(self, store: _FakeRedis) -> None:
        self._store = store
        self._ops: list[tuple[str, tuple[Any, ...]]] = []

    def incr(self, key: str) -> _FakePipeline:
        self._ops.append(("incr", (key,)))
        return self

    def ttl(self, key: str) -> _FakePipeline:
        self._ops.append(("ttl", (key,)))
        return self

    def execute(self) -> list[Any]:
        return [getattr(self._store, op)(*args) for op, args in self._ops]


class _FakeRedis:
    """Minimal Redis stand-in: incr/ttl/expire/pipeline, with explicit TTL bookkeeping."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

    def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = seconds
        return True

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline(self)


def test_defaults_are_a_real_limit() -> None:
    assert DEFAULT_LOGIN_LIMIT >= 1
    assert DEFAULT_LOGIN_WINDOW_SECONDS >= 1


def test_allows_up_to_limit_then_blocks() -> None:
    limiter = LoginRateLimiter(_FakeRedis(), limit=3, window_seconds=60)  # type: ignore[arg-type]
    results = [limiter.hit("ceo@abc.demo", "10.0.0.1") for _ in range(4)]
    assert [r.allowed for r in results] == [True, True, True, False]
    assert results[-1].retry_after > 0
    assert results[0].remaining == 2


def test_window_ttl_set_once_and_not_slid() -> None:
    fake = _FakeRedis()
    limiter = LoginRateLimiter(fake, limit=5, window_seconds=30)  # type: ignore[arg-type]
    limiter.hit("a@abc.demo", "10.0.0.1")
    key = limiter._key("a@abc.demo", "10.0.0.1")
    assert fake.ttls[key] == 30
    fake.ttls[key] = 12  # simulate time passing
    limiter.hit("a@abc.demo", "10.0.0.1")
    assert fake.ttls[key] == 12  # TTL not reset on a subsequent hit


def test_different_email_or_ip_are_isolated() -> None:
    limiter = LoginRateLimiter(_FakeRedis(), limit=1, window_seconds=60)  # type: ignore[arg-type]
    assert limiter.hit("a@abc.demo", "10.0.0.1").allowed
    assert limiter.hit("b@abc.demo", "10.0.0.1").allowed  # different email → own counter
    assert limiter.hit("a@abc.demo", "10.0.0.2").allowed  # different ip → own counter
    assert not limiter.hit("a@abc.demo", "10.0.0.1").allowed  # same key over limit


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValueError):
        LoginRateLimiter(_FakeRedis(), limit=0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        LoginRateLimiter(_FakeRedis(), window_seconds=0)  # type: ignore[arg-type]
