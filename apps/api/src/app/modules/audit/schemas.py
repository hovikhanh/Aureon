"""Pydantic schemas for the Audit Log endpoint (EP-52; 10 §7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.db.enums import ActorType


class AuditActorOut(BaseModel):
    """Actor identity for an audit entry (null for non-user actors)."""

    id: UUID
    full_name: str


class AuditLogOut(BaseModel):
    """One audit log entry (EP-52). Salary values in before/after/metadata are masked."""

    id: UUID
    occurred_at: datetime
    actor_type: ActorType
    actor: AuditActorOut | None = None
    actor_role_code: str | None = None
    action: str
    target_type: str
    target_id: UUID | None = None
    source_document_id: UUID | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
