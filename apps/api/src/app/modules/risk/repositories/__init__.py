"""Risk repositories — only `risk` services use them (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select

from app.core.base_repository import BaseRepository
from app.modules.risk.models import Mitigation, Risk, RiskAssessment, Scenario


class RiskRepository(BaseRepository[Risk]):
    model = Risk

    async def last_code(self, year: int) -> str | None:
        """Highest `RSK-<year>-NNN` (incl. soft-deleted rows — codes are never reused)."""
        stmt = (
            select(Risk.code)
            .where(Risk.code.like(f"RSK-{year:04d}-%"))
            .order_by(func.length(Risk.code).desc(), Risk.code.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def ids_stmt(*where: ColumnElement[bool]) -> Select[uuid.UUID]:
        """Ids of live risks matching `where` (scope subquery for mitigation lists)."""
        stmt = select(Risk.id).where(Risk.deleted_at.is_(None))
        for clause in where:
            stmt = stmt.where(clause)
        return stmt

    async def lock_codes(self) -> None:
        """Serialise `RSK-YYYY-NNN` generation inside the transaction (advisory xact lock)."""
        await self.db.execute(select(func.pg_advisory_xact_lock(func.hashtext("risk.code"))))

    async def lock(self, risk: Risk) -> None:
        await self.db.refresh(risk, with_for_update=True)

    async def by_source_event(self, event_id: uuid.UUID) -> Risk | None:
        stmt = select(Risk).where(Risk.source_event_id == event_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def open_for_link(self, category: str, key: str, value: str) -> Risk | None:
        """A live, non-terminal risk of `category` linked to the same source aggregate."""
        stmt = (
            self._live()
            .where(
                Risk.category == category,
                Risk.status.not_in(("closed", "rejected", "accepted")),
                Risk.linked_entities[key].astext == value,
            )
            .order_by(Risk.created_at)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def scoped(self, *where: ColumnElement[bool]) -> Sequence[Risk]:
        stmt = self._live()
        for clause in where:
            stmt = stmt.where(clause)
        return (await self.db.execute(stmt)).scalars().all()


class AssessmentRepository(BaseRepository[RiskAssessment]):
    model = RiskAssessment

    async def for_risk(self, risk_id: uuid.UUID) -> Sequence[RiskAssessment]:
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.risk_id == risk_id)
            .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.id)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def for_risks(self, risk_ids: Sequence[uuid.UUID]) -> Sequence[RiskAssessment]:
        if not risk_ids:
            return []
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.risk_id.in_(risk_ids))
            .order_by(RiskAssessment.assessed_at)
        )
        return (await self.db.execute(stmt)).scalars().all()


class MitigationRepository(BaseRepository[Mitigation]):
    model = Mitigation

    async def for_risks(self, risk_ids: Sequence[uuid.UUID]) -> Sequence[Mitigation]:
        if not risk_ids:
            return []
        stmt = self._live().where(Mitigation.risk_id.in_(risk_ids))
        return (await self.db.execute(stmt)).scalars().all()

    async def count_status(self, risk_id: uuid.UUID, status: str) -> int:
        stmt = select(func.count()).select_from(
            self._live()
            .where(Mitigation.risk_id == risk_id, Mitigation.status == status)
            .subquery()
        )
        return int((await self.db.execute(stmt)).scalar_one())

    @staticmethod
    def overdue_clause(today: date) -> Any:
        return (Mitigation.status.in_(("planned", "in_progress"))) & (Mitigation.due_date < today)


class ScenarioRepository(BaseRepository[Scenario]):
    model = Scenario
