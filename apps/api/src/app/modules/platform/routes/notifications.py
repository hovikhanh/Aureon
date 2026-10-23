"""EP-NTF-01..05 — the caller's own notification inbox + e-mail preferences (M1.2 T-616).

R-DEC-31: `(token)` only — like EP-ADM-03/04 there is no domain permission; every query is
pinned to `recipient_id = sub` + the current tenant in the repository.
"""

import uuid
from typing import Annotated, Any

from fastapi import Query

from app.core.deps import CurrentUser, DbSession
from app.core.idempotency import Idem
from app.core.routing import EnvelopeRouter
from app.modules.platform.schemas import (
    NotificationKind,
    NotificationOut,
    NotificationPreferenceOut,
    PreferencesIn,
    ReadAllIn,
    ReadAllOut,
)
from app.modules.platform.services.notification_service import NotificationService

router = EnvelopeRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut], summary="EP-NTF-01 My notifications")
async def list_notifications(
    db: DbSession,
    user: CurrentUser,
    unread_only: bool = False,
    kind: NotificationKind | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Any:
    return await NotificationService(db).inbox(
        user.user_id, unread_only=unread_only, kind=kind, limit=limit, offset=offset
    )


@router.post("/read-all", response_model=ReadAllOut, summary="EP-NTF-03 Mark all read")
async def read_all(body: ReadAllIn, db: DbSession, user: CurrentUser, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ReadAllOut.model_validate(hit)
    out = ReadAllOut(updated=await NotificationService(db).read_all(user.user_id, body.up_to))
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/preferences", response_model=list[NotificationPreferenceOut], summary="EP-NTF-04")
async def get_preferences(db: DbSession, user: CurrentUser) -> Any:
    return await NotificationService(db).preferences(user.user_id)


@router.patch("/preferences", response_model=list[NotificationPreferenceOut], summary="EP-NTF-05")
async def patch_preferences(body: PreferencesIn, db: DbSession, user: CurrentUser) -> Any:
    out = await NotificationService(db).update_preferences(user.user_id, body.items)
    await db.commit()
    return out


@router.post("/{notification_id}/read", response_model=NotificationOut, summary="EP-NTF-02")
async def mark_read(
    notification_id: uuid.UUID, db: DbSession, user: CurrentUser, idem: Idem
) -> Any:
    if (hit := await idem.replay({"id": str(notification_id)})) is not None:
        return NotificationOut.model_validate(hit)
    out = await NotificationService(db).mark_read(user.user_id, notification_id)
    await db.commit()
    await idem.remember(out)
    return out
