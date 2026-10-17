"""Idempotent Celery base task keyed by task id (T-007; 07 §5.1; TC-IDP-035).

CLAUDE.md § Celery: "task không idempotent → retry tạo duplicate. Mọi task phải
idempotent (dùng task_id)". 07 §5.1 fixes the deterministic task id format
``{document_id}:{step}:{attempt_key}``: enqueue with ``task_id=...`` so a re-enqueue or
broker redelivery (``task_acks_late``) of the same step carries the same id.

Guard protocol (per execution of ``IdempotentTask.__call__``):

1. ``is_already_processed(key)`` — domain hook, default ``False``. T-211 overrides it to
   check DB state (e.g. ENT-ExtractionJob already past this step) so idempotency also
   holds after the Redis marker expired. Real DB-level uniqueness for
   ``extracted_fields`` is T-211's job; this layer only prevents re-running the body.
2. ``store.acquire(key, lock_ttl)`` — atomic claim (Redis ``SET NX EX``). Lost claim →
   another run is in progress or already finished → skip via ``celery.exceptions.Ignore``
   (body not run, stored result of the first run left untouched).
3. Body runs. Success → ``store.complete(key, result_expires)`` marks the key done.
   Any exception (incl. ``self.retry()``'s ``Retry`` and ``SoftTimeLimitExceeded``) →
   ``store.release(key)`` so the retry with the same task id may run again.

The lock TTL is ``time_limit`` + margin, so a worker killed mid-task (hard limit, OOM)
cannot block the redelivered message forever.
"""

import logging
import threading
import time
from typing import Any, ClassVar, Final, Protocol

import redis

# celery 5.6 ships no py.typed and adding stub deps is forbidden (CLAUDE.md "Cấm tự quyết"
# #4); scoped to this import line.
from celery import Task  # type: ignore[import-untyped]
from celery.exceptions import Ignore  # type: ignore[import-untyped]  # same reason

from app.core.config import get_config

logger = logging.getLogger(__name__)

KEY_PREFIX: Final = "aureon:celery:idem:"
_RUNNING: Final = "running"
_DONE: Final = "done"
LOCK_MARGIN_S: Final = 30
_RELEASE_LUA: Final = (
    "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0"
)
# 07 §5.1 retry backoff 2s → 8s → 30s (04 IDP-E06).
RETRY_BACKOFF_S: Final = (2, 8, 30)


class IdempotencyStore(Protocol):
    """Injectable "already-processed" store (Redis in prod, in-memory in tests)."""

    def acquire(self, key: str, ttl_s: int) -> bool:
        """Atomically claim ``key``; False if it is running or done."""
        ...

    def complete(self, key: str, ttl_s: int) -> None:
        """Mark ``key`` done for ``ttl_s`` seconds."""
        ...

    def release(self, key: str) -> None:
        """Drop a claim after a failed run so a retry can proceed."""
        ...

    def is_done(self, key: str) -> bool: ...


class RedisIdempotencyStore:
    """SET NX + expiry on ``REDIS_URL`` (07 §7), separate DB from broker/results."""

    def __init__(self, client: "redis.Redis") -> None:
        self._r = client

    @classmethod
    def from_config(cls) -> "RedisIdempotencyStore":
        url = get_config().redis_url.get_secret_value()
        return cls(redis.Redis.from_url(url, decode_responses=True))

    def acquire(self, key: str, ttl_s: int) -> bool:
        return bool(self._r.set(KEY_PREFIX + key, _RUNNING, nx=True, ex=ttl_s))

    def complete(self, key: str, ttl_s: int) -> None:
        self._r.set(KEY_PREFIX + key, _DONE, ex=ttl_s)

    def release(self, key: str) -> None:
        # Atomic compare-and-delete: only drop a running claim, never a completed marker.
        self._r.eval(_RELEASE_LUA, 1, KEY_PREFIX + key, _RUNNING)

    def is_done(self, key: str) -> bool:
        return self._r.get(KEY_PREFIX + key) == _DONE


class InMemoryIdempotencyStore:
    """Process-local store for tests / eager mode (not shared across workers)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, tuple[str, float]] = {}

    def _get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None or item[1] <= time.monotonic():
            self._data.pop(key, None)
            return None
        return item[0]

    def acquire(self, key: str, ttl_s: int) -> bool:
        with self._lock:
            if self._get(key) is not None:
                return False
            self._data[key] = (_RUNNING, time.monotonic() + ttl_s)
            return True

    def complete(self, key: str, ttl_s: int) -> None:
        with self._lock:
            self._data[key] = (_DONE, time.monotonic() + ttl_s)

    def release(self, key: str) -> None:
        with self._lock:
            if self._get(key) == _RUNNING:
                del self._data[key]

    def is_done(self, key: str) -> bool:
        with self._lock:
            return self._get(key) == _DONE


_default_store: IdempotencyStore | None = None
_default_store_lock = threading.Lock()


def get_default_store() -> IdempotencyStore:
    """Lazily built Redis store (no connection at import → worker/tests import cheaply)."""
    global _default_store
    with _default_store_lock:
        if _default_store is None:
            _default_store = RedisIdempotencyStore.from_config()
        return _default_store


def retry_countdown(retries: int) -> int:
    """07 §5.1 backoff for the n-th retry (0-based): 2s, 8s, 30s."""
    return RETRY_BACKOFF_S[min(retries, len(RETRY_BACKOFF_S) - 1)]


# Subclassing Celery's untyped Task (Any) is unavoidable without stubs (see import note).
class IdempotentTask(Task):  # type: ignore[misc]
    """Base for every Aureon task (set as ``task_cls`` in app.worker)."""

    abstract = True
    max_retries = len(RETRY_BACKOFF_S)  # 07 §5.1: max 3 retries
    # Inject a store per task (tests: InMemoryIdempotencyStore); None → Redis default.
    idempotency_store: ClassVar[IdempotencyStore | None] = None

    def get_store(self) -> IdempotencyStore:
        return self.idempotency_store or get_default_store()

    def idempotency_key(self) -> str | None:
        """Key for the current execution; default ``{task name}:{task id}``.

        None (direct ``task()`` call outside Celery, no request id) → no guard.
        """
        task_id = self.request.id
        return None if task_id is None else f"{self.name}:{task_id}"

    def is_already_processed(self, key: str) -> bool:
        """Domain-state hook (T-211: check ENT-ExtractionJob / extracted_fields in DB)."""
        return False

    def _ttls(self) -> tuple[int, int]:
        conf = self.app.conf
        time_limit = self.time_limit or conf.task_time_limit or 0
        expires = conf.result_expires
        done_ttl = int(expires.total_seconds()) if hasattr(expires, "total_seconds") else expires
        return int(time_limit) + LOCK_MARGIN_S, int(done_ttl or 24 * 60 * 60)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        key = self.idempotency_key()
        if key is None:
            return super().__call__(*args, **kwargs)
        store = self.get_store()
        lock_ttl, done_ttl = self._ttls()
        if self.is_already_processed(key) or not store.acquire(key, lock_ttl):
            logger.info("idempotent skip: %s already running or processed", key)
            # Ignore → Celery does not write a new state, so the first run's stored
            # result (within result_expires) is preserved instead of being overwritten.
            raise Ignore()
        try:
            result = super().__call__(*args, **kwargs)
        except BaseException:
            store.release(key)
            raise
        store.complete(key, done_ttl)
        return result
