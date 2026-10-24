"""Schema `execution` (05 §4.7 + M1.3 §2.5 + M1.4 §2.6). Column groups follow 05 §2.1."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, LogModel
from app.core.columns import currency, fk, measure, money, pct, schema_args, sr, txt
from app.core.enums import CONFIDENCE_BAND, DATA_CLASSIFICATION, PERIOD_TYPE, PILLAR, pg_enum

S = "execution"
TS = DateTime(timezone=True)

# ---------- module-owned enums (05 §6) ----------
DECISION_STATUS = pg_enum(S, "decision_status", "open", "in_progress", "done", "cancelled")
TASK_STATUS = pg_enum(
    S, "task_status",
    "backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled",
)  # fmt: skip
TASK_PRIORITY = pg_enum(S, "task_priority", "low", "medium", "high", "urgent")
TASK_SOURCE = pg_enum(S, "task_source", "manual", "meeting", "ai", "document", "mitigation")
PROJECT_STATUS = pg_enum(S, "project_status", "planned", "active", "on_hold", "done", "cancelled")
OBJECTIVE_LEVEL = pg_enum(S, "objective_level", "company", "department", "team", "individual")
OKR_STATUS = pg_enum(S, "okr_status", "draft", "active", "closed")
OKR_TYPE = pg_enum(S, "okr_type", "committed", "aspirational")
KPI_DIRECTION = pg_enum(
    S, "kpi_direction", "HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE", "BINARY"
)
KPI_VALUE_TYPE = pg_enum(
    S, "kpi_value_type", "ratio", "percentage", "numeric", "currency", "duration", "count"
)
KPI_DATA_SOURCE = pg_enum(S, "kpi_data_source", "manual", "document", "automated", "ai_assisted")
KPI_BAND = pg_enum(S, "kpi_band", "CRITICAL", "BELOW", "NEAR", "MEETS", "EXCEEDS")
INITIATIVE_STATUS = pg_enum(
    S, "initiative_status", "planned", "active", "at_risk", "done", "cancelled"
)
MILESTONE_STATUS = pg_enum(S, "milestone_status", "planned", "done", "missed")
TRANSCRIPT_STATUS = pg_enum(S, "transcript_status", "UPLOADED", "PROCESSED", "FAILED")
TASK_DEPENDENCY_TYPE = pg_enum(S, "task_dependency_type", "finish_to_start")  # 05 §2.5
STRATEGY_STATUS = pg_enum(S, "strategy_status", "draft", "active", "closed")  # 05 §2.6

MODULE_ENUMS: tuple[ENUM, ...] = (
    DECISION_STATUS,
    TASK_STATUS,
    TASK_PRIORITY,
    TASK_SOURCE,
    PROJECT_STATUS,
    OBJECTIVE_LEVEL,
    OKR_STATUS,
    OKR_TYPE,
    KPI_DIRECTION,
    KPI_VALUE_TYPE,
    KPI_DATA_SOURCE,
    KPI_BAND,
    INITIATIVE_STATUS,
    MILESTONE_STATUS,
    TRANSCRIPT_STATUS,
    TASK_DEPENDENCY_TYPE,
    STRATEGY_STATUS,
)


def _hours() -> Any:
    """numeric(6,2) hours (05 §4.7 tasks)."""
    return mapped_column(Numeric(6, 2), nullable=True)


# ---------- meetings ----------
class Meeting(BusinessModel):
    __tablename__ = "meetings"
    __table_args__ = (
        Index("ix_meetings_attendee_ids", "attendee_ids", postgresql_using="gin"),
        {"schema": S},
    )

    title: Mapped[str] = txt()
    held_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    chair_id: Mapped[uuid.UUID | None] = sr()
    attendee_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    summary: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    # Cycle meetings ↔ meeting_transcripts → this side is added via ALTER (use_alter).
    transcript_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{S}.meeting_transcripts.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )


class MeetingTranscript(BusinessModel):
    """ENT-MeetingTranscript — manual upload (DEC-153); row level defaults to CONFIDENTIAL."""

    __tablename__ = "meeting_transcripts"
    __table_args__ = (
        CheckConstraint("language IN ('vi', 'en')", name="language_vi_en"),
        {"schema": S},
    )

    meeting_id: Mapped[uuid.UUID | None] = fk(f"{S}.meetings.id", nullable=True)
    source_document_id: Mapped[uuid.UUID] = sr(nullable=False)
    language: Mapped[str] = txt()
    speaker_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    text_content: Mapped[str] = txt()
    status: Mapped[str] = mapped_column(TRANSCRIPT_STATUS, nullable=False)
    consent_confirmed_by: Mapped[uuid.UUID] = sr(nullable=False)

    data_classification: Mapped[str] = mapped_column(
        DATA_CLASSIFICATION, nullable=False, server_default="CONFIDENTIAL"
    )


class Decision(BusinessModel):
    """ENT-Decision — Decision Log."""

    __tablename__ = "decisions"
    __table_args__ = schema_args(S)

    meeting_id: Mapped[uuid.UUID | None] = fk(f"{S}.meetings.id", nullable=True)
    content: Mapped[str] = txt()
    rationale: Mapped[str | None] = txt(nullable=True)
    alternatives_rejected: Mapped[str | None] = txt(nullable=True)
    expected_outcome: Mapped[str | None] = txt(nullable=True)
    owner_id: Mapped[uuid.UUID | None] = sr()
    decided_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_at: Mapped[list[date]] = mapped_column(ARRAY(Date), nullable=False)
    actual_outcome: Mapped[str | None] = txt(nullable=True)
    outcome_verified_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    initiative_id: Mapped[uuid.UUID | None] = fk(f"{S}.initiatives.id", nullable=True)
    source_insight_id: Mapped[uuid.UUID | None] = sr()
    status: Mapped[str] = mapped_column(DECISION_STATUS, nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


# ---------- projects / tasks ----------
class Project(BusinessModel):
    """ENT-Project — `currency` follows C8 (NOT NULL DEFAULT 'VND') although 05 marks Y."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_tenant_id_initiative_id", "tenant_id", "initiative_id"),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    name: Mapped[str] = txt()
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(PROJECT_STATUS, nullable=False)
    budget_amount: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()
    # Initiative → Project (05 §2.5, 0014); SET NULL when the initiative goes away.
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{S}.initiatives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class Task(BusinessModel):
    """ENT-Task — `task_source` is the domain detail column (DEC-154); `source` is C19."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_assignee_id_status_due_date", "assignee_id", "status", "due_date"),
        Index(
            "ix_tasks_tenant_id_assignee_id_due_date",
            "tenant_id",
            "assignee_id",
            "due_date",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "source_ref IS NULL OR (source_ref ? 'kind' AND source_ref ? 'id')",
            name="source_ref_kind_id",
        ),
        {"schema": S},
    )

    title: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    owner_id: Mapped[uuid.UUID | None] = sr()
    assignee_id: Mapped[uuid.UUID | None] = sr()
    department_id: Mapped[uuid.UUID | None] = sr()
    project_id: Mapped[uuid.UUID | None] = fk(f"{S}.projects.id", nullable=True)
    meeting_id: Mapped[uuid.UUID | None] = fk(f"{S}.meetings.id", nullable=True)
    decision_id: Mapped[uuid.UUID | None] = fk(f"{S}.decisions.id", nullable=True)
    key_result_id: Mapped[uuid.UUID | None] = fk(f"{S}.key_results.id", nullable=True)
    initiative_id: Mapped[uuid.UUID | None] = fk(f"{S}.initiatives.id", nullable=True)
    milestone_id: Mapped[uuid.UUID | None] = fk(f"{S}.milestones.id", nullable=True)
    kpi_id: Mapped[uuid.UUID | None] = fk(f"{S}.kpis.id", nullable=True)
    parent_task_id: Mapped[uuid.UUID | None] = fk(f"{S}.tasks.id", nullable=True)  # R-DEC-42
    priority: Mapped[str] = mapped_column(TASK_PRIORITY, nullable=False)
    status: Mapped[str] = mapped_column(TASK_STATUS, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    blocked_reason: Mapped[str | None] = txt(nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    estimate_hours: Mapped[Any] = _hours()
    actual_hours: Mapped[Any] = _hours()
    evidence: Mapped[Any] = mapped_column(JSONB, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    task_source: Mapped[str] = mapped_column(TASK_SOURCE, nullable=False)
    overdue_notified_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    # `{kind, id, page?}` pointer to the origin record (05 §2.5, P06 lineage).
    source_ref: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)


class TaskDependency(BusinessModel):
    """ENT-TaskDependency (FR-TASK-02, R-DEC-43): `task_id` is blocked by `depends_on_task_id`."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint("task_id <> depends_on_task_id", name="not_self"),
        Index(
            "uq_task_dependencies_tenant_id_task_id_depends_on_task_id_live",
            "tenant_id", "task_id", "depends_on_task_id", unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )  # fmt: skip

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{S}.tasks.id", ondelete="CASCADE"), index=True
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{S}.tasks.id", ondelete="CASCADE"), index=True
    )
    dependency_type: Mapped[str] = mapped_column(
        TASK_DEPENDENCY_TYPE, nullable=False, server_default="finish_to_start"
    )


# ---------- Strategy (05 §2.6, R-DEC-50) ----------
class Strategy(BusinessModel):
    """ENT-Strategy — "≤ 1 `active` overlapping per tenant" is checked in the service."""

    __tablename__ = "strategies"
    __table_args__ = (
        CheckConstraint("period_end > period_start", name="period_end_after_start"),
        Index("uq_strategies_code_live", "code", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        {"schema": S},
    )  # fmt: skip

    code: Mapped[str] = txt()
    name: Mapped[str] = txt()
    vision: Mapped[str | None] = txt(nullable=True)
    mission: Mapped[str | None] = txt(nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    status: Mapped[str] = mapped_column(STRATEGY_STATUS, nullable=False)


class StrategicObjective(BusinessModel):
    """ENT-StrategicObjective — parent of root KPI / root Objective / Initiative (R-DEC-50).

    `progress_pct` is system-computed (05 §2.6): weighted mean of live initiatives' progress
    (weights `weight_pct`, all 0 → plain mean); no initiative → mean of directly linked
    objectives; none → 0.
    """

    __tablename__ = "strategic_objectives"
    __table_args__ = (
        CheckConstraint("weight_pct BETWEEN 0 AND 100", name="weight_pct_0_100"),
        Index("uq_strategic_objectives_code_live", "code", unique=True,
              postgresql_where=text("deleted_at IS NULL")),
        Index("ix_strategic_objectives_strategy_id_sort_order", "strategy_id", "sort_order"),
        {"schema": S},
    )  # fmt: skip

    strategy_id: Mapped[uuid.UUID] = fk(f"{S}.strategies.id")
    code: Mapped[str] = txt()
    title: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    weight_pct: Mapped[Any] = pct(nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(OKR_STATUS, nullable=False)
    progress_pct: Mapped[Any] = pct(nullable=False)


# ---------- OKR ----------
class Objective(BusinessModel):
    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint("weight_pct BETWEEN 0 AND 100", name="weight_pct_0_100"),
        CheckConstraint("score BETWEEN 0 AND 1", name="score_0_1"),
        CheckConstraint("parent_id IS NULL OR strategic_objective_id IS NULL", name="so_root_only"),
        {"schema": S},
    )

    title: Mapped[str] = txt()
    period_key: Mapped[str] = txt()
    level: Mapped[str] = mapped_column(OBJECTIVE_LEVEL, nullable=False)
    okr_type: Mapped[str] = mapped_column(OKR_TYPE, nullable=False)
    weight_pct: Mapped[Any] = pct(nullable=False)
    team_id: Mapped[uuid.UUID | None] = sr()
    parent_id: Mapped[uuid.UUID | None] = fk(f"{S}.objectives.id", nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)
    status: Mapped[str] = mapped_column(OKR_STATUS, nullable=False)
    progress_pct: Mapped[Any] = pct(nullable=False)
    score: Mapped[Any] = mapped_column(Numeric(3, 2), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()
    strategic_objective_id: Mapped[uuid.UUID | None] = fk(
        f"{S}.strategic_objectives.id", nullable=True
    )


class KeyResult(BusinessModel):
    __tablename__ = "key_results"
    __table_args__ = (
        CheckConstraint("weight_pct BETWEEN 0 AND 100", name="weight_pct_0_100"),
        {"schema": S},
    )

    objective_id: Mapped[uuid.UUID] = fk(f"{S}.objectives.id")
    title: Mapped[str] = txt()
    metric_code: Mapped[str | None] = txt(nullable=True)
    unit: Mapped[str] = txt()
    baseline: Mapped[Any] = measure(nullable=False)
    target: Mapped[Any] = measure(nullable=False)
    current_value: Mapped[Any] = measure()
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    status: Mapped[str] = mapped_column(OKR_STATUS, nullable=False)
    confidence: Mapped[str | None] = mapped_column(CONFIDENCE_BAND, nullable=True)
    weight_pct: Mapped[Any] = pct(nullable=False)


class Initiative(BusinessModel):
    """ENT-Initiative — `currency` follows C8 (NOT NULL DEFAULT 'VND') although 05 marks Y."""

    __tablename__ = "initiatives"
    __table_args__ = (
        CheckConstraint("weight_pct BETWEEN 0 AND 100", name="weight_pct_0_100"),
        Index("ix_initiatives_status_planned_end_date", "status", "planned_end_date"),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    title: Mapped[str] = txt()
    description: Mapped[str | None] = txt(nullable=True)
    objective_id: Mapped[uuid.UUID | None] = fk(f"{S}.objectives.id", nullable=True)
    strategic_objective_id: Mapped[uuid.UUID | None] = fk(
        f"{S}.strategic_objectives.id", nullable=True
    )
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(INITIATIVE_STATUS, nullable=False)
    progress_pct: Mapped[Any] = pct(nullable=False)
    weight_pct: Mapped[Any] = pct(nullable=False)
    budget_amount: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()


class Milestone(BusinessModel):
    __tablename__ = "milestones"
    __table_args__ = (
        CheckConstraint("num_nonnulls(initiative_id, project_id) = 1", name="one_parent"),
        {"schema": S},
    )

    initiative_id: Mapped[uuid.UUID | None] = fk(f"{S}.initiatives.id", nullable=True)
    project_id: Mapped[uuid.UUID | None] = fk(f"{S}.projects.id", nullable=True)
    title: Mapped[str] = txt()
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(MILESTONE_STATUS, nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# ---------- KPI ----------
class Kpi(BusinessModel):
    __tablename__ = "kpis"
    __table_args__ = (
        CheckConstraint("weight_pct BETWEEN 0 AND 100", name="weight_pct_0_100"),
        CheckConstraint(
            "parent_kpi_id IS NULL OR strategic_objective_id IS NULL", name="so_root_only"
        ),
        {"schema": S},
    )

    code: Mapped[str] = txt(unique=True)
    name: Mapped[str] = txt()
    metric_code: Mapped[str | None] = txt(nullable=True)
    key_result_id: Mapped[uuid.UUID | None] = fk(f"{S}.key_results.id", nullable=True)
    unit: Mapped[str] = txt()
    period_type: Mapped[str] = mapped_column(PERIOD_TYPE, nullable=False)
    target_value: Mapped[Any] = measure(nullable=False)
    direction: Mapped[str] = mapped_column(KPI_DIRECTION, nullable=False)
    value_type: Mapped[str] = mapped_column(KPI_VALUE_TYPE, nullable=False)
    data_source_kind: Mapped[str] = mapped_column(KPI_DATA_SOURCE, nullable=False)
    parent_kpi_id: Mapped[uuid.UUID | None] = fk(f"{S}.kpis.id", nullable=True)
    weight_pct: Mapped[Any] = pct(nullable=False)
    initiative_id: Mapped[uuid.UUID | None] = fk(f"{S}.initiatives.id", nullable=True)
    owner_id: Mapped[uuid.UUID] = sr(nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    status: Mapped[str] = mapped_column(OKR_STATUS, nullable=False)
    strategic_objective_id: Mapped[uuid.UUID | None] = fk(
        f"{S}.strategic_objectives.id", nullable=True
    )
    pillar: Mapped[str | None] = mapped_column(PILLAR, nullable=True)  # DIR khối scope (R-DEC-57)


class KpiTarget(BusinessModel):
    """ENT-KPITarget — per-period target + evaluation bands (DEC-147)."""

    __tablename__ = "kpi_targets"
    __table_args__ = (
        Index(
            "uq_kpi_targets_kpi_id_period_key",
            "kpi_id",
            "period_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    kpi_id: Mapped[uuid.UUID] = fk(f"{S}.kpis.id")
    period_key: Mapped[str] = txt()
    baseline: Mapped[Any] = measure()
    minimum: Mapped[Any] = measure()
    target: Mapped[Any] = measure(nullable=False)
    stretch: Mapped[Any] = measure()
    band_thresholds: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default='{"CRITICAL":0,"BELOW":70,"NEAR":90,"MEETS":100,"EXCEEDS":110}',
    )
    score_cap_pct: Mapped[Any] = mapped_column(
        Numeric(7, 4), nullable=False, server_default=text("150")
    )
    locked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# ---------- append-only ----------
class CheckIn(LogModel):
    """ENT-CheckIn — append-only (05 §2.1): no C19, no `deleted_at`."""

    __tablename__ = "check_ins"
    __table_args__ = (
        CheckConstraint("num_nonnulls(key_result_id, kpi_id) = 1", name="one_target"),
        {"schema": S},
    )

    key_result_id: Mapped[uuid.UUID | None] = fk(f"{S}.key_results.id", nullable=True)
    kpi_id: Mapped[uuid.UUID | None] = fk(f"{S}.kpis.id", nullable=True)
    value: Mapped[Any] = measure(nullable=False)
    note: Mapped[str | None] = txt(nullable=True)
    blocker: Mapped[str | None] = txt(nullable=True)
    support_needed: Mapped[str | None] = txt(nullable=True)
    next_action: Mapped[str | None] = txt(nullable=True)
    confidence: Mapped[str] = mapped_column(CONFIDENCE_BAND, nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    user_id: Mapped[uuid.UUID] = sr(nullable=False)


class KpiMeasurement(LogModel):
    """ENT-KPIMeasurement — append-only (05 §2.1): no C19, no `deleted_at`.

    05 states UQ `(kpi_id, period_key) WHERE deleted_at IS NULL`, but the group has no
    `deleted_at` → implemented as a plain (non-partial) unique constraint.
    """

    __tablename__ = "kpi_measurements"
    __table_args__ = (
        UniqueConstraint("kpi_id", "period_key", name="uq_kpi_measurements_kpi_id_period_key"),
        {"schema": S},
    )

    kpi_id: Mapped[uuid.UUID] = fk(f"{S}.kpis.id")
    period_key: Mapped[str] = txt()
    actual_value: Mapped[Any] = measure(nullable=False)
    achievement_pct: Mapped[Any] = pct(nullable=False)
    evaluation_band: Mapped[str] = mapped_column(KPI_BAND, nullable=False)
    kpi_target_id: Mapped[uuid.UUID] = fk(f"{S}.kpi_targets.id")
    locked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = sr()
