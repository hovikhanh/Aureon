"""M3.1 two-way calendar sync engine (T-804/T-805/T-806, 10 §7.2.8, R-DEC-121/123).

Owns the `execution`-schema entities (`CalendarEvent`, `ExternalEventLink`) and orchestrates
two-way sync through platform's **public** `CalendarIntegrationService` (DEC-125 — execution →
platform via services only; platform never imports execution):

- **pull** (beat `calendar_sync`): per connected account, fold each remote change into the
  owner's internal `CalendarEvent` via `ExternalEventLink` (idempotent on `(account, external)`),
  last-writer-wins by `etag` (R-DEC-121).
- **push** (consumer `platform.on_calendar_event_changed`): mirror one internal change to every
  connected provider of the owner, idempotent via `ExternalEventLink`.

Provider 429/5xx raises `CalendarProviderError(retryable=True)`; the event-bus backoff
(5s/30s/120s → DLQ) handles it. Calendar bodies are mức-3 Confidential and never reach an LLM
(R-DEC-123) — this engine does no model calls.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import require_tenant
from app.modules.execution.models import CalendarEvent, ExternalEventLink
from app.modules.execution.repositories import (
    CalendarEventRepository,
    ExternalEventLinkRepository,
)
from app.modules.platform.services.calendar.types import RemoteEvent
from app.modules.platform.services.calendar_integration import (
    AccountRef,
    CalendarIntegrationService,
)


class CalendarSyncService:
    """Two-way sync engine; one instance per worker transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.events = CalendarEventRepository(db)
        self.links = ExternalEventLinkRepository(db)
        self.hub = CalendarIntegrationService(db)

    # ---------- pull (beat) ----------
    async def pull_all(self) -> int:
        applied = 0
        for ref in await self.hub.connected_accounts():
            applied += await self._pull_account(ref)
        return applied

    async def _pull_account(self, ref: AccountRef) -> int:
        result = await self.hub.pull(ref)
        if result is None:
            return 0
        applied = 0
        for remote in result.events:
            if await self._apply_remote(ref, remote):
                applied += 1
        return applied

    async def _apply_remote(self, ref: AccountRef, remote: RemoteEvent) -> bool:
        """Fold one remote event into the internal calendar; LWW by `etag`. True if applied."""
        link = await self.links.by_account_external(ref.account_id, remote.external_id)
        if remote.deleted:
            if link is None:
                return False
            event = await self.events.get(link.calendar_event_id)
            if event is not None:
                await self.events.soft_delete(event)
            await self.links.soft_delete(link)
            return True
        if link is not None and link.etag is not None and link.etag == remote.etag:
            return False  # last-writer-wins: unchanged remote, skip
        if link is None:
            event = await self.events.create(
                tenant_id=require_tenant(), owner_id=ref.user_id, source="EVENT",
                data_classification="CONFIDENTIAL", created_by=ref.user_id,
                event_source=ref.provider, visibility="private", title=remote.title,
                starts_at=remote.starts_at, ends_at=remote.ends_at,
                description=remote.description, location=remote.location,
            )  # fmt: skip
            await self.db.flush()
            await self.links.create(
                tenant_id=require_tenant(), calendar_event_id=event.id,
                account_id=ref.account_id, external_id=remote.external_id, etag=remote.etag,
            )  # fmt: skip
            return True
        event = await self.events.get(link.calendar_event_id)
        if event is None:
            return False
        await self.events.update(
            event, title=remote.title, starts_at=remote.starts_at, ends_at=remote.ends_at,
            description=remote.description, location=remote.location,
        )  # fmt: skip
        await self.links.update(link, etag=remote.etag)
        return True

    # ---------- push (consumer) ----------
    async def push_event(
        self, owner_id: uuid.UUID, calendar_event_id: uuid.UUID, change: str
    ) -> int:
        accounts = await self.hub.connected_for_user(owner_id)
        if not accounts:
            return 0
        event = await self.events.get(calendar_event_id)
        if change != "deleted" and (event is None or event.event_source != "internal"):
            # Only internal events are pushed out; a provider-sourced event is not echoed back.
            return 0
        pushed = 0
        for ref in accounts:
            if await self._push_to_account(ref, calendar_event_id, event, change):
                pushed += 1
        return pushed

    async def _push_to_account(
        self,
        ref: AccountRef,
        calendar_event_id: uuid.UUID,
        event: CalendarEvent | None,
        change: str,
    ) -> bool:
        link = await self._link_for(ref.account_id, calendar_event_id)
        if change == "deleted":
            if link is None:
                return False
            await self.hub.delete_remote(ref.account_id, link.external_id)
            await self.links.soft_delete(link)
            return True
        if event is None:
            return False
        remote = RemoteEvent(
            external_id=link.external_id if link else "",
            title=event.title, starts_at=event.starts_at, ends_at=event.ends_at,
            description=event.description, location=event.location,
        )  # fmt: skip
        saved = await self.hub.push_remote(
            ref.account_id, remote, external_id=link.external_id if link else None
        )
        if saved is None:
            return False
        if link is None:
            await self.links.create(
                tenant_id=require_tenant(), calendar_event_id=calendar_event_id,
                account_id=ref.account_id, external_id=saved.external_id, etag=saved.etag,
                last_pushed_at=datetime.now(UTC),
            )  # fmt: skip
        else:
            await self.links.update(link, etag=saved.etag, last_pushed_at=datetime.now(UTC))
        return True

    async def _link_for(
        self, account_id: uuid.UUID, calendar_event_id: uuid.UUID
    ) -> ExternalEventLink | None:
        for link in await self.links.for_event(calendar_event_id):
            if link.account_id == account_id:
                return link
        return None
