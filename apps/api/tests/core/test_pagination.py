"""TC-SYS-006 — pagination `page`/`page_size` (>100 → 400) and meta (10 §1.5, T-005)."""

import pytest
from fastapi.testclient import TestClient

from app.core.pagination import PageParams, build_page_meta


@pytest.mark.contract
def test_defaults_page_1_size_20(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/items")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"data", "meta"}
    assert body["meta"] == {"page": 1, "page_size": 20, "total": 47, "total_pages": 3}
    assert [i["id"] for i in body["data"]] == list(range(1, 21))


@pytest.mark.contract
def test_last_page_partial(client: TestClient) -> None:
    body = client.get("/api/v1/_test/items", params={"page": 3, "page_size": 20}).json()
    assert body["meta"] == {"page": 3, "page_size": 20, "total": 47, "total_pages": 3}
    assert [i["id"] for i in body["data"]] == list(range(41, 48))


@pytest.mark.contract
def test_page_beyond_last_is_empty(client: TestClient) -> None:
    body = client.get("/api/v1/_test/items", params={"page": 9}).json()
    assert body["data"] == []
    assert body["meta"]["total_pages"] == 3


@pytest.mark.contract
def test_page_size_100_is_allowed(client: TestClient) -> None:
    body = client.get("/api/v1/_test/items", params={"page_size": 100}).json()
    assert body["meta"] == {"page": 1, "page_size": 100, "total": 47, "total_pages": 1}
    assert len(body["data"]) == 47


@pytest.mark.contract
@pytest.mark.parametrize(
    "params",
    [{"page_size": 101}, {"page_size": 0}, {"page": 0}, {"page": -1}, {"page": "abc"}],
)
def test_out_of_range_returns_400_bad_request(
    client: TestClient, params: dict[str, object]
) -> None:
    resp = client.get("/api/v1/_test/items", params=params)
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "BAD_REQUEST"
    assert err["details"]["fields"][0]["loc"][0] == "query"
    assert resp.headers["X-Request-Id"]


def test_meta_helper_zero_total() -> None:
    meta = build_page_meta(PageParams(page=1, page_size=20), total=0)
    assert meta.model_dump() == {"page": 1, "page_size": 20, "total": 0, "total_pages": 0}


def test_page_params_offset() -> None:
    p = PageParams(page=3, page_size=25)
    assert (p.offset, p.limit) == (50, 25)
