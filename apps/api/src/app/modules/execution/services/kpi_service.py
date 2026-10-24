"""EP-KPI-01..07 KPIs + measurements, EP-PRF-01..05 check-ins (10 §7.2.3; v2.1 EP-47/48).

- Measurement history (R-DEC-51): every measurement INSERTs a row; the period value is the
  latest row, scored into `KPIEvaluation` (upsert, `kpi_target_service`). Target = the
  `KPITarget` version in force on the measurement day (R-DEC-52), created from
  `kpis.target_value` with default bands when the period has none (DEC-147). A locked
  target/period → `409 CONFLICT_STATE` (corrections go through ApprovalRequest, DEC-163).
- Each measurement publishes `EVT-execution.kpi_measured` (05 §5.3, payload 10 §9.2).
- Check-in on a KR (objective must be `active`) writes `CheckIn` + `KRMeasurement` and updates
  `current_value` / `confidence` / `last_checked_in_at` + objective progress; on a KPI it records
  a measurement of the KPI's current period linked by `check_in_id` (EP-PRF-04). The target
  comes from the path (`/key-results/{id}/check-ins`, `/kpis/{id}/check-ins`, R-DEC-58).
- Undo (Action Registry v2, M1.5): `delete_measurement`, `delete_check_in` remove the
  append-only rows and re-score in the caller's transaction (no commit here).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.execution.models import (
    CheckIn,
    KeyResult,
    Kpi,
    KpiEvaluation,
    KpiMeasurement,
    KrMeasurement,
    Objective,
    Task,
)
from app.modules.execution.repositories import (
    CheckInRepository,
    KeyResultRepository,
    KpiEvaluationRepository,
    KpiRepository,
    KpiTargetRepository,
    KrMeasurementRepository,
    MeasurementRepository,
    ObjectiveRepository,
    TaskRepository,
)
from app.modules.execution.schemas.kpi import (
    KpiCreate,
    KpiOut,
    KpiUpdate,
    MeasurementCreate,
    MeasurementOut,
)
from app.modules.execution.schemas.okr import (
    CheckInCreate,
    CheckInOut,
    KrMeasurementBrief,
    KrMeasurementOut,
)
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, num, today
from app.modules.execution.services.kpi_rules import (
    achievement_pct,
    band,
    kr_progress_pct,
    local_day,
    period_bounds,
    period_key_for,
)
from app.modules.execution.services.kpi_target_service import (
    KpiTargetService,
    check_period,
    evaluation_brief,
)
from app.modules.execution.services.meeting_service import _c19
from app.modules.execution.services.okr_service import OkrService, kr_scope_predicate

RULE = "FR-KPI-01"


def kpi_out(k: Kpi, ev: KpiEvaluation | None = None) -> KpiOut:
    return KpiOut(
        **_c19(k), code=k.code, name=k.name, unit=k.unit, target=float(k.target_value),
        owner_id=k.owner_id, metric_code=k.metric_code, key_result_id=k.key_result_id,
        period_type=k.period_type, direction=k.direction, value_type=k.value_type,
        data_source_kind=k.data_source_kind, parent_kpi_id=k.parent_kpi_id,
        weight_pct=float(k.weight_pct), initiative_id=k.initiative_id,
        department_id=k.department_id, status=k.status,
        strategic_objective_id=k.strategic_objective_id, pillar=k.pillar,
        latest_evaluation=evaluation_brief(ev),
    )  # fmt: skip


def measurement_out(m: KpiMeasurement) -> MeasurementOut:
    return MeasurementOut(
        id=m.id, created_at=m.created_at, kpi_id=m.kpi_id, period_key=m.period_key,
        actual_value=float(m.actual_value), achievement_pct=float(m.achievement_pct),
        evaluation_band=m.evaluation_band, kpi_target_id=m.kpi_target_id,
        locked_at=m.locked_at, measured_at=m.measured_at,
        source_document_id=m.source_document_id, measured_by=m.measured_by,
        data_source=m.data_source, note=m.note, check_in_id=m.check_in_id,
    )  # fmt: skip


def check_in_out(
    c: CheckIn, *, title: str | None = None, department_id: uuid.UUID | None = None,
    krm: KrMeasurement | None = None,
) -> CheckInOut:  # fmt: skip
    brief = None if krm is None else KrMeasurementBrief(
        value=float(krm.value), progress_pct=float(krm.progress_pct),
        previous_progress_pct=num(krm.previous_progress_pct),
    )  # fmt: skip
    return CheckInOut(
        id=c.id, created_at=c.created_at, key_result_id=c.key_result_id, kpi_id=c.kpi_id,
        value=float(c.value), confidence=c.confidence, note=c.note, blocker=c.blocker,
        support_needed=c.support_needed, next_action=c.next_action,
        checked_in_at=c.checked_in_at, user_id=c.user_id,
        target_type="kpi" if c.kpi_id is not None else "key_result",
        target_title=title, department_id=department_id, kr_measurement=brief,
    )  # fmt: skip


class KpiService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.kpis = KpiRepository(db)
        self.targets = KpiTargetRepository(db)
        self.measurements = MeasurementRepository(db)
        self.check_ins = CheckInRepository(db)
        self.tasks = TaskRepository(db)
        self.kr_measurements = KrMeasurementRepository(db)
        self.krs = KeyResultRepository(db)
        self.objectives = ObjectiveRepository(db)
        self.target_svc = KpiTargetService(db)

    # ---------- KPIs ----------
    def _pred(self, user: Principal) -> ColumnElement[bool] | None:
        return scope.predicate(user, "read", dept=Kpi.department_id,
                               own=[Kpi.owner_id == user.user_id])  # fmt: skip

    async def list_kpis(
        self, user: Principal, page: PageParams, *, owner_id: uuid.UUID | None,
        metric_code: str | None, department_id: uuid.UUID | None = None,
        parent_kpi_id: uuid.UUID | None = None, strategic_objective_id: uuid.UUID | None = None,
        band: str | None = None,
    ) -> tuple[list[KpiOut], int]:  # fmt: skip
        pred = self._pred(user)
        where = [pred] if pred is not None else []
        if band is not None:  # band of the latest-period evaluation (EP-KPI-01)
            where.append(Kpi.id.in_(KpiEvaluationRepository.kpis_with_latest_band(band)))
        raw = {"owner_id": owner_id, "metric_code": metric_code, "department_id": department_id,
               "parent_kpi_id": parent_kpi_id,
               "strategic_objective_id": strategic_objective_id}  # fmt: skip
        filters = {k: v for k, v in raw.items() if v is not None}
        items, total = await self.kpis.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        latest = await self.target_svc.latest([k.id for k in items])
        return [kpi_out(k, latest.get(k.id)) for k in items], total

    async def out(self, k: Kpi) -> KpiOut:
        """KpiOut + `latest_evaluation` (EP-KPI-02..04)."""
        return kpi_out(k, (await self.target_svc.latest([k.id])).get(k.id))

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
        self.require_root_link(data, "parent_kpi_id", RULE)
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
        before = await self.out(k)
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
        self.require_root_link({"parent_kpi_id": k.parent_kpi_id,
                                "strategic_objective_id": k.strategic_objective_id, **data},
                               "parent_kpi_id", RULE)  # fmt: skip
        await self.require_refs(data, RULE, parent_kpi_id=Kpi)
        await self.kpis.update(k, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(k)
        out = await self.out(k)
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

    # ---------- measurements (R-DEC-51) ----------
    async def list_measurements(
        self, user: Principal, kpi_id: uuid.UUID, page: PageParams,
        period_key: str | None = None,
    ) -> tuple[list[MeasurementOut], int]:  # fmt: skip
        k = await self.get_kpi(user, kpi_id)
        filters: dict[str, Any] = {"kpi_id": k.id}
        if period_key is not None:
            filters["period_key"] = period_key
        items, total = await self.measurements.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [measurement_out(m) for m in items], total

    async def measure(
        self, user: Principal, kpi_id: uuid.UUID, body: MeasurementCreate, source: str = "MANUAL"
    ) -> MeasurementOut:
        """EP-KPI-07 / ACT-record_kpi_measurement (EMP: only their own KPI)."""
        k = await self.get_kpi(user, kpi_id, "write")
        return await self._measure(
            k, body.period_key, body.actual_value, user.user_id,
            source_document_id=body.source_document_id, data_source=body.data_source,
            note=body.note, source=source,
        )  # fmt: skip

    async def _measure(
        self, k: Kpi, period_key: str, actual: Decimal, user_id: uuid.UUID | None, *,
        source_document_id: uuid.UUID | None = None, data_source: str = "manual",
        note: str | None = None, check_in_id: uuid.UUID | None = None, source: str = "MANUAL",
    ) -> MeasurementOut:  # fmt: skip
        check_period(k.period_type, period_key)
        k = await self.target_svc.lock_kpi(k.id)
        at = now_utc()
        versions = list(await self.targets.versions(k.id, period_key))
        self.target_svc.require_open(versions, period_key)
        t = await self.target_svc.target_for(k, period_key, local_day(at), user_id)
        ach = achievement_pct(k.direction, actual, Decimal(t.target), minimum=t.minimum,
                              cap=Decimal(t.score_cap_pct))  # fmt: skip
        m = await self.measurements.create(
            kpi_id=k.id, period_key=period_key, actual_value=actual, achievement_pct=ach,
            evaluation_band=band(ach, t.band_thresholds), kpi_target_id=t.id, measured_at=at,
            source_document_id=source_document_id, measured_by=user_id, data_source=data_source,
            note=note, check_in_id=check_in_id,
        )  # fmt: skip
        await self.db.refresh(m)
        out = measurement_out(m)
        await self.audit("kpi_measure", "kpi_measurements", m.id, after=out)
        scored = await self.target_svc.evaluate(k, period_key, source=source)
        ev = scored.evaluation
        payload: dict[str, Any] = {
            "kpi_id": str(k.id), "period_key": period_key, "actual_value": str(actual),
            "achievement_pct": str(ach), "kpi_code": k.code, "measurement_id": str(m.id),
            "target": str(t.target), "band": m.evaluation_band,
            "previous_band": scored.previous_band,
            "department_id": str(k.department_id) if k.department_id else None,
            "data_source": data_source,
        }  # fmt: skip
        await publish_in_tx(
            self.db, event_type="execution.kpi_measured", producer="execution",
            aggregate_schema="execution", aggregate_table="kpis", aggregate_id=k.id,
            payload=payload,
        )  # fmt: skip
        if ev is not None:
            await self.after_evaluation(k, ev, scored.previous_band)
        return out

    async def after_evaluation(self, k: Kpi, ev: KpiEvaluation, previous_band: str | None) -> None:
        """Hook for band transitions (`execution.kpi_below_threshold`, T-629)."""
        return None

    async def delete_measurement(self, measurement_id: uuid.UUID) -> None:
        """Undo of ACT-record_kpi_measurement (Action Registry v2, M1.5): remove the row and
        re-score the period in the caller's transaction. Locked period → 409."""
        m = await self.measurements.get(measurement_id)
        if m is None:
            raise not_found("KPI measurement")
        k = await self.target_svc.lock_kpi(m.kpi_id)
        self.target_svc.require_open(list(await self.targets.versions(k.id, m.period_key)),
                                     m.period_key)  # fmt: skip
        if m.locked_at is not None:
            raise ConflictStateError("measurement is locked", details={"period_key": m.period_key})
        before = measurement_out(m)
        await self.target_svc.evaluate(k, m.period_key, exclude=m.id)  # re-point first (FK)
        await self.measurements.remove(m)
        await self.audit("kpi_measure_delete", "kpi_measurements", m.id, before=before)

    async def list_kr_measurements(
        self, kr_id: uuid.UUID, page: PageParams
    ) -> tuple[list[KrMeasurementOut], int]:
        """EP-OKR-11 — caller checked the KR scope; default sort `measured_at` desc."""
        sort_by = "measured_at" if page.sort_by == "created_at" else page.sort_by
        items, total = await self.kr_measurements.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort_by, order=page.order,
            filters={"key_result_id": kr_id},
        )  # fmt: skip
        return [KrMeasurementOut.model_validate(m) for m in items], total

    # ---------- check-ins ----------
    async def list_check_ins(
        self, user: Principal, page: PageParams, *, owner_id: uuid.UUID | None,
        period_key: str | None, kpi_id: uuid.UUID | None, key_result_id: uuid.UUID | None,
        department_id: uuid.UUID | None = None, from_: datetime | None = None,
        to: datetime | None = None, confidence: str | None = None,
    ) -> tuple[list[CheckInOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        if department_id is not None:  # target's department (KPI / KR's objective)
            objs = ObjectiveRepository.ids_where(Objective.department_id == department_id)
            where.append(or_(
                CheckIn.kpi_id.in_(KpiRepository.ids_where(Kpi.department_id == department_id)),
                CheckIn.key_result_id.in_(KeyResultRepository.ids_where(
                    KeyResult.objective_id.in_(objs))),
            ))  # fmt: skip
        if from_ is not None:
            where.append(CheckIn.checked_in_at >= from_)
        if to is not None:
            where.append(CheckIn.checked_in_at < to)
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
        raw = {"user_id": owner_id, "kpi_id": kpi_id, "key_result_id": key_result_id,
               "confidence": confidence}  # fmt: skip
        filters = {k: v for k, v in raw.items() if v is not None}
        sort_by = "checked_in_at" if page.sort_by == "created_at" else page.sort_by  # EP-PRF-01
        items, total = await self.check_ins.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return await self._outs(list(items)), total

    async def _outs(self, rows: list[CheckIn]) -> list[CheckInOut]:
        """CheckInOut + `target_title`, `department_id` (EP-PRF-05), `kr_measurement`."""
        kpi_ids = {c.kpi_id for c in rows if c.kpi_id is not None}
        kr_ids = {c.key_result_id for c in rows if c.key_result_id is not None}
        kpis = {k.id: k for k in await self.kpis.where(Kpi.id.in_(kpi_ids))} if kpi_ids else {}
        krs = {k.id: k for k in await self.krs.where(KeyResult.id.in_(kr_ids))} if kr_ids else {}
        obj_ids = {k.objective_id for k in krs.values()}
        objs = ({o.id: o for o in await self.objectives.where(Objective.id.in_(obj_ids))}
                if obj_ids else {})  # fmt: skip
        krms = await self.kr_measurements.by_check_ins([c.id for c in rows if c.key_result_id])
        out: list[CheckInOut] = []
        for c in rows:
            if c.kpi_id is not None:
                k = kpis.get(c.kpi_id)
                title, dept = (k.name, k.department_id) if k else (None, None)
            else:
                kr = krs.get(c.key_result_id) if c.key_result_id else None
                o = objs.get(kr.objective_id) if kr else None
                title, dept = (kr.title if kr else None), (o.department_id if o else None)
            out.append(check_in_out(c, title=title, department_id=dept, krm=krms.get(c.id)))
        return out

    async def check_in_kr(
        self, user: Principal, kr_id: uuid.UUID, body: CheckInCreate
    ) -> CheckInOut:
        """EP-PRF-02 — one transaction: CheckIn + KRMeasurement + KR `current_value` /
        `confidence` / `last_checked_in_at` + objective progress (R-DEC-53)."""
        okr = OkrService(self.db)
        kr = await okr.get_kr(user, kr_id, "write")
        o = await self.objectives.get(kr.objective_id)
        if o is None or o.status != "active":
            raise ConflictStateError("objective is not active",
                                     details={"reason": "objective_not_active",
                                              "objective_id": str(kr.objective_id)})  # fmt: skip
        prev = await self.kr_measurements.latest(kr.id)
        c = await self._new_check_in(user, body, key_result_id=kr.id)
        krm = await self.kr_measurements.create(
            key_result_id=kr.id, check_in_id=c.id, period_key=o.period_key, value=body.value,
            progress_pct=kr_progress_pct(kr.baseline, kr.target, body.value),
            previous_progress_pct=prev.progress_pct if prev is not None else None,
            confidence=body.confidence, measured_at=c.checked_in_at, measured_by=user.user_id,
        )  # fmt: skip
        await okr.apply_check_in(kr, body.value, body.confidence, c.checked_in_at)
        out = check_in_out(c, title=kr.title, department_id=o.department_id, krm=krm)
        await self.audit("check_in_create", "check_ins", c.id, after=out)
        return out

    async def check_in_kpi(
        self, user: Principal, kpi_id: uuid.UUID, body: CheckInCreate
    ) -> CheckInOut:
        """EP-PRF-04 — CheckIn + measurement of the KPI's current period (`check_in_id`)."""
        k = await self.get_kpi(user, kpi_id, "write")
        period_key = period_key_for(k.period_type, today())
        k = await self.target_svc.lock_kpi(k.id)  # validate before any write
        self.target_svc.require_open(list(await self.targets.versions(k.id, period_key)),
                                     period_key)  # fmt: skip
        c = await self._new_check_in(user, body, kpi_id=k.id)
        await self._measure(k, period_key, body.value, user.user_id, note=body.note,
                            check_in_id=c.id)  # fmt: skip
        out = check_in_out(c, title=k.name, department_id=k.department_id)
        await self.audit("check_in_create", "check_ins", c.id, after=out)
        return out

    async def _new_check_in(
        self, user: Principal, body: CheckInCreate, **target: uuid.UUID
    ) -> CheckIn:
        c = await self.check_ins.create(**body.model_dump(), **target, checked_in_at=now_utc(),
                                        user_id=user.user_id)  # fmt: skip
        await self.db.refresh(c)
        return c

    async def delete_check_in(self, check_in_id: uuid.UUID) -> None:
        """Undo of ACT-record_kr_checkin (Action Registry v2, M1.5), caller's transaction.

        KR: remove its KRMeasurement + the check-in; KR `current_value` / `confidence` /
        `last_checked_in_at` go back to the previous measurement (none → value/confidence kept,
        `last_checked_in_at` NULL — the ACT snapshot restores the rest) + objective progress.
        KPI: remove the linked measurements (re-scored) + the check-in."""
        c = await self.check_ins.get(check_in_id)
        if c is None:
            raise not_found("check-in")
        before = check_in_out(c)
        for m in await self.measurements.for_check_in(c.id):
            await self.delete_measurement(m.id)
        if c.key_result_id is not None:
            krm = (await self.kr_measurements.by_check_ins([c.id])).get(c.id)
            kr = await self.krs.get(c.key_result_id)
            if krm is not None:
                await self.kr_measurements.remove(krm)
            if kr is not None:
                prev = await self.kr_measurements.latest(kr.id)
                okr = OkrService(self.db)
                if prev is not None:
                    await okr.apply_check_in(kr, Decimal(prev.value), prev.confidence,
                                             prev.measured_at)  # fmt: skip
                else:
                    await okr.apply_check_in(kr, kr.current_value, kr.confidence, None)
        await self.check_ins.remove(c)
        await self.audit("check_in_delete", "check_ins", c.id, before=before)
