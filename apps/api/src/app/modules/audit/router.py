"""Audit Log endpoint — EP-52 (10 §7; SCR-14; FR-DC-22; T-404 backing API).

Read-only, append-only log. Restricted to ROLE-01 (CEO) per 02 §3.6. Salary values in
``before`` / ``after`` / ``metadata`` are always masked (defense-in-depth on top of the
write-time masking in ``record_audit``), even for the CEO.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.envelope import Page
from app.core.pagination import PageParams, get_page_params, paginate
from app.db.enums import ActorType
from app.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditActorOut, AuditLogOut
from app.modules.audit.service import mask_salary
from app.modules.auth.deps import require_role
from app.modules.auth.models import Role, User

router = APIRouter(tags=["audit"])


def _apply_filters[S: Select[Any]](
    stmt: S,
    *,
    from_: datetime | None,
    to: datetime | None,
    actor_type: ActorType | None,
    actor_user_id: UUID | None,
    action: str | None,
    target_type: str | None,
    source_document_id: UUID | None,
) -> S:
    if from_ is not None:
        stmt = stmt.where(AuditLog.occurred_at >= from_)
    if to is not None:
        stmt = stmt.where(AuditLog.occurred_at <= to)
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action:
        # Substring match so the UI can filter by an action prefix (e.g. "action.").
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if source_document_id is not None:
        stmt = stmt.where(AuditLog.source_document_id == source_document_id)
    return stmt


def _serialize(db: Session, row: AuditLog) -> AuditLogOut:
    actor: AuditActorOut | None = None
    role_code: str | None = None
    if row.actor_user_id is not None:
        user = db.get(User, row.actor_user_id)
        if user is not None:
            actor = AuditActorOut(id=user.id, full_name=user.full_name)
    if row.actor_role_id is not None:
        role = db.get(Role, row.actor_role_id)
        if role is not None:
            role_code = role.code
    return AuditLogOut(
        id=row.id,
        occurred_at=row.occurred_at,
        actor_type=row.actor_type,
        actor=actor,
        actor_role_code=role_code,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        source_document_id=row.source_document_id,
        before=mask_salary(row.before) if row.before is not None else None,
        after=mask_salary(row.after) if row.after is not None else None,
        metadata=mask_salary(row.metadata_) if row.metadata_ is not None else None,
    )


@router.get(
    "/audit-logs",
    response_model=Page[AuditLogOut],
    summary="List audit log entries (EP-52)",
)
def list_audit_logs(
    current_user: Annotated[User, Depends(require_role("ROLE-01"))],
    db: Annotated[Session, Depends(get_db)],
    params: Annotated[PageParams, Depends(get_page_params)],
    from_: Annotated[datetime | None, Query(alias="from", description="occurred_at >=")] = None,
    to: Annotated[datetime | None, Query(description="occurred_at <=")] = None,
    actor_type: Annotated[ActorType | None, Query(description="Filter by actor_type")] = None,
    actor_user_id: Annotated[UUID | None, Query(description="Filter by actor_user_id")] = None,
    action: Annotated[str | None, Query(description="Substring match on action")] = None,
    target_type: Annotated[str | None, Query(description="Filter by target_type")] = None,
    source_document_id: Annotated[
        UUID | None, Query(description="Filter by source_document_id")
    ] = None,
    sort: Annotated[str, Query(description="Sort order, default -occurred_at")] = "-occurred_at",
) -> Page[AuditLogOut]:
    """EP-52: paginated, filterable audit log. ROLE-01 only; salary always masked."""
    base = select(AuditLog)
    base = _apply_filters(
        base,
        from_=from_,
        to=to,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        source_document_id=source_document_id,
    )

    count_stmt = _apply_filters(
        select(func.count()).select_from(AuditLog),
        from_=from_,
        to=to,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        source_document_id=source_document_id,
    )
    total = int(db.execute(count_stmt).scalar_one())

    order = (
        AuditLog.occurred_at.asc() if sort == "occurred_at" else AuditLog.occurred_at.desc()
    )
    rows = (
        db.execute(base.order_by(order).offset(params.offset).limit(params.limit))
        .scalars()
        .all()
    )
    items = [_serialize(db, r) for r in rows]
    return paginate(items, params=params, total=total)
