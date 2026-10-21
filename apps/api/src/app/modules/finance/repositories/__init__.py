"""Finance repositories — only `finance` services use them (DEC-125)."""

from collections.abc import Sequence

from sqlalchemy import select

from app.core.base_repository import BaseRepository
from app.modules.finance.models import CashPosition, Expense, Revenue


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

    async def closing_by_period(self, keys: Sequence[str]) -> dict[str, int]:
        """`{period_key: closing_balance}` for the given periods (live rows)."""
        if not keys:
            return {}
        stmt = select(CashPosition.period_key, CashPosition.closing_balance).where(
            CashPosition.deleted_at.is_(None), CashPosition.period_key.in_(keys)
        )
        return {k: int(v) for k, v in (await self.db.execute(stmt)).all()}
