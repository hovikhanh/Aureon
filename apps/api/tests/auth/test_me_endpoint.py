"""EP-03 /auth/me and require_role tests (T-104).

Coverage:
- TC-AUTH-005: JWT missing / invalid signature / expired / wrong iss/aud → 401 UNAUTHENTICATED
- TC-AUTH-006: EP-03 returns UserOut + permissions per 02 §3 matrix for 5 roles; no password_hash
- TC-AUTH-009: Request body spoofing role is ignored; role strictly from verified JWT claim
- TC-AUTH-011: require_role parameterized test across roles yielding 200 vs 403 FORBIDDEN_ROLE
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.envelope import Envelope
from app.db.session import get_db
from app.main import app
from app.modules.auth.deps import compute_permissions, require_role
from app.modules.auth.models import User
from app.modules.auth.token import ALGORITHM, create_access_token

pytestmark = pytest.mark.integration

DEMO_EMAILS = [
    ("ROLE-01", "ceo@abc.demo"),
    ("ROLE-02", "cfo@abc.demo"),
    ("ROLE-03", "sales@abc.demo"),
    ("ROLE-04", "hr@abc.demo"),
    ("ROLE-05", "reviewer@abc.demo"),
]


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _get_user_by_email(db: Session, email: str) -> User:
    stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
    user = db.scalar(stmt)
    assert user is not None, f"User with email {email} must exist in seed"
    return user


def test_tc_auth_005_missing_token_returns_401(client: TestClient) -> None:
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    body = res.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"


def test_tc_auth_005_invalid_bearer_format_returns_401(client: TestClient) -> None:
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_tc_auth_005_expired_token_returns_401(client: TestClient, db_session: Session) -> None:
    config = get_config()
    user = _get_user_by_email(db_session, "ceo@abc.demo")
    past = datetime.now(UTC) - timedelta(hours=10)
    token, _ = create_access_token(user, config, now=past)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_tc_auth_005_wrong_secret_returns_401(client: TestClient, db_session: Session) -> None:
    config = get_config()
    user = _get_user_by_email(db_session, "ceo@abc.demo")
    payload = {
        "sub": str(user.id),
        "role": user.role.code,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
    }
    fake_token = jwt.encode(payload, "wrong-secret-key-that-does-not-match", algorithm=ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_tc_auth_005_wrong_iss_and_aud_returns_401(client: TestClient, db_session: Session) -> None:
    config = get_config()
    user = _get_user_by_email(db_session, "ceo@abc.demo")
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role.code,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "iss": "invalid-issuer",
        "aud": "invalid-audience",
    }
    bad_token = jwt.encode(payload, config.jwt_secret.get_secret_value(), algorithm=ALGORITHM)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("expected_role,email", DEMO_EMAILS)
def test_tc_auth_006_ep03_me_returns_user_out_and_permissions(
    client: TestClient, db_session: Session, expected_role: str, email: str
) -> None:
    config = get_config()
    user = _get_user_by_email(db_session, email)
    token, _ = create_access_token(user, config)

    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    data = body["data"]

    # Verify UserOut
    assert data["user"]["email"] == email
    assert data["user"]["role"]["code"] == expected_role
    assert "password_hash" not in data["user"]
    assert "password_hash" not in str(body)

    # Verify demo_mode flag
    assert data["demo_mode"] == config.demo_mode

    # Verify permissions match 02 §3 specification
    perms = data["permissions"]
    expected_perms = compute_permissions(expected_role)
    assert perms == expected_perms

    # Specific checks per role
    if expected_role == "ROLE-01":
        assert perms["audit.read"] is True
        assert perms["onboarding"] is True
        assert set(perms["alerts.ack_pillars"]) == {"FIN", "CUS", "OPS", "HR"}
        assert perms["salary.view"] is False
    elif expected_role == "ROLE-02":
        assert perms["audit.read"] is False
        assert perms["review.pillars"] == ["FIN"]
        assert perms["alerts.ack_pillars"] == ["FIN"]
        assert perms["salary.view"] is False
    elif expected_role == "ROLE-03":
        assert perms["audit.read"] is False
        assert perms["review.pillars"] == []
        assert perms["alerts.ack_pillars"] == ["CUS"]
        assert perms["salary.view"] is False
    elif expected_role == "ROLE-04":
        assert perms["audit.read"] is False
        assert perms["review.pillars"] == ["HR"]
        assert perms["alerts.ack_pillars"] == ["HR"]
        assert perms["salary.view"] is True
    elif expected_role == "ROLE-05":
        assert perms["audit.read"] is False
        assert set(perms["review.pillars"]) == {"FIN", "CUS", "OPS", "HR"}
        assert perms["alerts.ack_pillars"] == []
        assert perms["onboarding"] is True
        assert perms["salary.view"] is True


def test_tc_auth_009_role_spoofing_in_request_ignored(
    client: TestClient, db_session: Session
) -> None:
    """Request body/params attempting to spoof 'role' must be completely ignored (02 §4.1)."""
    config = get_config()
    sales_user = _get_user_by_email(db_session, "sales@abc.demo")
    token, _ = create_access_token(sales_user, config)

    # Sending GET or extra query/body with role=ROLE-01 must not grant CEO privileges
    res = client.get(
        "/api/v1/auth/me?role=ROLE-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    # Role remains ROLE-03
    assert data["user"]["role"]["code"] == "ROLE-03"
    assert data["permissions"]["audit.read"] is False


# TC-AUTH-011: Parameterized test verifying require_role across different endpoint role constraints
dummy_role_router = APIRouter(prefix="/test-roles")


@dummy_role_router.get("/ceo-only", response_model=Envelope[dict])
def _ceo_only(user: Annotated[User, Depends(require_role("ROLE-01"))]) -> Envelope[dict]:
    return Envelope(data={"status": "ok", "user": user.email})


@dummy_role_router.get("/cfo-or-hr", response_model=Envelope[dict])
def _cfo_or_hr(
    user: Annotated[User, Depends(require_role("ROLE-02", "ROLE-04"))],
) -> Envelope[dict]:
    return Envelope(data={"status": "ok", "user": user.email})


@dummy_role_router.get("/reviewer-only", response_model=Envelope[dict])
def _reviewer_only(user: Annotated[User, Depends(require_role("ROLE-05"))]) -> Envelope[dict]:
    return Envelope(data={"status": "ok", "user": user.email})


app.include_router(dummy_role_router)


@pytest.mark.parametrize(
    "path,allowed_roles",
    [
        ("/test-roles/ceo-only", {"ROLE-01"}),
        ("/test-roles/cfo-or-hr", {"ROLE-02", "ROLE-04"}),
        ("/test-roles/reviewer-only", {"ROLE-05"}),
    ],
)
def test_tc_auth_011_require_role_matrix(
    client: TestClient, db_session: Session, path: str, allowed_roles: set[str]
) -> None:
    config = get_config()
    for role_code, email in DEMO_EMAILS:
        user = _get_user_by_email(db_session, email)
        token, _ = create_access_token(user, config)
        res = client.get(path, headers={"Authorization": f"Bearer {token}"})
        if role_code in allowed_roles:
            assert res.status_code == 200, f"Role {role_code} should be allowed on {path}"
            assert res.json()["data"]["status"] == "ok"
        else:
            assert res.status_code == 403, f"Role {role_code} should be forbidden on {path}"
            assert res.json()["error"]["code"] == "FORBIDDEN_ROLE"
