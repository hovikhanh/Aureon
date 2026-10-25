"""Goals seed M1.4 (T-631, 08 §3 D07–D10, §4.3 UC-03, §4.4 UC-04) — data in `exec_data`.

Runs on every seed (not behind the `seed_execution` skip flag) and upserts by deterministic id:
1 Strategy 2026–2027 → 4 StrategicObjectives (C/F/U/O) linked to root KPIs, Q4 objectives,
INI-01..04 and their projects; one KPIEvaluation per KPI × period (scored with `kpi_rules`);
check-ins + KRMeasurements (`CHECK_INS`) that set KR `current_value` / `confidence` /
`last_checked_in_at` / owner, and the R-DEC-55 at-risk flags at `REFERENCE` (columns only — no
outbox event from the seed). The v2.1 yearly root objective `OBJ-2026` and its 0016 backfill
(`STR-2026` / `SO-2026-01`) are retired (soft delete) — the Strategy layer replaces them.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.modules.auth.models import User
from app.modules.execution.models import (
    CheckIn,
    Initiative,
    KeyResult,
    Kpi,
    KpiEvaluation,
    KpiMeasurement,
    KpiTarget,
    KrMeasurement,
    Objective,
    Project,
    StrategicObjective,
    Strategy,
)
from app.modules.execution.services import kpi_rules
from app.modules.execution.services.at_risk import assess
from app.modules.execution.services.strategy_service import so_progress
from app.seed import exec_data as X
from app.seed.ids import seed_uuid
from app.seed.org_data import REFERENCE

SEED: dict[str, Any] = {"source": "SEED"}
OKR_PERIOD = "2026-Q4"


def _dept(code: str) -> uuid.UUID:
    return seed_uuid("department", code)


def kr_id(okr: str, index: int) -> uuid.UUID:
    return seed_uuid("key_result", f"{okr}:{index}")


def checked_at(day: Any) -> datetime:
    """Check-in at 09:00 local time of `day`."""
    return datetime.combine(day, time(9), tzinfo=kpi_rules.LOCAL_TZ).astimezone(UTC)


async def _users(db: AsyncSession) -> dict[str, uuid.UUID]:
    rows = (await db.execute(select(User.email, User.id))).all()
    return {e: i for e, i in rows}


async def _get(db: AsyncSession, model: Any, id_: uuid.UUID) -> Any:
    return await db.get(model, id_)


async def _retire_legacy(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    legacy = await _get(db, Objective, seed_uuid("objective", "OBJ-2026"))
    if legacy is not None and legacy.deleted_at is None:
        legacy.deleted_at = now
    olds = (await db.execute(select(Strategy).where(
        Strategy.code == "STR-2026", Strategy.source == "SEED",
        Strategy.deleted_at.is_(None)))).scalars().all()  # fmt: skip
    for s in olds:
        sos = (await db.execute(select(StrategicObjective).where(
            StrategicObjective.strategy_id == s.id))).scalars().all()  # fmt: skip
        for so in sos:
            so.deleted_at = now
        s.status, s.deleted_at = "closed", now
    await db.flush()


async def _strategy(db: AsyncSession, ceo: uuid.UUID, users: dict[str, uuid.UUID]) -> int:
    code, name, start, end = X.STRATEGY
    sid = seed_uuid("strategy", code)
    n = 0
    if await _get(db, Strategy, sid) is None:
        db.add(Strategy(id=sid, code=code, name=name, period_start=start, period_end=end,
                        owner_id=ceo, status="active", **SEED))  # fmt: skip
        await db.flush()
        n += 1
    inis = {i.code: i for i in (await db.execute(select(Initiative).where(
        Initiative.code.in_([so[8] for so in X.STRATEGIC_OBJECTIVES])))).scalars()}  # fmt: skip
    for order, (so_code, title, pillar, dept, owner, weight, kpis, okrs, ini, prjs) in enumerate(
        X.STRATEGIC_OBJECTIVES
    ):
        so_id = seed_uuid("strategic_objective", so_code)
        i = inis[ini]
        so = await _get(db, StrategicObjective, so_id)
        if so is None:
            so = StrategicObjective(id=so_id, strategy_id=sid, code=so_code, **SEED)
            db.add(so)
            n += 1
        so.title, so.pillar, so.department_id, so.sort_order = title, pillar, _dept(dept), order
        so.owner_id, so.weight_pct, so.status = users.get(owner, ceo), weight, "active"
        so.progress_pct = so_progress([(i.progress_pct, i.weight_pct)], [])
        await db.flush()
        i.strategic_objective_id = so_id
        i.objective_id = seed_uuid("objective", okrs[0])
        for k in kpis:
            kpi = await _get(db, Kpi, seed_uuid("kpi", k))
            kpi.strategic_objective_id, kpi.pillar = so_id, pillar
        for o in okrs:
            obj = await _get(db, Objective, seed_uuid("objective", o))
            obj.strategic_objective_id, obj.pillar = so_id, pillar
        for p in prjs:
            (await _get(db, Project, seed_uuid("project", p))).initiative_id = i.id
    await db.flush()
    return n


async def _evaluations(db: AsyncSession) -> int:
    grace = get_config().goals_kpi_grace_days
    n = 0
    for code, _, _, _, direction, target, actuals, _ in X.KPIS:
        kid = seed_uuid("kpi", code)
        previous: str | None = None
        for period, actual in zip(X.KPI_PERIODS, actuals, strict=True):
            m = await _get(db, KpiMeasurement, seed_uuid("kpi_measurement", f"{code}:{period}"))
            t = await _get(db, KpiTarget, seed_uuid("kpi_target", f"{code}:{period}"))
            a, tg = Decimal(str(actual)), Decimal(str(target))
            ach = kpi_rules.achievement_pct(direction, a, tg)
            ev = (await db.execute(select(KpiEvaluation).where(
                KpiEvaluation.kpi_id == kid, KpiEvaluation.period_key == period,
                KpiEvaluation.deleted_at.is_(None)))).scalar_one_or_none()  # fmt: skip
            vals: dict[str, Any] = {
                "kpi_target_id": t.id, "measurement_id": m.id, "actual_value": a, "target": tg,
                "achievement_pct": ach, "band": kpi_rules.band(ach), "previous_band": previous,
                "gap_value": kpi_rules.gap_value(direction, a, tg),
                "measured_on_time": kpi_rules.on_time(m.measured_at, period, grace),
                "evaluated_at": m.measured_at,
            }  # fmt: skip
            if ev is None:
                ev = KpiEvaluation(id=seed_uuid("kpi_evaluation", f"{code}:{period}"),
                                   kpi_id=kid, period_key=period, **vals, **SEED)  # fmt: skip
                db.add(ev)
                n += 1
            else:
                for key, value in vals.items():
                    setattr(ev, key, value)
            await db.flush()
            previous = ev.band
    await db.flush()
    return n


async def _check_ins(db: AsyncSession, ceo: uuid.UUID, users: dict[str, uuid.UUID]) -> int:
    n = 0
    by_kr: dict[uuid.UUID, list[tuple[int, Any]]] = defaultdict(list)
    for idx, row in enumerate(X.CHECK_INS):
        by_kr[kr_id(row[0], row[1])].append((idx, row))
    for kid, rows in by_kr.items():
        kr = await _get(db, KeyResult, kid)
        rows.sort(key=lambda r: r[1][4])
        previous: Decimal | None = None
        for idx, (_, _, value, conf, day, email, note) in rows:
            who = users.get(email, ceo) if email else ceo
            at = checked_at(day)
            cid = seed_uuid("check_in", str(idx))
            v = Decimal(str(value))
            progress = kpi_rules.kr_progress_pct(kr.baseline, kr.target, v)
            if await _get(db, CheckIn, cid) is None:
                db.add(CheckIn(id=cid, key_result_id=kid, value=v, note=note, confidence=conf,
                               checked_in_at=at, user_id=who))  # fmt: skip
                await db.flush()
                db.add(KrMeasurement(
                    id=seed_uuid("kr_measurement", str(idx)), key_result_id=kid,
                    check_in_id=cid, period_key=OKR_PERIOD, value=v, progress_pct=progress,
                    previous_progress_pct=previous, confidence=conf, measured_at=at,
                    measured_by=who))  # fmt: skip
                n += 2
            previous = progress
            kr.current_value, kr.confidence, kr.last_checked_in_at = v, conf, at
            kr.owner_id = who
    await db.flush()
    return n


async def _at_risk(db: AsyncSession) -> None:
    """R-DEC-55 flags at `REFERENCE` + objective progress (columns only, no event)."""
    ratio = get_config().goals_kr_behind_ratio
    for code, _, _, krs in X.OKRS:
        progress = []
        for i, (title, unit, base, target, _, _) in enumerate(krs):
            kr = await _get(db, KeyResult, kr_id(code, i))
            kr.title, kr.unit = title, unit  # T-631 definitions (DBs seeded before M1.4)
            kr.baseline, kr.target = Decimal(str(base)), Decimal(str(target))
            q = select(KrMeasurement).where(KrMeasurement.key_result_id == kr.id)
            q = q.order_by(KrMeasurement.measured_at.desc()).limit(1)
            latest = (await db.execute(q)).scalar_one_or_none()
            prev = None if latest is None else latest.previous_progress_pct
            a = assess(kr, OKR_PERIOD, REFERENCE, None if prev is None else Decimal(prev), ratio)
            kr.at_risk, kr.at_risk_reasons = a.at_risk, list(a.reasons) if a.at_risk else []
            kr.at_risk_since = (
                (kr.last_checked_in_at or checked_at(REFERENCE)) if a.at_risk else None
            )
            progress.append(a.progress_pct)
        obj = await _get(db, Objective, seed_uuid("objective", code))
        obj.progress_pct = (sum(progress, Decimal(0)) / len(progress)).quantize(kpi_rules.Q4)
    await db.flush()


async def seed_goals(db: AsyncSession, ceo: uuid.UUID | None) -> dict[str, int]:
    """Idempotent M1.4 goal layer on top of `seed_execution` (needs its KPIs / OKRs)."""
    if ceo is None or await _get(db, Kpi, seed_uuid("kpi", X.KPIS[0][0])) is None:
        return {"goals": 0}
    users = await _users(db)
    await _retire_legacy(db)
    for code, _, _, krs in X.OKRS:  # current values of KRs without seed check-ins
        for i, (_, _, _, _, current, conf) in enumerate(krs):
            kr = await _get(db, KeyResult, kr_id(code, i))
            if kr.last_checked_in_at is None:
                kr.current_value, kr.confidence = Decimal(str(current)), conf
    n = await _strategy(db, ceo, users)
    n += await _evaluations(db)
    n += await _check_ins(db, ceo, users)
    await _at_risk(db)
    return {"goals": n}
