"""EP-52 audit log read (SCR-14, FR-DC-05): list only — append-only, no C/U/D."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import mask
from app.core.envelope import Page
from app.modules.platform.repositories import AuditRepository
from app.modules.platform.schemas import AuditLogOut


class AuditQueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditRepository(db)

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        action: str | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> Page[AuditLogOut]:
        rows, total = await self.repo.list(
            limit=limit,
            offset=offset,
            action=action,
            target_table=target_type,
            target_id=target_id,
            actor_user_id=actor_user_id,
        )
        items = [
            AuditLogOut(
                id=r.id,
                occurred_at=r.occurred_at,
                actor_type=str(r.actor_type),
                actor_user_id=r.actor_user_id,
                actor_role=None if r.actor_role is None else str(r.actor_role),
                action=r.action,
                target_schema=r.target_schema,
                target_table=r.target_table,
                target_id=r.target_id,
                before=mask(r.before),  # defence in depth: rows are masked at write time too
                after=mask(r.after),
                why=r.why,
            )
            for r in rows
        ]
        return Page(items=items, total=total, limit=limit, offset=offset)
