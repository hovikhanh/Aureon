"""Public Integration-Hub service for cross-module callers (M3.1, DEC-125, R-DEC-121).

`CalendarIntegrationService` is the **public** surface the `execution` sync engine uses so it
never imports platform's `models`/`repositories`. It owns everything about `CalendarAccount` /
`CalendarSyncState` (platform schema) and all provider I/O (via the provider adapters), and
returns plain DTOs — never ORM rows, never tokens. A token that cannot be refreshed flips the
account to `expired` and raises a reconnect `Notification` (no new endpoint/tool).

Provider HTTP errors surface as `CalendarProviderError` (retryable on 429/5xx) so the event-bus
backoff (5s/30s/120s → DLQ) governs the push consumer.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import ConfigService, get_config
from app.core.tenant import require_tenant
from app.modules.platform.models import CalendarAccount
from app.modules.platform.repositories import (
    CalendarAccountRepository,
    CalendarSyncStateRepository,
)
from app.modules.platform.services.calendar import CalendarProvider, build_provider
from app.modules.platform.services.calendar.types import OAuthTokens, PullResult, RemoteEvent
from app.modules.platform.services.notification_service import NotificationService


@dataclass(slots=True)
class AccountRef:
    """A connected calendar account, provider-neutral — no tokens, no ORM."""

    account_id: uuid.UUID
    user_id: uuid.UUID
    provider: str


def _expired(account: CalendarAccount, *, now: datetime | None = None) -> bool:
    if account.expires_at is None:
        return False
    at = now or datetime.now(UTC)
    exp = account.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    return exp <= at


class CalendarIntegrationService:
    """Public API: account discovery, token refresh, and provider pull/push/delete."""

    def __init__(self, db: AsyncSession, config: ConfigService | None = None) -> None:
        self.db = db
        self.config = config or get_config()
        self.accounts = CalendarAccountRepository(db)
        self.sync_states = CalendarSyncStateRepository(db)

    # ---------- account discovery ----------
    async def connected_accounts(self) -> list[AccountRef]:
        return [_ref(a) for a in await self.accounts.connected()]

    async def connected_for_user(self, user_id: uuid.UUID) -> list[AccountRef]:
        return [_ref(a) for a in await self.accounts.for_user(user_id) if a.status == "connected"]

    # ---------- provider I/O ----------
    async def pull(self, ref: AccountRef) -> PullResult | None:
        account = await self.accounts.get(ref.account_id)
        if account is None:
            return None
        provider = self._provider(account)
        if not provider.is_configured():
            return None
        token = await self._ensure_token(account, provider)
        if token is None:
            return None
        state = await self.sync_states.for_account(account.id)
        result = await provider.pull(
            token,
            sync_token=state.sync_token if state else None,
            delta_link=state.delta_link if state else None,
        )
        await self._save_cursor(account.id, result)
        return result

    async def push_remote(
        self, account_id: uuid.UUID, remote: RemoteEvent, *, external_id: str | None
    ) -> RemoteEvent | None:
        account = await self.accounts.get(account_id)
        if account is None:
            return None
        provider = self._provider(account)
        if not provider.is_configured():
            return None
        token = await self._ensure_token(account, provider)
        if token is None:
            return None
        return await provider.push(token, remote, external_id=external_id)

    async def delete_remote(self, account_id: uuid.UUID, external_id: str) -> bool:
        account = await self.accounts.get(account_id)
        if account is None:
            return False
        provider = self._provider(account)
        if not provider.is_configured():
            return False
        token = await self._ensure_token(account, provider)
        if token is None:
            return False
        await provider.delete(token, external_id)
        return True

    # ---------- internals ----------
    def _provider(self, account: CalendarAccount) -> CalendarProvider:
        return build_provider(account.provider, self.config)

    async def _ensure_token(
        self, account: CalendarAccount, provider: CalendarProvider
    ) -> str | None:
        if account.access_token and not _expired(account):
            return account.access_token
        if not account.refresh_token:
            await self._mark_expired(account, provider.name)
            return None
        try:
            tokens: OAuthTokens = await provider.refresh(account.refresh_token)
        except Exception:
            await self._mark_expired(account, provider.name)
            return None
        await self.accounts.update(
            account,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token or account.refresh_token,
            scope=tokens.scope or account.scope,
            expires_at=tokens.expires_at,
            status="connected",
        )
        return tokens.access_token

    async def _mark_expired(self, account: CalendarAccount, provider_name: str) -> None:
        await self.accounts.update(account, status="expired")
        await NotificationService(self.db).create(
            recipient_id=account.user_id,
            kind="alert",
            title=f"Kết nối lịch {provider_name} đã hết hạn",
            body=f"Vui lòng kết nối lại lịch {provider_name} để tiếp tục đồng bộ.",
            link="/settings/integrations",
            ref_schema="platform",
            ref_table="calendar_accounts",
            ref_id=account.id,
        )
        await record_audit(
            self.db, action="platform.calendar_token_expired", target_schema="platform",
            target_table="calendar_accounts", target_id=account.id,
            metadata={"provider": provider_name},
        )  # fmt: skip

    async def _save_cursor(self, account_id: uuid.UUID, result: PullResult) -> None:
        values: dict[str, Any] = {
            "sync_token": result.next_sync_token,
            "delta_link": result.next_delta_link,
            "last_synced_at": datetime.now(UTC),
        }
        existing = await self.sync_states.for_account(account_id)
        if existing is None:
            await self.sync_states.create(
                tenant_id=require_tenant(), account_id=account_id, **values
            )
        else:
            await self.sync_states.update(existing, **values)


def _ref(a: CalendarAccount) -> AccountRef:
    return AccountRef(account_id=a.id, user_id=a.user_id, provider=a.provider)
