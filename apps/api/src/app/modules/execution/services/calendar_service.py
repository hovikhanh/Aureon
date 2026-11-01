"""EP-CAL-01..05 CalendarEvent service (10 §7.2.8; 05 §2.10, R-DEC-117/119/120/122/123).

Data-scope: every event is owned by its caller (`owner_id = user.user_id`); a user only sees
and edits their own calendar (R-DEC-17/119). Each mutation publishes
`execution.calendar_event_changed` (§9.2) in the request transaction — payload carries only
code + schedule metadata, never the mức-3 title/description/location (R-DEC-123).
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.events.outbox import publish_in_tx
from app.modules.execution.models import CalendarEvent, Task
from app.modules.execution.repositories import CalendarEventRepository
from app.modules.execution.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventUpdate,
)
from app.modules.execution.services.base import ExecBase, not_found
from app.modules.execution.services.scope import require_self


def calendar_event_out(e: CalendarEvent) -> CalendarEventOut:
    return CalendarEventOut(
        id=e.id, version=e.version, source=e.source,
        data_classification=e.data_classification, created_at=e.created_at,
        updated_at=e.updated_at, owner_id=e.owner_id, title=e.title, starts_at=e.starts_at,
        ends_at=e.ends_at, description=e.description, location=e.location,
        event_source=e.event_source, visibility=e.visibility, task_id=e.task_id,
    )  # fmt: skip


class CalendarService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.events = CalendarEventRepository(db)

    async def _publish_changed(self, e: CalendarEvent, change: str) -> None:
        await publish_in_tx(
            self.db, event_type="execution.calendar_event_changed", producer="execution",
            aggregate_schema="execution", aggregate_table="calendar_events", aggregate_id=e.id,
            payload={
                "calendar_event_id": str(e.id), "owner_id": str(e.owner_id), "change": change,
                "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                "ends_at": e.ends_at.isoformat() if e.ends_at else None,
                "event_source": e.event_source,
                "task_id": str(e.task_id) if e.task_id else None,
            },
        )  # fmt: skip

    async def list_events(
        self, user: Principal, *, date_from: date | None, date_to: date | None,
        event_source: str | None, task_id: uuid.UUID | None,
    ) -> list[CalendarEventOut]:  # fmt: skip
        where: list[ColumnElement[bool]] = [CalendarEvent.owner_id == user.user_id]
        if date_from is not None:
            where.append(
                CalendarEvent.starts_at >= datetime.combine(date_from, datetime.min.time())
            )
        if date_to is not None:
            where.append(CalendarEvent.starts_at <= datetime.combine(date_to, datetime.max.time()))
        if event_source is not None:
            where.append(CalendarEvent.event_source == event_source)
        if task_id is not None:
            where.append(CalendarEvent.task_id == task_id)
        rows = await self.events.where(*where, order=CalendarEvent.starts_at)
        return [calendar_event_out(e) for e in rows]

    async def get_event(self, user: Principal, id_: uuid.UUID) -> CalendarEvent:
        e = await self.events.get(id_)
        if e is None or e.owner_id != user.user_id:
            raise not_found("calendar event")
        return e

    async def create_event(self, user: Principal, body: CalendarEventCreate) -> CalendarEventOut:
        data = body.model_dump()
        _check_range(data.get("starts_at"), data.get("ends_at"))
        if data.get("task_id") is not None:
            await self.require_refs({"task_id": data["task_id"]}, "FR-CAL-01", task_id=Task)
        e = await self.events.create(
            owner_id=user.user_id, source="MANUAL", data_classification="CONFIDENTIAL",
            created_by=user.user_id, event_source="internal", visibility="private", **data,
        )  # fmt: skip
        await self.db.refresh(e)
        out = calendar_event_out(e)
        await self.audit("calendar_event_create", "calendar_events", e.id, after=out)
        await self._publish_changed(e, "created")
        return out

    async def update_event(
        self, user: Principal, id_: uuid.UUID, body: CalendarEventUpdate, expected: int
    ) -> CalendarEventOut:
        e = await self.get_event(user, id_)
        before = calendar_event_out(e)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _check_range(data.get("starts_at", e.starts_at), data.get("ends_at", e.ends_at))
        for k in ("title", "starts_at"):
            if k in data and data[k] is None:
                del data[k]
        await self.events.update(e, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(e)
        out = calendar_event_out(e)
        await self.audit("calendar_event_update", "calendar_events", e.id, before, out)
        await self._publish_changed(e, "updated")
        return out

    async def delete_event(self, user: Principal, id_: uuid.UUID) -> None:
        e = await self.get_event(user, id_)
        require_self(user, e.owner_id, field="owner_id")
        before = calendar_event_out(e)
        await self.events.soft_delete(e)
        await self.audit("calendar_event_delete", "calendar_events", e.id, before=before)
        await self._publish_changed(e, "deleted")


def _check_range(starts_at: Any, ends_at: Any) -> None:
    from app.core.errors import BusinessRuleError

    if starts_at is not None and ends_at is not None and ends_at < starts_at:
        raise BusinessRuleError(
            "ends_at must be on/after starts_at",
            details={"field": "ends_at", "rule": "FR-CAL-02"},
        )
