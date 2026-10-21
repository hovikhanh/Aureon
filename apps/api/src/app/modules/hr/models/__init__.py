"""Schema `hr` — 8 tables (05 §4.4). Column groups follow 05 §2.1.

FK cycles (departments.head_employee_id ↔ employees.department_id, teams.lead_employee_id ↔
employees.team_id) are broken with `use_alter=True` so create/drop order is deterministic.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel, LogModel
from app.core.columns import currency, fk, money, schema_args, sr, ts, txt
from app.core.crypto_columns import EncryptedBigInt, EncryptedText
from app.core.enums import pg_enum

S = "hr"

# ---------- module-owned enums (05 §6) ----------
EMPLOYEE_STATUS = pg_enum(S, "employee_status", "probation", "active", "on_leave", "terminated")
CONTRACT_TYPE = pg_enum(
    S, "contract_type", "permanent", "fixed_term", "probation", "intern", "contractor"
)
LEAVE_TYPE = pg_enum(S, "leave_type", "annual", "sick", "unpaid", "public_holiday", "other")
LEAVE_STATUS = pg_enum(S, "leave_status", "requested", "approved", "rejected", "cancelled")
HIRING_PRIORITY = pg_enum(S, "hiring_priority", "low", "medium", "high", "critical")
HIRING_STATUS = pg_enum(
    S,
    "hiring_status",
    "draft",
    "submitted",
    "approved",
    "rejected",
    "in_progress",
    "completed",
    "cancelled",
)

MODULE_ENUMS: tuple[ENUM, ...] = (
    EMPLOYEE_STATUS,
    CONTRACT_TYPE,
    LEAVE_TYPE,
    LEAVE_STATUS,
    HIRING_PRIORITY,
    HIRING_STATUS,
)


def _cyclic_fk(target: str) -> Any:
    """Nullable same-schema FK (RESTRICT, indexed) emitted via ALTER to break an FK cycle."""
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey(target, ondelete="RESTRICT", use_alter=True),
        nullable=True,
        index=True,
    )


class Department(BusinessModel):
    """ENT-Department — soft-ref target for `department_id` across all schemas (05 C7)."""

    __tablename__ = "departments"
    __table_args__ = schema_args(S)

    code: Mapped[str] = txt(unique=True)
    name: Mapped[str] = txt()
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = fk(f"{S}.departments.id", nullable=True)
    head_employee_id: Mapped[uuid.UUID | None] = _cyclic_fk(f"{S}.employees.id")
    cost_center: Mapped[str | None] = txt(nullable=True)


class Employee(BusinessModel):
    """ENT-Employee — no salary column (salary lives in `salary_history`, level 4)."""

    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name="termination_after_hire",
        ),
        Index(
            "uq_employees_employee_code_live",
            "employee_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_employees_normalized_name_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
        Index("ix_employees_department_id_status", "department_id", "status"),
        {"schema": S},
    )

    employee_code: Mapped[str] = txt()
    full_name: Mapped[str] = txt()
    normalized_name: Mapped[str] = txt()
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True, unique=True)
    phone: Mapped[str | None] = txt(nullable=True)
    department_id: Mapped[uuid.UUID] = fk(f"{S}.departments.id")
    position_id: Mapped[uuid.UUID | None] = fk(f"{S}.positions.id", nullable=True)
    team_id: Mapped[uuid.UUID | None] = fk(f"{S}.teams.id", nullable=True)
    status: Mapped[str] = mapped_column(EMPLOYEE_STATUS, nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(CONTRACT_TYPE, nullable=True)
    manager_id: Mapped[uuid.UUID | None] = fk(f"{S}.employees.id", nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = txt(nullable=True)
    # level 4 — pgcrypto `bytea` (migration 0008, T-234, DEC-207); plaintext in Python
    national_id: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    bank_account: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    emergency_contact: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class Team(BusinessModel):
    """ENT-Team (v2.1, DEC-147) — one team belongs to one department."""

    __tablename__ = "teams"
    __table_args__ = schema_args(S)

    department_id: Mapped[uuid.UUID] = fk(f"{S}.departments.id")
    code: Mapped[str] = txt(unique=True)
    name: Mapped[str] = txt()
    lead_employee_id: Mapped[uuid.UUID | None] = _cyclic_fk(f"{S}.employees.id")


class Position(BusinessModel):
    """ENT-Position (v2.1, DEC-147) — not effective-dated; one employee one position."""

    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint("headcount_budget >= 0", name="headcount_budget_non_negative"),
        {"schema": S},
    )

    department_id: Mapped[uuid.UUID] = fk(f"{S}.departments.id")
    code: Mapped[str] = txt(unique=True)
    title: Mapped[str] = txt()
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    headcount_budget: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reports_to_position_id: Mapped[uuid.UUID | None] = fk(f"{S}.positions.id", nullable=True)


class EmployeeSkill(BusinessModel):
    """ENT-EmployeeSkill (v2.1, DEC-147) — `skill` normalised lowercase in the service."""

    __tablename__ = "employee_skills"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 5", name="level_1_5"),
        Index(
            "uq_employee_skills_employee_id_skill_live",
            "employee_id",
            "skill",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    employee_id: Mapped[uuid.UUID] = fk(f"{S}.employees.id")
    skill: Mapped[str] = txt()
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    verified_by: Mapped[uuid.UUID | None] = sr()


class Leave(BusinessModel):
    """ENT-Leave (v2.1, DEC-147) — only `approved` rows reduce capacity (METRIC-HR-03)."""

    __tablename__ = "leaves"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="end_after_start"),
        Index("ix_leaves_employee_id_start_date", "employee_id", "start_date"),
        {"schema": S},
    )

    employee_id: Mapped[uuid.UUID] = fk(f"{S}.employees.id")
    leave_type: Mapped[str] = mapped_column(LEAVE_TYPE, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(LEAVE_STATUS, nullable=False)
    reason: Mapped[str | None] = txt(nullable=True)


class SalaryHistory(LogModel):
    """ENT-SalaryHistory — append-only, level 4; no C19, no `deleted_at` (05 C5, §2.1)."""

    __tablename__ = "salary_history"
    __table_args__ = (
        # `base_salary > 0` is enforced in the service: the column is ciphertext (DEC-207)
        UniqueConstraint("employee_id", "effective_date"),
        {"schema": S},
    )

    employee_id: Mapped[uuid.UUID] = fk(f"{S}.employees.id")
    base_salary: Mapped[int] = mapped_column(EncryptedBigInt, nullable=False)  # level 4, pgcrypto
    currency: Mapped[str] = currency()
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class HiringPlan(BusinessModel):
    """ENT-HiringPlan — source of METRIC-HR-04.

    `approved_by ≠ created_by` and "reject_reason required when rejected" are business rules
    enforced in the service (05 lists them as descriptions, not DB constraints).
    """

    __tablename__ = "hiring_plans"
    __table_args__ = (
        CheckConstraint("filled >= 0 AND filled <= headcount", name="filled_within_headcount"),
        Index("ix_hiring_plans_status_target_fill_date", "status", "target_fill_date"),
        {"schema": S},
    )

    title: Mapped[str] = txt()
    department_id: Mapped[uuid.UUID] = fk(f"{S}.departments.id")
    position: Mapped[str] = txt()
    headcount: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    filled: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    priority: Mapped[str] = mapped_column(HIRING_PRIORITY, nullable=False)
    status: Mapped[str] = mapped_column(HIRING_STATUS, nullable=False)
    salary_range_min: Mapped[int | None] = money(nullable=True)
    salary_range_max: Mapped[int | None] = money(nullable=True)
    currency: Mapped[str] = currency()
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_fill_date: Mapped[date] = mapped_column(Date, nullable=False)
    hiring_manager_id: Mapped[uuid.UUID] = sr(nullable=False)
    approved_by: Mapped[uuid.UUID | None] = sr()
    approved_at: Mapped[datetime | None] = ts()
    reject_reason: Mapped[str | None] = txt(nullable=True)
    requirements: Mapped[str | None] = txt(nullable=True)
    budget_allocated: Mapped[int] = money()
    budget_spent: Mapped[int] = money()
    delayed_notified_at: Mapped[datetime | None] = ts()
