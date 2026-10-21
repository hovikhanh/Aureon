"""Pure PIL-S computations shared by EP-100 and the metric provider (03 §2.5, BR-RSK-01).

"Open" = status ∈ {identified, assessed, mitigating, monitoring}: `proposed` risks are not yet
in the register (DEC-148) and `closed/accepted/rejected` are terminal.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.core.metrics import MetricReading, MetricStatus, RecordRef
from app.modules.risk.models import Mitigation, Risk
from app.modules.risk.services import rules

MAX_RECORDS = 50
UNOWNED_MEDIUM_DAYS = 7  # METRIC-RSK-02 warning
STALE_HIGH_DAYS = 30  # METRIC-RSK-03
RSK04_WARN, RSK04_CRIT = 10.0, 15.0  # DEC-143
RSK05_CRIT_COUNT = 5


def score(r: Risk) -> int:
    return r.likelihood * r.impact


def is_open(r: Risk) -> bool:
    return r.status in rules.OPEN_STATUSES


def existed_on(r: Risk, day: date) -> bool:
    return r.identified_at.date() <= day


def open_on(risks: Iterable[Risk], day: date, *, current: bool = True) -> list[Risk]:
    """Open risks at `day`. `current=True` = today's register (no cutoff: `identified_at` is a
    wall-clock timestamp while business today may be the demo reference date); historical trend
    points keep only risks identified on or before `day` (status as of now — no history table)."""
    return [r for r in risks if is_open(r) and (current or existed_on(r, day))]


def refs(rows: Sequence[Risk | Mitigation], table: str) -> tuple[RecordRef, ...]:
    """≤ 50 lineage refs, highest contribution first (risk score; 1 per mitigation)."""
    pairs = [(float(score(x)) if isinstance(x, Risk) else 1.0, x) for x in rows]
    pairs.sort(key=lambda p: (-p[0], str(p[1].id)))
    return tuple(
        RecordRef(schema="risk", table=table, id=str(x.id), contribution=c)
        for c, x in pairs[:MAX_RECORDS]
    )


def overdue(mitigations: Iterable[Mitigation], day: date) -> list[Mitigation]:
    return [m for m in mitigations if m.status in rules.ACTIVE_MITIGATION and m.due_date < day]


def level_status(levels: Iterable[str]) -> MetricStatus:
    s = set(levels)
    return "critical" if "critical" in s else "warning" if "high" in s else "ok"


def rsk04_status(value: float | None) -> MetricStatus:
    if value is None:
        return "no_data"
    return "critical" if value >= RSK04_CRIT else "warning" if value >= RSK04_WARN else "ok"


@dataclass(frozen=True)
class Readings:
    items: list[MetricReading]

    def statuses(self) -> list[str]:
        """Pillar status inputs; RSK-04 evaluated with the 03 thresholds when not forced."""
        return [m.status or rsk04_status(m.value) for m in self.items]


def compute_readings(
    risks: Sequence[Risk], mitigations: Sequence[Mitigation], as_of: date, *, current: bool = True
) -> Readings:
    key = f"{as_of.year:04d}-{as_of.month:02d}"
    live = open_on(risks, as_of, current=current)
    high = [r for r in live if r.severity in rules.HIGH_LEVELS]
    unowned_high = [r for r in high if r.owner_id is None]
    old_medium = [
        r for r in live
        if r.severity == "medium" and r.owner_id is None
        and r.identified_at.date() < as_of - timedelta(days=UNOWNED_MEDIUM_DAYS)
    ]  # fmt: skip
    in_progress = {m.risk_id for m in mitigations if m.status == "in_progress"}
    stale = [
        r for r in high
        if r.identified_at.date() < as_of - timedelta(days=STALE_HIGH_DAYS)
        and r.id not in in_progress
    ]  # fmt: skip
    late = overdue(mitigations, as_of)
    critical_ids = {r.id for r in live if r.severity == "critical"}
    agg = rules.aggregate_score([score(r) for r in live])

    def reading(code: str, value: float | None, status: MetricStatus | None,
                rows: Sequence[Risk | Mitigation], table: str = "risks",
                reason: str | None = None) -> MetricReading:  # fmt: skip
        return MetricReading(code=code, value=value, period_key=key, status=status,
                             status_reason=reason, records=refs(rows, table))  # fmt: skip

    rsk02: MetricStatus = "critical" if unowned_high else "warning" if old_medium else "ok"
    rsk03: MetricStatus = ("critical" if any(r.id in critical_ids for r in stale)
             else "warning" if stale else "ok")  # fmt: skip
    rsk05: MetricStatus = ("critical" if len(late) >= RSK05_CRIT_COUNT
             or any(m.risk_id in critical_ids for m in late)
             else "warning" if late else "ok")  # fmt: skip
    return Readings([
        reading("METRIC-RSK-01", len(high), level_status(r.severity for r in high), high),
        reading("METRIC-RSK-02", len(unowned_high), rsk02, unowned_high or old_medium),
        reading("METRIC-RSK-03", len(stale), rsk03, stale),
        reading("METRIC-RSK-04", agg, None if agg is not None else "no_data", live,
                reason=None if agg is not None else "NO_OPEN_RISKS"),
        reading("METRIC-RSK-05", len(late), rsk05, late, "mitigations"),
    ])  # fmt: skip
