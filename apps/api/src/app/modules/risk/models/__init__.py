"""Schema `risk` — 4 tables (05 §4.6). Column groups follow 05 §2.1."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Index,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, LogModel
from app.core.columns import fk, pct, schema_args, sr, txt
from app.core.enums import pg_enum

S = "risk"
TS = DateTime(timezone=True)

# ---------- module-owned enums (05 §6) ----------
RISK_CATEGORY = pg_enum(
    S, "risk_category",
    "financial", "operational", "strategic", "people", "business", "customer", "product",
    "technology", "security", "compliance", "legal", "partner_supplier", "ai",
)  # fmt: skip
RISK_SEVERITY = pg_enum(S, "risk_severity", "low", "medium", "high", "critical")
RISK_STATUS = pg_enum(
    S, "risk_status",
    "proposed", "identified", "assessed", "mitigating", "monitoring", "accepted", "closed",
    "rejected",
)  # fmt: skip
RISK_SOURCE = pg_enum(S, "risk_source", "manual", "event", "ai", "document")
MITIGATION_STATUS = pg_enum(S, "mitigation_status", "planned", "in_progress", "done", "cancelled")

MODULE_ENUMS: tuple[ENUM, ...] = (
    RISK_CATEGORY,
    RISK_SEVERITY,
    RISK_STATUS,
    RISK_SOURCE,
    MITIGATION_STATUS,
)


# ---------- business ----------
class Risk(BusinessModel):
    """ENT-Risk — `risk_source` is the domain detail column (DEC-154); `source` is C19."""

    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint("likelihood BETWEEN 1 AND 5", name="likelihood_1_5"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="impact_1_5"),
        Index("ix_risks_status_severity", "status", "severity"),
        Index(
            "uq_risks_source_event_id",
            "source_event_id",
            unique=True,
            postgresql_where=text("source_event_id IS NOT NULL"),
        ),
        Index("ix_risks_linked_entities", "linked_entities", postgresql_using="gin"),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    title: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    category: Mapped[str] = mapped_column(RISK_CATEGORY, nullable=False)
    likelihood: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    impact: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    risk_score: Mapped[int] = mapped_column(
        SmallInteger, Computed("likelihood * impact", persisted=True), nullable=False
    )
    severity: Mapped[str] = mapped_column(RISK_SEVERITY, nullable=False)
    status: Mapped[str] = mapped_column(RISK_STATUS, nullable=False)
    proposed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = sr()
    confirmed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    risk_source: Mapped[str] = mapped_column(RISK_SOURCE, nullable=False)
    # Covered by the partial unique index above (no separate plain index).
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = sr()
    department_id: Mapped[uuid.UUID | None] = sr()
    linked_entities: Mapped[Any] = mapped_column(JSONB, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    accepted_by: Mapped[uuid.UUID | None] = sr()
    accepted_reason: Mapped[str | None] = txt(nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    identified_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class Mitigation(BusinessModel):
    __tablename__ = "mitigations"
    __table_args__ = (
        CheckConstraint("progress_pct BETWEEN 0 AND 100", name="progress_pct_0_100"),
        {"schema": S},
    )

    risk_id: Mapped[uuid.UUID] = fk(f"{S}.risks.id")
    title: Mapped[str] = txt()
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    status: Mapped[str] = mapped_column(MITIGATION_STATUS, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    progress_pct: Mapped[Any] = pct(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    task_id: Mapped[uuid.UUID | None] = sr()


class Scenario(BusinessModel):
    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_risk_ids", "risk_ids", postgresql_using="gin"),
        {"schema": S},
    )

    name: Mapped[str] = txt()
    risk_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    horizon_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    assumptions: Mapped[Any] = mapped_column(JSONB, nullable=False)
    impact_domains: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    results: Mapped[Any] = mapped_column(JSONB, nullable=True)
    run_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# ---------- append-only ----------
class RiskAssessment(LogModel):
    """ENT-RiskAssessment — append-only (05 C5, §2.1): no C19, no `deleted_at`."""

    __tablename__ = "risk_assessments"
    __table_args__ = schema_args(S)

    risk_id: Mapped[uuid.UUID] = fk(f"{S}.risks.id")
    likelihood: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    impact: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    severity: Mapped[str] = mapped_column(RISK_SEVERITY, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    assessed_by: Mapped[uuid.UUID | None] = sr()
    rationale: Mapped[str | None] = txt(nullable=True)
