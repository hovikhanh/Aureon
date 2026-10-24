"""KPITarget effective-dated + KPIEvaluation scoring (05 §2.6, R-DEC-52/53) — EP-KPI-08..10.

- A period has versions `[valid_from, valid_to)` (local calendar days); ≤ 1 current version
  (`valid_to` NULL). Setting a target (EP-KPI-09) closes the current version at the new
  `valid_from` and opens a new one in **one** transaction (KPI row locked).
- The target "in force" for a measurement = version with `valid_from ≤ day < valid_to` of the
  measurement day; none yet → created from `kpis.target_value` with default bands (v2.1
  behaviour, DEC-147); a day before the first version → the first version, a day after the
  period (late measurement) → the latest version.
- `evaluate()` upserts the period's `KPIEvaluation` from its latest measurement (period value,
  R-DEC-51); no measurement left → the evaluation row is removed (undo path).
- Public for the Action Registry v2 (M1.5 undo): `upsert`, `evaluate` — they never commit,
  the caller's transaction owns the work.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.errors import BusinessRuleError, ConflictStateError
from app.modules.execution.models import Kpi, KpiEvaluation, KpiMeasurement, KpiTarget
from app.modules.execution.repositories import (
    KpiEvaluationRepository,
    KpiRepository,
    KpiTargetRepository,
    MeasurementRepository,
)
from app.modules.execution.schemas.kpi import (
    KpiEvaluationBrief,
    KpiEvaluationOut,
    KpiTargetCreate,
    KpiTargetOut,
)
from app.modules.execution.services.base import ExecBase, not_found, now_utc, num, today
from app.modules.execution.services.kpi_rules import (
    DEFAULT_BANDS,
    DEFAULT_CAP,
    achievement_pct,
    band,
    gap_value,
    in_force,
    local_day,
    on_time,
    period_bounds,
    period_key_for,
)
from app.modules.execution.services.meeting_service import _c19

RULE = "FR-KPI-01"
DEFAULT_EVALUATIONS = 12  # EP-KPI-10 default window


def target_out(t: KpiTarget) -> KpiTargetOut:
    return KpiTargetOut(
        **_c19(t), kpi_id=t.kpi_id, period_key=t.period_key, baseline=num(t.baseline),
        minimum=num(t.minimum), target=float(t.target), stretch=num(t.stretch),
        band_thresholds={k: float(v) for k, v in dict(t.band_thresholds).items()},
        score_cap_pct=float(t.score_cap_pct), locked_at=t.locked_at, valid_from=t.valid_from,
        valid_to=t.valid_to, reason=t.reason,
    )  # fmt: skip


def evaluation_out(e: KpiEvaluation) -> KpiEvaluationOut:
    return KpiEvaluationOut(
        **_c19(e), kpi_id=e.kpi_id, period_key=e.period_key, kpi_target_id=e.kpi_target_id,
        measurement_id=e.measurement_id, actual_value=float(e.actual_value),
        target=float(e.target), achievement_pct=float(e.achievement_pct), band=e.band,
        previous_band=e.previous_band, gap_value=float(e.gap_value),
        measured_on_time=e.measured_on_time, evaluated_at=e.evaluated_at, locked_at=e.locked_at,
    )  # fmt: skip


def evaluation_brief(e: KpiEvaluation | None) -> KpiEvaluationBrief | None:
    if e is None:
        return None
    return KpiEvaluationBrief(
        period_key=e.period_key, actual_value=float(e.actual_value), target=float(e.target),
        achievement_pct=float(e.achievement_pct), band=e.band, previous_band=e.previous_band,
        evaluated_at=e.evaluated_at,
    )  # fmt: skip


def check_period(period_type: str, period_key: str) -> None:
    """`period_key` must be a valid key of the KPI's `period_type` → else 422."""
    try:
        start, _ = period_bounds(period_key)
    except ValueError as exc:
        raise BusinessRuleError(str(exc), details={"field": "period_key", "rule": RULE}) from exc
    if period_key_for(period_type, start) != period_key:
        raise BusinessRuleError(
            f"period_key {period_key} does not match KPI period_type {period_type}",
            details={"field": "period_key", "rule": RULE},
        )


@dataclass(frozen=True)
class Scored:
    """Result of `evaluate()`: the upserted row (None = period has no measurement) and the
    band it had before (None = first evaluation of the period)."""

    evaluation: KpiEvaluation | None
    previous_band: str | None


class KpiTargetService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.kpis = KpiRepository(db)
        self.targets = KpiTargetRepository(db)
        self.evaluations = KpiEvaluationRepository(db)
        self.measurements = MeasurementRepository(db)

    async def lock_kpi(self, kpi_id: uuid.UUID) -> Kpi:
        """Row lock on the KPI: serialises targets / measurements / evaluation of all periods."""
        k = await self.kpis.lock(kpi_id)
        if k is None:
            raise not_found("KPI")
        return k

    @staticmethod
    def require_open(versions: list[KpiTarget], period_key: str) -> None:
        if any(t.locked_at is not None for t in versions):
            raise ConflictStateError("KPI period is locked", details={"period_key": period_key})

    async def target_for(
        self, k: Kpi, period_key: str, day: date, user_id: uuid.UUID | None
    ) -> KpiTarget:
        """Version in force on `day` (R-DEC-52); none → default from `kpis.target_value`."""
        versions = list(await self.targets.versions(k.id, period_key))
        for t in versions:
            if in_force(t.valid_from, t.valid_to, day):
                return t
        if versions:  # before the first version → first; after the period → current/last
            return versions[0] if day < versions[0].valid_from else versions[-1]
        start, _ = period_bounds(period_key)
        t = await self.targets.create(
            kpi_id=k.id, period_key=period_key, target=k.target_value, valid_from=start,
            band_thresholds=dict(DEFAULT_BANDS), score_cap_pct=DEFAULT_CAP, source="MANUAL",
            created_by=user_id,
        )  # fmt: skip
        await self.db.refresh(t)
        return t

    async def upsert(
        self, kpi_id: uuid.UUID, body: KpiTargetCreate, user_id: uuid.UUID | None,
        source: str = "MANUAL",
    ) -> KpiTargetOut:  # fmt: skip
        """EP-KPI-09 — close the current version at `valid_from` + open the new one, re-score
        the period (R-DEC-52). Caller checks scope and commits."""
        k = await self.lock_kpi(kpi_id)
        check_period(k.period_type, body.period_key)
        start, end = period_bounds(body.period_key)
        valid_from = body.valid_from or today()
        if not start <= valid_from < end:
            raise BusinessRuleError(
                "valid_from outside the period",
                details={"field": "valid_from", "rule": RULE, "period_start": str(start),
                         "period_end": str(end)},
            )  # fmt: skip
        versions = list(await self.targets.versions(k.id, body.period_key))
        self.require_open(versions, body.period_key)
        current = next((t for t in versions if t.valid_to is None), None)
        if current is not None and valid_from <= current.valid_from:
            raise BusinessRuleError(
                "valid_from must be after the current version's valid_from",
                details={"field": "valid_from", "rule": RULE,
                         "current_valid_from": str(current.valid_from)},
            )  # fmt: skip
        before = target_out(current) if current is not None else None
        if current is not None:
            await self.targets.update(current, valid_to=valid_from, updated_by=user_id)
        data = body.model_dump(exclude={"valid_from"}, exclude_none=True)
        data.setdefault("band_thresholds", dict(DEFAULT_BANDS))
        data.setdefault("score_cap_pct", DEFAULT_CAP)
        t = await self.targets.create(kpi_id=k.id, valid_from=valid_from, source=source,
                                      created_by=user_id, **data)  # fmt: skip
        await self.db.refresh(t)
        out = target_out(t)
        await self.audit("kpi_target_set", "kpi_targets", t.id, before, out)
        await self.evaluate(k, body.period_key, source=source)
        return out

    async def evaluate(
        self, k: Kpi, period_key: str, source: str = "MANUAL", exclude: uuid.UUID | None = None
    ) -> Scored:
        """Upsert the period's KPIEvaluation from its latest measurement (R-DEC-53);
        `exclude` = measurement being removed (undo) — scored as if already gone."""
        rows = [m for m in await self.measurements.of_period(k.id, period_key) if m.id != exclude]
        ev = await self.evaluations.find(k.id, period_key)
        old = ev.band if ev is not None else None
        if not rows:
            if ev is not None:
                await self.evaluations.remove(ev)
            return Scored(None, old)
        latest: KpiMeasurement = rows[0]
        t = await self.target_for(k, period_key, local_day(latest.measured_at), None)
        actual, target = Decimal(latest.actual_value), Decimal(t.target)
        ach = achievement_pct(k.direction, actual, target, minimum=t.minimum,
                              cap=Decimal(t.score_cap_pct))  # fmt: skip
        values: dict[str, Any] = {
            "kpi_target_id": t.id, "measurement_id": latest.id, "actual_value": actual,
            "target": target, "achievement_pct": ach, "band": band(ach, t.band_thresholds),
            "gap_value": gap_value(k.direction, actual, target, t.minimum),
            "measured_on_time": on_time(rows[-1].measured_at, period_key,
                                        get_config().goals_kpi_grace_days),
            "evaluated_at": now_utc(), "locked_at": t.locked_at,
        }  # fmt: skip
        if ev is None:
            ev = await self.evaluations.create(kpi_id=k.id, period_key=period_key, source=source,
                                               previous_band=None, **values)  # fmt: skip
        else:
            await self.evaluations.update(ev, previous_band=old, **values)
        return Scored(ev, old)

    # ---------- reads ----------
    async def list_targets(
        self, kpi_id: uuid.UUID, period_key: str | None, as_of: date | None
    ) -> list[KpiTargetOut]:
        return [target_out(t) for t in await self.targets.history(kpi_id, period_key, as_of)]

    async def list_evaluations(
        self, kpi_id: uuid.UUID, from_period: str | None, to_period: str | None
    ) -> list[KpiEvaluationOut]:
        limit = 1000 if from_period is not None else DEFAULT_EVALUATIONS
        rows = await self.evaluations.between(kpi_id, from_period, to_period, limit)
        return [evaluation_out(e) for e in rows]

    async def latest(self, kpi_ids: list[uuid.UUID]) -> dict[uuid.UUID, KpiEvaluation]:
        return await self.evaluations.latest_for(kpi_ids)
