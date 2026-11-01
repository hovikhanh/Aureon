"""Google Calendar provider over httpx (M3.1, R-DEC-118). Incremental sync via `syncToken`."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.modules.platform.services.calendar.base import (
    CalendarProvider,
    expires_at_from,
    raise_for,
)
from app.modules.platform.services.calendar.types import (
    OAuthTokens,
    PullResult,
    RemoteEvent,
)

_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN = "https://oauth2.googleapis.com/token"  # noqa: S105 (endpoint URL, not a secret)
_REVOKE = "https://oauth2.googleapis.com/revoke"
_API = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _parse_dt(node: dict[str, Any] | None) -> datetime | None:
    if not node:
        return None
    raw = node.get("dateTime") or node.get("date")
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _to_remote(item: dict[str, Any]) -> RemoteEvent:
    return RemoteEvent(
        external_id=str(item.get("id", "")),
        title=str(item.get("summary", "")),
        starts_at=_parse_dt(item.get("start")) or datetime.now().astimezone(),
        ends_at=_parse_dt(item.get("end")),
        description=item.get("description"),
        location=item.get("location"),
        etag=item.get("etag"),
        deleted=item.get("status") == "cancelled",
    )


def _body(event: RemoteEvent) -> dict[str, Any]:
    out: dict[str, Any] = {
        "summary": event.title,
        "start": {"dateTime": event.starts_at.isoformat()},
    }
    if event.ends_at:
        out["end"] = {"dateTime": event.ends_at.isoformat()}
    if event.description:
        out["description"] = event.description
    if event.location:
        out["location"] = event.location
    return out


class GoogleCalendarProvider(CalendarProvider):
    name = "google"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        timeout_s: float,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._timeout = timeout_s

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def authorize_url(self, *, state: str, code_challenge: str) -> str:
        q = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": _SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{_AUTH}?{q}"

    async def _token_call(self, data: dict[str, str]) -> OAuthTokens:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(_TOKEN, data=data)
        raise_for(self.name, resp)
        payload = resp.json()
        return OAuthTokens(
            access_token=str(payload["access_token"]),
            refresh_token=payload.get("refresh_token"),
            scope=payload.get("scope"),
            expires_at=expires_at_from(payload.get("expires_in")),
        )

    async def exchange_code(self, code: str, *, code_verifier: str) -> OAuthTokens:
        return await self._token_call(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "code_verifier": code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> OAuthTokens:
        tokens = await self._token_call(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )
        if tokens.refresh_token is None:
            tokens.refresh_token = refresh_token
        return tokens

    async def revoke(self, token: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(_REVOKE, data={"token": token})
        if resp.status_code not in (200, 400):  # already-invalid token → 400, treat as revoked
            raise_for(self.name, resp)

    async def pull(
        self, access_token: str, *, sync_token: str | None, delta_link: str | None
    ) -> PullResult:
        params: dict[str, str] = {"showDeleted": "true", "singleEvents": "true"}
        if sync_token:
            params["syncToken"] = sync_token
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(_API, params=params, headers=headers)
        raise_for(self.name, resp)
        data = resp.json()
        events = [_to_remote(i) for i in data.get("items", [])]
        return PullResult(events=events, next_sync_token=data.get("nextSyncToken"))

    async def push(
        self, access_token: str, event: RemoteEvent, *, external_id: str | None
    ) -> RemoteEvent:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if external_id:
                resp = await client.put(f"{_API}/{external_id}", json=_body(event), headers=headers)
            else:
                resp = await client.post(_API, json=_body(event), headers=headers)
        raise_for(self.name, resp)
        return _to_remote(resp.json())

    async def delete(self, access_token: str, external_id: str) -> None:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.delete(f"{_API}/{external_id}", headers=headers)
        if resp.status_code not in (200, 204, 404, 410):
            raise_for(self.name, resp)
