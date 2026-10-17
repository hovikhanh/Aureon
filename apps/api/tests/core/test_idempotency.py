"""TC-SYS-004 — Idempotency-Key replay / conflict / missing header (10 §1.6, T-005)."""

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_config
from app.core.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
    StoredResponse,
    build_store_key,
    get_idempotency_store,
    get_idempotency_user_id,
    hash_request_body,
)

from .conftest import Counter

URL = "/api/v1/_test/items"
BODY = {"name": "laptop", "qty": 2}


def _key() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


def test_same_key_same_body_replays_same_response(client: TestClient, counter: Counter) -> None:
    headers = _key()
    first = client.post(URL, json=BODY, headers=headers)
    second = client.post(URL, json=BODY, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json() == {"data": {"id": 1, "name": "laptop", "qty": 2}}
    assert len(counter.created) == 1  # 1 record only
    # Replay still gets its own request id (10 §1.2).
    assert first.headers["X-Request-Id"] != second.headers["X-Request-Id"]
    assert second.headers["content-type"] == "application/json"


def test_same_body_with_different_key_order_is_same_request(
    client: TestClient, counter: Counter
) -> None:
    headers = {**_key(), "Content-Type": "application/json"}
    client.post(URL, content=b'{"name":"laptop","qty":2}', headers=headers)
    resp = client.post(URL, content=b'{ "qty": 2, "name": "laptop" }', headers=headers)
    assert resp.status_code == 201
    assert len(counter.created) == 1


def test_same_key_different_body_returns_409(client: TestClient, counter: Counter) -> None:
    headers = _key()
    assert client.post(URL, json=BODY, headers=headers).status_code == 201
    resp = client.post(URL, json={"name": "laptop", "qty": 3}, headers=headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert len(counter.created) == 1


def test_different_keys_create_two_records(client: TestClient, counter: Counter) -> None:
    client.post(URL, json=BODY, headers=_key())
    client.post(URL, json=BODY, headers=_key())
    assert len(counter.created) == 2


@pytest.mark.parametrize("headers", [{}, {"Idempotency-Key": "   "}])
def test_missing_header_on_required_endpoint_returns_400(
    client: TestClient, counter: Counter, headers: dict[str, str]
) -> None:
    resp = client.post(URL, json=BODY, headers=headers)
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "BAD_REQUEST"
    assert err["details"] == {"header": "Idempotency-Key"}
    assert counter.created == []


def test_too_long_key_returns_400(client: TestClient) -> None:
    resp = client.post(URL, json=BODY, headers={"Idempotency-Key": "k" * 256})
    assert resp.status_code == 400


def test_key_scoped_per_user(test_app: FastAPI, counter: Counter) -> None:
    headers = _key()
    with TestClient(test_app) as c:
        c.post(URL, json=BODY, headers=headers)
        test_app.dependency_overrides[get_idempotency_user_id] = lambda: "user-b"
        resp = c.post(URL, json={"name": "other", "qty": 1}, headers=headers)
    assert resp.status_code == 201  # no conflict: different (user_id, ...) tuple
    assert len(counter.created) == 2


def test_key_scoped_per_path(client: TestClient, counter: Counter) -> None:
    headers = _key()
    client.post(URL, json=BODY, headers=headers)
    resp = client.post("/api/v1/_test/items-optional", json=BODY, headers=headers)
    assert resp.status_code == 200
    assert len(counter.created) == 2


def test_optional_endpoint_without_header_always_executes(
    client: TestClient, counter: Counter
) -> None:
    for _ in range(2):
        assert client.post("/api/v1/_test/items-optional", json=BODY).status_code == 200
    assert len(counter.created) == 2


def test_optional_endpoint_with_header_replays(client: TestClient, counter: Counter) -> None:
    headers = _key()
    a = client.post("/api/v1/_test/items-optional", json=BODY, headers=headers)
    b = client.post("/api/v1/_test/items-optional", json=BODY, headers=headers)
    assert a.json() == b.json()
    assert len(counter.created) == 1


def test_errors_are_not_cached(client: TestClient, counter: Counter) -> None:
    headers = _key()
    for _ in range(2):
        resp = client.post("/api/v1/_test/items-fail", json=BODY, headers=headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONFLICT_STATE"
    assert len(counter.created) == 2  # handler re-ran: failure not replayed


def test_store_key_hashes_tuple() -> None:
    k1 = build_store_key("u", "post", "/p", "k")
    assert k1 == build_store_key("u", "POST", "/p", "k")
    assert k1 != build_store_key("u2", "POST", "/p", "k")
    assert k1 != build_store_key("u", "POST", "/p2", "k")
    assert "/p" not in k1 and k1.startswith("idem:v1:")


def test_hash_request_body_non_json() -> None:
    assert hash_request_body(b"\xff\xfe") == hash_request_body(b"\xff\xfe")
    assert hash_request_body(b"a") != hash_request_body(b"b")


def test_in_memory_store_ttl_expiry() -> None:
    now = [0.0]
    store = InMemoryIdempotencyStore(clock=lambda: now[0])
    value = StoredResponse(request_hash="h", status_code=201, body_b64="e30=")

    async def scenario() -> tuple[object, object, object]:
        await store.set("k", value, IDEMPOTENCY_TTL_SECONDS)
        now[0] = IDEMPOTENCY_TTL_SECONDS - 1
        hit = await store.get("k")
        now[0] = IDEMPOTENCY_TTL_SECONDS
        miss = await store.get("k")
        return hit, miss, await store.get("absent")

    hit, miss, absent = asyncio.run(scenario())
    assert hit == value
    assert miss is None and absent is None


def test_default_store_is_redis() -> None:
    store = get_idempotency_store(get_config())
    assert isinstance(store, RedisIdempotencyStore)


@pytest.fixture
def redis_client(test_app: FastAPI) -> Iterator[TestClient]:
    from redis.asyncio import Redis

    url = get_config().redis_url.get_secret_value()
    # Fresh client per test so it binds to the TestClient event loop.
    test_app.dependency_overrides[get_idempotency_store] = lambda: RedisIdempotencyStore(
        Redis.from_url(url)
    )
    with TestClient(test_app) as c:
        yield c


@pytest.mark.integration
def test_redis_store_replay_conflict_and_ttl(redis_client: TestClient, counter: Counter) -> None:
    import redis as redis_sync

    headers = _key()
    first = redis_client.post(URL, json=BODY, headers=headers)
    second = redis_client.post(URL, json=BODY, headers=headers)
    conflict = redis_client.post(URL, json={"name": "x", "qty": 9}, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert len(counter.created) == 1

    sync = redis_sync.Redis.from_url(get_config().redis_url.get_secret_value())
    key = build_store_key("anonymous", "POST", URL, headers["Idempotency-Key"])
    ttl = sync.ttl(key)
    assert isinstance(ttl, int) and 0 < ttl <= IDEMPOTENCY_TTL_SECONDS
    sync.delete(key)
    sync.close()
