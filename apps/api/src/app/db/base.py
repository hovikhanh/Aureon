"""Declarative base + common-column mixins (T-004; 05-DATA-MODEL §1 C3–C6).

Every table (ENT-User → ENT-AuditLog) composes:
- ``UUIDPrimaryKeyMixin``: ``id uuid PK DEFAULT gen_random_uuid()`` (C3)
- ``TimestampMixin``: ``created_at`` / ``updated_at timestamptz NOT NULL DEFAULT now()`` (C4)
- ``SoftDeleteMixin``: ``deleted_at timestamptz NULL`` for business entities (C5;
  not for ``audit_logs``, which is append-only).

Verified by TC-DATA-002 (apps/api/tests/db).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint/index names so Alembic autogenerate + downgrade are stable.
# `ix` yields `ix_<table>_<column>` as required by 05 §1 C6.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Root declarative base; ``Base.metadata`` is Alembic's ``target_metadata``."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """05 §1 C3. Python-side uuid4 so the id is known before flush; DB default as backstop."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """05 §1 C4. DB clock (``now()``) on insert; ``onupdate`` refreshes ``updated_at``."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """05 §1 C5. ``NULL`` = live row; set to a timestamp to soft-delete."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
