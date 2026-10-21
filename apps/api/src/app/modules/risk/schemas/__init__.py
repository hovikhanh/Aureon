"""Risk API DTOs (10 §3.10, §4 EP-101..106). API names follow 10; columns follow 05 (DEC-215).

10 ↔ 05 mapping (in the service, never in the DB): `level` ↔ `severity`; `linked_entities`
is the 05 jsonb object of soft refs `{hiring_plan_id, budget_id, deal_id, product_id,
client_id, …}`; assessment `note` ↔ `rationale`.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal[
    "financial", "operational", "strategic", "people", "business", "customer", "product",
    "technology", "security", "compliance", "legal", "partner_supplier", "ai",
]  # fmt: skip
Level = Literal["low", "medium", "high", "critical"]
RiskStatus = Literal[
    "proposed", "identified", "assessed", "mitigating", "monitoring", "accepted", "closed",
    "rejected",
]  # fmt: skip
RiskSource = Literal["manual", "event", "ai", "document"]
_LINK_KEY = re.compile(r"^[a-z][a-z_]{1,40}_id$")


def check_links(value: dict[str, uuid.UUID] | None) -> dict[str, uuid.UUID] | None:
    """`linked_entities` keys must be `<entity>_id` soft refs (05 ENT-Risk)."""
    if value is None:
        return None
    bad = sorted(k for k in value if not _LINK_KEY.match(k))
    if bad:
        raise ValueError(f"linked_entities keys must be `<entity>_id`: {bad}")
    return value


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class RiskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: Category
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    linked_entities: dict[str, uuid.UUID] = Field(default_factory=dict, max_length=20)
    review_date: date | None = None

    _links = field_validator("linked_entities")(check_links)


class RiskUpdate(BaseModel):
    """PATCH: only sent fields; `status` changes go through EP-106 / EP-104."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: Category | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    linked_entities: dict[str, uuid.UUID] | None = Field(default=None, max_length=20)
    review_date: date | None = None

    _links = field_validator("linked_entities")(check_links)


class RiskOut(_Out):
    code: str
    title: str
    description: str | None
    category: Category
    likelihood: int
    impact: int
    risk_score: int
    level: Level
    status: RiskStatus
    risk_source: RiskSource
    owner_id: uuid.UUID | None
    department_id: uuid.UUID | None
    linked_entities: dict[str, Any]
    review_date: date | None
    identified_at: datetime
    proposed_at: datetime | None
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    accepted_by: uuid.UUID | None
    accepted_reason: str | None
    accepted_at: datetime | None
    source_event_id: uuid.UUID | None
    source_document_id: uuid.UUID | None


# ---------- EP-102 ----------
class AssessmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    likelihood: int
    impact: int
    risk_score: int
    level: Level
    note: str | None
    assessed_at: datetime
    assessed_by: uuid.UUID | None


# ---------- EP-104 / EP-106 ----------
class AcceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000)


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_status: RiskStatus
    reason: str | None = Field(default=None, max_length=2000)
    owner_id: uuid.UUID | None = None
