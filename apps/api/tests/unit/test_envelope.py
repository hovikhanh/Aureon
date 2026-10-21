"""TC-SYS-003 — envelope `{data, meta}` / `{error}` + X-Request-Id (10 §1.3, §1.9)."""

import uuid

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.envelope import Envelope, Page, to_envelope
from app.core.errors import (
    AI_ERROR_CODES,
    AppError,
    BusinessRuleError,
    ConflictStateError,
    NotFoundError,
    ScopeDeniedError,
    ai_error,
)
from app.core.handlers import install_error_handlers
from app.core.request_context import RequestIdMiddleware
from app.core.routing import EnvelopeRouter


class Item(BaseModel):
    id: int
    name: str


class Body(BaseModel):
    amount: int


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    r = EnvelopeRouter()

    @r.get("/item", response_model=Item)
    async def item() -> Item:
        return Item(id=1, name="a")

    @r.get("/items", response_model=list[Item])
    async def items() -> Page[Item]:
        return Page(items=[Item(id=i, name=str(i)) for i in range(3)], total=7, limit=3, offset=3)

    @r.get("/dict", response_model=dict[str, int])
    async def as_dict() -> dict[str, int]:
        return {"x": 1}

    @r.delete("/gone", status_code=204, response_class=Response)
    async def gone() -> Response:
        return Response(status_code=204)

    @r.post("/body", response_model=Item)
    async def body(b: Body) -> Item:
        return Item(id=b.amount, name="x")

    @r.get("/err/{kind}", response_model=Item)
    async def err(kind: str) -> Item:
        errors: dict[str, AppError] = {
            "404": NotFoundError("no such thing"),
            "409": ConflictStateError("bad transition", details={"from": "A", "to": "B"}),
            "scope": ScopeDeniedError(),
            "br": BusinessRuleError("BR-PRD-01"),
            "ai": ai_error("AI_QUOTA_EXCEEDED"),
        }
        if kind == "boom":
            raise RuntimeError("secret stack detail")
        raise errors[kind]

    app.include_router(r)
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


def test_success_wrapped_with_meta(client: TestClient) -> None:
    r = client.get("/item")
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == {"id": 1, "name": "a"}
    assert body["meta"]["request_id"] == r.headers["x-request-id"]
    assert body["meta"]["generated_at"].endswith("Z") or "+00:00" in body["meta"]["generated_at"]
    assert body["meta"]["pagination"] is None


def test_page_wrapped_with_pagination(client: TestClient) -> None:
    body = client.get("/items").json()
    assert [i["id"] for i in body["data"]] == [0, 1, 2]
    assert body["meta"]["pagination"] == {"total": 7, "limit": 3, "offset": 3, "has_next": True}


def test_non_model_payload_and_204(client: TestClient) -> None:
    assert client.get("/dict").json()["data"] == {"x": 1}
    r = client.delete("/gone")
    assert r.status_code == 204
    assert r.content == b""
    assert "x-request-id" in r.headers


def test_openapi_shows_envelope(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    ref = spec["paths"]["/item"]["get"]["responses"]["200"]["content"]["application/json"]
    name = ref["schema"]["$ref"].rsplit("/", 1)[-1]
    assert set(spec["components"]["schemas"][name]["properties"]) == {"data", "meta"}


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("404", 404, "NOT_FOUND"),
        ("409", 409, "CONFLICT_STATE"),
        ("scope", 403, "FORBIDDEN_SCOPE"),
        ("br", 422, "BUSINESS_RULE_VIOLATION"),
        ("ai", 429, "AI_QUOTA_EXCEEDED"),
    ],
)
def test_app_errors(client: TestClient, kind: str, status: int, code: str) -> None:
    r = client.get(f"/err/{kind}")
    assert r.status_code == status
    assert set(r.json()) == {"error"}
    assert set(r.json()["error"]) == {"code", "message", "details"}
    assert r.json()["error"]["code"] == code
    assert "x-request-id" in r.headers


def test_error_details_kept(client: TestClient) -> None:
    assert client.get("/err/409").json()["error"]["details"] == {"from": "A", "to": "B"}


def test_validation_error_fields(client: TestClient) -> None:
    r = client.post("/body", json={"amount": "abc"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["details"]["fields"][0]["loc"] == ["body", "amount"]


def test_unknown_route_and_method(client: TestClient) -> None:
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
    r = client.put("/item")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "BAD_REQUEST"


def test_unhandled_is_500_without_leak(client: TestClient) -> None:
    r = client.get("/err/boom")
    assert r.status_code == 500
    assert r.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "internal error", "details": {}}
    }
    assert "secret" not in r.text
    assert "x-request-id" in r.headers


def test_request_id_echo_and_mint(client: TestClient) -> None:
    rid = str(uuid.uuid4())
    r = client.get("/item", headers={"X-Request-Id": rid})
    assert r.headers["x-request-id"] == rid
    assert r.json()["meta"]["request_id"] == rid
    minted = client.get("/item", headers={"X-Request-Id": "not-a-uuid"}).headers["x-request-id"]
    assert minted != "not-a-uuid"
    uuid.UUID(minted)


def test_ai_error_codes() -> None:
    for code, status in AI_ERROR_CODES.items():
        e = ai_error(code, detail="x")
        assert (e.code, e.status_code, e.details) == (code, status, {"detail": "x"})
    with pytest.raises(ValueError):
        ai_error("AI_MADE_UP")


def test_to_envelope_passthrough() -> None:
    env = Envelope[int](data=1)
    assert to_envelope(env) is env


def test_sync_endpoint_rejected() -> None:
    r = EnvelopeRouter()
    with pytest.raises(TypeError, match="async"):

        @r.get("/sync", response_model=Item)
        def sync() -> Item:
            return Item(id=1, name="x")
