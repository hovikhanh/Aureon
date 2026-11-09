"""Schema `sales` — 8 tables (05 §4.3, §2.13). Column groups follow 05 §2.1.

Business entities → `BusinessModel`: clients, deals, sales_targets, contracts, and the CRM
entities of R-DEC-176 (D-08 defaults): leads, contacts, activities.
Append-only → `LogModel`: deal_stage_history (05 §1 C5, §2.1 group 3).
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Index,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, LogModel
from app.core.columns import currency, fk, money, pct, schema_args, sr, txt
from app.core.enums import PERIOD_TYPE, pg_enum

S = "sales"
TS = DateTime(timezone=True)
ZERO_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"

# ---------- module-owned enums (05 §6) ----------
COMPANY_SIZE = pg_enum(S, "company_size", "startup", "small", "medium", "enterprise")
CLIENT_STATUS = pg_enum(S, "client_status", "prospect", "active", "churned")
DEAL_STAGE = pg_enum(
    S, "deal_stage", "lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"
)
TARGET_SCOPE = pg_enum(S, "target_scope", "team", "individual")
CONTRACT_STATUS = pg_enum(S, "contract_status", "draft", "active", "expired", "terminated")

# R-DEC-176 CRM (migration 0028)
LEAD_STATUS = pg_enum(
    S, "lead_status",
    "new", "contacted", "engaged", "qualified", "nurturing", "converted", "disqualified",
)  # fmt: skip
INFLUENCE_LEVEL = pg_enum(S, "influence_level", "low", "medium", "high")
ACTIVITY_TYPE = pg_enum(
    S, "activity_type",
    "call", "email", "meeting", "demo", "workshop", "poc", "proposal", "follow_up", "other",
)  # fmt: skip
ACTIVITY_STATUS = pg_enum(S, "activity_status", "planned", "completed", "cancelled")

MODULE_ENUMS = (
    COMPANY_SIZE, CLIENT_STATUS, DEAL_STAGE, TARGET_SCOPE, CONTRACT_STATUS,
    LEAD_STATUS, INFLUENCE_LEVEL, ACTIVITY_TYPE, ACTIVITY_STATUS,
)  # fmt: skip


def code_default(prefix: str, sequence: str) -> Any:
    """Auto code `<prefix>-000001` from a per-type sequence (R-DEC-176 e); unique column."""
    return text(f"'{prefix}-' || lpad(nextval('{S}.{sequence}')::text, 6, '0')")


class Client(BusinessModel):
    """ENT-Client — master data; `normalized_name` has a GIN trigram index (needs `pg_trgm`)."""

    __tablename__ = "clients"
    __table_args__ = (
        Index(
            "uq_clients_tax_code",
            "tax_code",
            unique=True,
            postgresql_where=text("tax_code IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index(
            "ix_clients_normalized_name_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
        {"schema": S},
    )

    name: Mapped[str] = txt()
    normalized_name: Mapped[str] = txt()
    tax_code: Mapped[str | None] = txt(nullable=True)
    industry: Mapped[str | None] = txt(nullable=True)
    company_size: Mapped[str | None] = mapped_column(COMPANY_SIZE, nullable=True)
    contact_person: Mapped[str | None] = txt(nullable=True)  # level 3
    contact_email: Mapped[str | None] = txt(nullable=True)  # level 3
    contact_phone: Mapped[str | None] = txt(nullable=True)  # level 3
    address: Mapped[str | None] = txt(nullable=True)
    website: Mapped[str | None] = txt(nullable=True)
    account_owner_id: Mapped[uuid.UUID | None] = sr()
    status: Mapped[str] = mapped_column(CLIENT_STATUS, nullable=False)
    merged_into_id: Mapped[uuid.UUID | None] = fk(f"{S}.clients.id", nullable=True)
    notes: Mapped[str | None] = txt(nullable=True)


class Deal(BusinessModel):
    """ENT-Deal — `weighted_value` is a STORED generated column."""

    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("deal_value >= 0", name="deal_value_non_negative"),
        CheckConstraint(
            "probability_pct >= 0 AND probability_pct <= 100", name="probability_pct_range"
        ),
        Index("ix_deals_stage_expected_close_date", "stage", "expected_close_date"),
        {"schema": S},
    )

    name: Mapped[str] = txt()
    client_id: Mapped[uuid.UUID] = fk(f"{S}.clients.id")
    deal_value: Mapped[int] = money()
    currency: Mapped[str] = currency()
    stage: Mapped[str] = mapped_column(DEAL_STAGE, nullable=False)
    probability_pct: Mapped[Any] = pct(nullable=False)
    weighted_value: Mapped[int] = mapped_column(
        BigInteger,
        Computed("(deal_value * probability_pct / 100)::bigint", persisted=True),
        nullable=False,
    )
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    lost_reason: Mapped[str | None] = txt(nullable=True)
    assigned_to: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    product_id: Mapped[uuid.UUID | None] = sr()
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    description: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class DealStageHistory(LogModel):
    """ENT-DealStageHistory — append-only (no C19, no `deleted_at`); source of METRIC-CUS-06."""

    __tablename__ = "deal_stage_history"
    __table_args__ = schema_args(S)

    deal_id: Mapped[uuid.UUID] = fk(f"{S}.deals.id")
    stage: Mapped[str] = mapped_column(DEAL_STAGE, nullable=False)
    entered_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class SalesTarget(BusinessModel):
    """ENT-SalesTarget — team targets have `owner_id` NULL (COALESCE in partial UQ)."""

    __tablename__ = "sales_targets"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_amount_positive"),
        Index(
            "uq_sales_targets_period_scope_owner",
            "period_key",
            "scope",
            text(f"COALESCE(owner_id, {ZERO_UUID})"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    period_type: Mapped[str] = mapped_column(PERIOD_TYPE, nullable=False)
    period_key: Mapped[str] = txt()
    scope: Mapped[str] = mapped_column(TARGET_SCOPE, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = sr()
    target_amount: Mapped[int] = money()
    currency: Mapped[str] = currency()


class Contract(BusinessModel):
    """ENT-Contract — `contract_value` is a critical field (always human-reviewed via IDP)."""

    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("contract_value > 0", name="contract_value_positive"),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date >= effective_date", name="expiry_after_effective"
        ),
        Index(
            "uq_contracts_contract_number",
            "contract_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_contracts_status_expiry_date", "status", "expiry_date"),
        {"schema": S},
    )

    contract_number: Mapped[str] = txt()
    client_id: Mapped[uuid.UUID] = fk(f"{S}.clients.id")
    deal_id: Mapped[uuid.UUID | None] = fk(f"{S}.deals.id", nullable=True)
    contract_value: Mapped[int] = money()
    currency: Mapped[str] = currency()
    signed_at: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_notice_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    payment_terms: Mapped[Any] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(CONTRACT_STATUS, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = sr()


# ---------- R-DEC-176 CRM entities (D-08 defaults, migration 0028) ----------
class Lead(BusinessModel):
    """ENT-Lead — a prospect before it becomes Client + Contact (+ Deal) via convert.

    `email` / `phone` are PII level 3 (`core.field_policy`) — masked in audit, never in events.
    `department_id` is pinned to a MANAGER's department like deals (02 §6.2 `◑d`).
    """

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="contact_channel_required"),
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        CheckConstraint("budget IS NULL OR budget >= 0", name="budget_non_negative"),
        Index("ix_leads_status_next_action_date", "status", "next_action_date"),
        {"schema": S},
    )

    code: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, server_default=code_default("LD", "lead_code_seq")
    )
    company_name: Mapped[str | None] = txt(nullable=True)
    full_name: Mapped[str] = txt()
    job_title: Mapped[str | None] = txt(nullable=True)
    email: Mapped[str | None] = txt(nullable=True)  # level 3
    phone: Mapped[str | None] = txt(nullable=True)  # level 3
    industry: Mapped[str | None] = txt(nullable=True)
    lead_source: Mapped[str | None] = txt(nullable=True)
    need: Mapped[str | None] = txt(nullable=True)
    budget: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(LEAD_STATUS, nullable=False, server_default=text("'new'"))
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    next_action: Mapped[str | None] = txt(nullable=True)
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    converted_client_id: Mapped[uuid.UUID | None] = fk(f"{S}.clients.id", nullable=True)
    converted_contact_id: Mapped[uuid.UUID | None] = fk(f"{S}.contacts.id", nullable=True)
    converted_deal_id: Mapped[uuid.UUID | None] = fk(f"{S}.deals.id", nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class SalesContact(BusinessModel):
    """ENT-Contact — a person at a client (buying committee); replaces the flat client contact
    columns going forward (those stay, R-DEC-176 g). No `department_id`: follows the client."""

    __tablename__ = "contacts"
    __table_args__ = schema_args(S)

    code: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, server_default=code_default("CT", "contact_code_seq")
    )
    client_id: Mapped[uuid.UUID] = fk(f"{S}.clients.id")
    first_name: Mapped[str] = txt()
    last_name: Mapped[str | None] = txt(nullable=True)
    job_title: Mapped[str | None] = txt(nullable=True)
    department: Mapped[str | None] = txt(nullable=True)  # free text at the client, not hr
    email: Mapped[str | None] = txt(nullable=True)  # level 3
    phone: Mapped[str | None] = txt(nullable=True)  # level 3
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    decision_authority: Mapped[str | None] = txt(nullable=True)
    influence_level: Mapped[str | None] = mapped_column(INFLUENCE_LEVEL, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = sr()
    notes: Mapped[str | None] = txt(nullable=True)


class SalesActivity(BusinessModel):
    """ENT-SalesActivity — call / meeting / demo … on a lead, client, contact or deal.

    Code prefix `SA-` (not `ACT-`: that is the Action Registry, R-DEC-176 e).
    """

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "lead_id IS NOT NULL OR client_id IS NOT NULL OR contact_id IS NOT NULL "
            "OR deal_id IS NOT NULL",
            name="link_required",
        ),
        CheckConstraint("end_at IS NULL OR end_at >= start_at", name="end_after_start"),
        Index("ix_activities_status_start_at", "status", "start_at"),
        {"schema": S},
    )

    code: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, server_default=code_default("SA", "activity_code_seq")
    )
    type: Mapped[str] = mapped_column(ACTIVITY_TYPE, nullable=False)
    subject: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    lead_id: Mapped[uuid.UUID | None] = fk(f"{S}.leads.id", nullable=True)
    client_id: Mapped[uuid.UUID | None] = fk(f"{S}.clients.id", nullable=True)
    contact_id: Mapped[uuid.UUID | None] = fk(f"{S}.contacts.id", nullable=True)
    deal_id: Mapped[uuid.UUID | None] = fk(f"{S}.deals.id", nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    start_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    status: Mapped[str] = mapped_column(
        ACTIVITY_STATUS, nullable=False, server_default=text("'planned'")
    )
    outcome: Mapped[str | None] = txt(nullable=True)
    next_action: Mapped[str | None] = txt(nullable=True)
