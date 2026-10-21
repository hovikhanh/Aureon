"""Schema `sales` — 5 tables (05 §4.3). Column groups follow 05 §2.1.

Business entities → `BusinessModel`: clients, deals, sales_targets, contracts.
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

MODULE_ENUMS = (COMPANY_SIZE, CLIENT_STATUS, DEAL_STAGE, TARGET_SCOPE, CONTRACT_STATUS)


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
