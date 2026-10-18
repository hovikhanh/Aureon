"""TC-SYS-005 — mutation + audit share one transaction; salary is masked (10 §1.7; T-102).

- A mutation and its ``record_audit`` entry live in the SAME transaction: rolling back the unit
  leaves NO audit row (atomicity — 05 §4.12, FR-DC-22).
- There is no API to update/delete audit rows (asserted by TC-DATA-014 / the service surface).
- ``before`` / ``after`` salary values are masked to ``••••`` before they reach the row
  (10 §1.7, 05 §10 S6).

Runs against the dev Postgres; the outer ``db_session`` transaction is rolled back (conftest),
and each test drives an inner SAVEPOINT it can roll back to prove atomicity.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import ActorType
from app.modules.audit.models import AuditLog
from app.modules.audit.service import SALARY_MASK, mask_salary, record_audit
from app.modules.auth.models import User

pytestmark = pytest.mark.integration


def _audit_count(db: Session, action: str) -> int:
    stmt = select(func.count()).select_from(AuditLog).where(AuditLog.action == action)
    return db.scalar(stmt) or 0


def test_rollback_leaves_no_audit_row(db_session: Session) -> None:
    action = f"user.rename.{uuid.uuid4().hex}"
    user = db_session.scalars(select(User).limit(1)).first()
    assert user is not None, "DB must be seeded"

    # One atomic unit: mutate + audit inside a SAVEPOINT, then roll it back.
    savepoint = db_session.begin_nested()
    original_name = user.full_name
    user.full_name = "Changed In Rolled-Back Tx"
    record_audit(
        db_session,
        action=action,
        target_type="user",
        actor_type=ActorType.SYSTEM,
        target_id=user.id,
        before={"full_name": original_name},
        after={"full_name": user.full_name},
    )
    db_session.flush()
    assert _audit_count(db_session, action) == 1  # visible inside the tx

    savepoint.rollback()
    db_session.expire_all()

    # After rollback: neither the mutation nor the audit row survive.
    assert _audit_count(db_session, action) == 0
    assert user.full_name == original_name


def test_commit_persists_mutation_and_audit_together(db_session: Session) -> None:
    action = f"user.rename.{uuid.uuid4().hex}"
    user = db_session.scalars(select(User).limit(1)).first()
    assert user is not None

    savepoint = db_session.begin_nested()
    user.full_name = "Committed Name"
    record_audit(
        db_session,
        action=action,
        target_type="user",
        actor_type=ActorType.SYSTEM,
        target_id=user.id,
        after={"full_name": user.full_name},
    )
    savepoint.commit()
    db_session.flush()

    # Both are present after the inner unit commits (the outer tx is still rolled back in teardown).
    assert _audit_count(db_session, action) == 1
    row = db_session.scalars(select(AuditLog).where(AuditLog.action == action)).one()
    assert row.after == {"full_name": "Committed Name"}


def test_salary_is_masked_in_before_and_after(db_session: Session) -> None:
    action = f"field.correct.{uuid.uuid4().hex}"
    user = db_session.scalars(select(User).limit(1)).first()
    assert user is not None

    entry = record_audit(
        db_session,
        action=action,
        target_type="business_record",
        actor_type=ActorType.USER,
        actor_user_id=user.id,
        before={"salary": 25_000_000, "full_name": "Keep Me"},
        after={"salary": 30_000_000, "full_name": "Keep Me"},
    )
    db_session.flush()

    assert entry.before == {"salary": SALARY_MASK, "full_name": "Keep Me"}
    assert entry.after == {"salary": SALARY_MASK, "full_name": "Keep Me"}
    assert SALARY_MASK == "••••"


def test_salary_mask_covers_nested_and_sensitivity_labelled_fields() -> None:
    # Pure unit coverage of mask_salary (05 §10 S6; 10 §1.8 DS3 value keys).
    raw = {
        "employee": {"salary": 10, "name": "A"},
        "fields": [
            {"field_key": "salary", "value": 999, "raw_text": "999"},
            {"sensitivity": "SALARY", "value": 1, "corrected_value": 2, "final_value": 3},
            {"field_key": "title", "value": "Manager"},
        ],
    }
    masked = mask_salary(raw)
    assert masked["employee"]["salary"] == SALARY_MASK
    assert masked["employee"]["name"] == "A"
    assert masked["fields"][0]["value"] == SALARY_MASK
    assert masked["fields"][0]["raw_text"] == SALARY_MASK
    assert masked["fields"][1]["value"] == SALARY_MASK
    assert masked["fields"][1]["corrected_value"] == SALARY_MASK
    assert masked["fields"][1]["final_value"] == SALARY_MASK
    # A non-salary field keeps its value.
    assert masked["fields"][2]["value"] == "Manager"
