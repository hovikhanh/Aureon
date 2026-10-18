"""Redis-backed fixed-window rate limiter for EP-02 login (10 §1.3 RATE_LIMITED; DEC-080). T-103.

The login endpoint limits attempts **per (email, client IP)** (10 EP-02 "per IP/email"): a single
counter key ``auth:login:{ip}:{email}`` with a fixed window. Using email+IP keeps one noisy client
from locking out everyone while still throttling credential-stuffing against one account.

Design for testability WITHOUT weakening the real limit:

- ``LoginRateLimiter`` takes ``limit`` and ``window_seconds`` as constructor args. Production uses
  :func:`default_login_rate_limiter` (a real limit); a test constructs one with ``limit=2`` or a
  short window, or passes a fake ``redis.Redis``-compatible client, to drive the 429 path fast.
- The limiter never raises on a Redis outage during ``hit`` beyond surfacing it to the caller; it
  does not silently allow unlimited attempts.

``hit`` increments the window counter and returns a :class:`RateLimitResult`; the caller raises the
contract ``RATE_LIMITED`` error (with ``Retry-After``) when ``allowed`` is ``False``.
"""

from __future__ import annotations

from dataclasses import dataclass

import redis

from app.core.config import ConfigService

# Real default (DEC-080): generous enough for a server-side NextAuth caller, tight enough to
# throttle brute force. 10 does not pin the number; these are the proposed defaults (report DEC-RL).
DEFAULT_LOGIN_LIMIT = 10
DEFAULT_LOGIN_WINDOW_SECONDS = 60

_KEY_PREFIX = "auth:login"


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


def _normalise(value: str) -> str:
    # Keep the key bounded and case-insensitive on email; ``:`` would split the key, so drop it.
    return value.strip().lower().replace(":", "_")[:320]


class LoginRateLimiter:
    """Fixed-window counter in Redis, keyed by (ip, email)."""

    def __init__(
        self,
        client: redis.Redis,
        *,
        limit: int = DEFAULT_LOGIN_LIMIT,
        window_seconds: int = DEFAULT_LOGIN_WINDOW_SECONDS,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        self._client = client
        self._limit = limit
        self._window = window_seconds

    @property
    def limit(self) -> int:
        return self._limit

    def _key(self, email: str, ip: str) -> str:
        return f"{_KEY_PREFIX}:{_normalise(ip)}:{_normalise(email)}"

    def hit(self, email: str, ip: str) -> RateLimitResult:
        """Count one attempt in the current window; ``allowed`` is False once over the limit."""
        key = self._key(email, ip)
        pipe = self._client.pipeline()
        pipe.incr(key)
        # Set the TTL only when the counter is first created so the window does not slide on hits.
        pipe.ttl(key)
        count, ttl = pipe.execute()
        count = int(count)
        if ttl is None or ttl < 0:
            self._client.expire(key, self._window)
            ttl = self._window
        allowed = count <= self._limit
        remaining = max(self._limit - count, 0)
        retry_after = int(ttl) if not allowed else 0
        return RateLimitResult(allowed=allowed, remaining=remaining, retry_after=retry_after)


def build_redis(config: ConfigService) -> redis.Redis:
    """A decode-responses Redis client from ``ConfigService.redis_url`` (never a hard-coded URL)."""
    return redis.Redis.from_url(config.redis_url.get_secret_value(), decode_responses=True)


def default_login_rate_limiter(config: ConfigService) -> LoginRateLimiter:
    """Production limiter with the real default limit/window; used as the FastAPI dependency."""
    return LoginRateLimiter(build_redis(config))
