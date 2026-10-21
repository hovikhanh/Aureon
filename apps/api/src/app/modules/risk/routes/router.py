"""HTTP routes for `risk` — EP-100..106 (10 §3.10, §4).

One permission per route, `Idem` on create / action POSTs, `IfMatch` + body `version` on
PATCH, `Page` on lists, commit at the end of the request (same pattern as sales/finance).
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.risk.schemas import (
    AcceptIn,
    AssessmentIn,
    AssessmentOut,
    Category,
    Level,
    MitigationCreate,
    MitigationOut,
    MitigationStatus,
    MitigationUpdate,
    RiskCreate,
    RiskDashboardOut,
    RiskOut,
    RiskSource,
    RiskStatus,
    RiskUpdate,
    ScenarioIn,
    ScenarioOut,
    StatusChange,
)
from app.modules.risk.services.dashboard_service import RiskDashboardService
from app.modules.risk.services.lifecycle_service import RiskLifecycleService
from app.modules.risk.services.mitigation_service import MitigationService
from app.modules.risk.services.risk_service import RiskService
from app.modules.risk.services.scenario_service import ScenarioService

router = EnvelopeRouter(tags=["risk"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("risk:read"))]
Writer = Annotated[Principal, Depends(require_permission("risk:write"))]
Querier = Annotated[Principal, Depends(require_permission("risk:query"))]
Approver = Annotated[Principal, Depends(require_permission("risk:approve"))]
DASHBOARD_CACHE = {"Cache-Control": "private, max-age=60", "Vary": "Authorization"}


# ---------- EP-100 dashboard ----------
@router.get("/risk/dashboard", response_model=RiskDashboardOut)
async def dashboard(
    db: Db, user: Querier, response: Response,
    period: Annotated[str | None, Query(max_length=20)] = None,
) -> Any:  # fmt: skip
    response.headers.update(DASHBOARD_CACHE)
    return await RiskDashboardService(db).dashboard(user, period)


# ---------- EP-101 risks ----------
@router.get("/risk/risks", response_model=list[RiskOut])
async def list_risks(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("risk_score", "identified_at", "updated_at", "code")
    )],
    status: RiskStatus | None = None, category: Category | None = None,
    level: Level | None = None, risk_source: RiskSource | None = None,
    owner_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    filters = {
        "status": status, "category": category, "severity": level, "risk_source": risk_source,
        "owner_id": owner_id, "department_id": department_id,
    }  # fmt: skip
    items, total = await RiskService(db).list_risks(user, page, filters=filters)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/risk/risks", response_model=RiskOut, status_code=201)
async def create_risk(body: RiskCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return RiskOut.model_validate(hit)
    out = await RiskService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/risk/risks/{risk_id}", response_model=RiskOut)
async def get_risk(risk_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await RiskService(db).get(user, risk_id)


@router.patch("/risk/risks/{risk_id}", response_model=RiskOut)
async def update_risk(
    risk_id: uuid.UUID, body: RiskUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await RiskService(db).update(user, risk_id, body, exp)
    await db.commit()
    return out


# ---------- EP-102 assessments ----------
@router.get("/risk/risks/{risk_id}/assessments", response_model=list[AssessmentOut])
async def list_assessments(risk_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await RiskService(db).list_assessments(user, risk_id)


@router.post("/risk/risks/{risk_id}/assessments", response_model=AssessmentOut, status_code=201)
async def create_assessment(
    risk_id: uuid.UUID, body: AssessmentIn, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return AssessmentOut.model_validate(hit)
    out = await RiskService(db).assess(user, risk_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-104 accept ----------
@router.post("/risk/risks/{risk_id}/accept", response_model=RiskOut)
async def accept_risk(
    risk_id: uuid.UUID, body: AcceptIn, db: Db, user: Approver, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return RiskOut.model_validate(hit)
    out = await RiskLifecycleService(db).accept(user, risk_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-106 status ----------
@router.post("/risk/risks/{risk_id}/status", response_model=RiskOut)
async def change_status(
    risk_id: uuid.UUID, body: StatusChange, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return RiskOut.model_validate(hit)
    out = await RiskLifecycleService(db).change_status(user, risk_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-103 mitigations ----------
@router.get("/risk/mitigations", response_model=list[MitigationOut])
async def list_mitigations(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("due_date", "progress_pct", "updated_at"))],
    risk_id: uuid.UUID | None = None, status: MitigationStatus | None = None,
    owner_id: uuid.UUID | None = None, overdue: Annotated[bool | None, Query()] = None,
) -> Any:  # fmt: skip
    items, total = await MitigationService(db).list_mitigations(
        user, page, risk_id=risk_id, status=status, owner_id=owner_id, overdue=overdue
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/risk/mitigations", response_model=MitigationOut, status_code=201)
async def create_mitigation(body: MitigationCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return MitigationOut.model_validate(hit)
    out = await MitigationService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/risk/mitigations/{mitigation_id}", response_model=MitigationOut)
async def get_mitigation(mitigation_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await MitigationService(db).get(user, mitigation_id)


@router.patch("/risk/mitigations/{mitigation_id}", response_model=MitigationOut)
async def update_mitigation(
    mitigation_id: uuid.UUID, body: MitigationUpdate, db: Db, user: Writer,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await MitigationService(db).update(user, mitigation_id, body, exp)
    await db.commit()
    return out


# ---------- EP-105 what-if ----------
@router.post("/risk/scenarios", response_model=ScenarioOut, status_code=201)
async def run_scenario(body: ScenarioIn, db: Db, user: Querier, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ScenarioOut.model_validate(hit)
    out = await ScenarioService(db).run(user, body)
    await db.commit()
    await idem.remember(out)
    return out
