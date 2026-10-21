"""PIL-S metric provider (T-220 contract, DEC-205): METRIC-RSK-01..05, company scope.

METRIC-RSK-06 (SEI) is computed from execution Initiatives — not provided here (DEC-219).
`proposed` risks are ignored (not yet in the register, DEC-148).
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.metrics import MetricReading, metric_provider
from app.modules.risk.repositories import MitigationRepository, RiskRepository
from app.modules.risk.services.analytics import compute_readings


@metric_provider("risk")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    risks = list(await RiskRepository(db).scoped())
    mitigations = list(await MitigationRepository(db).live_all())
    current = as_of >= business_today()
    return compute_readings(risks, mitigations, as_of, current=current).items
