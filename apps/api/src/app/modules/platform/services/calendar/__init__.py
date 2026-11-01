"""Calendar provider factory (M3.1, R-DEC-118). Build a `CalendarProvider` from ConfigService."""

from __future__ import annotations

from app.core.config import ConfigService
from app.modules.platform.services.calendar.base import (
    CalendarProvider,
    make_pkce,
    make_state,
)
from app.modules.platform.services.calendar.google import GoogleCalendarProvider
from app.modules.platform.services.calendar.outlook import OutlookCalendarProvider
from app.modules.platform.services.calendar.types import (
    CalendarProviderError,
    OAuthTokens,
    ProviderNotConfiguredError,
    PullResult,
    RemoteEvent,
)

PROVIDER_NAMES = ("google", "outlook")


def _secret(value: object) -> str:
    """Read a pydantic SecretStr | None → plain str ('' when unset)."""
    get = getattr(value, "get_secret_value", None)
    return get() if callable(get) else ""


def build_provider(name: str, config: ConfigService) -> CalendarProvider:
    """Return the provider adapter for `name`. Unknown → ValueError (routed to 404 upstream)."""
    if name == "google":
        return GoogleCalendarProvider(
            client_id=config.google_oauth_client_id,
            client_secret=_secret(config.google_oauth_client_secret),
            redirect_uri=config.google_oauth_redirect_uri,
            timeout_s=config.calendar_http_timeout_seconds,
        )
    if name == "outlook":
        return OutlookCalendarProvider(
            client_id=config.ms_oauth_client_id,
            client_secret=_secret(config.ms_oauth_client_secret),
            redirect_uri=config.ms_oauth_redirect_uri,
            tenant=config.ms_oauth_tenant,
            timeout_s=config.calendar_http_timeout_seconds,
        )
    raise ValueError(f"unknown calendar provider: {name}")


__all__ = [
    "PROVIDER_NAMES",
    "CalendarProvider",
    "CalendarProviderError",
    "GoogleCalendarProvider",
    "OAuthTokens",
    "OutlookCalendarProvider",
    "ProviderNotConfiguredError",
    "PullResult",
    "RemoteEvent",
    "build_provider",
    "make_pkce",
    "make_state",
]
