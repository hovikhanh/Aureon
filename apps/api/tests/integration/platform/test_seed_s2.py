"""TC-SEED-002/003 (T-236, DEC-208): Sales/HR + product/risk/execution seed + exit criteria.

Runs the seed groups inside the rolled-back test session (each group skips when `source='SEED'`
rows already exist, so the assertions are on the resulting DB state, not on return values).
"""

import uuid
from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import Initiative, Task
from app.modules.finance.models import Revenue
from app.modules.hr.models import Department, Employee, HiringPlan, SalaryHistory, Team
from app.modules.platform.models import Alert, Metric, MetricValue
from app.modules.platform.services.metric_store import MetricStore, seed_catalog
from app.modules.product.models import Feature, Product
from app.modules.risk.models import Mitigation, Risk
from app.modules.sales.models import Client, Deal, SalesTarget
from app.seed.execution_seed import seed_execution
from app.seed.hr_seed import seed_hr
from app.seed.product_seed import seed_product
from app.seed.risk_seed import seed_risk
from app.seed.sales_seed import seed_sales
from app.workers.consumers import load_metric_providers
from tests.conftest import ApiClient


async def _count(db: AsyncSession, model: Any, *where: Any) -> int:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED", *where)
    return int((await db.execute(stmt)).scalar_one())


async def test_seed_shape_and_dashboards(api: ApiClient, db_session: AsyncSession) -> None:
    owner = uuid.uuid4()
    await seed_hr(db_session, owner, uuid.uuid4())
    await seed_sales(db_session, owner)
    await seed_hr(db_session, owner, uuid.uuid4())  # idempotent: second run adds nothing
    await seed_sales(db_session, owner)

    assert await _count(db_session, Client) == 20
    stages = Counter((await db_session.execute(
        select(Deal.stage).where(Deal.source == "SEED"))).scalars())  # fmt: skip
    assert sum(stages.values()) == 30
    assert stages["closed_won"] == 10 and stages["closed_lost"] == 5
    assert (
        stages["negotiation"] == 5
        and sum(stages[s] for s in ("lead", "qualified", "proposal")) == 10
    )
    assert await _count(db_session, SalesTarget, SalesTarget.period_key == "2026-Q4") == 1
    assert await _count(db_session, Department) == 5 and await _count(db_session, Team) == 3
    st = Counter((await db_session.execute(
        select(Employee.status).where(Employee.source == "SEED"))).scalars())  # fmt: skip
    assert st == {"active": 5, "probation": 3, "terminated": 2}
    assert await _count(db_session, HiringPlan) == 5
    months = (await db_session.execute(
        select(func.count(func.distinct(SalaryHistory.effective_date)))
        .join(Employee, Employee.id == SalaryHistory.employee_id)
        .where(Employee.source == "SEED"))).scalar_one()  # fmt: skip
    assert months == 3

    sales = (await api.call("GET", "/sales/dashboard", "VP_SALES")).json()["data"]["summary"]
    assert sales["deals_open"] >= 10 and sales["pipeline_value"] > 0
    hr = await api.call("GET", "/hr/dashboard", "HR_MANAGER", params={"period": "ytd"})
    hs = hr.json()["data"]["summary"]
    assert hs["headcount"] + hs["terminated"] >= 10 and hs["turnover_rate_pct"] > 0


async def test_seed_product_risk_execution_populate_all_metrics(db_session: AsyncSession) -> None:
    """TC-SEED-003: product / risk / execution seed → all 32 metrics valued, ≥ 10 alerts."""
    owner = uuid.uuid4()
    await seed_hr(db_session, owner, uuid.uuid4())
    await seed_sales(db_session, owner)
    for _ in range(2):  # second pass is a no-op (idempotent)
        await seed_product(db_session, owner)
        await seed_risk(db_session, owner)
        await seed_execution(db_session, owner)
    assert await _count(db_session, Product) == 3 and await _count(db_session, Feature) == 5
    assert await _count(db_session, Risk) == 8 and await _count(db_session, Mitigation) == 4
    assert await _count(db_session, Risk, Risk.status == "proposed") == 2
    assert await _count(db_session, Initiative) == 4 and await _count(db_session, Task) == 28
    unlinked = select(func.count()).select_from(Revenue).where(
        Revenue.source == "SEED", Revenue.client_id.is_(None))  # fmt: skip
    assert (await db_session.execute(unlinked)).scalar_one() == 0

    await seed_catalog(db_session)
    load_metric_providers()
    stats = await MetricStore(db_session).recompute(date(2026, 10, 20))
    assert stats["failed_providers"] == 0
    valued = (await db_session.execute(
        select(func.count(func.distinct(Metric.code))).join(
            MetricValue, MetricValue.metric_id == Metric.id)
        .where(MetricValue.is_current.is_(True), MetricValue.scope_type == "company",
               MetricValue.value.is_not(None))
    )).scalar_one()  # fmt: skip
    assert valued == 32
    open_alerts = select(func.count()).select_from(Alert).where(Alert.status == "OPEN")
    assert (await db_session.execute(open_alerts)).scalar_one() >= 10
