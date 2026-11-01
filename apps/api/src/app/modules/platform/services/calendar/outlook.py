"""Outlook (Microsoft Graph) calendar provider over httpx (M3.1, R-DEC-118).

Incremental sync via Graph delta query (`/me/calendarView/delta` → `@odata.deltaLink`).
"""

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

_SCOPE = "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
_GRAPH = "https://graph.microsoft.com/v1.0/me/events"
_DELTA = "https://graph.microsoft.com/v1.0/me/calendarView/delta"


def _auth_base(tenant: str) -> str:
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"


def _parse_dt(node: dict[str, Any] | None) -> datetime | None:
    if not node or not node.get("dateTime"):
        return None
    raw = str(node["dateTime"])
    if not raw.endswith(("Z", "+00:00")) and "+" not in raw:
        raw += "+00:00"
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _to_remote(item: dict[str, Any]) -> RemoteEvent:
    body = item.get("body") or {}
    loc = item.get("location") or {}
    return RemoteEvent(
        external_id=str(item.get("id", "")),
        title=str(item.get("subject", "")),
        starts_at=_parse_dt(item.get("start")) or datetime.now().astimezone(),
        ends_at=_parse_dt(item.get("end")),
        description=body.get("content"),
        location=loc.get("displayName"),
        etag=item.get("@odata.etag"),
        deleted="@removed" in item,
    )


def _body(event: RemoteEvent) -> dict[str, Any]:
    out: dict[str, Any] = {
        "subject": event.title,
        "start": {"dateTime": event.starts_at.isoformat(), "timeZone": "UTC"},
    }
    if event.ends_at:
        out["end"] = {"dateTime": event.ends_at.isoformat(), "timeZone": "UTC"}
    if event.description:
        out["body"] = {"contentType": "text", "content": event.description}
    if event.location:
        out["location"] = {"displayName": event.location}
    return out


class OutlookCalendarProvider(CalendarProvider):
    name = "outlook"

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        tenant: str,
        timeout_s: float,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._tenant = tenant
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
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{_auth_base(self._tenant)}/authorize?{q}"

    async def _token_call(self, data: dict[str, str]) -> OAuthTokens:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{_auth_base(self._tenant)}/token", data=data)
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
                "scope": _SCOPE,
            }
        )

    async def refresh(self, refresh_token: str) -> OAuthTokens:
        tokens = await self._token_call(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": _SCOPE,
            }
        )
        if tokens.refresh_token is None:
            tokens.refresh_token = refresh_token
        return tokens

    async def revoke(self, token: str) -> None:
        # Graph has no RFC-7009 revoke; dropping the stored token is the revoke (R-DEC-121).
        return None

    async def pull(
        self, access_token: str, *, sync_token: str | None, delta_link: str | None
    ) -> PullResult:
        url = delta_link or _DELTA
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, headers=headers)
        raise_for(self.name, resp)
        data = resp.json()
        events = [_to_remote(i) for i in data.get("value", [])]
        return PullResult(events=events, next_delta_link=data.get("@odata.deltaLink"))

    async def push(
        self, access_token: str, event: RemoteEvent, *, external_id: str | None
    ) -> RemoteEvent:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if external_id:
                resp = await client.patch(
                    f"{_GRAPH}/{external_id}", json=_body(event), headers=headers
                )
            else:
                resp = await client.post(_GRAPH, json=_body(event), headers=headers)
        raise_for(self.name, resp)
        return _to_remote(resp.json())

    async def delete(self, access_token: str, external_id: str) -> None:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.delete(f"{_GRAPH}/{external_id}", headers=headers)
        if resp.status_code not in (200, 204, 404):
            raise_for(self.name, resp)
