"""KR at-risk evaluation (R-DEC-55, 05 §2.6) + weekly check-in reminder (10 §9.2) — T-629.

`assess(kr, objective, day)` is pure: reasons = `declining` (progress below the previous
measurement) ∪ `low_confidence` (`confidence = LOW`) ∪ `behind_plan` (progress <
`GOALS_KR_BEHIND_RATIO` × elapsed share of the objective period); `at_risk = reasons ≠ ∅ ∧
days_to_period_end ≥ 21`. `AtRiskService.refresh` stores the columns and publishes
`execution.okr_at_risk` only on the false → true transition (true → false only updates
columns). Runs after each KR check-in and from the 07:00 daily job (`daily`).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_config
from app.core.events.outbox import publish_in_tx
from app.modules.execution.models import KeyResult, Objective
from app.modules.execution.repositories import (
    KeyResultRepository,
    KrMeasurementRepository,
    ObjectiveRepository,
)
from app.modules.execution.services.kpi_rules import (
    LOCAL_TZ,
    Q4,
    kr_progress_pct,
    period_bounds,
)

REMINDER_LINK = "/goals/check-ins"  # SCR-60 (F4)
MIN_DAYS_TO_END = 21  # UC-04 "cảnh báo trước ≥ 3 tuần" (R-DEC-55)


def in_period(period_key: str, day: date) -> bool:
    start, end = period_bounds(period_key)
    return start <= day < end


async def current_objectives(db: AsyncSession, day: date) -> list[Objective]:
    """`active` objectives whose period contains `day` (at-risk job, reminder, EP-PRF-06)."""
    rows = await ObjectiveRepository(db).where(Objective.status == "active")
    return [o for o in rows if in_period(o.period_key, day)]


@dataclass(frozen=True)
class Assessment:
    progress_pct: Decimal
    previous_progress_pct: Decimal | None
    expected_progress_pct: Decimal
    reasons: tuple[str, ...]
    days_to_period_end: int

    @property
    def at_risk(self) -> bool:
        return bool(self.reasons) and self.days_to_period_end >= MIN_DAYS_TO_END


def assess(
    kr: KeyResult, period_key: str, day: date, previous: Decimal | None, ratio: float
) -> Assessment:
    start, end = period_bounds(period_key)  # `end` exclusive
    span = max((end - start).days, 1)
    elapsed = min(max((day - start).days, 0), span)
    expected = (Decimal(elapsed * 100) / Decimal(span)).quantize(Q4)
    progress = kr_progress_pct(kr.baseline, kr.target, kr.current_value)
    reasons: list[str] = []
    if previous is not None and progress < Decimal(previous):
        reasons.append("declining")
    if kr.confidence == "LOW":
        reasons.append("low_confidence")
    if progress < Decimal(str(ratio)) * expected:
        reasons.append("behind_plan")
    days_left = (end - timedelta(days=1) - day).days
    return Assessment(progress, previous, expected, tuple(reasons), days_left)


class AtRiskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.krs = KeyResultRepository(db)
        self.objectives = ObjectiveRepository(db)
        self.measurements = KrMeasurementRepository(db)

    async def refresh(self, kr: KeyResult, o: Objective, day: date) -> Assessment:
        """Store at-risk columns; publish `execution.okr_at_risk` on false → true."""
        latest = await self.measurements.latest(kr.id)
        prev = latest.previous_progress_pct if latest is not None else None
        a = assess(kr, o.period_key, day, None if prev is None else Decimal(prev),
                   get_config().goals_kr_behind_ratio)  # fmt: skip
        was = kr.at_risk
        if a.at_risk != was or list(a.reasons) != list(kr.at_risk_reasons or []):
            kr.at_risk = a.at_risk
            kr.at_risk_reasons = list(a.reasons) if a.at_risk else []
            kr.at_risk_since = (kr.at_risk_since or datetime.now(UTC)) if a.at_risk else None
            await self.db.flush()
        if a.at_risk and not was:
            await publish_in_tx(
                self.db, event_type="execution.okr_at_risk", producer="execution",
                aggregate_schema="execution", aggregate_table="key_results", aggregate_id=kr.id,
                payload={
                    "key_result_id": str(kr.id), "objective_id": str(o.id),
                    "period_key": o.period_key, "progress_pct": str(a.progress_pct),
                    "previous_progress_pct": None if prev is None else str(prev),
                    "expected_progress_pct": str(a.expected_progress_pct),
                    "confidence": kr.confidence, "reasons": list(a.reasons),
                    "days_to_period_end": a.days_to_period_end, "owner_id": str(kr.owner_id),
                    "department_id": str(o.department_id) if o.department_id else None,
                },
            )  # fmt: skip
        return a

    async def daily(self, day: date) -> int:
        """07:00 job: KRs of `active` objectives whose period contains `day`. Returns the
        number of KRs that became at risk."""
        objs = await current_objectives(self.db, day)
        if not objs:
            return 0
        by_id = {o.id: o for o in objs}
        n = 0
        for kr in await self.krs.where(KeyResult.objective_id.in_(list(by_id)),
                                       order=KeyResult.id):  # fmt: skip
            was = kr.at_risk
            a = await self.refresh(kr, by_id[kr.objective_id], day)
            n += int(a.at_risk and not was)
        return n


def iso_week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def checkin_reminder(db: AsyncSession, day: date) -> int:
    """Friday 08:00 (Asia/Ho_Chi_Minh) beat `execution.checkin_reminder` (F4 step 1): one
    `reminder` "Check-in tuần: N KR của bạn" per KR owner with KRs of active objectives in the
    current period; idempotent per `(user_id, ISO week)`. No event. Returns notifications made."""
    from app.modules.auth.services.auth_service import AuthService
    from app.modules.platform.services.notification_service import NotificationService

    objs = await current_objectives(db, day)
    if not objs:
        return 0
    counts: dict[uuid.UUID, int] = {}
    for kr in await KeyResultRepository(db).where(
            KeyResult.objective_id.in_([o.id for o in objs]), order=KeyResult.id):  # fmt: skip
        counts[kr.owner_id] = counts.get(kr.owner_id, 0) + 1
    auth, ntf = AuthService(db), NotificationService(db)
    since = datetime.combine(iso_week_start(day), time(), tzinfo=LOCAL_TZ)  # local Monday 00:00
    made = 0
    for ref, n in sorted(counts.items(), key=lambda x: str(x[0])):
        uid = await auth.user_id_for_ref(ref)
        if uid is None or await ntf.already_sent(uid, kind="reminder", since=since,
                                                 link=REMINDER_LINK):  # fmt: skip
            continue
        text = f"Check-in tuần: {n} KR của bạn"
        await ntf.create(
            recipient_id=uid,
            kind="reminder",
            title=text,
            body=text,
            link=REMINDER_LINK,
            ref_schema="execution",
            ref_table="key_results",
        )
        made += 1
    return made
