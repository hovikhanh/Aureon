"""EP-46 objectives + key results (T-132).

- Scope (DEC-220): department + `owner_id`; a KR inherits its objective's department.
- KR count per objective ≤ 5 (05 ENT-KeyResult, BRD FR-OKR-01); activating an objective
  (`status = active`) needs 2..5 KRs and a non-`◑o` caller — "kích hoạt chỉ sau duyệt"
  (10 EP-46, US-DC-005; DEC-223).
- `progress_pct`: KR = baseline → target (0..100); objective = weighted mean of KRs.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.pagination import PageParams
from app.modules.execution.models import KeyResult, Kpi, Objective
from app.modules.execution.repositories import (
    KeyResultRepository,
    KpiRepository,
    ObjectiveRepository,
)
from app.modules.execution.schemas.okr import (
    KeyResultCreate,
    KeyResultOut,
    KeyResultUpdate,
    ObjectiveCreate,
    ObjectiveOut,
    ObjectiveUpdate,
)
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, num
from app.modules.execution.services.kpi_rules import kr_progress_pct, weighted_avg
from app.modules.execution.services.meeting_service import _c19

MAX_KR, MIN_KR_ACTIVE = 5, 2
RULE = "FR-OKR-01"


def objective_out(o: Objective) -> ObjectiveOut:
    return ObjectiveOut(
        **_c19(o), title=o.title, owner_id=o.owner_id, period_key=o.period_key,
        parent_id=o.parent_id, level=o.level, okr_type=o.okr_type,
        weight_pct=float(o.weight_pct), team_id=o.team_id, department_id=o.department_id,
        pillar=o.pillar, status=o.status, progress_pct=float(o.progress_pct),
        score=num(o.score), source_document_id=o.source_document_id,
    )  # fmt: skip


def kr_out(k: KeyResult) -> KeyResultOut:
    return KeyResultOut(
        **_c19(k), objective_id=k.objective_id, title=k.title, metric_code=k.metric_code,
        unit=k.unit, baseline=float(k.baseline), target=float(k.target),
        current_value=num(k.current_value), owner_id=k.owner_id, status=k.status,
        confidence=k.confidence, weight_pct=float(k.weight_pct),
        progress_pct=float(kr_progress_pct(k.baseline, k.target, k.current_value)),
    )  # fmt: skip


def _drop_nulls(data: dict[str, Any], *keys: str) -> None:
    for k in keys:
        if k in data and data[k] is None:
            del data[k]


class OkrService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.objectives = ObjectiveRepository(db)
        self.krs = KeyResultRepository(db)
        self.kpis = KpiRepository(db)

    # ---------- objectives ----------
    async def list_objectives(
        self, user: Principal, page: PageParams, *, period_key: str | None,
        owner_id: uuid.UUID | None,
    ) -> tuple[list[ObjectiveOut], int]:  # fmt: skip
        pred = scope.predicate(user, "read", dept=Objective.department_id,
                               own=[Objective.owner_id == user.user_id])  # fmt: skip
        filters = {k: v for k, v in {"period_key": period_key, "owner_id": owner_id}.items() if v}
        items, total = await self.objectives.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=[pred] if pred is not None else [],
        )  # fmt: skip
        return [objective_out(o) for o in items], total

    async def get_objective(
        self, user: Principal, id_: uuid.UUID, action: str = "read"
    ) -> Objective:
        o = await self.objectives.get(id_)
        if o is None:
            raise not_found("objective")
        scope.check(user, action, dept=o.department_id, owners=(o.owner_id,), what="objective")
        return o

    async def _check_activation(self, user: Principal, objective_id: uuid.UUID | None) -> None:
        if scope.level(user, "write") == "o":
            raise scope.deny("objective activation (needs approval)", rule="US-DC-005")
        n = 0 if objective_id is None else len(await self._krs_of(objective_id))
        if not MIN_KR_ACTIVE <= n <= MAX_KR:
            raise BusinessRuleError(
                f"an active objective needs {MIN_KR_ACTIVE}..{MAX_KR} key results",
                details={"field": "status", "rule": RULE, "key_results": n},
            )

    async def _krs_of(self, objective_id: uuid.UUID) -> list[KeyResult]:
        return list(await self.krs.where(KeyResult.objective_id == objective_id,
                                         order=KeyResult.created_at))  # fmt: skip

    async def create_objective(self, user: Principal, body: ObjectiveCreate) -> ObjectiveOut:
        data = body.model_dump()
        scope.require_self(user, data["owner_id"], field="owner_id")
        data["department_id"] = scope.pin_department(user, data["department_id"])
        if data["status"] == "active":
            await self._check_activation(user, None)
        await self.require_refs(data, RULE, parent_id=Objective)
        o = await self.objectives.create(**data, progress_pct=Decimal(0), source="MANUAL",
                                         created_by=user.user_id)  # fmt: skip
        await self.db.refresh(o)
        out = objective_out(o)
        await self.audit("objective_create", "objectives", o.id, after=out)
        return out

    async def update_objective(
        self, user: Principal, id_: uuid.UUID, body: ObjectiveUpdate, expected: int
    ) -> ObjectiveOut:
        o = await self.get_objective(user, id_, "write")
        before = objective_out(o)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _drop_nulls(data, "title", "owner_id", "period_key", "level", "okr_type", "weight_pct",
                    "status")  # fmt: skip
        scope.require_self(user, data.get("owner_id"), field="owner_id")
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        if data.get("status") == "active" and o.status != "active":
            await self._check_activation(user, o.id)
        if data.get("parent_id") == o.id:
            raise BusinessRuleError("objective cannot be its own parent",
                                    details={"field": "parent_id", "rule": RULE})  # fmt: skip
        await self.require_refs(data, RULE, parent_id=Objective)
        await self.objectives.update(o, expected_version=expected, updated_by=user.user_id,
                                     **data)  # fmt: skip
        await self.db.refresh(o)
        out = objective_out(o)
        await self.audit("objective_update", "objectives", o.id, before, out)
        return out

    async def delete_objective(self, user: Principal, id_: uuid.UUID) -> None:
        o = await self.get_objective(user, id_, "write")
        children = await self.objectives.where(Objective.parent_id == o.id)
        if await self._krs_of(o.id) or children:
            raise ConflictStateError("objective still has key results or children",
                                     details={"objective_id": str(o.id)})  # fmt: skip
        before = objective_out(o)
        o.updated_by = user.user_id
        await self.objectives.soft_delete(o)
        await self.audit("objective_delete", "objectives", o.id, before=before)

    async def recompute_progress(self, objective_id: uuid.UUID) -> None:
        o = await self.objectives.get(objective_id)
        if o is None:
            return
        pairs = [(kr_progress_pct(k.baseline, k.target, k.current_value), k.weight_pct)
                 for k in await self._krs_of(objective_id)]  # fmt: skip
        o.progress_pct = weighted_avg(pairs)
        await self.db.flush()

    # ---------- key results ----------
    async def list_krs(
        self, user: Principal, objective_id: uuid.UUID, page: PageParams
    ) -> tuple[list[KeyResultOut], int]:
        o = await self.get_objective(user, objective_id)
        items, total = await self.krs.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={"objective_id": o.id},
        )  # fmt: skip
        return [kr_out(k) for k in items], total

    async def get_kr(self, user: Principal, kr_id: uuid.UUID, action: str = "read") -> KeyResult:
        k = await self.krs.get(kr_id)
        if k is None:
            raise not_found("key result")
        o = await self.objectives.get(k.objective_id)
        dept = o.department_id if o is not None else None
        owners = (k.owner_id, o.owner_id if o is not None else None)
        scope.check(user, action, dept=dept, owners=owners, what="key result")
        return k

    async def create_kr(
        self, user: Principal, objective_id: uuid.UUID, body: KeyResultCreate
    ) -> KeyResultOut:
        o = await self.get_objective(user, objective_id, "write")
        data = body.model_dump()
        scope.require_self(user, data["owner_id"], field="owner_id")
        if len(await self._krs_of(o.id)) >= MAX_KR:
            raise BusinessRuleError(f"at most {MAX_KR} key results per objective",
                                    details={"field": "objective_id", "rule": RULE})  # fmt: skip
        k = await self.krs.create(**data, objective_id=o.id, source="MANUAL",
                                  created_by=user.user_id)  # fmt: skip
        await self.recompute_progress(o.id)
        await self.db.refresh(k)
        out = kr_out(k)
        await self.audit("key_result_create", "key_results", k.id, after=out)
        return out

    async def update_kr(
        self, user: Principal, objective_id: uuid.UUID, kr_id: uuid.UUID,
        body: KeyResultUpdate, expected: int,
    ) -> KeyResultOut:  # fmt: skip
        k = await self._kr_in(user, objective_id, kr_id)
        before = kr_out(k)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _drop_nulls(data, "title", "baseline", "target", "unit", "owner_id", "status",
                    "weight_pct")  # fmt: skip
        scope.require_self(user, data.get("owner_id"), field="owner_id")
        await self.krs.update(k, expected_version=expected, updated_by=user.user_id, **data)
        await self.recompute_progress(k.objective_id)
        await self.db.refresh(k)
        out = kr_out(k)
        await self.audit("key_result_update", "key_results", k.id, before, out)
        return out

    async def _kr_in(self, user: Principal, objective_id: uuid.UUID, kr_id: uuid.UUID) -> KeyResult:
        k = await self.get_kr(user, kr_id, "write")
        if k.objective_id != objective_id:
            raise not_found("key result")
        return k

    async def delete_kr(self, user: Principal, objective_id: uuid.UUID, kr_id: uuid.UUID) -> None:
        k = await self._kr_in(user, objective_id, kr_id)
        if await self.kpis.where(Kpi.key_result_id == k.id):
            raise ConflictStateError("key result still has KPIs",
                                     details={"key_result_id": str(k.id)})  # fmt: skip
        before = kr_out(k)
        k.updated_by = user.user_id
        await self.krs.soft_delete(k)
        await self.recompute_progress(k.objective_id)
        await self.audit("key_result_delete", "key_results", k.id, before=before)

    async def apply_check_in(self, k: KeyResult, value: Decimal, confidence: str) -> None:
        k.current_value = value
        k.confidence = confidence
        k.version = (k.version or 0) + 1
        await self.db.flush()
        await self.recompute_progress(k.objective_id)


def kr_scope_predicate(user: Principal) -> ColumnElement[bool] | None:
    """KRs visible to `user` (used by the check-in list)."""
    pred = scope.predicate(user, "read", dept=Objective.department_id,
                           own=[Objective.owner_id == user.user_id])  # fmt: skip
    if pred is None:
        return None
    return KeyResult.objective_id.in_(ObjectiveRepository.ids_where(pred)) | (
        KeyResult.owner_id == user.user_id
    )
