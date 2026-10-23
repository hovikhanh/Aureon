"""10 §1.6 — `Idempotency-Key` on create / action POSTs (Redis, 24 h)."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from redis.exceptions import RedisError

from app.core import idempotency as idem_mod
from app.core.base_model import DEFAULT_TENANT_ID
from app.core.handlers import install_error_handlers
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.core.security import sign_access_token

pytestmark = pytest.mark.integration


class Body(BaseModel):
    name: str


class Out(BaseModel):
    id: uuid.UUID
    name: str


CALLS: list[str] = []


def _app() -> FastAPI:
    router = EnvelopeRouter()

    @router.post("/things", response_model=Out, status_code=201)
    async def create(body: Body, idem: Idem) -> Any:
        if (hit := await idem.replay(body)) is not None:
            return Out.model_validate(hit)
        CALLS.append(body.name)
        out = Out(id=uuid.uuid4(), name=body.name)
        await idem.remember(out)
        return out

    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    return app


def _auth() -> dict[str, str]:
    token, _ = sign_access_token(
        user_id=uuid.uuid4(), email="cfo@abc.test", role="CFO", role_id="r",
        permissions=["finance:write"], department_id=None, tenant_id=DEFAULT_TENANT_ID,
    )  # fmt: skip
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app()), base_url="http://test"
    ) as c:
        yield c


async def test_same_key_same_body_replays_without_second_write(client: httpx.AsyncClient) -> None:
    h = {**_auth(), "Idempotency-Key": str(uuid.uuid4())}
    before = len(CALLS)
    r1 = await client.post("/things", json={"name": "a"}, headers=h)
    r2 = await client.post("/things", json={"name": "a"}, headers=h)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["data"] == r2.json()["data"]
    assert len(CALLS) == before + 1


async def test_same_key_other_body_conflicts(client: httpx.AsyncClient) -> None:
    h = {**_auth(), "Idempotency-Key": str(uuid.uuid4())}
    assert (await client.post("/things", json={"name": "a"}, headers=h)).status_code == 201
    r = await client.post("/things", json={"name": "b"}, headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize("key", [None, "", "not-a-uuid"])
async def test_missing_or_invalid_key_is_400(client: httpx.AsyncClient, key: str | None) -> None:
    h = _auth() if key is None else {**_auth(), "Idempotency-Key": key}
    r = await client.post("/things", json={"name": "a"}, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_REQUEST"


async def test_keys_are_scoped_per_user(client: httpx.AsyncClient) -> None:
    key = str(uuid.uuid4())
    before = len(CALLS)
    for _ in range(2):  # two different users (fresh token = fresh user id)
        h = {**_auth(), "Idempotency-Key": key}
        assert (await client.post("/things", json={"name": "x"}, headers=h)).status_code == 201
    assert len(CALLS) == before + 2


async def test_redis_down_fails_closed(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Broken:
        async def __aenter__(self) -> "Broken":
            raise RedisError("down")

        async def __aexit__(self, *a: object) -> None:  # pragma: no cover
            return None

    monkeypatch.setattr(idem_mod, "_redis", lambda: Broken())
    h = {**_auth(), "Idempotency-Key": str(uuid.uuid4())}
    r = await client.post("/things", json={"name": "a"}, headers=h)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
