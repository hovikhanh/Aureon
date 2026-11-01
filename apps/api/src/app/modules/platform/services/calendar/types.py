"""Calendar provider value types (M3.1, R-DEC-118). Provider-neutral DTOs; no ORM, no vendor SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class CalendarProviderError(RuntimeError):
    """Provider HTTP/OAuth failure. `status` carries the upstream code (body never stored)."""

    def __init__(self, provider: str, status: int, *, retryable: bool = False) -> None:
        super().__init__(f"{provider} calendar provider error (status={status})")
        self.provider = provider
        self.status = status
        self.retryable = retryable


class ProviderNotConfiguredError(RuntimeError):
    """Client id/secret missing — surfaced as 503 DEPENDENCY_UNAVAILABLE (no new error code)."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"{provider} calendar provider is not configured")
        self.provider = provider


@dataclass(slots=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    scope: str | None
    expires_at: datetime | None


@dataclass(slots=True)
class RemoteEvent:
    """A provider calendar event normalised to internal fields."""

    external_id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    description: str | None = None
    location: str | None = None
    etag: str | None = None
    deleted: bool = False


@dataclass(slots=True)
class PullResult:
    events: list[RemoteEvent] = field(default_factory=list)
    next_sync_token: str | None = None
    next_delta_link: str | None = None
