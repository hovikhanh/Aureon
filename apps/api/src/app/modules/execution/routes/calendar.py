"""EP-CAL-01..05 Calendar events (10 §7.2.8, R-DEC-117/119). Prefix `/calendar` (D13 · execution).

Every event is owned by its caller (`owner_id`); `execution:read` to list/get, `execution:write`
to create/update/delete. Same request shape as meetings: `Idem` on create, `IfMatch`/body
`version` on PATCH, commit at the end of the request.
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.modules.execution.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventUpdate,
    CalendarSource,
)
from app.modules.execution.services.calendar_service import (
    CalendarService,
    calendar_event_out,
)

router = EnvelopeRouter(tags=["calendar"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("execution", "read"))]
Writer = Annotated[Principal, Depends(require_permission("execution", "write"))]


@router.get("/calendar/events", response_model=list[CalendarEventOut], summary="EP-CAL-01")
async def list_events(
    db: Db, user: Reader,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None, event_source: CalendarSource | None = None,
    task_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    return await CalendarService(db).list_events(
        user, date_from=from_, date_to=to, event_source=event_source, task_id=task_id
    )


@router.post("/calendar/events", response_model=CalendarEventOut, status_code=201,
             summary="EP-CAL-02")  # fmt: skip
async def create_event(body: CalendarEventCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return CalendarEventOut.model_validate(hit)
    out = await CalendarService(db).create_event(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/calendar/events/{event_id}", response_model=CalendarEventOut, summary="EP-CAL-03")
async def get_event(event_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return calendar_event_out(await CalendarService(db).get_event(user, event_id))


@router.patch("/calendar/events/{event_id}", response_model=CalendarEventOut, summary="EP-CAL-04")
async def update_event(
    event_id: uuid.UUID, body: CalendarEventUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await CalendarService(db).update_event(user, event_id, body, exp)
    await db.commit()
    return out


@router.delete("/calendar/events/{event_id}", status_code=204, response_class=Response,
               summary="EP-CAL-05")  # fmt: skip
async def delete_event(event_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await CalendarService(db).delete_event(user, event_id)
    await db.commit()
    return Response(status_code=204)
