"""Finance API DTOs (10 §4.6). API field names follow 10; columns follow 05 (DEC-185).

10 ↔ 05 renames are handled in the service, never in the DB: `recognized_on`↔`revenue_date`,
`spent_on`↔`expense_date`, `vendor`↔`counterparty_name`, `period`↔`period_key`.
`opening_balance` (EP-65) has no column: it is derived = previous period's `closing_balance`.
"""

import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

RevenueCategory = Literal["product_sales", "service", "consulting", "other"]
ExpenseCategory = Literal[
    "cogs", "salary", "infrastructure", "marketing", "office", "travel", "other"
]
CashSource = Literal["bank_statement", "manual", "imported"]
Recurrence = Literal["monthly", "quarterly", "yearly"]


def currency_field() -> Any:
    return Field(default="VND", pattern=r"^[A-Z]{3}$")


def check_period(value: str | None) -> str | None:
    if value is not None and not PERIOD_RE.match(value):
        raise ValueError("period must be YYYY-MM")
    return value


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


# ---------- EP-61 revenues ----------
class RevenueCreate(BaseModel):
    amount: int
    currency: str = currency_field()
    category: RevenueCategory
    recognized_on: date
    client_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    source_note: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)


class RevenueUpdate(_Patch):
    amount: int | None = None
    category: RevenueCategory | None = None
    recognized_on: date | None = None
    client_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    source_note: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)


class RevenueOut(_Out):
    amount: int
    currency: str
    category: str
    recognized_on: date
    period: str
    client_id: uuid.UUID | None
    product_id: uuid.UUID | None
    invoice_id: uuid.UUID | None
    source_note: str
    description: str | None


# ---------- EP-62 expenses ----------
class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    amount: int
    currency: str = currency_field()
    category: ExpenseCategory
    department_id: uuid.UUID | None = None
    budget_id: uuid.UUID | None = None
    spent_on: date
    is_recurring: bool = False
    recurrence_period: Recurrence | None = None
    vendor: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)


class ExpenseUpdate(_Patch):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    amount: int | None = None
    category: ExpenseCategory | None = None
    department_id: uuid.UUID | None = None
    budget_id: uuid.UUID | None = None
    spent_on: date | None = None
    is_recurring: bool | None = None
    recurrence_period: Recurrence | None = None
    vendor: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=2000)


class ExpenseOut(_Out):
    title: str
    amount: int
    currency: str
    category: str
    department_id: uuid.UUID | None
    budget_id: uuid.UUID | None
    spent_on: date
    period: str
    is_recurring: bool
    recurrence_period: str | None
    vendor: str | None
    description: str | None


# ---------- EP-65 cash positions ----------
class CashPositionCreate(BaseModel):
    period: str
    closing_balance: int = Field(ge=0)
    currency: str = currency_field()
    cash_source: CashSource = "manual"
    note: str | None = Field(default=None, max_length=1000)

    _p = field_validator("period")(check_period)


class CashPositionUpdate(_Patch):
    closing_balance: int | None = Field(default=None, ge=0)
    cash_source: CashSource | None = None
    note: str | None = Field(default=None, max_length=1000)


class CashPositionOut(_Out):
    period: str
    opening_balance: int | None
    closing_balance: int
    currency: str
    cash_source: str
    note: str | None
    recorded_by: uuid.UUID


# ---------- EP-63 budgets / EP-64 status ----------
Quarter = Literal["Q1", "Q2", "Q3", "Q4"]


class BudgetCategory(BaseModel):
    category: ExpenseCategory
    allocated_amount: int = Field(gt=0)


class BudgetCreate(BaseModel):
    department_id: uuid.UUID
    fiscal_year: int = Field(ge=2000, le=2100)
    quarter: Quarter | None = None
    allocated_amount: int = Field(gt=0)
    currency: str = currency_field()
    category: ExpenseCategory | None = None
    categories: list[BudgetCategory] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)


class BudgetUpdate(_Patch):
    allocated_amount: int | None = Field(default=None, gt=0)
    categories: list[BudgetCategory] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class BudgetOut(_Out):
    department_id: uuid.UUID
    fiscal_year: int
    quarter: str | None
    period: str
    allocated_amount: int
    currency: str
    category: str | None
    categories: list[BudgetCategory]
    notes: str | None


BudgetStatus = Literal["ok", "warning", "critical"]


class BudgetStatusOut(BaseModel):
    budget_id: uuid.UUID
    department_id: uuid.UUID
    period: str
    allocated_amount: int
    spent_amount: int
    budget_utilization_pct: float
    currency: str
    status: BudgetStatus


# ---------- EP-66 forecasts (+ lines) ----------
Scenario = Literal["optimistic", "base", "pessimistic"]
Horizon = Literal["1m", "3m", "6m", "1y"]
HORIZON_MONTHS: dict[str, int] = {"3m": 3, "6m": 6, "1y": 12}


class ForecastLineIn(BaseModel):
    period_key: str
    revenue: int = Field(ge=0)
    expense: int = Field(ge=0)

    _p = field_validator("period_key")(check_period)


class ForecastCreate(BaseModel):
    scenario: Scenario
    horizon: Horizon
    lines: list[ForecastLineIn] = Field(min_length=1, max_length=12)
    confidence_pct: float = Field(ge=0, le=100)
    assumptions: dict[str, Any] = Field(default_factory=dict)


class ForecastUpdate(_Patch):
    lines: list[ForecastLineIn] | None = Field(default=None, min_length=1, max_length=12)
    confidence_pct: float | None = Field(default=None, ge=0, le=100)
    assumptions: dict[str, Any] | None = None


class ForecastLineOut(BaseModel):
    period_key: str
    revenue: int
    expense: int
    net_profit: int
    closing_cash: int
    currency: str
    confidence_level: str


class ForecastOut(_Out):
    scenario: str
    horizon: str
    horizon_months: int
    is_current: bool
    generated_at: datetime
    generated_by: str
    confidence_pct: float | None
    assumptions: dict[str, Any]
    lines: list[ForecastLineOut]


# ---------- EP-67 invoices (+ lines) / EP-68 pay ----------
InvoiceStatus = Literal["draft", "sent", "partial", "paid", "overdue", "cancelled"]
VatPct = Literal[0, 5, 8, 10]


class InvoiceLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: float = Field(gt=0)
    unit_price: int = Field(ge=0)
    vat_pct: VatPct = 10
    product_id: uuid.UUID | None = None


class InvoiceCreate(BaseModel):
    direction: Literal["OUT", "IN"] = "OUT"
    client_id: uuid.UUID | None = None
    client_name: str | None = Field(default=None, max_length=300)
    counterparty_name: str | None = Field(default=None, max_length=300)
    counterparty_tax_code: str | None = Field(default=None, max_length=20)
    series: str | None = Field(default=None, max_length=20)
    number: str = Field(min_length=1, max_length=50)
    issued_on: date
    due_date: date
    currency: str = currency_field()
    status: Literal["draft", "sent"] = "sent"
    lines: list[InvoiceLineIn] = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class InvoiceUpdate(_Patch):
    due_date: date | None = None
    status: Literal["draft", "sent", "cancelled"] | None = None
    lines: list[InvoiceLineIn] | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class InvoiceLineOut(BaseModel):
    line_no: int
    description: str
    quantity: float
    unit_price: int
    amount: int
    vat_pct: float
    product_id: uuid.UUID | None


class InvoiceOut(_Out):
    direction: str
    client_id: uuid.UUID | None
    client_name: str | None
    counterparty_name: str | None
    series: str | None
    number: str
    issued_on: date
    due_date: date | None
    subtotal: int
    vat_pct: float
    vat_amount: int
    total_amount: int
    paid_amount: int
    amount_due: int
    currency: str
    status: str
    overdue: bool
    days_overdue: int
    paid_at: datetime | None
    notes: str | None
    lines: list[InvoiceLineOut]


class InvoicePay(BaseModel):
    amount_paid: int = Field(gt=0)
    paid_at: datetime
    method: Literal["bank_transfer", "cash", "card", "other"] | None = None
