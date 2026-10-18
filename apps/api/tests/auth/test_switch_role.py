"""EP-04 switch-role and EP-05 demo-users integration tests (T-105).

Coverage:
- TC-AUTH-007: DEMO_MODE=true: EP-04 switches role, issues new JWT, updates last_login_at,
  and records audit log with metadata {from_role, to_role, from_user_id, to_user_id}.
- TC-AUTH-008: DEMO_MODE=false: EP-04 and EP-05 return 404 NOT_FOUND.
- TC-AUTH-010: EP-05 returns exactly 5 demo accounts ordered by ROLE-01..05.
- Validation: EP-04 invalid target role format returns 422 VALIDATION_ERROR.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ConfigService, get_config
from app.db.session import get_db
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.token import create_access_token, decode_access_token

pytestmark = pytest.mark.integration


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
    assert user is not None, f"User {email} must exist in seed"
    return user


def test_tc_auth_007_switch_role_success(client: TestClient, db_session: Session) -> None:
    config = get_config()
    ceo = _get_user_by_email(db_session, "ceo@abc.demo")
    cfo = _get_user_by_email(db_session, "cfo@abc.demo")
    cfo_last_login_before = cfo.last_login_at

    token_ceo, _ = create_access_token(ceo, config)

    res = client.post(
        "/api/v1/auth/switch-role",
        headers={"Authorization": f"Bearer {token_ceo}"},
        json={"target_role_code": "ROLE-02"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "data" in body
    data = body["data"]

    # Verify response structure per 10 EP-04
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "cfo@abc.demo"
    assert data["user"]["role"]["code"] == "ROLE-02"
    assert data["home_route"] == "/dashboard"

    # Verify newly minted JWT
    new_token = data["access_token"]
    claims = decode_access_token(new_token, config)
    assert claims.sub == cfo.id
    assert claims.role == "ROLE-02"

    # Verify last_login_at updated on target user
    db_session.refresh(cfo)
    assert cfo.last_login_at is not None
    if cfo_last_login_before is not None:
        assert cfo.last_login_at >= cfo_last_login_before

    # Verify audit log row
    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "role.switch", AuditLog.target_id == cfo.id)
        .order_by(AuditLog.created_at.desc())
    )
    audit = db_session.scalars(stmt).first()
    assert audit is not None
    assert audit.actor_user_id == ceo.id
    assert audit.actor_role_id == ceo.role_id
    assert audit.metadata_["from_role"] == "ROLE-01"
    assert audit.metadata_["to_role"] == "ROLE-02"
    assert audit.metadata_["from_user_id"] == str(ceo.id)
    assert audit.metadata_["to_user_id"] == str(cfo.id)


def test_tc_auth_007_switch_role_to_same_role_succeeds(
    client: TestClient, db_session: Session
) -> None:
    """Switching to current active role is idempotent/valid and yields fresh JWT (10 EP-04)."""
    config = get_config()
    ceo = _get_user_by_email(db_session, "ceo@abc.demo")
    token, _ = create_access_token(ceo, config)

    res = client.post(
        "/api/v1/auth/switch-role",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_role_code": "ROLE-01"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["user"]["role"]["code"] == "ROLE-01"


def test_tc_auth_007_switch_role_validation_error(client: TestClient, db_session: Session) -> None:
    config = get_config()
    ceo = _get_user_by_email(db_session, "ceo@abc.demo")
    token, _ = create_access_token(ceo, config)

    res = client.post(
        "/api/v1/auth/switch-role",
        headers={"Authorization": f"Bearer {token}"},
        json={"target_role_code": "INVALID_ROLE"},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_tc_auth_008_demo_mode_disabled_returns_404(
    client: TestClient, db_session: Session
) -> None:
    """When DEMO_MODE=false, both EP-04 and EP-05 must return 404 NOT_FOUND (07 §8.1.1)."""
    # Create config service with demo_mode=False
    real_config = get_config()
    disabled_config = ConfigService(
        **{
            **real_config.model_dump(),
            "demo_mode": False,
        }
    )

    app.dependency_overrides[get_config] = lambda: disabled_config
    try:
        ceo = _get_user_by_email(db_session, "ceo@abc.demo")
        token, _ = create_access_token(ceo, real_config)

        # EP-04 returns 404
        res_switch = client.post(
            "/api/v1/auth/switch-role",
            headers={"Authorization": f"Bearer {token}"},
            json={"target_role_code": "ROLE-02"},
        )
        assert res_switch.status_code == 404
        assert res_switch.json()["error"]["code"] == "NOT_FOUND"

        # EP-05 returns 404
        res_users = client.get(
            "/api/v1/auth/demo-users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_users.status_code == 404
        assert res_users.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_config, None)


def test_tc_auth_010_demo_users_returns_ordered_five_accounts(
    client: TestClient, db_session: Session
) -> None:
    """EP-05 returns exactly 5 demo accounts ordered ROLE-01..05."""
    config = get_config()
    ceo = _get_user_by_email(db_session, "ceo@abc.demo")
    token, _ = create_access_token(ceo, config)

    res = client.get(
        "/api/v1/auth/demo-users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    items = body["data"]

    assert len(items) == 5
    expected_order = ["ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"]
    assert [item["role_code"] for item in items] == expected_order

    for item in items:
        assert item["role_name_i18n_key"].startswith("shell.roles.")
        assert len(item["full_name"]) > 0
        assert item["user_id"] is not None
