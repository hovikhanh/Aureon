"""EP-CAL-01..05 Calendar event DTOs (10 §7.2.8; 05 §2.10, R-DEC-117/119/123).

CalendarEvent is mức-3 Confidential (R-DEC-123). Integration (OAuth account) DTOs live in
`platform.schemas.integrations` — the Integration Hub owns those entities.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.execution.schemas.common import Out, Patch

CalendarSource = Literal["internal", "google", "outlook"]


# ---------- EP-CAL-01..05 calendar events ----------
class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = Field(default=None, max_length=20000)
    location: str | None = Field(default=None, max_length=500)
    task_id: uuid.UUID | None = None


class CalendarEventUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    description: str | None = Field(default=None, max_length=20000)
    location: str | None = Field(default=None, max_length=500)


class CalendarEventOut(Out):
    owner_id: uuid.UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    description: str | None
    location: str | None
    event_source: CalendarSource
    visibility: str
    task_id: uuid.UUID | None
