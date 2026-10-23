"""EP-47 KPIs + measurements, EP-48 check-ins (T-132, T-133).

- Measurement of `(kpi, period_key)`: target = `KPITarget` of that period, created on first
  measurement from `kpis.target_value` with default bands (DEC-147, DEC-224); achievement +
  5-level band from `kpi_rules`. One row per period (DEC-163 unique): a re-measure of an
  unlocked period updates the row in place (append-only = no delete); a locked target/period
  → `409 CONFLICT_STATE` (corrections go through ApprovalRequest, DEC-163).
- Each measurement publishes `EVT-execution.kpi_measured`
  `{kpi_id, period_key, actual_value, achievement_pct}` (05 §5.3).
- Check-in on a KR updates `current_value` / `confidence` + objective progress; on a KPI it
  records a measurement of the KPI's current period (EP-48 → `kpi_measured`).
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.execution.models import CheckIn, Kpi, KpiMeasurement, KpiTarget, Task
from app.modules.execution.repositories import (
    CheckInRepository,
    KeyResultRepository,
    KpiRepository,
    KpiTargetRepository,
    MeasurementRepository,
    TaskRepository,
)
from app.modules.execution.schemas.okr import (
    CheckInCreate,
    CheckInOut,
    KpiCreate,
    KpiOut,
    KpiUpdate,
    MeasurementCreate,
    MeasurementOut,
)
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, today
from app.modules.execution.services.kpi_rules import (
    DEFAULT_BANDS,
    achievement_pct,
    band,
    period_bounds,
    period_key_for,
)
from app.modules.execution.services.meeting_service import _c19
from app.modules.execution.services.okr_service import OkrService, kr_scope_predicate

RULE = "FR-KPI-01"


def kpi_out(k: Kpi) -> KpiOut:
    return KpiOut(
        **_c19(k), code=k.code, name=k.name, unit=k.unit, target=float(k.target_value),
        owner_id=k.owner_id, metric_code=k.metric_code, key_result_id=k.key_result_id,
        period_type=k.period_type, direction=k.direction, value_type=k.value_type,
        data_source_kind=k.data_source_kind, parent_kpi_id=k.parent_kpi_id,
        weight_pct=float(k.weight_pct), initiative_id=k.initiative_id,
        department_id=k.department_id, status=k.status,
    )  # fmt: skip


def measurement_out(m: KpiMeasurement) -> MeasurementOut:
    return MeasurementOut(
        id=m.id, created_at=m.created_at, kpi_id=m.kpi_id, period_key=m.period_key,
        actual_value=float(m.actual_value), achievement_pct=float(m.achievement_pct),
        evaluation_band=m.evaluation_band, kpi_target_id=m.kpi_target_id,
        locked_at=m.locked_at, measured_at=m.measured_at,
        source_document_id=m.source_document_id,
    )  # fmt: skip


def check_in_out(c: CheckIn) -> CheckInOut:
    return CheckInOut(
        id=c.id, created_at=c.created_at, key_result_id=c.key_result_id, kpi_id=c.kpi_id,
        value=float(c.value), confidence=c.confidence, note=c.note, blocker=c.blocker,
        support_needed=c.support_needed, next_action=c.next_action,
        checked_in_at=c.checked_in_at, user_id=c.user_id,
    )  # fmt: skip


def _check_period(period_type: str, period_key: str) -> None:
    start, _ = period_bounds(period_key)
    if period_key_for(period_type, start) != period_key:
        raise BusinessRuleError(
            f"period_key {period_key} does not match KPI period_type {period_type}",
            details={"field": "period_key", "rule": RULE},
        )


class KpiService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.kpis = KpiRepository(db)
        self.targets = KpiTargetRepository(db)
        self.measurements = MeasurementRepository(db)
        self.check_ins = CheckInRepository(db)
        self.tasks = TaskRepository(db)

    # ---------- KPIs ----------
    def _pred(self, user: Principal) -> ColumnElement[bool] | None:
        return scope.predicate(user, "read", dept=Kpi.department_id,
                               own=[Kpi.owner_id == user.user_id])  # fmt: skip

    async def list_kpis(
        self, user: Principal, page: PageParams, *, owner_id: uuid.UUID | None,
        metric_code: str | None,
    ) -> tuple[list[KpiOut], int]:  # fmt: skip
        pred = self._pred(user)
        filters = {k: v for k, v in {"owner_id": owner_id, "metric_code": metric_code}.items()
                   if v is not None}  # fmt: skip
        items, total = await self.kpis.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=[pred] if pred is not None else [],
        )  # fmt: skip
        return [kpi_out(k) for k in items], total

    async def get_kpi(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Kpi:
        k = await self.kpis.get(id_)
        if k is None:
            raise not_found("KPI")
        scope.check(user, action, dept=k.department_id, owners=(k.owner_id,), what="KPI")
        return k

    async def create_kpi(self, user: Principal, body: KpiCreate) -> KpiOut:
        data = body.model_dump()
        data["target_value"] = data.pop("target")
        scope.require_self(user, data["owner_id"], field="owner_id")
        data["department_id"] = scope.pin_department(user, data["department_id"])
        await self.require_unique(Kpi, "code", data["code"], None)
        await self.require_refs(data, RULE, parent_kpi_id=Kpi)
        k = await self.kpis.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(k)
        out = kpi_out(k)
        await self.audit("kpi_create", "kpis", k.id, after=out)
        return out

    async def update_kpi(
        self, user: Principal, id_: uuid.UUID, body: KpiUpdate, expected: int
    ) -> KpiOut:
        k = await self.get_kpi(user, id_, "write")
        before = kpi_out(k)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "target" in data:
            data["target_value"] = data.pop("target")
        for key in ("name", "unit", "target_value", "owner_id", "direction", "value_type",
                    "data_source_kind", "weight_pct", "status"):  # fmt: skip
            if key in data and data[key] is None:
                del data[key]
        scope.require_self(user, data.get("owner_id"), field="owner_id")
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        if data.get("parent_kpi_id") == k.id:
            raise BusinessRuleError("KPI cannot be its own parent",
                                    details={"field": "parent_kpi_id", "rule": RULE})  # fmt: skip
        await self.require_refs(data, RULE, parent_kpi_id=Kpi)
        await self.kpis.update(k, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(k)
        out = kpi_out(k)
        await self.audit("kpi_update", "kpis", k.id, before, out)
        return out

    async def delete_kpi(self, user: Principal, id_: uuid.UUID) -> None:
        k = await self.get_kpi(user, id_, "write")
        children = await self.kpis.where(Kpi.parent_kpi_id == k.id)
        if children or await self.tasks.where(Task.kpi_id == k.id):
            raise ConflictStateError("KPI still has child KPIs or tasks",
                                     details={"kpi_id": str(k.id)})  # fmt: skip
        before = kpi_out(k)
        k.updated_by = user.user_id
        await self.kpis.soft_delete(k)
        await self.audit("kpi_delete", "kpis", k.id, before=before)

    # ---------- measurements ----------
    async def list_measurements(
        self, user: Principal, kpi_id: uuid.UUID, page: PageParams
    ) -> tuple[list[MeasurementOut], int]:
        k = await self.get_kpi(user, kpi_id)
        items, total = await self.measurements.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={"kpi_id": k.id},
        )  # fmt: skip
        return [measurement_out(m) for m in items], total

    async def _target(self, k: Kpi, period_key: str, user_id: uuid.UUID | None) -> KpiTarget:
        t = await self.targets.find(k.id, period_key)
        if t is None:
            t = await self.targets.create(
                kpi_id=k.id, period_key=period_key, target=k.target_value,
                band_thresholds=dict(DEFAULT_BANDS), source="MANUAL", created_by=user_id,
            )  # fmt: skip
            await self.db.refresh(t)
        return t

    async def measure(
        self, user: Principal, kpi_id: uuid.UUID, body: MeasurementCreate
    ) -> MeasurementOut:
        k = await self.get_kpi(user, kpi_id, "write")
        return await self._measure(k, body.period_key, body.actual_value, user.user_id,
                                   body.source_document_id)  # fmt: skip

    async def _measure(
        self, k: Kpi, period_key: str, actual: Decimal, user_id: uuid.UUID | None,
        source_document_id: uuid.UUID | None = None,
    ) -> MeasurementOut:  # fmt: skip
        try:
            _check_period(k.period_type, period_key)
        except ValueError as exc:
            raise BusinessRuleError(
                str(exc), details={"field": "period_key", "rule": RULE}
            ) from exc
        t = await self._target(k, period_key, user_id)
        if t.locked_at is not None:
            raise ConflictStateError("KPI period is locked", details={"period_key": period_key})
        ach = achievement_pct(k.direction, actual, Decimal(t.target), minimum=t.minimum,
                              cap=Decimal(t.score_cap_pct))  # fmt: skip
        values: dict[str, Any] = {
            "actual_value": actual, "achievement_pct": ach, "kpi_target_id": t.id,
            "evaluation_band": band(ach, t.band_thresholds), "measured_at": now_utc(),
            "source_document_id": source_document_id,
        }  # fmt: skip
        m = await self.measurements.find(k.id, period_key)
        if m is not None and m.locked_at is not None:
            raise ConflictStateError("measurement is locked", details={"period_key": period_key})
        before = measurement_out(m) if m is not None else None
        if m is None:
            m = await self.measurements.create(kpi_id=k.id, period_key=period_key, **values)
        else:
            await self.measurements.update(m, **values)
        await self.db.refresh(m)
        out = measurement_out(m)
        await self.audit("kpi_measure", "kpi_measurements", m.id, before, out)
        await publish_in_tx(
            self.db, event_type="execution.kpi_measured", producer="execution",
            aggregate_schema="execution", aggregate_table="kpis", aggregate_id=k.id,
            payload={"kpi_id": str(k.id), "period_key": period_key,
                     "actual_value": str(actual), "achievement_pct": str(ach)},
        )  # fmt: skip
        return out

    # ---------- check-ins ----------
    async def list_check_ins(
        self, user: Principal, page: PageParams, *, owner_id: uuid.UUID | None,
        period_key: str | None, kpi_id: uuid.UUID | None, key_result_id: uuid.UUID | None,
    ) -> tuple[list[CheckInOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        if scope.level(user) != "all":
            kp = self._pred(user)
            kpi_ids = KpiRepository.ids_where(*([kp] if kp is not None else []))
            kr_pred = kr_scope_predicate(user)
            parts = [CheckIn.kpi_id.in_(kpi_ids), CheckIn.user_id == user.user_id]
            if kr_pred is not None:
                parts.append(CheckIn.key_result_id.in_(KeyResultRepository.ids_where(kr_pred)))
            where.append(or_(*parts))
        if period_key is not None:
            try:
                start, end = period_bounds(period_key)
            except ValueError as exc:
                raise BusinessRuleError(str(exc), details={"field": "period_key"}) from exc
            where += [CheckIn.checked_in_at >= start, CheckIn.checked_in_at < end]
        raw = {"user_id": owner_id, "kpi_id": kpi_id, "key_result_id": key_result_id}
        filters = {k: v for k, v in raw.items() if v is not None}
        items, total = await self.check_ins.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [check_in_out(c) for c in items], total

    async def check_in(self, user: Principal, body: CheckInCreate) -> CheckInOut:
        at = now_utc()
        if body.kpi_id is None:  # schema guarantees exactly one target
            okr = OkrService(self.db)
            kr = await okr.get_kr(user, body.key_result_id or uuid.UUID(int=0), "write")
            await okr.apply_check_in(kr, body.value, body.confidence)
        else:
            k = await self.get_kpi(user, body.kpi_id, "write")
            key = period_key_for(k.period_type, today())
            await self._measure(k, key, body.value, user.user_id)
        c = await self.check_ins.create(**body.model_dump(), checked_in_at=at, user_id=user.user_id)
        await self.db.refresh(c)
        out = check_in_out(c)
        await self.audit("check_in_create", "check_ins", c.id, after=out)
        return out
