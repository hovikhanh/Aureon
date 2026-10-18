"""EP-02 login integration tests — TC-AUTH-001..004 (10 EP-02; T-103).

Needs Postgres + Redis (``@pytest.mark.integration``). Each test runs inside the ``db_session``
outer transaction (conftest) that is rolled back, so no row survives and the shared DB is left
seeded. ``get_db`` is overridden to that same session so audit rows written by the endpoint are
visible to assertions and rolled back with everything else. The real rate limiter is replaced per
test with a configurable one (tiny limit / unique Redis namespace) — the real default is never
weakened.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import ConfigService, get_config
from app.db.session import get_db
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.rate_limit import LoginRateLimiter, build_redis
from app.modules.auth.router import get_login_rate_limiter
from app.modules.auth.token import decode_access_token

pytestmark = pytest.mark.integration

# Password env var (ConfigService.demo_<key>_password) per demo account — never hard-coded here.
CEO_EMAIL = "ceo@abc.demo"


def _ceo_password(config: ConfigService) -> str:
    secret = config.demo_ceo_password
    assert secret is not None, "DEMO_CEO_PASSWORD must be set for TC-AUTH-001"
    return secret.get_secret_value()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient wired to the rolled-back ``db_session`` and a generous (non-blocking) limiter."""
    config = get_config()
    redis_client = build_redis(config)
    # High limit so auth tests are not throttled; a unique namespace avoids cross-test bleed.
    generous = LoginRateLimiter(redis_client, limit=10_000, window_seconds=5)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_login_rate_limiter] = lambda: generous
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        redis_client.close()


def _audit_rows(db: Session, request_id: str) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "auth.login")
        .where(AuditLog.metadata_["request_id"].astext == request_id)
    )
    return list(db.scalars(stmt))


# --- TC-AUTH-001 -----------------------------------------------------------------------------


def test_valid_credentials_return_200_envelope_and_jwt(
    client: TestClient, db_session: Session
) -> None:
    config = get_config()
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": CEO_EMAIL, "password": _ceo_password(config)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"data"}  # envelope {data}, meta omitted (10 §1.2)
    data = body["data"]
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["expires_at"]

    # UserOut has no password_hash anywhere (10 §1.8 DS6).
    assert "password_hash" not in data["user"]
    assert "password_hash" not in resp.text
    assert data["user"]["email"] == CEO_EMAIL
    assert data["user"]["role"]["code"] == "ROLE-01"

    # Decoded JWT carries the required claims with the right values (10 §1.4).
    claims = decode_access_token(data["access_token"], config)
    assert str(claims.sub) == data["user"]["id"]
    assert claims.role == "ROLE-01"
    assert claims.iss == config.jwt_issuer
    assert claims.aud == config.jwt_audience
    assert claims.exp > claims.iat


# --- TC-AUTH-002 -----------------------------------------------------------------------------


def test_wrong_password_and_unknown_email_are_identical_401(client: TestClient) -> None:
    config = get_config()
    wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": CEO_EMAIL, "password": _ceo_password(config) + "-wrong"},
    )
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": f"nobody-{uuid.uuid4().hex}@abc.demo", "password": "whatever"},
    )
    for resp in (wrong_pw, unknown):
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"
    # Identical message and body shape → no user enumeration (10 EP-02 protection 3).
    assert wrong_pw.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert set(wrong_pw.json()["error"]) == set(unknown.json()["error"])


# --- TC-AUTH-003 -----------------------------------------------------------------------------


def test_rate_limit_returns_429_over_threshold(db_session: Session) -> None:
    config = get_config()
    redis_client = build_redis(config)
    # A real, small limiter (limit=2) in a unique namespace — drives the documented 429 path.
    limiter = LoginRateLimiter(redis_client, limit=2, window_seconds=30)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    try:
        client = TestClient(app)
        email = f"rl-{uuid.uuid4().hex}@abc.demo"
        payload = {"email": email, "password": "irrelevant"}
        # Under the limit → allowed (reaches auth logic → 401 for unknown user), not 429.
        first = client.post("/api/v1/auth/login", json=payload)
        second = client.post("/api/v1/auth/login", json=payload)
        assert first.status_code != 429
        assert second.status_code != 429
        # Over the limit → 429 RATE_LIMITED with Retry-After.
        third = client.post("/api/v1/auth/login", json=payload)
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "RATE_LIMITED"
        assert int(third.headers["Retry-After"]) > 0
    finally:
        app.dependency_overrides.clear()
        redis_client.delete(limiter._key(email, "testclient"))
        redis_client.close()


# --- TC-AUTH-004 -----------------------------------------------------------------------------


def test_audit_written_for_success_and_failure_without_password(
    client: TestClient, db_session: Session
) -> None:
    config = get_config()
    before = db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "auth.login")
    )

    success_rid = uuid.uuid4().hex
    ok = client.post(
        "/api/v1/auth/login",
        json={"email": CEO_EMAIL, "password": _ceo_password(config)},
        headers={"X-Request-Id": success_rid},
    )
    assert ok.status_code == 200

    fail_rid = uuid.uuid4().hex
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": CEO_EMAIL, "password": "definitely-wrong-pw"},
        headers={"X-Request-Id": fail_rid},
    )
    assert bad.status_code == 401

    after = db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "auth.login")
    )
    assert (after or 0) == (before or 0) + 2  # one row per attempt

    success_rows = _audit_rows(db_session, success_rid)
    fail_rows = _audit_rows(db_session, fail_rid)
    assert len(success_rows) == 1
    assert len(fail_rows) == 1

    success = success_rows[0]
    failure = fail_rows[0]
    # Success: USER actor; failure: SYSTEM actor with no user identity (10 §1.7, audit rules).
    assert success.actor_user_id is not None
    assert success.metadata_ is not None and success.metadata_["result"] == "success"
    assert failure.actor_user_id is None
    assert failure.metadata_ is not None and failure.metadata_["result"] == "failure"

    # The password is NEVER present in any audit field (10 EP-02 / §1.7).
    ceo_pw = _ceo_password(config)
    for row in (success, failure):
        blob = f"{row.before}|{row.after}|{row.metadata_}"
        assert ceo_pw not in blob
        assert "password" not in blob.lower()
        assert "definitely-wrong-pw" not in blob
