"""TC-DATA-014 — ``audit_logs`` is append-only (05 §4.12; T-102).

Two layers of protection, both asserted:
- the ORM ``before_flush`` guard raises ``AuditLogImmutableError`` on UPDATE/DELETE;
- the DB trigger ``trg_audit_logs_append_only`` (migration 0003) rejects raw SQL UPDATE/DELETE
  with SQLSTATE ``55000`` even when the ORM guard is bypassed.

Runs against the dev Postgres; ``db_session`` rolls everything back (conftest).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.enums import ActorType
from app.modules.audit.models import AuditLog, AuditLogImmutableError
from app.modules.audit.service import record_audit

pytestmark = pytest.mark.integration


def _insert_audit(db: Session) -> AuditLog:
    entry = record_audit(
        db,
        action="test.create",
        target_type="demo",
        actor_type=ActorType.SYSTEM,
        target_id=uuid.uuid4(),
        after={"field": "value"},
    )
    db.flush()
    return entry


def test_orm_update_is_rejected(db_session: Session) -> None:
    entry = _insert_audit(db_session)
    entry.action = "test.tampered"
    with pytest.raises(AuditLogImmutableError, match="UPDATE"):
        db_session.flush()


def test_orm_delete_is_rejected(db_session: Session) -> None:
    entry = _insert_audit(db_session)
    db_session.delete(entry)
    with pytest.raises(AuditLogImmutableError, match="DELETE"):
        db_session.flush()


def test_db_trigger_rejects_raw_update(db_session: Session) -> None:
    entry = _insert_audit(db_session)
    with pytest.raises(OperationalError) as exc:
        db_session.execute(
            text("UPDATE audit_logs SET action = :a WHERE id = :id"),
            {"a": "hacked", "id": entry.id},
        )
    assert "append-only" in str(exc.value)


def test_db_trigger_rejects_raw_delete(db_session: Session) -> None:
    entry = _insert_audit(db_session)
    with pytest.raises(OperationalError) as exc:
        db_session.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": entry.id})
    assert "append-only" in str(exc.value)
