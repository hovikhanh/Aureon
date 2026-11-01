"""EP-INT-01..04 Integration Hub DTOs (10 §7.2.8; 05 §2.10, R-DEC-117/118).

Integration (OAuth calendar account) DTOs live in `platform` — the Integration Hub owns the
`CalendarAccount`/`CalendarSyncState` entities (platform schema). Tokens are never exposed
(R-DEC-117). `CalendarProviderName` + `CalendarAccountStatus` mirror the 05/enums values.
"""

from typing import Literal

from pydantic import BaseModel

CalendarProviderName = Literal["google", "outlook"]
CalendarAccountStatus = Literal["connected", "expired", "revoked", "none"]


class ProviderStatusOut(BaseModel):
    provider: CalendarProviderName
    configured: bool
    status: CalendarAccountStatus


class ConnectOut(BaseModel):
    """EP-INT-02 — the OAuth consent URL to redirect the user to (no token here)."""

    authorize_url: str
