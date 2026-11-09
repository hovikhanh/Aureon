"""Sales repositories — only `sales` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, String, cast, func, or_, select, update

from app.core.base_repository import BaseRepository
from app.core.tenant import require_tenant
from app.modules.sales.models import (
    Client,
    Contract,
    Deal,
    DealStageHistory,
    Lead,
    SalesActivity,
    SalesContact,
    SalesTarget,
)


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
        # v4 CRM: live contacts / activities would be orphaned by a client delete
        contacts = select(SalesContact.id).where(
            SalesContact.client_id == client_id, SalesContact.deleted_at.is_(None)
        )
        activities = select(SalesActivity.id).where(
            SalesActivity.client_id == client_id, SalesActivity.deleted_at.is_(None)
        )
        stmt = select(deals.exists() | contracts.exists() | contacts.exists() | activities.exists())
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


# ---------- R-DEC-176 CRM ----------
def digits(phone: str) -> str:
    """Phone compared on digits only (`+84 90-123` ≡ `8490123`)."""
    return "".join(ch for ch in phone if ch.isdigit())


def _same_channel(model: Any, email: str | None, phone: str | None) -> ColumnElement[bool] | None:
    """R-DEC-176 d (D-08): exact e-mail (case-insensitive) or phone (digits) match."""
    clauses: list[ColumnElement[bool]] = []
    if email and email.strip():
        clauses.append(func.lower(model.email) == email.strip().lower())
    if phone and digits(phone):
        clauses.append(func.regexp_replace(model.phone, r"\D", "", "g") == digits(phone))
    return or_(*clauses) if clauses else None


def search_clause(q: str, *cols: Any) -> ColumnElement[bool]:
    """`q` filter: case-insensitive substring over the given text columns."""
    pattern = "%" + q.strip().replace("%", "").replace("_", "") + "%"
    return or_(*(cast(c, String).ilike(pattern) for c in cols))


class LeadRepository(BaseRepository[Lead]):
    model = Lead

    async def lock(self, lead: Lead) -> None:
        """`SELECT … FOR UPDATE` so two converts of one lead cannot both pass the status check."""
        await self.db.refresh(lead, with_for_update=True)

    async def same_channel(
        self, email: str | None, phone: str | None, *where: Any, limit: int = 5
    ) -> Sequence[Lead]:
        match = _same_channel(Lead, email, phone)
        if match is None:
            return []
        stmt = self._live().where(match, *where).order_by(Lead.created_at).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()


class ContactRepository(BaseRepository[SalesContact]):
    model = SalesContact

    async def same_channel(
        self, email: str | None, phone: str | None, *where: Any, limit: int = 5
    ) -> Sequence[SalesContact]:
        match = _same_channel(SalesContact, email, phone)
        if match is None:
            return []
        stmt = self._live().where(match, *where).order_by(SalesContact.created_at).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

    async def client_ids(self) -> set[uuid.UUID]:
        """Clients that already have a live contact (seed back-fill, R-DEC-176 g)."""
        stmt = self._scoped(select(SalesContact.client_id)).where(SalesContact.deleted_at.is_(None))
        return set((await self.db.execute(stmt)).scalars().all())


class ActivityRepository(BaseRepository[SalesActivity]):
    model = SalesActivity

    async def move_lead_history(
        self, lead_id: uuid.UUID, client_id: uuid.UUID, contact_id: uuid.UUID, actor: uuid.UUID
    ) -> None:
        """Lead converted: its live activities without an account follow it to the client."""
        await self.db.execute(
            update(SalesActivity)
            .where(SalesActivity.tenant_id == require_tenant(), SalesActivity.lead_id == lead_id,
                   SalesActivity.deleted_at.is_(None), SalesActivity.client_id.is_(None))
            .values(client_id=client_id, updated_by=actor,
                    contact_id=func.coalesce(SalesActivity.contact_id, contact_id),
                    version=SalesActivity.version + 1)
        )  # fmt: skip
