"""Public revenue read for other modules (hr METRIC-HR-01 — DEC-205). Returns totals only.

Finance is the only source of actual revenue (D-09): whoever reports revenue against a target
goes through `revenue_vs_target_pct`, the METRIC-FIN-01 formula.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance import rules
from app.modules.finance.repositories import AnalyticsRepository


async def revenue_total(db: AsyncSession, periods: list[str]) -> int:
    """Sum of revenues over `YYYY-MM` period keys (VND)."""
    return sum((await AnalyticsRepository(db).monthly_revenue(periods)).values())


def revenue_vs_target_pct(revenue: int, target: int | None) -> float | None:
    """METRIC-FIN-01: actual revenue ÷ target × 100 (1 decimal); no target → `None`."""
    return rules.pct(revenue, target) if target else None


async def revenue_by_client(db: AsyncSession, periods: list[str]) -> dict[uuid.UUID, int]:
    """Revenue per `client_id` over `YYYY-MM` period keys (sales NRR / concentration)."""
    return await AnalyticsRepository(db).revenue_by_client(periods)
