"""Finance repositories — only `finance` services use them (DEC-125)."""

import uuid
from datetime import date

from sqlalchemy import func, or_, select, update

from app.core.base_repository import BaseRepository
from app.core.events.envelope import OUTBOX
from app.modules.finance.models import (
    Budget,
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
