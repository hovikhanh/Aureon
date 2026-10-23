"""HR API DTOs (10 §4.8). API field names follow 10; columns follow 05 (DEC-195).

10 ↔ 05 renames are handled in the service, never in the DB:
- EP-81 `manager_id` ↔ `departments.head_employee_id`.
- EP-82 `title` ↔ `employees.position_id` (→ `positions.title`); `contract_type` API enum
  (`full_time, part_time, contract, intern`) ↔ DB enum (`permanent, fixed_term, contractor,
  intern`; a legacy DB `probation` reads as `full_time`).
- EP-84 `salary_min/max` ↔ `salary_range_min/max`, `target_date` ↔ `target_fill_date`,
  `budget_amount` ↔ `budget_allocated`.

Level-4 fields (02 §6.3) are typed `T | Masked`: only CEO / HR-DIR get the value, every
other role gets `{ "masked": true }` (10 §4.8 EP-82).
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EmployeeStatus = Literal["probation", "active", "on_leave", "terminated"]
ContractType = Literal["full_time", "part_time", "contract", "intern"]
HiringPriority = Literal["low", "medium", "high", "critical"]
HiringStatus = Literal[
    "draft", "submitted", "approved", "rejected", "in_progress", "completed", "cancelled"
]
PlanPatchStatus = Literal["draft", "in_progress", "completed", "cancelled"]
Decision = Literal["approve", "reject"]
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def currency_field() -> Any:
    return Field(default="VND", pattern=r"^[A-Z]{3}$")


class Masked(BaseModel):
    """Placeholder for a level-4 field the caller may not see (02 §6.3)."""

    masked: Literal[True] = True


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class _Patch(BaseModel):
    """PATCH bodies: only sent fields are applied (`model_dump(exclude_unset=True)`)."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None


# ---------- EP-81 departments ----------
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    parent_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None


class DepartmentUpdate(_Patch):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    parent_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None


class DepartmentOut(_Out):
    name: str
    code: str
    parent_id: uuid.UUID | None
    manager_id: uuid.UUID | None


# ---------- EP-82 employees ----------
class _EmployeeLevel4(BaseModel):
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=500)
    national_id: str | None = Field(default=None, max_length=20)
    bank_account: str | None = Field(default=None, max_length=40)
    emergency_contact: dict[str, Any] | None = None


class EmployeeCreate(_EmployeeLevel4):
    employee_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_RE)
    phone: str | None = Field(default=None, max_length=30)
    department_id: uuid.UUID
    title: str | None = Field(default=None, min_length=1, max_length=200)
    contract_type: ContractType | None = None
    status: EmployeeStatus = "probation"
    hire_date: date
    termination_date: date | None = None
    manager_id: uuid.UUID | None = None


class EmployeeUpdate(_Patch, _EmployeeLevel4):
    employee_code: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_RE)
    phone: str | None = Field(default=None, max_length=30)
    department_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    contract_type: ContractType | None = None
    status: EmployeeStatus | None = None
    hire_date: date | None = None
    termination_date: date | None = None
    manager_id: uuid.UUID | None = None


class EmployeeOut(_Out):
    employee_code: str
    full_name: str
    email: str | None
    phone: str | None
    department_id: uuid.UUID
    title: str | None
    contract_type: ContractType | None
    status: EmployeeStatus
    hire_date: date
    termination_date: date | None
    manager_id: uuid.UUID | None
    date_of_birth: date | Masked | None
    address: str | Masked | None
    national_id: str | Masked | None
    bank_account: str | Masked | None
    emergency_contact: dict[str, Any] | Masked | None


# ---------- EP-83 salary history ----------
class SalaryCreate(BaseModel):
    effective_date: date
    base_salary: int
    currency: str = currency_field()
    reason: str | None = Field(default=None, max_length=1000)


class SalaryOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    effective_date: date
    base_salary: int
    currency: str
    reason: str | None
    created_at: datetime


# ---------- EP-84 hiring plans ----------
class _PlanRanges(BaseModel):
    salary_min: int | None = Field(default=None, gt=0)
    salary_max: int | None = Field(default=None, gt=0)
    start_date: date | None = None
    target_date: date | None = None

    @model_validator(mode="after")
    def _ranges(self) -> "_PlanRanges":
        lo, hi = self.salary_min, self.salary_max
        if lo is not None and hi is not None and hi < lo:
            raise ValueError("salary_max must be >= salary_min")
        if self.start_date and self.target_date and self.target_date <= self.start_date:
            raise ValueError("target_date must be after start_date")
        return self


class HiringPlanCreate(_PlanRanges):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    department_id: uuid.UUID
    position: str = Field(min_length=1, max_length=200)
    headcount: int = Field(ge=1, le=10_000)
    filled: int = Field(default=0, ge=0)
    priority: HiringPriority = "medium"
    currency: str = currency_field()
    start_date: date
    target_date: date
    budget_amount: int = Field(default=0, ge=0)
    hiring_manager_id: uuid.UUID | None = None
    requirements: str | None = Field(default=None, max_length=5000)


class HiringPlanUpdate(_Patch, _PlanRanges):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    department_id: uuid.UUID | None = None
    position: str | None = Field(default=None, min_length=1, max_length=200)
    headcount: int | None = Field(default=None, ge=1, le=10_000)
    filled: int | None = Field(default=None, ge=0)
    priority: HiringPriority | None = None
    budget_amount: int | None = Field(default=None, ge=0)
    budget_spent: int | None = Field(default=None, ge=0)
    hiring_manager_id: uuid.UUID | None = None
    requirements: str | None = Field(default=None, max_length=5000)
    status: PlanPatchStatus | None = None


class HiringPlanOut(_Out):
    title: str
    department_id: uuid.UUID
    position: str
    headcount: int
    filled: int
    priority: HiringPriority
    status: HiringStatus
    salary_min: int | None
    salary_max: int | None
    currency: str
    start_date: date
    target_date: date
    budget_amount: int
    budget_spent: int
    hiring_manager_id: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    reject_reason: str | None
    requirements: str | None


class ApprovalIn(BaseModel):
    decision: Decision
    reason: str = Field(min_length=1, max_length=2000)


# ---------- EP-87 workload ----------
class WorkloadOut(BaseModel):
    employee_ref: str
    open_tasks: int
    load_pct: float
    overloaded: bool


# ---------- EP-80 dashboard (10 §5) ----------
class PeriodOut(BaseModel):
    key: str
    type: str
    start_date: date
    end_date: date


class HeadcountPoint(BaseModel):
    period_key: str
    headcount: int


class TurnoverPoint(BaseModel):
    period_key: str
    turnover_rate_pct: float


class HrDashboardOut(BaseModel):
    """`summary` is a flat dict: `payroll_total` is absent (not null) for roles without
    payroll visibility (02 §6.2, DEC-197)."""

    pillar: Literal["O"] = "O"
    status: Literal["ok", "warning", "critical", "no_data"]
    period: PeriodOut
    summary: dict[str, Any]
    metrics: list[dict[str, Any]]
    headcount_trend: list[HeadcountPoint]
    turnover_trend: list[TurnoverPoint]
    open_alerts: int | None
