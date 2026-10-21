"""Finance repositories — only `finance` services use them (DEC-125)."""

import uuid

from sqlalchemy import func, or_, select

from app.core.base_repository import BaseRepository
from app.core.events.envelope import OUTBOX
from app.modules.finance.models import (
    Budget,
    CashPosition,
    Expense,
    Forecast,
    ForecastLine,
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
