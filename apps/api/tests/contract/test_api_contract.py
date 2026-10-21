"""TC-SYS-003 (contract) — the live OpenAPI and code agree with 10-API-SPECIFICATION.

Parses 10 §1.4 (error-code table) and §4.1 (auth EPs) straight from the spec file, so a spec
change without a code change (or the reverse) fails here.
"""

import inspect
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import errors
from app.core.config import REPO_ROOT
from app.core.handlers import _HTTP_CODES
from app.main import API_PREFIX, create_app

pytestmark = pytest.mark.contract

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
PUBLIC_ALLOWED = {("POST", "/auth/login"), ("POST", "/auth/refresh"), ("GET", "/health")}


def _section(title: str) -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(title)
    nxt = re.search(r"\n#{2,3} ", text[start + len(title) :])
    return text[start : start + len(title) + (nxt.start() if nxt else len(text))]


def spec_error_codes() -> dict[str, int]:
    rows = re.findall(r"^\| (\d{3}) \| `([A-Z_]+)` \|", _section("### 1.4."), re.M)
    return {code: int(status) for status, code in rows}


@pytest.fixture(scope="module")
def app_routes() -> list[APIRoute]:
    return [r for r in create_app().routes if isinstance(r, APIRoute)]


def _code_error_classes() -> list[type[errors.AppError]]:
    return [
        c
        for _, c in inspect.getmembers(errors, inspect.isclass)
        if issubclass(c, errors.AppError) and c is not errors.AppError
    ]


def test_spec_table_parsed() -> None:
    codes = spec_error_codes()
    assert len(codes) >= 25
    assert codes["RATE_LIMIT_EXCEEDED"] == 429


def test_every_error_class_uses_a_spec_code_and_status() -> None:
    spec = spec_error_codes()
    for cls in _code_error_classes():
        assert cls.code in spec, f"{cls.__name__}.code={cls.code} not in 10 §1.4"
        assert spec[cls.code] == cls.status_code, cls.__name__


def test_ai_codes_match_spec() -> None:
    spec = spec_error_codes()
    spec_ai = {c: s for c, s in spec.items() if c.startswith("AI_")}
    assert spec_ai == errors.AI_ERROR_CODES


def test_http_fallback_codes_in_spec() -> None:
    spec = spec_error_codes()
    for status, code in _HTTP_CODES.items():
        assert code in spec, (status, code)


def test_no_v1_codes() -> None:
    src = (Path(errors.__file__)).read_text()
    assert 'RATE_LIMITED"' not in src and '"FORBIDDEN"' not in src


def test_all_routes_under_base_path(app_routes: list[APIRoute]) -> None:
    for r in app_routes:
        assert r.path.startswith(API_PREFIX + "/"), r.path


def test_every_route_declares_envelope_or_204(app_routes: list[APIRoute]) -> None:
    for r in app_routes:
        if r.status_code == 204:
            continue
        assert r.response_model is not None, r.path
        assert getattr(r.response_model, "__name__", "").startswith("Envelope["), r.path


def test_public_endpoints_are_only_the_allowed_ones(app_routes: list[APIRoute]) -> None:
    """10 §2.2: only EP-01/02/06 are public. Everything else 401s without a token."""
    client = TestClient(create_app())
    for r in app_routes:
        rel = r.path.removeprefix(API_PREFIX)
        for method in r.methods:
            if (method, rel) in PUBLIC_ALLOWED:
                continue
            res = client.request(method, r.path, json={})
            assert res.status_code == 401, (method, r.path, res.status_code)
            assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_paths_exist_in_spec(app_routes: list[APIRoute]) -> None:
    spec_paths = set(
        re.findall(r"\| (?:GET|POST|PATCH|DELETE)[^|]*\| `(/auth/[a-z/-]+)`", SPEC.read_text())
    )
    for r in app_routes:
        rel = r.path.removeprefix(API_PREFIX)
        if rel.startswith("/auth/"):
            assert rel in spec_paths, rel


def test_no_register_endpoint(app_routes: list[APIRoute]) -> None:
    assert all("register" not in r.path for r in app_routes)  # DEC-137


def test_user_out_has_no_password_hash() -> None:
    spec = create_app().openapi()
    user_out = spec["components"]["schemas"]["UserOut"]["properties"]
    assert "password_hash" not in user_out
    expected = {
        "id", "email", "full_name", "role_code", "role_id", "permissions",
        "department_id", "locale", "is_active", "last_login_at",
    }  # fmt: skip
    assert set(user_out) == expected  # 10 §4.1 UserOut
