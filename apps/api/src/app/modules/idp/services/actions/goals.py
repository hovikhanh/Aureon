"""ACT-upsert_objective / _key_result / _kpi / _kpi_target, ACT-record_kpi_measurement /
_kr_checkin → `execution` public services (10 §7.2.4, doc #2 PLAN_KPI_OKR / #3 PERIOD_REPORT).

Upserts keep a `snapshot` of the fields they overwrite (undo = update back to it; created rows
are deleted). `owner_code` = `employee_code` resolved through `hr` (soft ref, 05 C7).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.execution.schemas.common import ObjectiveLevel
from app.modules.execution.schemas.kpi import (
    KpiCreate,
    KpiTargetCreate,
    KpiUpdate,
    MeasurementCreate,
)
from app.modules.execution.schemas.okr import (
    CheckInCreate,
    KeyResultCreate,
    KeyResultUpdate,
    ObjectiveCreate,
    ObjectiveUpdate,
)
from app.modules.execution.services.kpi_rules import period_bounds
from app.modules.execution.services.kpi_service import KpiService
from app.modules.execution.services.kpi_target_service import KpiTargetService
from app.modules.execution.services.okr_service import OkrService, kr_out
from app.modules.hr.services.hr_service import HrService
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)

_WRITE = ("execution:write",)
PERIOD = r"^\d{4}(-(0[1-9]|1[0-2]|Q[1-4]|H[12]))?$"


def _err(field: str, code: str, message: str) -> RowError:
    return {"field": field, "code": code, "message": message}


async def _owner(db: AsyncSession, ctx: ActionContext, code: str) -> uuid.UUID | None:
    return ctx.recall("employee", code) or await HrService(db).employee_id_by_code(code)


async def _need_owner(db: AsyncSession, ctx: ActionContext, code: str) -> list[RowError]:
    if ctx.is_planned("employee", code) or await _owner(db, ctx, code) is not None:
        return []
    return [_err("owner_code", "not_found", f"employee {code} not found")]


def _id(outcome: ActionOutcome) -> uuid.UUID:
    return uuid.UUID(outcome.result_refs[0]["id"])


def _created(outcome: ActionOutcome) -> bool:
    return outcome.snapshot is None or outcome.snapshot.get("created", False)


def _dump(out: BaseModel, keys: tuple[str, ...]) -> dict[str, Any]:
    data = out.model_dump(mode="json")
    return {"created": False, **{k: data[k] for k in keys}}


async def _noop_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return []


# ---------------------------------------------------------------- objective
class ObjectiveParams(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    period_key: str = Field(pattern=PERIOD)
    level: ObjectiveLevel = "company"
    owner_code: str = Field(min_length=1, max_length=50)
    parent_title: str | None = Field(default=None, max_length=500)


_OBJ_KEYS = ("level", "parent_id")


async def _obj_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors = await _need_owner(db, ctx, p.owner_code)
    if p.parent_title and not (
        ctx.is_planned("objective", p.parent_title)
        or await OkrService(db).objective_id_by_key(p.period_key, p.parent_title)
    ):
        errors.append(_err("parent_title", "not_found", "parent objective not found"))
    ctx.plan("objective", p.title)
    return errors


async def _obj_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    svc = OkrService(db)
    owner = await _owner(db, ctx, p.owner_code)
    if owner is None:
        raise NotFoundError("owner not found", details={"field": "owner_code"})
    parent = None
    if p.parent_title:
        parent = ctx.recall("objective", p.parent_title) or await svc.objective_id_by_key(
            p.period_key, p.parent_title
        )
    existing = await svc.objective_id_by_key(p.period_key, p.title, owner)
    if existing is not None:
        o = await svc.get_objective(user, existing, "write")
        snap = _dump(await svc.out(o), _OBJ_KEYS)
        out = await svc.update_objective(
            user, existing, ObjectiveUpdate(level=p.level, parent_id=parent), int(o.version)
        )
    else:
        snap = None
        out = await svc.create_objective(user, ObjectiveCreate(
            title=p.title, owner_id=owner, period_key=p.period_key, level=p.level,
            parent_id=parent, source_document_id=ctx.source_document_id,
        ), source=ctx.source)  # fmt: skip
    ctx.remember("objective", p.title, out.id)
    return ActionOutcome([ref("execution", "objectives", out.id)], snap, out.version)


async def _obj_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    svc, id_ = OkrService(db), _id(outcome)
    if _created(outcome):
        await svc.delete_objective(user, id_)
        return
    o = await svc.get_objective(user, id_, "write")
    snap = {k: v for k, v in (outcome.snapshot or {}).items() if k in _OBJ_KEYS}
    await svc.update_objective(user, id_, ObjectiveUpdate(**snap), int(o.version))


register(ActionDef(
    name="ACT-upsert_objective", module="execution", required_permission=_WRITE,
    reversible=True, is_finance=False, params_model=ObjectiveParams, validate=_obj_validate,
    run=_obj_run, undo=_obj_undo,
))  # fmt: skip


# ---------------------------------------------------------------- key result
class KeyResultParams(BaseModel):
    objective_title: str = Field(min_length=1, max_length=500)
    period_key: str = Field(pattern=PERIOD)
    title: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=50)
    baseline: Decimal
    target: Decimal
    owner_code: str = Field(min_length=1, max_length=50)


_KR_KEYS = ("unit", "baseline", "target", "owner_id")


async def _objective_for(db: AsyncSession, ctx: ActionContext, p: Any) -> uuid.UUID | None:
    return ctx.recall("objective", p.objective_title) or await OkrService(db).objective_id_by_key(
        p.period_key, p.objective_title
    )


async def _kr_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors = await _need_owner(db, ctx, p.owner_code)
    if not ctx.is_planned("objective", p.objective_title) and not await _objective_for(db, ctx, p):
        errors.append(_err("objective_title", "not_found", "objective not found"))
    ctx.plan("key_result", f"{p.objective_title}/{p.title}")
    return errors


async def _kr_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    svc = OkrService(db)
    obj, owner = await _objective_for(db, ctx, p), await _owner(db, ctx, p.owner_code)
    if obj is None or owner is None:
        raise NotFoundError("objective/owner not found", details={"field": "objective_title"})
    existing = await svc.kr_id_by_title(obj, p.title)
    fields = {"unit": p.unit, "baseline": p.baseline, "target": p.target, "owner_id": owner}
    if existing is not None:
        k = await svc.get_kr(user, existing, "write")
        snap = _dump(kr_out(k), _KR_KEYS)
        out = await svc.update_kr(user, existing, KeyResultUpdate(**fields), int(k.version))
    else:
        snap = None
        out = await svc.create_kr(user, obj, KeyResultCreate(title=p.title, **fields),
                                  source=ctx.source)  # fmt: skip
    ctx.remember("key_result", f"{p.objective_title}/{p.title}", out.id)
    return ActionOutcome([ref("execution", "key_results", out.id)], snap, out.version)


async def _kr_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    svc, id_ = OkrService(db), _id(outcome)
    if _created(outcome):
        await svc.delete_kr(user, id_)
        return
    k = await svc.get_kr(user, id_, "write")
    snap = {k_: v for k_, v in (outcome.snapshot or {}).items() if k_ in _KR_KEYS}
    await svc.update_kr(user, id_, KeyResultUpdate(**snap), int(k.version))


register(ActionDef(
    name="ACT-upsert_key_result", module="execution", required_permission=_WRITE,
    reversible=True, is_finance=False, params_model=KeyResultParams, validate=_kr_validate,
    run=_kr_run, undo=_kr_undo,
))  # fmt: skip


# ---------------------------------------------------------------- KPI
class KpiParams(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=50)
    target: Decimal  # `KpiCreate.target` is required by the target service
    period_type: Literal["MONTH", "QUARTER", "YEAR", "ROLLING_12M"] = "MONTH"
    direction: Literal["HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE",
                       "BINARY"] = "HIGHER_IS_BETTER"  # fmt: skip
    owner_code: str = Field(min_length=1, max_length=50)
    department_code: str | None = Field(default=None, max_length=50)


_KPI_KEYS = ("name", "unit", "target", "direction", "owner_id", "department_id")


async def _department(db: AsyncSession, ctx: ActionContext, code: str) -> uuid.UUID | None:
    return ctx.recall("department", code) or await HrService(db).department_id_by_code(code)


async def _kpi_id(db: AsyncSession, ctx: ActionContext, code: str) -> uuid.UUID | None:
    return ctx.recall("kpi", code) or await KpiService(db).kpi_id_by_code(code)


async def _kpi_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    errors = await _need_owner(db, ctx, p.owner_code)
    if (
        p.department_code
        and await _department(db, ctx, p.department_code) is None
        and not (ctx.is_planned("department", p.department_code))
    ):
        errors.append(_err("department_code", "not_found", "department not found"))
    ctx.plan("kpi", p.code)
    return errors


async def _kpi_run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    svc = KpiService(db)
    owner = await _owner(db, ctx, p.owner_code)
    if owner is None:
        raise NotFoundError("owner not found", details={"field": "owner_code"})
    dept = await _department(db, ctx, p.department_code) if p.department_code else None
    fields = {"name": p.name, "unit": p.unit, "target": p.target, "direction": p.direction,
              "owner_id": owner, "department_id": dept}  # fmt: skip
    existing = await svc.kpi_id_by_code(p.code)
    if existing is not None:  # `code` → update, snapshot of the overwritten values
        k = await svc.get_kpi(user, existing, "write")
        snap = _dump(await svc.out(k), _KPI_KEYS)
        out = await svc.update_kpi(user, existing, KpiUpdate(**fields), int(k.version))
    else:
        snap = None
        out = await svc.create_kpi(user, KpiCreate(code=p.code, period_type=p.period_type,
                                                   **fields), source=ctx.source)  # fmt: skip
    ctx.remember("kpi", p.code, out.id)
    return ActionOutcome([ref("execution", "kpis", out.id)], snap, out.version)


async def _kpi_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    svc, id_ = KpiService(db), _id(outcome)
    if _created(outcome):
        await svc.delete_kpi(user, id_)
        return
    k = await svc.get_kpi(user, id_, "write")
    snap = {k_: v for k_, v in (outcome.snapshot or {}).items() if k_ in _KPI_KEYS}
    await svc.update_kpi(user, id_, KpiUpdate(**snap), int(k.version))


register(ActionDef(
    name="ACT-upsert_kpi", module="execution", required_permission=_WRITE, reversible=True,
    is_finance=False, params_model=KpiParams, validate=_kpi_validate, run=_kpi_run,
    undo=_kpi_undo,
))  # fmt: skip


async def _need_kpi(db: AsyncSession, ctx: ActionContext, code: str) -> list[RowError]:
    if ctx.is_planned("kpi", code) or await _kpi_id(db, ctx, code) is not None:
        return []
    return [_err("kpi_code", "not_found", f"KPI {code} not found")]


async def _scoped_kpi(db: AsyncSession, user: Principal, ctx: ActionContext,
                      code: str) -> uuid.UUID:  # fmt: skip
    kpi = await _kpi_id(db, ctx, code)
    if kpi is None:
        raise NotFoundError("KPI not found", details={"field": "kpi_code"})
    await KpiService(db).get_kpi(user, kpi, "write")  # scope, as EP-KPI-09
    return kpi


# ---------------------------------------------------------------- KPI target
class KpiTargetParams(BaseModel):
    kpi_code: str = Field(min_length=1, max_length=50)
    period_key: str = Field(pattern=PERIOD)
    target: Decimal
    baseline: Decimal | None = None
    stretch: Decimal | None = None


async def _target_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return await _need_kpi(db, ctx, p.kpi_code)


async def _target_run(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> ActionOutcome:
    kpi = await _scoped_kpi(db, user, ctx, p.kpi_code)
    start, end = period_bounds(p.period_key)
    now = business_today()  # a plan sets future/past periods → effective from the period start
    valid_from = now if start <= now < end else start
    body = KpiTargetCreate(period_key=p.period_key, target=p.target, baseline=p.baseline,
                           stretch=p.stretch, valid_from=valid_from)  # fmt: skip
    # locked period → 409 CONFLICT_STATE from the service (`locked_at`, R-DEC-52)
    out = await KpiTargetService(db).upsert(kpi, body, user.user_id, source=ctx.source)
    return ActionOutcome([ref("execution", "kpi_targets", out.id)], None, out.version)


async def _target_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await KpiTargetService(db).revert(_id(outcome), user.user_id)


register(ActionDef(
    name="ACT-upsert_kpi_target", module="execution", required_permission=_WRITE,
    reversible=True, is_finance=False, params_model=KpiTargetParams,
    validate=_target_validate, run=_target_run, undo=_target_undo,
))  # fmt: skip


# ---------------------------------------------------------------- KPI measurement
class MeasurementParams(BaseModel):
    kpi_code: str = Field(min_length=1, max_length=50)
    period_key: str = Field(pattern=PERIOD)
    actual_value: Decimal


async def _measure_run(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> ActionOutcome:
    kpi = await _kpi_id(db, ctx, p.kpi_code)
    if kpi is None:
        raise NotFoundError("KPI not found", details={"field": "kpi_code"})
    body = MeasurementCreate(period_key=p.period_key, actual_value=p.actual_value,
                             source_document_id=ctx.source_document_id,
                             data_source="document")  # fmt: skip
    out = await KpiService(db).measure(user, kpi, body, source=ctx.source)
    return ActionOutcome([ref("execution", "kpi_measurements", out.id)])


async def _measure_validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    return await _need_kpi(db, ctx, p.kpi_code)


async def _measure_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await KpiService(db).delete_measurement(_id(outcome))


register(ActionDef(
    name="ACT-record_kpi_measurement", module="execution", required_permission=_WRITE,
    reversible=True, is_finance=False, params_model=MeasurementParams,
    validate=_measure_validate, run=_measure_run, undo=_measure_undo,
))  # fmt: skip


# ---------------------------------------------------------------- KR check-in
class KrCheckInParams(BaseModel):
    kr_ref: uuid.UUID
    value: Decimal
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    note: str | None = Field(default=None, max_length=5000)


async def _checkin_run(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> ActionOutcome:
    body = CheckInCreate(value=p.value, confidence=p.confidence, note=p.note)
    out = await KpiService(db).check_in_kr(user, p.kr_ref, body)  # → apply_check_in
    return ActionOutcome([ref("execution", "check_ins", out.id)])


async def _checkin_undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await KpiService(db).delete_check_in(_id(outcome))  # + recompute_progress


register(ActionDef(
    name="ACT-record_kr_checkin", module="execution", required_permission=_WRITE,
    reversible=True, is_finance=False, params_model=KrCheckInParams,
    validate=_noop_validate, run=_checkin_run, undo=_checkin_undo,
))  # fmt: skip
