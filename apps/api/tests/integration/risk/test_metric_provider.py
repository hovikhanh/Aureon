"""TC-RSK-008 — `@metric_provider("risk")` registered and reading the live register (DEC-205)."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.metrics import METRIC_PROVIDERS
from app.modules.risk.services import metrics
from app.workers.consumers import load_metric_providers
from tests.conftest import ApiClient
from tests.integration.risk.helpers import make_risk


async def test_provider_registered_and_counts(api: ApiClient, db_session: AsyncSession) -> None:
    load_metric_providers()
    assert METRIC_PROVIDERS.providers["risk"] is metrics.compute
    today = business_today()
    before = {m.code: m for m in await metrics.compute(db_session, today)}
    r = await make_risk(api, likelihood=5, impact=5)
    after = {m.code: m for m in await metrics.compute(db_session, today)}
    assert set(after) == {f"METRIC-RSK-0{i}" for i in range(1, 6)}
    rsk01 = after["METRIC-RSK-01"]
    assert rsk01.value == (before["METRIC-RSK-01"].value or 0) + 1
    assert rsk01.status == "critical" and rsk01.period_key == f"{today:%Y-%m}"
    assert r["id"] in {x.id for x in rsk01.records} or len(rsk01.records) == 50
    past = {m.code: m for m in await metrics.compute(db_session, date(2000, 1, 31))}
    assert past["METRIC-RSK-01"].value == 0 and past["METRIC-RSK-04"].status == "no_data"
