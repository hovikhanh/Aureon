"""EP-103 mitigations (FR-RSK-04, T-213) + automatic risk status sync (DEC-217).

- A mitigation moving to `in_progress` puts an `identified`/`assessed` risk in `mitigating`.
- When the last active mitigation (`planned`/`in_progress`) of a `mitigating` risk ends with at
  least one `done`, the risk moves to `monitoring` and `EVT-risk.risk_mitigated` is published.
- `overdue` = status ∈ {planned, in_progress} and `due_date` < business today (METRIC-RSK-05).
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.core.errors import ConflictStateError, NotFoundError
from app.core.pagination import PageParams
from app.modules.risk.models import Mitigation, Risk
from app.modules.risk.repositories import MitigationRepository, RiskRepository
from app.modules.risk.schemas import MitigationCreate, MitigationOut, MitigationUpdate
from app.modules.risk.services import rules, scope
from app.modules.risk.services.common import audit, now_utc, publish, risk_out
from app.modules.risk.services.risk_service import RiskService

CLOSED_RISK = frozenset({"proposed", "rejected", "closed", "accepted"})


def is_overdue(m: Mitigation, today: date) -> bool:
    return m.status in rules.ACTIVE_MITIGATION and m.due_date < today


def mitigation_out(m: Mitigation, today: date | None = None) -> MitigationOut:
    return MitigationOut(
        id=m.id, version=m.version, created_at=m.created_at, updated_at=m.updated_at,
        risk_id=m.risk_id, title=m.title, owner_id=m.owner_id, due_date=m.due_date,
        progress_pct=float(m.progress_pct), status=m.status, completed_at=m.completed_at,
        task_id=m.task_id, overdue=is_overdue(m, today or business_today()),
    )  # fmt: skip


class MitigationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MitigationRepository(db)
        self.risks = RiskRepository(db)

    async def _risk(self, user: Principal, risk_id: uuid.UUID) -> Risk:
        return await RiskService(self.db).get_row(user, risk_id)

    async def list_mitigations(
        self, user: Principal, page: PageParams, *, risk_id: uuid.UUID | None,
        status: str | None, owner_id: uuid.UUID | None, overdue: bool | None,
    ) -> tuple[list[MitigationOut], int]:  # fmt: skip
        where: list[Any] = []
        risk_where = scope.read_filter(user)
        if risk_where:
            where.append(Mitigation.risk_id.in_(RiskRepository.ids_stmt(*risk_where)))
        if overdue is not None:
            clause = MitigationRepository.overdue_clause(business_today())
            where.append(clause if overdue else ~clause)
        filters = {"risk_id": risk_id, "status": status, "owner_id": owner_id}
        items, total = await self.repo.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None}, where=where,
        )  # fmt: skip
        today = business_today()
        return [mitigation_out(m, today) for m in items], total

    async def get_row(self, user: Principal, id_: uuid.UUID) -> tuple[Mitigation, Risk]:
        obj = await self.repo.get(id_)
        if obj is None:
            raise NotFoundError("mitigation not found")
        return obj, await self._risk(user, obj.risk_id)

    async def get(self, user: Principal, id_: uuid.UUID) -> MitigationOut:
        return mitigation_out((await self.get_row(user, id_))[0])

    async def create(self, user: Principal, body: MitigationCreate) -> MitigationOut:
        risk = await self._risk(user, body.risk_id)
        scope.check_write(user, risk)
        if risk.status in CLOSED_RISK:
            raise ConflictStateError(
                f"cannot add a mitigation to a {risk.status} risk", details={"status": risk.status}
            )
        obj = Mitigation(
            risk_id=risk.id, title=body.title, owner_id=body.owner_id, due_date=body.due_date,
            progress_pct=Decimal(str(body.progress_pct)), status=body.status, task_id=body.task_id,
            completed_at=now_utc() if body.status == "done" else None,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        out = mitigation_out(obj)
        await audit(self.db, "risk.mitigation_create", "mitigations", obj, after=out)
        await self._sync_risk(user, risk)
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: MitigationUpdate, expected: int
    ) -> MitigationOut:
        obj, risk = await self.get_row(user, id_)
        scope.check_write(user, risk)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if data.get("owner_id", obj.owner_id) is None:
            data.pop("owner_id")  # owner is NOT NULL (05): an explicit null keeps the owner
        if "progress_pct" in data:
            data["progress_pct"] = Decimal(str(data["progress_pct"]))
        new_status = data.get("status", obj.status)
        if new_status == "done" and obj.status != "done":
            data["completed_at"] = now_utc()
        elif new_status != "done":
            data["completed_at"] = None
        before = mitigation_out(obj)
        await self.repo.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = mitigation_out(obj)
        await audit(self.db, "risk.mitigation_update", "mitigations", obj, before, out)
        await self._sync_risk(user, risk)
        return out

    async def _sync_risk(self, user: Principal, risk: Risk) -> None:
        if risk.status in CLOSED_RISK:
            return
        await self.risks.lock(risk)
        rows = await self.repo.for_risks([risk.id])
        statuses = [m.status for m in rows]
        target: str | None = None
        if "in_progress" in statuses and risk.status in ("identified", "assessed"):
            target = "mitigating" if risk.owner_id is not None else None
        elif (
            risk.status == "mitigating"
            and "done" in statuses
            and not (set(statuses) & rules.ACTIVE_MITIGATION)
        ):
            target = "monitoring"
        if target is None:
            return
        before = risk_out(risk)
        await self.risks.update(risk, status=target, updated_by=user.user_id)
        await self.db.refresh(risk)
        await audit(self.db, "risk.risk_status_change", "risks", risk, before, risk_out(risk),
                    why="mitigation progress")  # fmt: skip
        if target in rules.MITIGATED_STATUSES:
            await publish(self.db, "risk.risk_mitigated", risk, {"status": target})
