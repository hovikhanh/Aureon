"""Public revenue read for other modules (hr METRIC-HR-01 — DEC-205). Returns totals only."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.repositories import AnalyticsRepository


async def revenue_total(db: AsyncSession, periods: list[str]) -> int:
    """Sum of revenues over `YYYY-MM` period keys (VND)."""
    return sum((await AnalyticsRepository(db).monthly_revenue(periods)).values())


async def revenue_by_client(db: AsyncSession, periods: list[str]) -> dict[uuid.UUID, int]:
    """Revenue per `client_id` over `YYYY-MM` period keys (sales NRR / concentration)."""
    return await AnalyticsRepository(db).revenue_by_client(periods)
