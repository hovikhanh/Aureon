"""CalendarProvider protocol + shared OAuth/PKCE helpers (M3.1, R-DEC-118).

All provider I/O goes through `httpx` (no vendor SDK, 07 §6.1). OAuth 2.0 authorization-code
with PKCE (S256). Providers raise `CalendarProviderError` (status only; body never logged —
it may echo tokens) or `ProviderNotConfiguredError` when credentials are absent.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from app.modules.platform.services.calendar.types import (
    CalendarProviderError,
    OAuthTokens,
    PullResult,
    RemoteEvent,
)


def make_pkce() -> tuple[str, str]:
    """Return `(verifier, challenge)` for PKCE S256 (RFC 7636)."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def make_state() -> str:
    return secrets.token_urlsafe(32)


def expires_at_from(expires_in: Any) -> datetime | None:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return datetime.now(UTC) + timedelta(seconds=seconds)


class CalendarProvider(Protocol):
    """Provider-neutral calendar contract used by the service layer."""

    name: str

    def is_configured(self) -> bool: ...

    def authorize_url(self, *, state: str, code_challenge: str) -> str: ...

    async def exchange_code(self, code: str, *, code_verifier: str) -> OAuthTokens: ...

    async def refresh(self, refresh_token: str) -> OAuthTokens: ...

    async def revoke(self, token: str) -> None: ...

    async def pull(
        self, access_token: str, *, sync_token: str | None, delta_link: str | None
    ) -> PullResult: ...

    async def push(
        self, access_token: str, event: RemoteEvent, *, external_id: str | None
    ) -> RemoteEvent: ...

    async def delete(self, access_token: str, external_id: str) -> None: ...


def raise_for(provider: str, resp: httpx.Response) -> None:
    """Translate a non-2xx provider response into `CalendarProviderError` (no body stored)."""
    if resp.is_success:
        return
    retryable = resp.status_code == 429 or resp.status_code >= 500
    raise CalendarProviderError(provider, resp.status_code, retryable=retryable)
