"""METRIC-DQ-02 building blocks (03 §2.6, R-DEC-68): share of new records that came in through a
document / import / AI instead of being typed by hand (C1 form excluded).

Each target module declares its lineage-whitelist tables with `register_capture_source(...)` from
its `services/metrics.py` (same pattern as `register_dq`), handing in its own model objects so
`platform` never imports another module (DEC-125). `captured` marks a row as captured; the default
reads the C19 `source` column (`IDP` / `IMPORT` / `AI`).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

Predicate = Callable[[Any], ColumnElement[bool]]
CAPTURED_SOURCES = ("IDP", "IMPORT", "AI")


def by_source(m: Any) -> ColumnElement[bool]:
    clause: ColumnElement[bool] = m.source.in_(CAPTURED_SOURCES)
    return clause


@dataclass(frozen=True)
class CaptureSource:
    model: Any
    captured: Predicate = by_source


@dataclass
class CaptureRegistry:
    sources: dict[str, list[CaptureSource]] = field(default_factory=dict)

    def register(self, domain: str, *sources: CaptureSource) -> None:
        self.sources[domain] = list(sources)  # module re-import replaces (idempotent)


CAPTURE_SOURCES = CaptureRegistry()


def register_capture_source(domain: str, *sources: CaptureSource) -> None:
    CAPTURE_SOURCES.register(domain, *sources)


async def capture_counts(
    db: AsyncSession, sources: Sequence[CaptureSource], start: date, end: date
) -> tuple[int, int]:
    """(captured, total) live rows created in `[start, end)` over `sources`."""
    lo = datetime.combine(start, time.min, tzinfo=UTC)
    hi = datetime.combine(end, time.min, tzinfo=UTC)
    captured = total = 0
    for s in sources:
        m = s.model
        live = m.deleted_at.is_(None) if hasattr(m, "deleted_at") else and_(True)
        q = select(func.count(), func.count().filter(s.captured(m))).where(
            live, m.created_at >= lo, m.created_at < hi
        )
        n, c = (await db.execute(q)).one()
        total, captured = total + n, captured + c
    return captured, total
