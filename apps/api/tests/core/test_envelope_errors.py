"""TC-SYS-002 — envelope `{data, meta?}` / `{error:{...}}` + X-Request-Id (T-005)."""

import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ERROR_HTTP_STATUS, ApiError, ErrorCode
from app.core.handlers import code_for_http_status
from app.core.request_id import get_request_id

REPO_ROOT = Path(__file__).resolve().parents[4]
API_SPEC = REPO_ROOT / "docs/3.EXECUTION/10-API-SPECIFICATION.md"
SHARED_TYPES = REPO_ROOT / "packages/shared-types/src/index.ts"


def _spec_error_table() -> dict[str, int]:
    """Parse 10 §1.3 rows `| 400 | `BAD_REQUEST` | ...`."""
    text = API_SPEC.read_text(encoding="utf-8")
    section = text.split("### 1.3.", 1)[1].split("### 1.4.", 1)[0]
    return {
        code: int(http)
        for http, code in re.findall(r"^\| (\d{3}) \| `([A-Z_]+)` \|", section, re.M)
    }


def _assert_error(resp_json: dict[str, object], code: str) -> dict[str, object]:
    assert set(resp_json) == {"error"}
    err = resp_json["error"]
    assert isinstance(err, dict)
    assert set(err) == {"code", "message", "details"}
    assert err["code"] == code
    assert err["code"] in {c.value for c in ErrorCode}
    assert isinstance(err["message"], str) and err["message"]
    return err


def _assert_uuid4(value: str) -> None:
    assert uuid.UUID(value).version == 4


@pytest.mark.contract
def test_error_code_enum_equals_spec_table() -> None:
    table = _spec_error_table()
    assert len(table) == 20
    assert {c.value for c in ErrorCode} == set(table)
    assert {c.value: s for c, s in ERROR_HTTP_STATUS.items()} == table
    for code in ErrorCode:
        assert code.http_status == table[code.value]


@pytest.mark.contract
def test_error_codes_match_shared_types_union() -> None:
    ts = SHARED_TYPES.read_text(encoding="utf-8")
    union = ts.split("export type ApiErrorCode =", 1)[1].split(";", 1)[0]
    assert set(re.findall(r'"([A-Z_]+)"', union)) == {c.value for c in ErrorCode}


@pytest.mark.contract
def test_success_envelope_without_meta(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/ok")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"id": 1, "name": "item-1", "qty": 1}}
    _assert_uuid4(resp.headers["X-Request-Id"])


@pytest.mark.contract
def test_success_envelope_with_meta(client: TestClient) -> None:
    body = client.get("/api/v1/_test/ok-meta").json()
    assert set(body) == {"data", "meta"}
    assert body["meta"] == {"generated_at": "2026-10-05T08:30:00+07:00"}


@pytest.mark.contract
def test_api_error_envelope(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/api-error")
    assert resp.status_code == 409
    err = _assert_error(resp.json(), "REVIEW_LOCKED")
    assert err["details"] == {"locked_by": "u-1"}
    assert resp.headers["X-Request-Id"]


@pytest.mark.contract
def test_body_validation_returns_422_with_fields(client: TestClient) -> None:
    resp = client.post("/api/v1/_test/validate", json={"name": "x", "qty": "not-int"})
    assert resp.status_code == 422
    err = _assert_error(resp.json(), "VALIDATION_ERROR")
    details = err["details"]
    assert isinstance(details, dict)
    assert details["fields"] == [
        {"loc": ["body", "qty"], "msg": details["fields"][0]["msg"], "type": "int_parsing"}
    ]
    assert "not-int" not in resp.text  # input is not echoed back
    assert resp.headers["X-Request-Id"]


@pytest.mark.contract
def test_missing_body_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/_test/validate")
    assert resp.status_code == 422
    _assert_error(resp.json(), "VALIDATION_ERROR")


@pytest.mark.contract
def test_unknown_route_returns_404_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    _assert_error(resp.json(), "NOT_FOUND")
    assert resp.headers["X-Request-Id"]


@pytest.mark.contract
def test_wrong_method_returns_405_enveloped(client: TestClient) -> None:
    resp = client.delete("/api/v1/_test/ok")
    assert resp.status_code == 405
    _assert_error(resp.json(), "BAD_REQUEST")
    assert "GET" in resp.headers["allow"]


@pytest.mark.contract
def test_unhandled_exception_returns_500_without_leak(test_app: object) -> None:
    with TestClient(test_app, raise_server_exceptions=False) as c:  # type: ignore[arg-type]
        resp = c.get("/api/v1/_test/boom")
    assert resp.status_code == 500
    err = _assert_error(resp.json(), "INTERNAL_ERROR")
    assert err["details"] == {}
    for leak in ("secret-internal-detail", "hunter2", "RuntimeError", "Traceback", "/srv/db"):
        assert leak not in resp.text
    _assert_uuid4(resp.headers["X-Request-Id"])


def test_incoming_safe_request_id_is_echoed(client: TestClient) -> None:
    rid = "req-123.abc:XYZ"
    assert (
        client.get("/api/v1/_test/ok", headers={"X-Request-Id": rid}).headers["X-Request-Id"] == rid
    )
    # Also on error responses.
    assert client.get("/api/v1/nope", headers={"X-Request-Id": rid}).headers["X-Request-Id"] == rid


@pytest.mark.parametrize("bad", ["has space", "x" * 129, "semi;colon", "<script>"])
def test_unsafe_request_id_is_replaced(client: TestClient, bad: str) -> None:
    resp = client.get("/api/v1/_test/ok", headers={"X-Request-Id": bad})
    _assert_uuid4(resp.headers["X-Request-Id"])


def test_request_ids_are_unique_per_request(client: TestClient) -> None:
    ids = {client.get("/api/v1/_test/ok").headers["X-Request-Id"] for _ in range(5)}
    assert len(ids) == 5


def test_request_id_exposed_via_contextvar_and_state() -> None:
    from fastapi import Request

    from app.main import API_PREFIX, create_app

    application = create_app()
    seen: dict[str, str | None] = {}

    @application.get(f"{API_PREFIX}/_ctx")
    def ctx(request: Request) -> dict[str, str]:
        seen["var"] = get_request_id()
        seen["state"] = request.state.request_id
        return {"ok": "1"}

    with TestClient(application) as c:
        rid = c.get(f"{API_PREFIX}/_ctx").headers["X-Request-Id"]
    assert seen == {"var": rid, "state": rid}
    assert get_request_id() is None  # reset after the request


def test_health_keeps_ep01_shape_and_gets_request_id(client: TestClient) -> None:
    from app.core.health import Probe
    from app.modules.system.router import get_probes

    def probes() -> dict[str, Probe]:
        return {n: (lambda: True) for n in ("database", "redis", "storage", "model_gateway")}

    client.app.dependency_overrides[get_probes] = probes  # type: ignore[attr-defined]
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "ok"
    assert resp.headers["X-Request-Id"]


def test_api_error_defaults_and_status() -> None:
    exc = ApiError(ErrorCode.NOT_FOUND)
    assert exc.status_code == 404
    assert exc.message == "Not found"
    assert exc.details == {}


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, ErrorCode.BAD_REQUEST),
        (401, ErrorCode.UNAUTHENTICATED),
        (404, ErrorCode.NOT_FOUND),
        (418, ErrorCode.BAD_REQUEST),
        (502, ErrorCode.INTERNAL_ERROR),
        (503, ErrorCode.DEPENDENCY_UNAVAILABLE),
    ],
)
def test_code_for_http_status(status: int, code: ErrorCode) -> None:
    assert code_for_http_status(status) is code


def test_http_exception_raised_in_endpoint_is_enveloped() -> None:
    from fastapi import HTTPException

    from app.main import API_PREFIX, create_app

    application = create_app()

    @application.get(f"{API_PREFIX}/_http")
    def raise_http() -> None:
        raise HTTPException(
            status_code=401, detail="token expired", headers={"WWW-Authenticate": "Bearer"}
        )

    @application.get(f"{API_PREFIX}/_http500")
    def raise_http_500() -> None:
        raise HTTPException(status_code=500, detail="db password=hunter2")

    with TestClient(application) as c:
        resp = c.get(f"{API_PREFIX}/_http")
        resp500 = c.get(f"{API_PREFIX}/_http500")
    assert resp.status_code == 401
    assert _assert_error(resp.json(), "UNAUTHENTICATED")["message"] == "token expired"
    assert resp.headers["WWW-Authenticate"] == "Bearer"
    assert resp500.status_code == 500
    _assert_error(resp500.json(), "INTERNAL_ERROR")
    assert "hunter2" not in resp500.text
