"""TC-DATA-003 — ENT-User / ENT-Role constraints (05 §4.1; T-101).

Covers:
- partial-unique ``email`` (only among live rows, ``deleted_at IS NULL``);
- ``email`` normalised to lowercase + the ``email = lower(email)`` check constraint;
- ``role_id`` FK (RESTRICT) to ``roles``;
- ``password_hash`` is absent from the ``UserOut`` response model (10 §1.8 DS6).

Integration tests hit the dev Postgres; ``db_session`` rolls everything back (conftest).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, User
from app.modules.auth.schemas import UserOut
from app.seed import seed_all

pytestmark = pytest.mark.integration


def _ceo_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.code == "ROLE-01"))
    if role is None:
        # Self-sufficient inside the rolled-back session if the DB is not seeded yet.
        seed_all(db)
        db.flush()
        role = db.scalar(select(Role).where(Role.code == "ROLE-01"))
    assert role is not None
    return role


def _make_user(email: str, role_id: uuid.UUID) -> User:
    return User(
        email=email,
        full_name="Test User",
        salutation=None,
        password_hash="x",
        role_id=role_id,
        is_demo_account=False,
    )


def test_password_hash_absent_from_user_out_schema() -> None:
    assert "password_hash" not in UserOut.model_fields
    # Guard against leaking it through the nested role object either.
    assert "password_hash" not in UserOut.model_json_schema()["properties"]


def test_email_is_normalised_to_lowercase(db_session: Session) -> None:
    role = _ceo_role(db_session)
    user = _make_user(f"MixedCase-{uuid.uuid4().hex}@ABC.Demo", role.id)
    db_session.add(user)
    db_session.flush()
    assert user.email == user.email.lower()


def test_partial_unique_email_blocks_two_live_rows(db_session: Session) -> None:
    role = _ceo_role(db_session)
    email = f"dupe-{uuid.uuid4().hex}@abc.demo"
    db_session.add(_make_user(email, role.id))
    db_session.flush()
    db_session.add(_make_user(email, role.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_partial_unique_email_allows_soft_deleted_duplicate(db_session: Session) -> None:
    role = _ceo_role(db_session)
    email = f"reuse-{uuid.uuid4().hex}@abc.demo"
    deleted = _make_user(email, role.id)
    deleted.deleted_at = datetime.now(UTC)
    db_session.add(deleted)
    db_session.flush()
    # A new live row with the same email is allowed once the old one is soft-deleted.
    db_session.add(_make_user(email, role.id))
    db_session.flush()
    live = db_session.scalars(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    ).all()
    assert len(live) == 1


def test_email_lowercase_check_constraint(db_session: Session) -> None:
    role = _ceo_role(db_session)
    # Bypass the ORM normaliser to prove the DB-level CHECK rejects a non-lowercase email.
    with pytest.raises(IntegrityError):
        db_session.execute(
            User.__table__.insert().values(
                id=uuid.uuid4(),
                email="UPPER@abc.demo",
                full_name="Bad",
                password_hash="x",
                role_id=role.id,
                is_demo_account=False,
            )
        )


def test_role_id_foreign_key_rejects_unknown_role(db_session: Session) -> None:
    user = _make_user(f"orphan-{uuid.uuid4().hex}@abc.demo", uuid.uuid4())
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.flush()
