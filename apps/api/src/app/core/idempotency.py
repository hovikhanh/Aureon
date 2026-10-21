"""`Idempotency-Key` for create / action `POST`s (10 §1.6).

Usage in a route:

    async def create(body: X, idem: Idem, ...) -> Out:
        if (hit := await idem.replay(body)) is not None:
            return Out.model_validate(hit)
        out = await svc.create(...)
        await idem.remember(out)
        return out

Storage: Redis, TTL 24 h, key `(user_id, method, path, Idempotency-Key)` → `{body_sha256,
response}`. Missing header → `400 BAD_REQUEST`; same key + different body →
`409 IDEMPOTENCY_CONFLICT`. Redis unreachable → `503 DEPENDENCY_UNAVAILABLE` (fail closed:
a silent duplicate write is worse than a retryable error).
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_config
from app.core.deps import CurrentUser
from app.core.errors import (
    BadRequestError,
    DependencyUnavailableError,
    IdempotencyConflictError,
)

TTL_SECONDS = 24 * 3600
_PREFIX = "idem:v1"


def _redis() -> Redis:
    """Fresh client per call: no pool bound to a closed event loop (tests, workers)."""
    return Redis.from_url(get_config().redis_url.get_secret_value())


def _sha(body: Any) -> str:
    if isinstance(body, BaseModel):
        raw = body.model_dump_json()
    else:
        raw = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Idempotency:
    redis_key: str
    body_sha: str | None = None

    async def replay(self, body: Any) -> Any | None:
        """Stored response for this key, `None` on first use; conflicting body → 409."""
        self.body_sha = _sha(body)
        try:
            async with _redis() as r:
                raw = await r.get(self.redis_key)
        except RedisError as exc:
            raise DependencyUnavailableError("idempotency store unavailable") from exc
        if raw is None:
            return None
        stored = json.loads(raw)
        if stored.get("body_sha256") != self.body_sha:
            raise IdempotencyConflictError("Idempotency-Key reused with a different body")
        return stored.get("response")

    async def remember(self, response: Any) -> None:
        payload = response.model_dump(mode="json") if isinstance(response, BaseModel) else response
        doc = json.dumps({"body_sha256": self.body_sha, "response": payload}, default=str)
        try:
            async with _redis() as r:
                await r.set(self.redis_key, doc, ex=TTL_SECONDS)
        except RedisError as exc:
            raise DependencyUnavailableError("idempotency store unavailable") from exc


async def idempotency(
    request: Request,
    user: CurrentUser,
    key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Idempotency:
    if key is None or not key.strip():
        raise BadRequestError(
            "Idempotency-Key header is required", details={"header": "Idempotency-Key"}
        )
    try:
        norm = str(uuid.UUID(key.strip()))
    except ValueError as exc:
        raise BadRequestError(
            "Idempotency-Key must be a UUID", details={"header": "Idempotency-Key"}
        ) from exc
    redis_key = f"{_PREFIX}:{user.user_id}:{request.method}:{request.url.path}:{norm}"
    return Idempotency(redis_key=redis_key)


Idem = Annotated[Idempotency, Depends(idempotency)]
