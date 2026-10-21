"""Public read of the metric store for domain dashboards (10 §5 `metrics[]` + `open_alerts`).

EP-49/60/70/80/90/100 call `pillar_snapshot(db, pillar, codes=...)`. Partial-failure isolation
(FR-DSH-07, T-222): the store read runs in a savepoint; any error is logged and the domain
dashboard still answers 200 with `metrics=[]`, `open_alerts=None` and its own live summary.
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.services.metric_query import MetricQueryService

log = logging.getLogger(__name__)
OUT_FIELDS = ("metric_code", "value", "unit", "status", "computed_at", "freshness",
              "data_quality_pct", "lineage_url", "period_key", "currency")  # fmt: skip


@dataclass(frozen=True)
class PillarSnapshot:
    metrics: list[dict[str, Any]] = field(default_factory=list)
    open_alerts: int | None = None
    available: bool = True


async def pillar_snapshot(
    db: AsyncSession, pillar: str, *, codes: set[str] | None = None
) -> PillarSnapshot:
    """`MetricValueOut` dicts of `pillar` (optionally limited to `codes`, e.g. the caller's
    visible subset) ordered by metric code, and the pillar's open/acknowledged alert count."""
    q = MetricQueryService(db)
    try:
        async with db.begin_nested():
            rows = await q.current_values(pillars={pillar})
            alerts = await q.open_alert_count({pillar})
    except Exception:  # isolate the store from the domain dashboard (FR-DSH-07)
        log.exception("metric store unavailable for pillar %s", pillar)
        return PillarSnapshot(available=False)
    metrics = [
        {k: v for k, v in asdict(r).items() if k in OUT_FIELDS}
        for r in sorted(rows, key=lambda r: r.metric_code)
        if codes is None or r.metric_code in codes
    ]
    return PillarSnapshot(metrics=metrics, open_alerts=alerts.get(pillar, 0))


def pillar_status_of(statuses: list[str]) -> str:
    """03 §4: `no_data` if ≥ 50 % of metrics have no data, else the worst status."""
    if not statuses or statuses.count("no_data") * 2 >= len(statuses):
        return "no_data"
    rank = {"ok": 0, "warning": 1, "critical": 2}
    return max((s for s in statuses if s in rank), key=rank.__getitem__)
