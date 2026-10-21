"""Schema `finance` — 10 tables (05 §4.2). Column groups follow 05 §2.1.

All 10 tables are business entities (05 §2.1 group 1) → `BusinessModel` (full C19 + soft delete).
DEC-154: domain source columns are `revenues.source_note` / `cash_positions.cash_source`; the bare
`source` column is the C19 `platform.record_source` inherited from `BusinessModel`.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Index,
    SmallInteger,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BusinessModel
from app.core.columns import currency, fk, measure, money, pct, sr, txt
from app.core.enums import ACTOR_TYPE, CONFIDENCE_BAND, pg_enum

S = "finance"
TS = DateTime(timezone=True)

# ---------- module-owned enums (05 §6) ----------
REVENUE_CATEGORY = pg_enum(S, "revenue_category", "product_sales", "service", "consulting", "other")
EXPENSE_CATEGORY = pg_enum(
    S, "expense_category",
    "salary", "cogs", "infrastructure", "marketing", "office", "travel", "other",
)  # fmt: skip
RECORD_ORIGIN = pg_enum(S, "record_origin", "manual", "invoice", "financial_report", "imported")
RECURRENCE_PERIOD = pg_enum(S, "recurrence_period", "monthly", "quarterly", "yearly")
QUARTER = pg_enum(S, "quarter", "Q1", "Q2", "Q3", "Q4")
FORECAST_SCENARIO = pg_enum(S, "forecast_scenario", "base", "optimistic", "pessimistic")
INVOICE_DIRECTION = pg_enum(S, "invoice_direction", "OUT", "IN")
INVOICE_STATUS = pg_enum(
    S, "invoice_status", "draft", "sent", "partial", "paid", "overdue", "cancelled"
)
CASH_SOURCE = pg_enum(S, "cash_source", "bank_statement", "manual", "imported")

MODULE_ENUMS = (
    REVENUE_CATEGORY, EXPENSE_CATEGORY, RECORD_ORIGIN, RECURRENCE_PERIOD, QUARTER,
    FORECAST_SCENARIO, INVOICE_DIRECTION, INVOICE_STATUS, CASH_SOURCE,
)  # fmt: skip


# ---------- invoices (referenced by revenues / expenses) ----------
class Invoice(BusinessModel):
    """ENT-Invoice — XD-05 business UQ; `overdue` set by the daily job (METRIC-FIN-05)."""

    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("due_date IS NULL OR due_date >= issue_date", name="due_after_issue"),
        CheckConstraint("direction <> 'OUT' OR client_id IS NOT NULL", name="out_requires_client"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("vat_rate_pct IN (0, 5, 8, 10)", name="vat_rate_allowed"),
        CheckConstraint("total_amount = subtotal + vat_amount", name="total_is_sum"),
        CheckConstraint("paid_amount >= 0 AND paid_amount <= total_amount", name="paid_in_range"),
        Index(
            "uq_invoices_business_key",
            "direction",
            text("COALESCE(counterparty_tax_code, '')"),
            text("COALESCE(series, '')"),
            "number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_invoices_direction_status_due_date", "direction", "status", "due_date"),
        Index("ix_invoices_issue_date", "issue_date"),
        {"schema": S},
    )

    direction: Mapped[str] = mapped_column(INVOICE_DIRECTION, nullable=False)
    series: Mapped[str | None] = txt(nullable=True)
    number: Mapped[str] = txt()
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    client_id: Mapped[uuid.UUID | None] = sr()
    client_name_snapshot: Mapped[str | None] = txt(nullable=True)
    client_tax_code: Mapped[str | None] = txt(nullable=True)
    counterparty_name: Mapped[str | None] = txt(nullable=True)
    counterparty_tax_code: Mapped[str | None] = txt(nullable=True)
    subtotal: Mapped[int] = money()
    vat_rate_pct: Mapped[Any] = pct(nullable=False)
    vat_amount: Mapped[int] = money()
    total_amount: Mapped[int] = money()
    paid_amount: Mapped[int] = money()
    amount_due: Mapped[int] = mapped_column(
        BigInteger, Computed("total_amount - paid_amount", persisted=True), nullable=False
    )
    currency: Mapped[str] = currency()
    status: Mapped[str] = mapped_column(INVOICE_STATUS, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    notes: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class InvoiceLine(BusinessModel):
    """ENT-InvoiceLine — `currency` added per 05 §1 C8 (money needs a same-table currency)."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        UniqueConstraint("invoice_id", "line_no"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        {"schema": S},
    )

    invoice_id: Mapped[uuid.UUID] = fk(f"{S}.invoices.id")
    line_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str] = txt()
    quantity: Mapped[Any] = measure(nullable=False)
    unit_price: Mapped[int] = money()
    amount: Mapped[int] = money()
    currency: Mapped[str] = currency()
    product_id: Mapped[uuid.UUID | None] = sr()


# ---------- revenue / expense / budget ----------
class Budget(BusinessModel):
    """ENT-Budget — `quarter` NULL = whole year."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("allocated_amount > 0", name="allocated_positive"),
        Index(
            "uq_budgets_department_year_quarter",
            "department_id",
            "fiscal_year",
            "quarter",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    department_id: Mapped[uuid.UUID] = sr(nullable=False)
    fiscal_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quarter: Mapped[str | None] = mapped_column(QUARTER, nullable=True)
    allocated_amount: Mapped[int] = money()
    currency: Mapped[str] = currency()
    categories: Mapped[Any] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class Revenue(BusinessModel):
    """ENT-Revenue — `source_note` renamed from `source` (DEC-154, C19)."""

    __tablename__ = "revenues"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        Index("ix_revenues_period_key_category", "period_key", "category"),
        {"schema": S},
    )

    source_note: Mapped[str] = txt()
    category: Mapped[str] = mapped_column(REVENUE_CATEGORY, nullable=False)
    amount: Mapped[int] = money()
    currency: Mapped[str] = currency()
    revenue_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_key: Mapped[str] = txt()
    client_id: Mapped[uuid.UUID | None] = sr()
    product_id: Mapped[uuid.UUID | None] = sr()
    invoice_id: Mapped[uuid.UUID | None] = fk(f"{S}.invoices.id", nullable=True)
    origin: Mapped[str] = mapped_column(RECORD_ORIGIN, nullable=False)
    description: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class Expense(BusinessModel):
    """ENT-Expense."""

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        Index("ix_expenses_period_key_department_id", "period_key", "department_id"),
        Index("ix_expenses_period_key_category", "period_key", "category"),
        {"schema": S},
    )

    title: Mapped[str] = txt()
    category: Mapped[str] = mapped_column(EXPENSE_CATEGORY, nullable=False)
    department_id: Mapped[uuid.UUID | None] = sr()
    budget_id: Mapped[uuid.UUID | None] = fk(f"{S}.budgets.id", nullable=True)
    amount: Mapped[int] = money()
    currency: Mapped[str] = currency()
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_key: Mapped[str] = txt()
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recurrence_period: Mapped[str | None] = mapped_column(RECURRENCE_PERIOD, nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = fk(f"{S}.invoices.id", nullable=True)
    counterparty_name: Mapped[str | None] = txt(nullable=True)
    counterparty_tax_code: Mapped[str | None] = txt(nullable=True)
    origin: Mapped[str] = mapped_column(RECORD_ORIGIN, nullable=False)
    description: Mapped[str | None] = txt(nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = sr()


# ---------- forecasts (P&L, monthly) ----------
class Forecast(BusinessModel):
    """ENT-Forecast — one current forecast per scenario (partial UQ)."""

    __tablename__ = "forecasts"
    __table_args__ = (
        CheckConstraint("horizon_months IN (3, 6, 12)", name="horizon_allowed"),
        Index(
            "uq_forecasts_current_scenario",
            "scenario",
            unique=True,
            postgresql_where=text("is_current AND deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    horizon_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    scenario: Mapped[str] = mapped_column(FORECAST_SCENARIO, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    generated_by: Mapped[str] = mapped_column(ACTOR_TYPE, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assumptions: Mapped[Any] = mapped_column(JSONB, nullable=False)
    ai_insights: Mapped[str | None] = txt(nullable=True)


class ForecastLine(BusinessModel):
    """ENT-ForecastLine."""

    __tablename__ = "forecast_lines"
    __table_args__ = (
        UniqueConstraint("forecast_id", "period_key"),
        {"schema": S},
    )

    forecast_id: Mapped[uuid.UUID] = fk(f"{S}.forecasts.id")
    period_key: Mapped[str] = txt()
    projected_revenue: Mapped[int] = money()
    projected_expenses: Mapped[int] = money()
    projected_net_profit: Mapped[int] = money()
    projected_closing_cash: Mapped[int] = money()
    currency: Mapped[str] = currency()
    confidence_level: Mapped[str] = mapped_column(CONFIDENCE_BAND, nullable=False)


# ---------- cash ----------
class CashPosition(BusinessModel):
    """ENT-CashPosition — `cash_source` renamed from `source` (DEC-154, C19)."""

    __tablename__ = "cash_positions"
    __table_args__ = (
        Index(
            "uq_cash_positions_period_key",
            "period_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    period_key: Mapped[str] = txt()
    closing_balance: Mapped[int] = money()
    currency: Mapped[str] = currency()
    cash_source: Mapped[str] = mapped_column(CASH_SOURCE, nullable=False)
    note: Mapped[str | None] = txt(nullable=True)
    recorded_by: Mapped[uuid.UUID] = sr(nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = sr()


class CashFlowForecast(BusinessModel):
    """ENT-CashFlowForecast — 13-week cash forecast (DEC-148); one current row (partial UQ)."""

    __tablename__ = "cash_flow_forecasts"
    __table_args__ = (
        CheckConstraint("weeks = 13", name="weeks_is_13"),
        CheckConstraint("min_cash_week BETWEEN 1 AND 13", name="min_cash_week_range"),
        Index(
            "uq_cash_flow_forecasts_current",
            "is_current",
            unique=True,
            postgresql_where=text("is_current AND deleted_at IS NULL"),
        ),
        {"schema": S},
    )

    start_week: Mapped[date] = mapped_column(Date, nullable=False)
    weeks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    opening_cash: Mapped[int] = money()
    currency: Mapped[str] = currency()
    min_projected_cash: Mapped[int] = money()
    min_cash_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    generated_by: Mapped[str] = mapped_column(ACTOR_TYPE, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assumptions: Mapped[Any] = mapped_column(JSONB, nullable=False)


class CashFlowForecastLine(BusinessModel):
    """ENT-CashFlowForecastLine — `net_flow` / `closing_cash` are precomputed, not generated."""

    __tablename__ = "cash_flow_forecast_lines"
    __table_args__ = (
        UniqueConstraint("forecast_id", "week_no"),
        CheckConstraint("week_no BETWEEN 1 AND 13", name="week_no_range"),
        {"schema": S},
    )

    forecast_id: Mapped[uuid.UUID] = fk(f"{S}.cash_flow_forecasts.id")
    week_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    inflow_receivables: Mapped[int] = money()
    inflow_other: Mapped[int] = money()
    outflow_payables: Mapped[int] = money()
    outflow_payroll: Mapped[int] = money()
    outflow_opex: Mapped[int] = money()
    outflow_other: Mapped[int] = money()
    net_flow: Mapped[int] = money()
    closing_cash: Mapped[int] = money()
    currency: Mapped[str] = currency()
    confidence_level: Mapped[str] = mapped_column(CONFIDENCE_BAND, nullable=False)
