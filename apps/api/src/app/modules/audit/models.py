"""ENT-AuditLog (`audit_logs`) — 05 §4.12 (T-102).

Append-only: no ``deleted_at`` (05 §1 C5 exception) and a DB trigger rejects UPDATE/DELETE
(migration 0003). ``updated_at`` exists only for convention C4 and always equals ``created_at``.

`source_document_id` is an FK → source_documents per 05 §4.12; that table arrives in T-201,
which adds the FK constraint. Until then the column is a plain indexed uuid.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, event, func
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, Session, UOWTransaction, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.enums import ActorType

ACTOR_TYPE_ENUM = ENUM(
    ActorType,
    name="actor_type",
    values_callable=lambda cls: [member.value for member in cls],
    create_type=False,
)


class AuditLogImmutableError(RuntimeError):
    """Raised when code tries to update or delete an audit row through the ORM."""


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """One immutable audit row; write only through ``app.modules.audit.service.record_audit``."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_target_type_target_id", "target_type", "target_id"),)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    actor_type: Mapped[ActorType] = mapped_column(ACTOR_TYPE_ENUM, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    actor_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # `metadata` is reserved on declarative classes → attribute `metadata_`, column `metadata`.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)

    # C4 columns without `onupdate`: rows never change, so updated_at stays = created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@event.listens_for(Session, "before_flush")
def _reject_audit_mutation(session: Session, _ctx: UOWTransaction, _instances: object) -> None:
    """Repository-level append-only guard (TC-DATA-014); the DB trigger is the backstop."""
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise AuditLogImmutableError("audit_logs is append-only: DELETE is not allowed")
    for obj in session.dirty:
        if isinstance(obj, AuditLog) and session.is_modified(obj, include_collections=False):
            raise AuditLogImmutableError("audit_logs is append-only: UPDATE is not allowed")
