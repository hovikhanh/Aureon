"""EP-52 GET /api/v1/audit-logs — audit log endpoint tests (T-404; 10 §7; SCR-14).

TC-AUDIT-001 ROLE-01 lists entries with actor + pagination; TC-AUDIT-002 role guard
(ROLE-02..05 -> 403); TC-AUDIT-003 filters (action substring, actor_type); TC-AUDIT-004
salary values masked in before/after even for the CEO.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.db.enums import ActorType
from app.db.session import get_db
from app.main import app
from app.modules.audit.service import SALARY_MASK, record_audit
from app.modules.auth.models import User
from app.modules.auth.token import create_access_token

pytestmark = pytest.mark.integration

_EMAILS = {
    "ROLE-01": "ceo@abc.demo",
    "ROLE-02": "cfo@abc.demo",
    "ROLE-03": "sales@abc.demo",
    "ROLE-04": "hr@abc.demo",
    "ROLE-05": "reviewer@abc.demo",
}


@pytest.fixture
def tokens(db_session: Session) -> dict[str, str]:
    cfg = get_config()
    out: dict[str, str] = {}
    for role, email in _EMAILS.items():
        user = db_session.execute(select(User).where(User.email == email)).scalars().first()
        assert user is not None, f"seed missing {email}"
        token, _ = create_access_token(user, cfg)
        out[role] = token
    return out


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_entry(
    db: Session,
    *,
    action: str,
    actor_type: ActorType = ActorType.USER,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    ceo = db.execute(select(User).where(User.email == "ceo@abc.demo")).scalars().first()
    assert ceo is not None
    record_audit(
        db=db,
        actor_type=actor_type,
        actor_user_id=ceo.id if actor_type == ActorType.USER else None,
        actor_role_id=ceo.role_id if actor_type == ActorType.USER else None,
        action=action,
        target_type="business_records",
        target_id=uuid4(),
        before=before,
        after=after,
    )
    db.flush()


def test_tc_audit_001_ceo_lists_entries(
    client: TestClient, tokens: dict[str, str], db_session: Session
) -> None:
    _seed_entry(db_session, action="action.invoice.create")
    _seed_entry(db_session, action="auth.switch_role")
    db_session.commit()

    r = client.get("/api/v1/audit-logs", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["total"] >= 2
    first = body["data"][0]
    assert {"id", "occurred_at", "actor_type", "action", "target_type"} <= set(first)
    # Default sort -occurred_at: the most recent entry is first.
    actions = [e["action"] for e in body["data"]]
    assert "auth.switch_role" in actions


def test_tc_audit_002_role_guard(
    client: TestClient, tokens: dict[str, str], db_session: Session
) -> None:
    _seed_entry(db_session, action="action.invoice.create")
    db_session.commit()
    for role in ("ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"):
        r = client.get("/api/v1/audit-logs", headers=_auth(tokens[role]))
        assert r.status_code == 403, role
        assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_tc_audit_003_filters(
    client: TestClient, tokens: dict[str, str], db_session: Session
) -> None:
    _seed_entry(db_session, action="action.invoice.create")
    _seed_entry(db_session, action="auth.switch_role")
    _seed_entry(db_session, action="ai.classify", actor_type=ActorType.AI)
    db_session.commit()

    # action substring filter
    r = client.get("/api/v1/audit-logs?action=invoice", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200
    assert all("invoice" in e["action"] for e in r.json()["data"])

    # actor_type filter
    r2 = client.get("/api/v1/audit-logs?actor_type=AI", headers=_auth(tokens["ROLE-01"]))
    assert r2.status_code == 200
    assert all(e["actor_type"] == "AI" for e in r2.json()["data"])
    assert any(e["action"] == "ai.classify" for e in r2.json()["data"])


def test_tc_audit_004_salary_masked(
    client: TestClient, tokens: dict[str, str], db_session: Session
) -> None:
    _seed_entry(
        db_session,
        action="action.employee.upsert",
        after={"name": "Nguyễn Văn A", "salary": 45_000_000},
    )
    db_session.commit()
    r = client.get(
        "/api/v1/audit-logs?action=employee", headers=_auth(tokens["ROLE-01"])
    )
    assert r.status_code == 200
    entry = next(e for e in r.json()["data"] if e["action"] == "action.employee.upsert")
    assert entry["after"]["salary"] == SALARY_MASK
    assert entry["after"]["name"] == "Nguyễn Văn A"
