"""Sales repositories — only `sales` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update

from app.core.base_repository import BaseRepository
from app.modules.sales.models import Client, Contract, Deal, DealStageHistory, SalesTarget


class ClientRepository(BaseRepository[Client]):
    model = Client

    async def by_normalized_name(self, norm: str) -> Client | None:
        stmt = self._live().where(Client.normalized_name == norm).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_tax_code(self, tax_code: str) -> Client | None:
        stmt = self._live().where(Client.tax_code == tax_code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def similar(
        self, norm: str, *, threshold: float, exclude: uuid.UUID | None = None, limit: int = 5
    ) -> list[tuple[Client, float]]:
        """Trigram neighbours of `norm` (`pg_trgm`, GIN index) with score ≥ `threshold`."""
        score = func.similarity(Client.normalized_name, norm)
        stmt = (
            select(Client, score)
            .where(Client.deleted_at.is_(None), score >= threshold)
            .order_by(score.desc(), Client.id)
            .limit(limit)
        )
        if exclude is not None:
            stmt = stmt.where(Client.id != exclude)
        return [(c, float(s)) for c, s in (await self.db.execute(stmt)).all()]

    async def has_live_children(self, client_id: uuid.UUID) -> bool:
        deals = select(Deal.id).where(Deal.client_id == client_id, Deal.deleted_at.is_(None))
        contracts = select(Contract.id).where(
            Contract.client_id == client_id, Contract.deleted_at.is_(None)
        )
        stmt = select(deals.exists() | contracts.exists())
        return bool((await self.db.execute(stmt)).scalar_one())


class DealRepository(BaseRepository[Deal]):
    model = Deal

    async def lock(self, deal: Deal) -> None:
        """`SELECT … FOR UPDATE` re-read so two stage changes cannot both pass the check."""
        await self.db.refresh(deal, with_for_update=True)

    async def scoped(self, *where: Any) -> Sequence[Deal]:
        stmt = self._live()
        for clause in where:
            stmt = stmt.where(clause)
        return (await self.db.execute(stmt)).scalars().all()


class StageHistoryRepository(BaseRepository[DealStageHistory]):
    model = DealStageHistory

    async def for_deal(self, deal_id: uuid.UUID) -> Sequence[DealStageHistory]:
        stmt = (
            select(DealStageHistory)
            .where(DealStageHistory.deal_id == deal_id)
            .order_by(DealStageHistory.entered_at, DealStageHistory.created_at)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def for_deals(self, deal_ids: Sequence[uuid.UUID]) -> Sequence[DealStageHistory]:
        if not deal_ids:
            return []
        stmt = (
            select(DealStageHistory)
            .where(DealStageHistory.deal_id.in_(deal_ids))
            .order_by(DealStageHistory.deal_id, DealStageHistory.entered_at)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def close_current(self, deal_id: uuid.UUID, at: Any) -> None:
        """Set `exited_at` on the open row — the only UPDATE this log ever receives."""
        await self.db.execute(
            update(DealStageHistory)
            .where(DealStageHistory.deal_id == deal_id, DealStageHistory.exited_at.is_(None))
            .values(exited_at=at)
        )


class TargetRepository(BaseRepository[SalesTarget]):
    model = SalesTarget

    async def find(
        self, period_key: str, scope: str, owner_id: uuid.UUID | None
    ) -> SalesTarget | None:
        stmt = self._live().where(SalesTarget.period_key == period_key, SalesTarget.scope == scope)
        if owner_id is None:
            stmt = stmt.where(SalesTarget.owner_id.is_(None))
        else:
            stmt = stmt.where(SalesTarget.owner_id == owner_id)
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

    async def by_period(self, period_key: str) -> Sequence[SalesTarget]:
        stmt = self._live().where(SalesTarget.period_key == period_key)
        return (await self.db.execute(stmt)).scalars().all()


class ContractRepository(BaseRepository[Contract]):
    model = Contract

    async def by_number(self, number: str) -> Contract | None:
        stmt = self._live().where(Contract.contract_number == number)
        return (await self.db.execute(stmt)).scalar_one_or_none()
