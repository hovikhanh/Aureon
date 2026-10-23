"""Notification e-mail tasks (T-616b, R-DEC-20/33; 10 §7.2.1 `notifications.dispatch_email`).

* `app.notifications.dispatch_email` (beat): per active tenant, enqueue one send task per
  `PENDING` notification. Re-enqueueing the same id is harmless — the send is idempotent.
* `app.notifications.send_email(tenant_id, notification_id)`: claim → send → mark, one
  transaction; SMTP error → retry with 5 s / 30 s / 120 s backoff (attempts stored on the row),
  third failure → `FAILED`.
"""

import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import active_tenant_ids, tenant_scope
from app.modules.platform.services.email_sender import dispatch, pending_ids
from app.worker import celery_app
from app.workers.events import _engine

LIMITS: dict[str, Any] = {"time_limit": 60, "soft_time_limit": 50}


async def _send(tenant_id: uuid.UUID, notification_id: uuid.UUID) -> tuple[str, int | None]:
    async with _engine() as engine:
        with tenant_scope(tenant_id):
            async with AsyncSession(engine, expire_on_commit=False) as db:
                out = await dispatch(db, notification_id)
                await db.commit()
                return out.status, out.retry_in


async def _sweep() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    async with _engine() as engine:
        for tenant in active_tenant_ids():
            with tenant_scope(tenant):
                async with AsyncSession(engine) as db:
                    found += [(str(tenant), str(i)) for i in await pending_ids(db)]
    return found


@celery_app.task(name="app.notifications.send_email", bind=True, **LIMITS)  # type: ignore[untyped-decorator]
def send_email(self: Any, tenant_id: str, notification_id: str) -> str:
    status, retry_in = asyncio.run(_send(uuid.UUID(tenant_id), uuid.UUID(notification_id)))
    if status == "RETRY" and retry_in is not None:
        self.apply_async(args=[tenant_id, notification_id], countdown=retry_in)
    return status


@celery_app.task(name="app.notifications.dispatch_email", **LIMITS)  # type: ignore[untyped-decorator]
def dispatch_email() -> int:
    """Beat sweep. Rows already being retried are picked again only after they are idle."""
    rows = asyncio.run(_sweep())
    for tenant_id, notification_id in rows:
        send_email.delay(tenant_id, notification_id)
    return len(rows)
