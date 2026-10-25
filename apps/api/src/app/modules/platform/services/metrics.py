"""METRIC-DQ-01 Data Quality Score provider (03 §2.6, 08 §10.3, DEC-209).

`dq_score = completeness × w_c + accuracy × w_a + freshness × w_f` per domain over the sources
each domain registers (`core.data_quality.register_dq`); company value = mean of the domains
that have rows (domains without rows are excluded; none → `no_data`). Freshness uses the Data
Quality SLA `SLA_FRESHNESS_<DOMAIN>_HOURS` (DEC-158), never the operational SLA. Only the
company reading is stored in `metric_values`; the per-domain breakdown goes to
`platform.dq_domain_scores` (R-DEC-68). Provider order is irrelevant: DQ reads source
tables, not other metric values.
"""

import logging
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key
from app.core.config import get_config
from app.core.data_quality import DQ_SOURCES, DomainDq, domain_stats, dq_score
from app.core.metrics import MetricReading, metric_provider
from app.modules.platform.repositories import DqDomainScoreRepository

log = logging.getLogger(__name__)
DOMAINS = ("finance", "sales", "hr", "product", "risk", "execution")


async def domain_scores(db: AsyncSession, as_of: date) -> list[tuple[DomainDq, float]]:
    cfg = get_config()
    out = []
    for domain in DOMAINS:
        sources = DQ_SOURCES.sources.get(domain)
        if not sources:
            continue
        sla = int(getattr(cfg, f"sla_freshness_{domain}_hours"))
        stats = await domain_stats(db, domain, sources, as_of, sla)
        if stats is not None:
            score = dq_score(stats, cfg.dq_weight_completeness, cfg.dq_weight_accuracy,
                             cfg.dq_weight_freshness)  # fmt: skip
            out.append((stats, score))
    return out


async def _persist(db: AsyncSession, key: str, scores: list[tuple[DomainDq, float]]) -> None:
    """R-DEC-68: per-domain breakdown of DQ-01 → `platform.dq_domain_scores` (upsert)."""
    now = datetime.now(UTC)
    repo = DqDomainScoreRepository(db)
    for d, score in scores:
        await repo.upsert(d.domain, key, completeness=d.completeness, accuracy=d.accuracy,
                          freshness=d.freshness, score=score, rows=d.rows,
                          computed_at=now)  # fmt: skip


@metric_provider("platform")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    scores = await domain_scores(db, as_of)
    key = month_key(as_of)
    if not scores:
        return [MetricReading("METRIC-DQ-01", None, key, status_reason="no source records")]
    await _persist(db, key, scores)
    value = round(sum(s for _, s in scores) / len(scores), 1)
    completeness = round(sum(d.completeness for d, _ in scores) / len(scores), 2)
    log.info("DQ-01 %s: %s", key, ", ".join(f"{d.domain}={s}" for d, s in scores))
    return [MetricReading("METRIC-DQ-01", value, key, data_quality_pct=completeness)]
