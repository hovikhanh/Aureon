"""TC-SYS-004 — `limit/offset/sort_by/order` (10 §1.5, DEC-130): defaults, max, whitelist."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.envelope import Page, page_meta
from app.core.handlers import install_error_handlers
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageParams, page_params
from app.core.routing import EnvelopeRouter

DATA = list(range(47))
Params = Annotated[PageParams, Depends(page_params("amount"))]


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    r = EnvelopeRouter()

    @r.get("/n", response_model=list[int])
    async def numbers(p: Params) -> Page[int]:
        ordered = sorted(DATA, reverse=p.order == "desc")
        return Page(
            items=ordered[p.offset : p.offset + p.limit],
            total=len(DATA),
            limit=p.limit,
            offset=p.offset,
        )

    @r.get("/params", response_model=dict[str, str | int])
    async def echo(p: Params) -> dict[str, str | int]:
        return {"limit": p.limit, "offset": p.offset, "sort_by": p.sort_by, "order": p.order}

    app.include_router(r)
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_app())


def test_defaults(client: TestClient) -> None:
    assert client.get("/params").json()["data"] == {
        "limit": DEFAULT_LIMIT,
        "offset": 0,
        "sort_by": "created_at",
        "order": "desc",
    }
    body = client.get("/n").json()
    assert len(body["data"]) == 20
    assert body["meta"]["pagination"] == {"total": 47, "limit": 20, "offset": 0, "has_next": True}


def test_offset_and_last_page(client: TestClient) -> None:
    body = client.get("/n", params={"limit": 20, "offset": 40, "order": "asc"}).json()
    assert body["data"] == list(range(40, 47))
    assert body["meta"]["pagination"]["has_next"] is False


def test_max_limit_allowed(client: TestClient) -> None:
    body = client.get("/n", params={"limit": MAX_LIMIT}).json()
    assert len(body["data"]) == 47
    assert body["meta"]["pagination"]["limit"] == 100


@pytest.mark.parametrize(
    ("params", "param"),
    [
        ({"limit": 101}, "limit"),
        ({"limit": 0}, "limit"),
        ({"offset": -1}, "offset"),
        ({"sort_by": "password_hash"}, "sort_by"),
        ({"order": "sideways"}, "order"),
    ],
)
def test_invalid_is_400(client: TestClient, params: dict[str, object], param: str) -> None:
    r = client.get("/n", params=params)
    assert r.status_code == 400  # 10 §1.5: "> 100 → 400 BAD_REQUEST"
    assert r.json()["error"]["code"] == "BAD_REQUEST"
    assert r.json()["error"]["details"]["param"] == param


def test_non_integer_limit_is_422(client: TestClient) -> None:
    r = client.get("/n", params={"limit": "abc"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_sort_whitelist(client: TestClient) -> None:
    r = client.get("/params", params={"sort_by": "amount", "order": "asc"})
    assert r.json()["data"]["sort_by"] == "amount"


@pytest.mark.parametrize(
    ("total", "limit", "offset", "has_next"),
    [(0, 20, 0, False), (20, 20, 0, False), (21, 20, 0, True), (47, 20, 20, True)],
)
def test_has_next(total: int, limit: int, offset: int, has_next: bool) -> None:
    assert page_meta(total=total, limit=limit, offset=offset).has_next is has_next
