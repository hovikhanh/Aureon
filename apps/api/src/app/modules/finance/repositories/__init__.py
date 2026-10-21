"""Finance repositories — only `finance` services use them (DEC-125)."""

import uuid
from datetime import date

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_repository import BaseRepository
from app.core.events.envelope import OUTBOX
from app.modules.finance.models import (
    Budget,
    CashFlowForecast,
    CashFlowForecastLine,
    CashPosition,
    Expense,
    Forecast,
    ForecastLine,
    Invoice,
    InvoiceLine,
    Revenue,
)


class RevenueRepository(BaseRepository[Revenue]):
    model = Revenue


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense


class CashPositionRepository(BaseRepository[CashPosition]):
    model = CashPosition

    async def by_period(self, period_key: str) -> CashPosition | None:
        stmt = self._live().where(CashPosition.period_key == period_key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def previous(self, period_key: str) -> CashPosition | None:
        stmt = (
            self._live()
            .where(CashPosition.period_key < period_key)
            .order_by(CashPosition.period_key.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class BudgetRepository(BaseRepository[Budget]):
    model = Budget

    async def find(
        self, department_id: uuid.UUID, fiscal_year: int, quarter: str | None
    ) -> Budget | None:
        q = Budget.quarter.is_(None) if quarter is None else Budget.quarter == quarter
        stmt = self._live().where(
            Budget.department_id == department_id, Budget.fiscal_year == fiscal_year, q
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def covering(
        self, department_id: uuid.UUID, fiscal_year: int, quarter: str
    ) -> list[Budget]:
        """Quarter budget + whole-year budget of the department that include an expense."""
        stmt = self._live().where(
            Budget.department_id == department_id,
            Budget.fiscal_year == fiscal_year,
            or_(Budget.quarter == quarter, Budget.quarter.is_(None)),
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def spent(
        self, department_id: uuid.UUID, periods: list[str], category: str | None = None
    ) -> int:
        stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.deleted_at.is_(None),
            Expense.department_id == department_id,
            Expense.period_key.in_(periods),
        )
        if category is not None:
            stmt = stmt.where(Expense.category == category)
        return int((await self.db.execute(stmt)).scalar_one())

    async def event_already_published(self, event_type: str, aggregate_id: uuid.UUID) -> bool:
        stmt = select(func.count()).where(
            OUTBOX.c.event_type == event_type, OUTBOX.c.aggregate_id == aggregate_id
        )
        return int((await self.db.execute(stmt)).scalar_one()) > 0


class ForecastRepository(BaseRepository[Forecast]):
    model = Forecast

    async def current(self, scenario: str) -> Forecast | None:
        stmt = self._live().where(Forecast.scenario == scenario, Forecast.is_current.is_(True))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def lines(self, forecast_id: uuid.UUID) -> list[ForecastLine]:
        stmt = (
            select(ForecastLine)
            .where(ForecastLine.forecast_id == forecast_id, ForecastLine.deleted_at.is_(None))
            .order_by(ForecastLine.period_key)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def latest_closing(self) -> int:
        stmt = (
            select(CashPosition.closing_balance)
            .where(CashPosition.deleted_at.is_(None))
            .order_by(CashPosition.period_key.desc())
            .limit(1)
        )
        return int((await self.db.execute(stmt)).scalar_one_or_none() or 0)


OPEN_STATUSES = ("sent", "partial", "overdue")


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    async def lines(self, invoice_id: uuid.UUID) -> list[InvoiceLine]:
        stmt = (
            select(InvoiceLine)
            .where(InvoiceLine.invoice_id == invoice_id, InvoiceLine.deleted_at.is_(None))
            .order_by(InvoiceLine.line_no)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def number_taken(
        self, direction: str, tax_code: str | None, series: str | None, number: str
    ) -> bool:
        stmt = select(func.count()).where(
            Invoice.deleted_at.is_(None),
            Invoice.direction == direction,
            func.coalesce(Invoice.counterparty_tax_code, "") == (tax_code or ""),
            func.coalesce(Invoice.series, "") == (series or ""),
            Invoice.number == number,
        )
        return int((await self.db.execute(stmt)).scalar_one()) > 0

    async def mark_overdue(self, as_of: date) -> list[uuid.UUID]:
        stmt = (
            update(Invoice)
            .where(
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(("sent", "partial")),
                Invoice.due_date < as_of,
                Invoice.total_amount > Invoice.paid_amount,
            )
            .values(status="overdue", version=Invoice.version + 1)
            .returning(Invoice.id)
        )
        return [r[0] for r in (await self.db.execute(stmt)).all()]

    async def receivables(self, as_of: date) -> tuple[int, int]:
        """(open AR, overdue AR) for OUT invoices at `as_of` (METRIC-FIN-04/05)."""
        due = Invoice.total_amount - Invoice.paid_amount
        stmt = select(
            func.coalesce(func.sum(due), 0),
            func.coalesce(func.sum(due).filter(Invoice.due_date < as_of), 0),
        ).where(
            Invoice.deleted_at.is_(None),
            Invoice.direction == "OUT",
            Invoice.status.in_(OPEN_STATUSES),
            Invoice.issue_date <= as_of,
        )
        total, overdue = (await self.db.execute(stmt)).one()
        return int(total), int(overdue)


class AnalyticsRepository:
    """Read-only aggregates for BR-FIN / dashboard (one GROUP BY per source, no N+1)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def monthly_revenue(self, periods: list[str]) -> dict[str, int]:
        stmt = (
            select(Revenue.period_key, func.sum(Revenue.amount))
            .where(Revenue.deleted_at.is_(None), Revenue.period_key.in_(periods))
            .group_by(Revenue.period_key)
        )
        return {p: int(v) for p, v in (await self.db.execute(stmt)).all()}

    async def revenue_by_client(self, periods: list[str]) -> dict[uuid.UUID, int]:
        stmt = (
            select(Revenue.client_id, func.sum(Revenue.amount))
            .where(
                Revenue.deleted_at.is_(None), Revenue.period_key.in_(periods),
                Revenue.client_id.is_not(None),
            )
            .group_by(Revenue.client_id)
        )  # fmt: skip
        return {c: int(v) for c, v in (await self.db.execute(stmt)).all() if c is not None}

    async def monthly_expense(
        self, periods: list[str], category: str | None = None
    ) -> dict[str, int]:
        stmt = (
            select(Expense.period_key, func.sum(Expense.amount))
            .where(Expense.deleted_at.is_(None), Expense.period_key.in_(periods))
            .group_by(Expense.period_key)
        )
        if category is not None:
            stmt = stmt.where(Expense.category == category)
        return {p: int(v) for p, v in (await self.db.execute(stmt)).all()}

    async def sum_between(
        self, model: type[Revenue] | type[Expense], start: date, end: date
    ) -> int:
        col = Revenue.revenue_date if model is Revenue else Expense.expense_date
        stmt = select(func.coalesce(func.sum(model.amount), 0)).where(
            model.deleted_at.is_(None), col >= start, col < end
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def cash_on_or_before(self, period_key: str) -> CashPosition | None:
        stmt = (
            select(CashPosition)
            .where(CashPosition.deleted_at.is_(None), CashPosition.period_key <= period_key)
            .order_by(CashPosition.period_key.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def cash_by_period(self, periods: list[str]) -> dict[str, int]:
        stmt = select(CashPosition.period_key, CashPosition.closing_balance).where(
            CashPosition.deleted_at.is_(None), CashPosition.period_key.in_(periods)
        )
        return {p: int(v) for p, v in (await self.db.execute(stmt)).all()}

    async def forecast_line(self, scenario: str, period_key: str) -> ForecastLine | None:
        """Line of the earliest-generated forecast of `scenario` covering `period_key`
        (= "bản đầu tháng", METRIC-FIN-07)."""
        stmt = (
            select(ForecastLine)
            .join(Forecast, Forecast.id == ForecastLine.forecast_id)
            .where(
                Forecast.deleted_at.is_(None), ForecastLine.deleted_at.is_(None),
                Forecast.scenario == scenario, ForecastLine.period_key == period_key,
            )
            .order_by(Forecast.generated_at.asc())
            .limit(1)
        )  # fmt: skip
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def burn_event_published(self, day: date) -> bool:
        stmt = select(func.count()).where(
            OUTBOX.c.event_type == "finance.burn_over_forecast",
            OUTBOX.c.payload["as_of"].astext == day.isoformat(),
        )
        return int((await self.db.execute(stmt)).scalar_one()) > 0


class CashFlowRepository(BaseRepository[CashFlowForecast]):
    model = CashFlowForecast

    async def current(self) -> CashFlowForecast | None:
        stmt = self._live().where(CashFlowForecast.is_current.is_(True))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def lines(self, forecast_id: uuid.UUID) -> list[CashFlowForecastLine]:
        stmt = (
            select(CashFlowForecastLine)
            .where(CashFlowForecastLine.forecast_id == forecast_id)
            .order_by(CashFlowForecastLine.week_no)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def open_invoices(self, direction: str) -> list[tuple[date | None, int]]:
        """(due_date, amount_due) of open invoices of a direction."""
        stmt = select(Invoice.due_date, Invoice.total_amount - Invoice.paid_amount).where(
            Invoice.deleted_at.is_(None),
            Invoice.direction == direction,
            Invoice.status.in_(OPEN_STATUSES),
            Invoice.total_amount > Invoice.paid_amount,
        )
        return [(d, int(a)) for d, a in (await self.db.execute(stmt)).all()]

    async def inputs_fingerprint(self) -> str:
        """Changes on any input (invoice, expense, cash position — incl. soft delete) change
        this value; compared with the one stored at compute time → `stale`."""
        parts = []
        for model in (Invoice, Expense, CashPosition):
            stmt = select(
                func.count(), func.coalesce(func.sum(model.version), 0), func.max(model.updated_at)
            )
            n, versions, latest = (await self.db.execute(stmt)).one()
            parts.append(f"{n}:{versions}:{latest.isoformat() if latest else '-'}")
        return "|".join(parts)
