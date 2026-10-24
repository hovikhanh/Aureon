"""EP-STR-12..21 initiatives + milestones (10 §7.2.3; v2.1 EP-45, T-133).

- Scope (R-DEC-57, `goal_scope`): department subtree + pillar + `owner_id`; milestones
  inherit the initiative's scope.
- `progress_pct` is system-computed (10 EP-STR-15; DEC-225): share of `done` milestones; with no
  milestones, share of `done` among the initiative's non-cancelled tasks; else 0. It is
  recomputed whenever a milestone or a linked task changes.
- `planned_end_date ≥ start_date`; milestone `done` stamps `done_at`.
- M1.4 (R-DEC-50): `strategic_objective_id` required on create (EP-STR-13), `objective_id`
  optional; any change of `progress_pct` / weight / SO link recomputes the StrategicObjective
  `progress_pct` in the same transaction (EP-STR-15, 05 §2.6).
"""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.pagination import PageParams
from app.modules.execution.models import (
    Decision,
    Initiative,
    Kpi,
    Milestone,
    Objective,
    Project,
    Task,
)
from app.modules.execution.repositories import (
    DecisionRepository,
    InitiativeRepository,
    KpiRepository,
    MilestoneRepository,
    ProjectRepository,
    TaskRepository,
)
from app.modules.execution.schemas.initiatives import (
    InitiativeCreate,
    InitiativeOut,
    InitiativeUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
)
from app.modules.execution.services import goal_scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, today
from app.modules.execution.services.meeting_service import _c19
from app.modules.execution.services.project_rules import milestone_late
from app.modules.execution.services.strategy_service import StrategyService

RULE = "FR-INI-01"


def initiative_out(i: Initiative) -> InitiativeOut:
    return InitiativeOut(
        **_c19(i), code=i.code, title=i.title, description=i.description,
        objective_id=i.objective_id, strategic_objective_id=i.strategic_objective_id,
        pillar=i.pillar, owner_id=i.owner_id,
        department_id=i.department_id, start_date=i.start_date,
        planned_end_date=i.planned_end_date, status=i.status,
        progress_pct=float(i.progress_pct), weight_pct=float(i.weight_pct),
        budget_amount=i.budget_amount, currency=i.currency,
    )  # fmt: skip


def milestone_out(m: Milestone, as_of: date | None = None) -> MilestoneOut:
    return MilestoneOut(**_c19(m), initiative_id=m.initiative_id, project_id=m.project_id,
                        title=m.title, due_date=m.due_date, status=m.status, done_at=m.done_at,
                        late=milestone_late(m.status, m.due_date, as_of or today()))  # fmt: skip


def share_done(statuses: list[str], done: str = "done", skip: str | None = None) -> Decimal:
    counted = [s for s in statuses if s != skip]
    if not counted:
        return Decimal(0)
    pct = Decimal(sum(1 for s in counted if s == done) * 100) / len(counted)
    return pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _drop_nulls(data: dict[str, Any], *keys: str) -> None:
    for k in keys:
        if k in data and data[k] is None:
            del data[k]


class InitiativeService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.initiatives = InitiativeRepository(db)
        self.milestones = MilestoneRepository(db)
        self.tasks = TaskRepository(db)

    async def list_initiatives(
        self, user: Principal, page: PageParams, *, objective_id: uuid.UUID | None,
        status: str | None, pillar: str | None, strategic_objective_id: uuid.UUID | None = None,
    ) -> tuple[list[InitiativeOut], int]:  # fmt: skip
        gs = await goal_scope.resolve(self.db, user)
        pred = gs.predicate(dept=Initiative.department_id, owner=Initiative.owner_id,
                            pillar=Initiative.pillar)  # fmt: skip
        raw = {"objective_id": objective_id, "status": status, "pillar": pillar,
               "strategic_objective_id": strategic_objective_id}  # fmt: skip
        items, total = await self.initiatives.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in raw.items() if v is not None},
            where=[pred] if pred is not None else [],
        )  # fmt: skip
        return [initiative_out(i) for i in items], total

    async def get_initiative(
        self, user: Principal, id_: uuid.UUID, action: goal_scope.Action = "read"
    ) -> Initiative:
        i = await self.initiatives.get(id_)
        if i is None:
            raise not_found("initiative")
        gs = await goal_scope.resolve(self.db, user)
        gs.check(action, dept=i.department_id, owners=(i.owner_id,), pillar=i.pillar,
                 what="initiative")  # fmt: skip
        return i

    @staticmethod
    def _dates(start: Any, end: Any) -> None:
        if end < start:
            raise BusinessRuleError(
                "planned_end_date must be on/after start_date",
                details={"field": "planned_end_date", "rule": RULE},
            )

    async def create_initiative(self, user: Principal, body: InitiativeCreate) -> InitiativeOut:
        data = body.model_dump()
        gs = await goal_scope.resolve(self.db, user)
        gs.require_writer("initiative")
        data["department_id"] = gs.pin_department(data["department_id"])
        self._dates(data["start_date"], data["planned_end_date"])
        await self.require_unique(Initiative, "code", data["code"], None)
        await self.require_refs(data, RULE, objective_id=Objective)
        i = await self.initiatives.create(**data, progress_pct=Decimal(0), source="MANUAL",
                                          created_by=user.user_id)  # fmt: skip
        await self._so_progress(i.strategic_objective_id)
        await self.db.refresh(i)
        out = initiative_out(i)
        await self.audit("initiative_create", "initiatives", i.id, after=out)
        return out

    async def update_initiative(
        self, user: Principal, id_: uuid.UUID, body: InitiativeUpdate, expected: int
    ) -> InitiativeOut:
        i = await self.get_initiative(user, id_, "write")
        before = initiative_out(i)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _drop_nulls(data, "code", "title", "objective_id", "strategic_objective_id", "owner_id",
                    "start_date", "planned_end_date", "status", "weight_pct")  # fmt: skip
        old_so = i.strategic_objective_id
        if "department_id" in data:
            gs = await goal_scope.resolve(self.db, user)
            data["department_id"] = gs.pin_department(data["department_id"])
        self._dates(data.get("start_date", i.start_date),
                    data.get("planned_end_date", i.planned_end_date))  # fmt: skip
        if "code" in data:
            await self.require_unique(Initiative, "code", data["code"], i.id)
        await self.require_refs(data, RULE, objective_id=Objective)
        await self.initiatives.update(i, expected_version=expected, updated_by=user.user_id,
                                      **data)  # fmt: skip
        await self._so_progress(old_so, i.strategic_objective_id)
        await self.db.refresh(i)
        out = initiative_out(i)
        await self.audit("initiative_update", "initiatives", i.id, before, out)
        return out

    async def delete_initiative(self, user: Principal, id_: uuid.UUID) -> None:
        i = await self.get_initiative(user, id_, "write")
        linked = (
            await self.milestones.where(Milestone.initiative_id == i.id)
            or await self.tasks.where(Task.initiative_id == i.id)
            or await DecisionRepository(self.db).where(Decision.initiative_id == i.id)
            or await KpiRepository(self.db).where(Kpi.initiative_id == i.id)
            or await ProjectRepository(self.db).where(Project.initiative_id == i.id)  # TC-M14-06
        )
        if linked:
            raise ConflictStateError(
                "initiative still has milestones, tasks, decisions, KPIs or projects",
                details={"initiative_id": str(i.id)},
            )
        before = initiative_out(i)
        i.updated_by = user.user_id
        await self.initiatives.soft_delete(i)
        await self._so_progress(i.strategic_objective_id)
        await self.audit("initiative_delete", "initiatives", i.id, before=before)

    async def recompute_progress(self, initiative_id: uuid.UUID | None) -> None:
        if initiative_id is None:
            return
        i = await self.initiatives.get(initiative_id)
        if i is None:
            return
        ms = await self.milestones.where(Milestone.initiative_id == i.id)
        if ms:
            i.progress_pct = share_done([m.status for m in ms])
        else:
            ts = await self.tasks.where(Task.initiative_id == i.id)
            i.progress_pct = share_done([t.status for t in ts], skip="cancelled")
        await self.db.flush()
        await self._so_progress(i.strategic_objective_id)

    async def _so_progress(self, *so_ids: uuid.UUID | None) -> None:
        svc = StrategyService(self.db)
        for so_id in dict.fromkeys(so_ids):
            await svc.recompute_progress(so_id)

    # ---------- milestones ----------
    async def list_milestones(
        self, user: Principal, initiative_id: uuid.UUID, page: PageParams
    ) -> tuple[list[MilestoneOut], int]:
        i = await self.get_initiative(user, initiative_id)
        items, total = await self.milestones.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={"initiative_id": i.id},
        )  # fmt: skip
        return [milestone_out(m) for m in items], total

    async def _milestone(
        self,
        user: Principal,
        initiative_id: uuid.UUID,
        milestone_id: uuid.UUID,
        action: goal_scope.Action,
    ) -> Milestone:
        await self.get_initiative(user, initiative_id, action)
        m = await self.milestones.get(milestone_id)
        if m is None or m.initiative_id != initiative_id:
            raise not_found("milestone")
        return m

    async def get_milestone(
        self, user: Principal, initiative_id: uuid.UUID, milestone_id: uuid.UUID
    ) -> MilestoneOut:
        return milestone_out(await self._milestone(user, initiative_id, milestone_id, "read"))

    async def create_milestone(
        self, user: Principal, initiative_id: uuid.UUID, body: MilestoneCreate
    ) -> MilestoneOut:
        i = await self.get_initiative(user, initiative_id, "write")
        data = body.model_dump()
        done_at = now_utc() if data["status"] == "done" else None
        m = await self.milestones.create(**data, initiative_id=i.id, done_at=done_at,
                                         source="MANUAL", created_by=user.user_id)  # fmt: skip
        await self.recompute_progress(i.id)
        await self.db.refresh(m)
        out = milestone_out(m)
        await self.audit("milestone_create", "milestones", m.id, after=out)
        return out

    async def update_milestone(
        self, user: Principal, initiative_id: uuid.UUID, milestone_id: uuid.UUID,
        body: MilestoneUpdate, expected: int,
    ) -> MilestoneOut:  # fmt: skip
        m = await self._milestone(user, initiative_id, milestone_id, "write")
        before = milestone_out(m)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _drop_nulls(data, "title", "due_date", "status")
        if "status" in data and data["status"] != m.status:
            data["done_at"] = now_utc() if data["status"] == "done" else None
        await self.milestones.update(m, expected_version=expected, updated_by=user.user_id,
                                     **data)  # fmt: skip
        await self.recompute_progress(initiative_id)
        await self.db.refresh(m)
        out = milestone_out(m)
        await self.audit("milestone_update", "milestones", m.id, before, out)
        return out

    async def delete_milestone(
        self, user: Principal, initiative_id: uuid.UUID, milestone_id: uuid.UUID
    ) -> None:
        m = await self._milestone(user, initiative_id, milestone_id, "write")
        if await self.tasks.where(Task.milestone_id == m.id):
            raise ConflictStateError("milestone still has tasks",
                                     details={"milestone_id": str(m.id)})  # fmt: skip
        before = milestone_out(m)
        m.updated_by = user.user_id
        await self.milestones.soft_delete(m)
        await self.recompute_progress(initiative_id)
        await self.audit("milestone_delete", "milestones", m.id, before=before)
