"""`Idempotency-Key` for mutations — 10 §1.6. T-005, TC-SYS-004.

Contract (10 §1.6):
- Stored in Redis with TTL 24 h, keyed by `(user_id, method, path, Idempotency-Key)`.
- Same key + same body → replay the stored response (same status, same body), no new record.
- Same key + different body → `409 IDEMPOTENCY_CONFLICT`.
- Header required on resource-creating/commit mutations (EP-20..23, EP-30..34, EP-40) →
  missing → `400 BAD_REQUEST`.

Usage in a mutation endpoint:

    @router.post("/things", status_code=201, response_model=Envelope[ThingOut])
    async def create_thing(
        body: ThingIn,
        idem: Annotated[Idempotency, Depends(require_idempotency)],
    ) -> Response:
        return await idem.run(lambda: create_and_envelope(body), status_code=201)

`Idempotency.run(fn)` replays the cached response or calls `fn` once, stores and returns it.
Only 2xx responses are stored; an `ApiError`/exception is not cached so the client can retry.
Use `optional_idempotency` for mutations where the header is only recommended.

User identity: auth (`get_current_user`, T-103/T-104) does not exist yet, so the principal is
resolved by the overridable dependency `get_idempotency_user_id`, which returns
`ANONYMOUS_USER_ID`. Once auth lands, override/replace it with the JWT `sub` so keys are scoped
per user as 10 §1.6 requires.

Concurrency: two simultaneous first requests with the same key may both execute (the store has
no in-flight lock). Business commits are additionally protected by `business_records.
idempotency_key` (10 §1.6 last row).
"""

import base64
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from typing import Annotated, Any, Protocol

from fastapi import Depends, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.config import ConfigService, get_config
from app.core.errors import ApiError, ErrorCode

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60  # 10 §1.6
ANONYMOUS_USER_ID = "anonymous"
_KEY_PREFIX = "idem:v1"
_MAX_KEY_LENGTH = 255
# Headers that must not be replayed verbatim (recomputed by the server per response).
_SKIP_REPLAY_HEADERS = frozenset({"content-length", "x-request-id", "date", "server"})


class StoredResponse(BaseModel):
    """What is cached per idempotency key."""

    request_hash: str
    status_code: int
    body_b64: str
    media_type: str | None = None
    headers: dict[str, str] = {}

    def to_response(self) -> Response:
        return Response(
            content=base64.b64decode(self.body_b64),
            status_code=self.status_code,
            media_type=self.media_type,
            headers=self.headers,
        )


class IdempotencyStore(Protocol):
    async def get(self, key: str) -> StoredResponse | None: ...

    async def set(self, key: str, value: StoredResponse, ttl_seconds: int) -> None: ...


class InMemoryIdempotencyStore:
    """Process-local store for tests/dev. Honors TTL using a monotonic clock."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._items: dict[str, tuple[float, StoredResponse]] = {}
        self._clock = clock

    async def get(self, key: str) -> StoredResponse | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._clock() >= expires_at:
            del self._items[key]
            return None
        return value

    async def set(self, key: str, value: StoredResponse, ttl_seconds: int) -> None:
        self._items[key] = (self._clock() + ttl_seconds, value)


class RedisIdempotencyStore:
    """Redis store (10 §1.6). Values are JSON; expiry via Redis `EX`."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> StoredResponse | None:
        raw: bytes | str | None = await self._client.get(key)
        return None if raw is None else StoredResponse.model_validate_json(raw)

    async def set(self, key: str, value: StoredResponse, ttl_seconds: int) -> None:
        await self._client.set(key, value.model_dump_json(), ex=ttl_seconds)


@lru_cache
def _redis_store(redis_url: str) -> RedisIdempotencyStore:
    return RedisIdempotencyStore(Redis.from_url(redis_url))


def get_idempotency_store(
    config: Annotated[ConfigService, Depends(get_config)],
) -> IdempotencyStore:
    """Default store: Redis from `ConfigService.redis_url`. Tests override this dependency."""
    return _redis_store(config.redis_url.get_secret_value())


def get_idempotency_user_id() -> str:
    """Principal for key scoping. Placeholder until T-103/T-104 provide `get_current_user`."""
    return ANONYMOUS_USER_ID


def build_store_key(user_id: str, method: str, path: str, idempotency_key: str) -> str:
    """Hash of `(user_id, method, path, Idempotency-Key)` (10 §1.6) — fixed-size, no raw input."""
    material = json.dumps([user_id, method.upper(), path, idempotency_key])
    return f"{_KEY_PREFIX}:{hashlib.sha256(material.encode()).hexdigest()}"


def hash_request_body(body: bytes) -> str:
    """Fingerprint of the request body; JSON bodies are canonicalized (key order/whitespace)."""
    try:
        canonical = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":")).encode()
    except (ValueError, UnicodeDecodeError):
        canonical = body
    return hashlib.sha256(canonical).hexdigest()


def _render(result: Any, status_code: int) -> Response:
    if isinstance(result, Response):
        return result
    return JSONResponse(content=jsonable_encoder(result), status_code=status_code)


@dataclass
class Idempotency:
    """Per-request handle returned by `require_idempotency` / `optional_idempotency`."""

    store: IdempotencyStore
    key: str | None
    store_key: str | None
    request_hash: str

    async def lookup(self) -> Response | None:
        """Replay a stored response, raise 409 on body mismatch, or return None (first call)."""
        if self.store_key is None:
            return None
        stored = await self.store.get(self.store_key)
        if stored is None:
            return None
        if stored.request_hash != self.request_hash:
            raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT)
        return stored.to_response()

    async def save(self, response: Response) -> None:
        if self.store_key is None or not 200 <= response.status_code < 300:
            return
        headers = {
            k: v for k, v in response.headers.items() if k.lower() not in _SKIP_REPLAY_HEADERS
        }
        await self.store.set(
            self.store_key,
            StoredResponse(
                request_hash=self.request_hash,
                status_code=response.status_code,
                body_b64=base64.b64encode(bytes(response.body)).decode(),
                media_type=response.media_type,
                headers=headers,
            ),
            IDEMPOTENCY_TTL_SECONDS,
        )

    async def run(
        self, handler: Callable[[], Awaitable[Any] | Any], *, status_code: int = 200
    ) -> Response:
        """Replay, or execute `handler` once; a model/dict result is rendered as JSON."""
        replay = await self.lookup()
        if replay is not None:
            return replay
        result = handler()
        if isinstance(result, Awaitable):
            result = await result
        response = _render(result, status_code)
        await self.save(response)
        return response


async def _build(
    request: Request, store: IdempotencyStore, user_id: str, *, required: bool
) -> Idempotency:
    key = request.headers.get(IDEMPOTENCY_HEADER)
    if key is not None:
        key = key.strip()
    if not key:
        if required:
            raise ApiError(
                ErrorCode.BAD_REQUEST,
                f"Missing {IDEMPOTENCY_HEADER} header",
                {"header": IDEMPOTENCY_HEADER},
            )
        return Idempotency(store=store, key=None, store_key=None, request_hash="")
    if len(key) > _MAX_KEY_LENGTH:
        raise ApiError(
            ErrorCode.BAD_REQUEST,
            f"{IDEMPOTENCY_HEADER} is too long",
            {"header": IDEMPOTENCY_HEADER},
        )
    body = await request.body()
    return Idempotency(
        store=store,
        key=key,
        store_key=build_store_key(user_id, request.method, request.url.path, key),
        request_hash=hash_request_body(body),
    )


async def require_idempotency(
    request: Request,
    store: Annotated[IdempotencyStore, Depends(get_idempotency_store)],
    user_id: Annotated[str, Depends(get_idempotency_user_id)],
) -> Idempotency:
    """Dependency for EP-20..23, EP-30..34, EP-40: header mandatory (400 BAD_REQUEST if missing)."""
    return await _build(request, store, user_id, required=True)


async def optional_idempotency(
    request: Request,
    store: Annotated[IdempotencyStore, Depends(get_idempotency_store)],
    user_id: Annotated[str, Depends(get_idempotency_user_id)],
) -> Idempotency:
    """Dependency for other mutations: header recommended; without it `run` just executes."""
    return await _build(request, store, user_id, required=False)
