"""Task notifications written in the caller's tx (R-DEC-46, 05 §2.5 ENT-Notification).

Platform's public `NotificationService` (lazy import, same precedent as IDP `_notify`); task
people refs (employee id, or user id when there is no employee record — R-DEC-41) are mapped to
a user through the auth public service; no active account → skipped with an info log.
Links: `/work?task=<id>`. Title/body carry no level 3–4 data.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import Task


async def _users(db: AsyncSession, *refs: uuid.UUID | None) -> list[uuid.UUID]:
    from app.modules.auth.services.auth_service import AuthService

    auth, out = AuthService(db), []
    for ref in dict.fromkeys(r for r in refs if r is not None):
        uid = await auth.user_id_for_ref(ref)
        if uid is None:
            from app.modules.platform.services.notification_service import log

            log.info("notification skipped: %s has no active account", ref)
        else:
            out.append(uid)
    return out


async def notify_task(
    db: AsyncSession, t: Task, *, kind: str, title: str, to: tuple[uuid.UUID | None, ...],
    actor: uuid.UUID | None,
) -> list[uuid.UUID]:  # fmt: skip
    """Notify the users behind `to` (minus the actor) about task `t`."""
    from app.modules.platform.services.notification_service import NotificationService

    return await NotificationService(db).notify_users(
        await _users(db, *to), skip=(actor,), kind=kind, title=title, body=t.title,
        link=f"/work?task={t.id}", ref_schema="execution", ref_table="tasks", ref_id=t.id,
    )  # fmt: skip
