"""METRIC-DQ-01 building blocks (03 §2.6, 08 §10.3, DEC-209): per-domain data-quality stats.

Each domain module declares its own sources (model + required fields + business-invalid
predicates) with `register_dq(...)` from its `services/metrics.py`; the owning module's model
objects are handed in, so `platform` never imports another module (DEC-125) — same pattern as
`@metric_provider`. `domain_stats` turns sources into the three DQ components (0–100).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

Predicate = Callable[[Any], ColumnElement[bool]]


@dataclass(frozen=True)
class DqSource:
    """One source table. `required`: columns that must be filled (05 business fields);
    `invalid`: predicates marking a row as failing a business validation (FR-DC-14)."""

    model: Any
    required: tuple[str, ...] = ()
    invalid: tuple[Predicate, ...] = ()
    where: tuple[Predicate, ...] = ()  # optional row filter (e.g. a department / test subset)


@dataclass(frozen=True)
class DomainDq:
    domain: str
    rows: int
    completeness: float
    accuracy: float
    freshness: float


@dataclass
class DqRegistry:
    sources: dict[str, list[DqSource]] = field(default_factory=dict)

    def register(self, domain: str, *sources: DqSource) -> None:
        # re-import of the declaring module replaces its sources (idempotent)
        self.sources[domain] = list(sources)


DQ_SOURCES = DqRegistry()


def register_dq(domain: str, *sources: DqSource) -> None:
    DQ_SOURCES.register(domain, *sources)


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole else 100.0


async def domain_stats(
    db: AsyncSession, domain: str, sources: Sequence[DqSource], as_of: date, sla_hours: int
) -> DomainDq | None:
    """`None` when the domain has no live rows (excluded from the company average)."""
    ref = datetime.combine(as_of + timedelta(days=1), time.min, tzinfo=UTC)
    rows = complete = bad = fresh = tables = 0
    for s in sources:
        m = s.model
        live = m.deleted_at.is_(None) if hasattr(m, "deleted_at") else and_(True)
        filled = and_(True, *[getattr(m, c).is_not(None) for c in s.required])
        wrong = or_(False, *[p(m) for p in s.invalid])
        q = select(
            func.count(), func.count().filter(filled), func.count().filter(wrong),
            func.max(m.updated_at),
        ).where(live, *[p(m) for p in s.where])  # fmt: skip
        n, ok, err, last = (await db.execute(q)).one()
        if not n:
            continue
        rows, complete, bad, tables = rows + n, complete + ok, bad + err, tables + 1
        if last is not None and ref - last <= timedelta(hours=sla_hours):
            fresh += 1
    if not rows:
        return None
    return DomainDq(domain, rows, _pct(complete, rows), _pct(rows - bad, rows),
                    _pct(fresh, tables))  # fmt: skip


def dq_score(d: DomainDq, w_complete: float, w_accuracy: float, w_fresh: float) -> float:
    return round(d.completeness * w_complete + d.accuracy * w_accuracy + d.freshness * w_fresh, 1)
