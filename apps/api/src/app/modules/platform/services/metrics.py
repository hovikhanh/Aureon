"""METRIC-DQ-01 Data Quality Score provider (03 §2.6, 08 §10.3, DEC-209).

`dq_score = completeness × w_c + accuracy × w_a + freshness × w_f` per domain over the sources
each domain registers (`core.data_quality.register_dq`); company value = mean of the domains
that have rows (domains without rows are excluded; none → `no_data`). Freshness uses the Data
Quality SLA `SLA_FRESHNESS_<DOMAIN>_HOURS` (DEC-158), never the operational SLA. Only the
company reading is stored (05 `scope_type` has no domain scope); the per-domain breakdown is
logged. Provider order is irrelevant: DQ reads source tables, not other metric values.
"""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import month_key
from app.core.config import get_config
from app.core.data_quality import DQ_SOURCES, DomainDq, domain_stats, dq_score
from app.core.metrics import MetricReading, metric_provider

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


@metric_provider("platform")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    scores = await domain_scores(db, as_of)
    key = month_key(as_of)
    if not scores:
        return [MetricReading("METRIC-DQ-01", None, key, status_reason="no source records")]
    value = round(sum(s for _, s in scores) / len(scores), 1)
    completeness = round(sum(d.completeness for d, _ in scores) / len(scores), 2)
    log.info("DQ-01 %s: %s", key, ", ".join(f"{d.domain}={s}" for d, s in scores))
    return [MetricReading("METRIC-DQ-01", value, key, data_quality_pct=completeness)]
