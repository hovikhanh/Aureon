"""EP-INT-01..04 Integration Hub — calendar OAuth connect/callback/disconnect (10 §7.2.8).

Per-user delegated OAuth (R-DEC-17/119): the caller connects their own calendar; tokens are
stored encrypted (`EncryptedText`, 05 §2.10) and never returned. A provider with no client
id/secret is "not configured" → `DependencyUnavailableError` 503 (R-DEC-118, no new code). The
ephemeral OAuth `state`+PKCE `code_verifier` live in `platform.user_preferences` keyed
`calendar.oauth.<provider>` until the callback consumes them.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import ConfigService, get_config
from app.core.errors import BadRequestError, DependencyUnavailableError, NotFoundError
from app.core.tenant import require_tenant
from app.modules.platform.models import CalendarAccount
from app.modules.platform.repositories import (
    CalendarAccountRepository,
    UserPreferenceRepository,
)
from app.modules.platform.services.calendar import (
    PROVIDER_NAMES,
    CalendarProvider,
    build_provider,
    make_pkce,
    make_state,
)


def _pref_key(provider: str) -> str:
    return f"calendar.oauth.{provider}"


class IntegrationService:
    def __init__(self, db: AsyncSession, config: ConfigService | None = None) -> None:
        self.db = db
        self.config = config or get_config()
        self.accounts = CalendarAccountRepository(db)
        self.prefs = UserPreferenceRepository(db)

    def _provider(self, name: str) -> CalendarProvider:
        if name not in PROVIDER_NAMES:
            raise NotFoundError(f"unknown calendar provider: {name}")
        return build_provider(name, self.config)

    def _require_configured(self, provider: CalendarProvider) -> None:
        if not provider.is_configured():
            raise DependencyUnavailableError(
                f"calendar provider {provider.name} is not configured",
                details={"provider": provider.name},
            )

    async def providers(self, user_id: uuid.UUID) -> list[dict[str, Any]]:
        linked = {a.provider: a.status for a in await self.accounts.for_user(user_id)}
        out: list[dict[str, Any]] = []
        for name in PROVIDER_NAMES:
            provider = build_provider(name, self.config)
            out.append(
                {
                    "provider": name,
                    "configured": provider.is_configured(),
                    "status": linked.get(name, "none"),
                }
            )
        return out

    async def connect(self, user_id: uuid.UUID, name: str) -> str:
        provider = self._provider(name)
        self._require_configured(provider)
        state = make_state()
        verifier, challenge = make_pkce()
        await self._store_pending(user_id, name, {"state": state, "code_verifier": verifier})
        await record_audit(
            self.db, action="platform.calendar_connect_start", target_schema="platform",
            target_table="calendar_accounts", metadata={"provider": name},
        )  # fmt: skip
        return provider.authorize_url(state=state, code_challenge=challenge)

    async def callback(self, user_id: uuid.UUID, name: str, *, code: str, state: str) -> None:
        provider = self._provider(name)
        self._require_configured(provider)
        pending = await self._pending(user_id, name)
        if not pending or pending.get("state") != state:
            raise BadRequestError("invalid or expired OAuth state", details={"provider": name})
        tokens = await provider.exchange_code(code, code_verifier=str(pending["code_verifier"]))
        await self._clear_pending(user_id, name)
        await self._upsert_account(user_id, name, tokens)
        await record_audit(
            self.db, action="platform.calendar_connected", target_schema="platform",
            target_table="calendar_accounts", metadata={"provider": name},
        )  # fmt: skip

    async def disconnect(self, user_id: uuid.UUID, name: str) -> None:
        provider = self._provider(name)
        account = await self.accounts.by_user_provider(user_id, name)
        if account is None:
            raise NotFoundError(f"no connected {name} calendar")
        token = account.access_token or account.refresh_token
        if provider.is_configured() and token:
            await provider.revoke(token)
        await self.accounts.update(account, status="revoked", access_token=None, refresh_token=None)
        await record_audit(
            self.db, action="platform.calendar_disconnected", target_schema="platform",
            target_table="calendar_accounts", target_id=account.id, metadata={"provider": name},
        )  # fmt: skip

    async def _upsert_account(self, user_id: uuid.UUID, name: str, tokens: Any) -> CalendarAccount:
        account = await self.accounts.by_user_provider(user_id, name)
        values = {
            "access_token": tokens.access_token, "refresh_token": tokens.refresh_token,
            "scope": tokens.scope, "expires_at": tokens.expires_at, "status": "connected",
        }  # fmt: skip
        if account is None:
            return await self.accounts.create(
                tenant_id=require_tenant(), user_id=user_id, provider=name, **values
            )
        await self.accounts.update(account, **values)
        return account

    async def _store_pending(self, user_id: uuid.UUID, name: str, value: dict[str, str]) -> None:
        existing = await self.prefs.by_key(user_id, _pref_key(name))
        if existing is None:
            await self.prefs.create(
                tenant_id=require_tenant(), user_id=user_id, key=_pref_key(name), value_json=value
            )
        else:
            await self.prefs.update(existing, value_json=value)

    async def _pending(self, user_id: uuid.UUID, name: str) -> dict[str, Any] | None:
        row = await self.prefs.by_key(user_id, _pref_key(name))
        if row is None or not row.value_json:
            return None
        return dict(row.value_json)

    async def _clear_pending(self, user_id: uuid.UUID, name: str) -> None:
        """Consume the one-time state: blank the stored value (ConfigModel has no soft delete)."""
        row = await self.prefs.by_key(user_id, _pref_key(name))
        if row is not None:
            await self.prefs.update(row, value_json={})
