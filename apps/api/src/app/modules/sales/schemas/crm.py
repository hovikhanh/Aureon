"""CRM DTOs — Lead / Contact / Activity (R-DEC-176, D-08 defaults; 10 EP-SAL-10..13).

Field names = 05 §2.13 column names. Money: BIGINT smallest unit + `currency` (C8).
`email` / `phone` are PII level 3 (`core.field_policy`): masked in audit snapshots, never in
event payloads. `confirm_duplicate` acknowledges the duplicate warning (R-DEC-176 d).
"""

import uuid
from datetime import date
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.modules.sales.schemas import ClientOut, DealOut, _Out, _Patch, currency_field

LeadStatus = Literal[
    "new", "contacted", "engaged", "qualified", "nurturing", "converted", "disqualified"
]
# Statuses a PATCH / create may set — `converted` only through EP-SAL-13 convert.
OpenLeadStatus = Literal["new", "contacted", "engaged", "qualified", "nurturing", "disqualified"]
LeadSource = Literal[
    "website", "referral", "event", "cold_call", "partner", "social", "advertising", "other"
]
ContactRole = Literal["decision_maker", "economic_buyer", "influencer", "user", "champion", "other"]
InfluenceLevel = Literal["low", "medium", "high"]
ActivityType = Literal[
    "call", "email", "meeting", "demo", "workshop", "poc", "proposal", "follow_up", "other"
]
ActivityStatus = Literal["planned", "completed", "cancelled"]

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE = r"^[0-9+()\-.\s]{6,30}$"


def _email() -> Any:
    return Field(default=None, max_length=320, pattern=EMAIL)


def _phone() -> Any:
    return Field(default=None, max_length=30, pattern=PHONE)


def _text(n: int) -> Any:
    return Field(default=None, max_length=n)


class SimilarRecord(BaseModel):
    """One possible duplicate in `409 DUPLICATE_RESOURCE.details.similar`."""

    id: uuid.UUID
    code: str
    name: str
    match: list[Literal["email", "phone"]]


# ---------- EP-SAL-10 leads ----------
class LeadCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    company_name: str | None = _text(300)
    job_title: str | None = _text(200)
    email: str | None = _email()
    phone: str | None = _phone()
    industry: str | None = _text(200)
    lead_source: LeadSource | None = None
    need: str | None = _text(2000)
    budget: int | None = Field(default=None, ge=0)
    currency: str = currency_field()
    score: int = Field(default=0, ge=0, le=100)
    status: OpenLeadStatus = "new"
    owner_id: uuid.UUID | None = None  # default: the caller
    department_id: uuid.UUID | None = None  # MANAGER: pinned to their department
    next_action: str | None = _text(500)
    next_action_date: date | None = None
    confirm_duplicate: bool = False


class LeadUpdate(_Patch):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_name: str | None = _text(300)
    job_title: str | None = _text(200)
    email: str | None = _email()
    phone: str | None = _phone()
    industry: str | None = _text(200)
    lead_source: LeadSource | None = None
    need: str | None = _text(2000)
    budget: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    score: int | None = Field(default=None, ge=0, le=100)
    status: OpenLeadStatus | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    next_action: str | None = _text(500)
    next_action_date: date | None = None


class LeadOut(_Out):
    code: str
    full_name: str
    company_name: str | None
    job_title: str | None
    email: str | None
    phone: str | None
    industry: str | None
    lead_source: str | None
    need: str | None
    budget: int | None
    currency: str
    score: int
    status: str
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    next_action: str | None
    next_action_date: date | None
    converted_client_id: uuid.UUID | None
    converted_contact_id: uuid.UUID | None
    converted_deal_id: uuid.UUID | None
    converted_at: AwareDatetime | None


# ---------- EP-SAL-13 convert ----------
class LeadConvert(BaseModel):
    """Client: link `client_id` or create one from the lead; Deal only when `create_deal`."""

    model_config = ConfigDict(extra="forbid")

    client_id: uuid.UUID | None = None
    create_deal: bool = False
    deal_name: str | None = Field(default=None, min_length=1, max_length=300)
    deal_value: int | None = Field(default=None, gt=0)  # default: the lead's budget
    probability_pct: float = Field(default=10, ge=0, le=100)
    expected_close_date: date | None = None


# ---------- EP-SAL-11 contacts ----------
class ContactCreate(BaseModel):
    client_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = _text(100)
    job_title: str | None = _text(200)
    department: str | None = _text(200)
    email: str | None = _email()
    phone: str | None = _phone()
    roles: list[ContactRole] = Field(default_factory=list, max_length=6)
    decision_authority: str | None = _text(500)
    influence_level: InfluenceLevel | None = None
    owner_id: uuid.UUID | None = None
    notes: str | None = _text(2000)
    confirm_duplicate: bool = False


class ContactUpdate(_Patch):
    client_id: uuid.UUID | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = _text(100)
    job_title: str | None = _text(200)
    department: str | None = _text(200)
    email: str | None = _email()
    phone: str | None = _phone()
    roles: list[ContactRole] | None = Field(default=None, max_length=6)
    decision_authority: str | None = _text(500)
    influence_level: InfluenceLevel | None = None
    owner_id: uuid.UUID | None = None
    notes: str | None = _text(2000)


class ContactOut(_Out):
    code: str
    client_id: uuid.UUID
    first_name: str
    last_name: str | None
    full_name: str
    job_title: str | None
    department: str | None
    email: str | None
    phone: str | None
    roles: list[str]
    decision_authority: str | None
    influence_level: str | None
    owner_id: uuid.UUID | None
    notes: str | None


class LeadConvertOut(BaseModel):
    lead: LeadOut
    client: ClientOut
    client_created: bool
    contact: ContactOut
    deal: DealOut | None


# ---------- EP-SAL-12 activities ----------
class ActivityCreate(BaseModel):
    type: ActivityType
    subject: str = Field(min_length=1, max_length=300)
    description: str | None = _text(4000)
    lead_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None  # default: the caller
    department_id: uuid.UUID | None = None
    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    status: ActivityStatus = "planned"
    outcome: str | None = _text(2000)
    next_action: str | None = _text(500)


class ActivityUpdate(_Patch):
    type: ActivityType | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = _text(4000)
    lead_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    contact_id: uuid.UUID | None = None
    deal_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    status: ActivityStatus | None = None
    outcome: str | None = _text(2000)
    next_action: str | None = _text(500)


class ActivityOut(_Out):
    code: str
    type: str
    subject: str
    description: str | None
    lead_id: uuid.UUID | None
    client_id: uuid.UUID | None
    contact_id: uuid.UUID | None
    deal_id: uuid.UUID | None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    start_at: AwareDatetime
    end_at: AwareDatetime | None
    status: str
    outcome: str | None
    next_action: str | None
