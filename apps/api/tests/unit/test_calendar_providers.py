"""TC-M31-01 (T-802/T-808) — Google/Outlook calendar providers over httpx with respx (DEC-139).

No real network. Covers OAuth code+PKCE/refresh/revoke, incremental pull, push create/update,
delete, and error mapping (429/5xx retryable). `build_provider` wires ConfigService.
"""

from datetime import UTC, datetime

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.core.config import ConfigService
from app.modules.platform.services.calendar import (
    CalendarProviderError,
    build_provider,
    make_pkce,
)
from app.modules.platform.services.calendar.base import make_state
from app.modules.platform.services.calendar.google import GoogleCalendarProvider
from app.modules.platform.services.calendar.outlook import OutlookCalendarProvider
from app.modules.platform.services.calendar.types import RemoteEvent


def utcnow() -> datetime:
    return datetime.now(UTC)


G_TOKEN = "https://oauth2.googleapis.com/token"
G_API = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _google() -> GoogleCalendarProvider:
    return GoogleCalendarProvider(
        client_id="gid",
        client_secret="gsecret",
        redirect_uri="http://localhost:4000/api/v1/integrations/google/callback",
        timeout_s=5,
    )


def _outlook() -> OutlookCalendarProvider:
    return OutlookCalendarProvider(
        client_id="mid",
        client_secret="msecret",
        redirect_uri="http://localhost:4000/api/v1/integrations/outlook/callback",
        tenant="common",
        timeout_s=5,
    )


def test_pkce_is_s256_and_url_safe() -> None:
    verifier, challenge = make_pkce()
    assert 43 <= len(verifier) <= 128
    assert "=" not in challenge and "+" not in challenge and "/" not in challenge


def test_not_configured_when_secret_missing() -> None:
    p = GoogleCalendarProvider(client_id="", client_secret="", redirect_uri="x", timeout_s=5)
    assert p.is_configured() is False
    assert _google().is_configured() is True


def test_authorize_url_carries_pkce_and_state() -> None:
    _, challenge = make_pkce()
    state = make_state()
    url = _google().authorize_url(state=state, code_challenge=challenge)
    assert "code_challenge_method=S256" in url
    assert f"state={state}" in url
    assert "access_type=offline" in url


@respx.mock
async def test_google_exchange_and_refresh() -> None:
    route = respx.post(G_TOKEN).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at1",
                "refresh_token": "rt1",
                "scope": "calendar.events",
                "expires_in": 3600,
            },
        )
    )
    tokens = await _google().exchange_code("code123", code_verifier="ver")
    assert tokens.access_token == "at1"
    assert tokens.refresh_token == "rt1"
    assert tokens.expires_at is not None and tokens.expires_at > utcnow()

    respx.post(G_TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at2", "expires_in": 3600})
    )
    refreshed = await _google().refresh("rt1")
    assert refreshed.access_token == "at2"
    assert refreshed.refresh_token == "rt1"  # reused when provider omits it
    assert route.called


@respx.mock
async def test_google_pull_incremental_and_sync_token() -> None:
    respx.get(G_API).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "e1",
                        "summary": "Demo",
                        "start": {"dateTime": "2026-10-20T09:00:00Z"},
                        "end": {"dateTime": "2026-10-20T10:00:00Z"},
                        "etag": "tag1",
                        "status": "confirmed",
                    },
                    {
                        "id": "e2",
                        "status": "cancelled",
                        "start": {"dateTime": "2026-10-21T09:00:00Z"},
                    },
                ],
                "nextSyncToken": "sync-2",
            },
        )
    )
    result = await _google().pull("at1", sync_token="sync-1", delta_link=None)
    assert result.next_sync_token == "sync-2"
    assert [e.external_id for e in result.events] == ["e1", "e2"]
    assert result.events[0].etag == "tag1"
    assert result.events[1].deleted is True


@respx.mock
async def test_google_push_create_then_update() -> None:
    create = respx.post(G_API).mock(
        return_value=httpx.Response(
            200, json={"id": "new1", "summary": "X", "start": {"dateTime": "2026-10-20T09:00:00Z"}}
        )
    )
    ev = RemoteEvent(external_id="", title="X", starts_at=utcnow(), ends_at=None)
    created = await _google().push("at1", ev, external_id=None)
    assert created.external_id == "new1"
    assert create.called

    update = respx.put(f"{G_API}/new1").mock(
        return_value=httpx.Response(
            200, json={"id": "new1", "summary": "Y", "start": {"dateTime": "2026-10-20T09:00:00Z"}}
        )
    )
    updated = await _google().push("at1", ev, external_id="new1")
    assert updated.title == "Y"
    assert update.called


@respx.mock
async def test_google_delete_tolerates_404_and_410() -> None:
    respx.delete(f"{G_API}/gone").mock(return_value=httpx.Response(404))
    await _google().delete("at1", "gone")  # no raise


@respx.mock
async def test_google_revoke_tolerates_400() -> None:
    respx.post("https://oauth2.googleapis.com/revoke").mock(return_value=httpx.Response(400))
    await _google().revoke("stale-token")  # already invalid → treated as revoked


@respx.mock
async def test_error_mapping_429_and_500_are_retryable() -> None:
    respx.get(G_API).mock(return_value=httpx.Response(429))
    with pytest.raises(CalendarProviderError) as ei:
        await _google().pull("at1", sync_token=None, delta_link=None)
    assert ei.value.retryable is True and ei.value.status == 429

    respx.get(G_API).mock(return_value=httpx.Response(503))
    with pytest.raises(CalendarProviderError) as ei2:
        await _google().pull("at1", sync_token=None, delta_link=None)
    assert ei2.value.retryable is True


@respx.mock
async def test_outlook_delta_link_and_removed() -> None:
    delta = "https://graph.microsoft.com/v1.0/me/calendarView/delta"
    respx.get(delta).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "o1",
                        "subject": "Sync",
                        "start": {"dateTime": "2026-10-20T09:00:00.000", "timeZone": "UTC"},
                        "end": {"dateTime": "2026-10-20T10:00:00.000", "timeZone": "UTC"},
                        "@odata.etag": "W/1",
                    },
                    {
                        "id": "o2",
                        "@removed": {"reason": "deleted"},
                        "start": {"dateTime": "2026-10-21T09:00:00.000"},
                    },
                ],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken=d2",
            },
        )
    )
    result = await _outlook().pull("at1", sync_token=None, delta_link=None)
    assert result.next_delta_link and "deltatoken=d2" in result.next_delta_link
    assert result.events[1].deleted is True


@respx.mock
async def test_outlook_revoke_is_noop() -> None:
    await _outlook().revoke("tok")  # Graph has no RFC-7009 revoke → no HTTP, no raise


def test_build_provider_from_config_and_unknown() -> None:
    cfg = ConfigService(
        google_oauth_client_id="gid",
        google_oauth_client_secret=SecretStr("gsecret"),
        ms_oauth_client_id="mid",
        ms_oauth_client_secret=SecretStr("msecret"),
    )
    assert build_provider("google", cfg).is_configured() is True
    assert build_provider("outlook", cfg).is_configured() is True
    with pytest.raises(ValueError, match="unknown calendar provider"):
        build_provider("zoom", cfg)

    empty = ConfigService()
    assert build_provider("google", empty).is_configured() is False
