"""TC-SEED-002 (T-236, DEC-208): Sales/HR seed shape + exit criteria (dashboards non-zero).

Runs the seed groups inside the rolled-back test session (each group skips when `source='SEED'`
rows already exist, so the assertions are on the resulting DB state, not on return values).
"""

import uuid
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.models import Department, Employee, HiringPlan, SalaryHistory, Team
from app.modules.sales.models import Client, Deal, SalesTarget
from app.seed.hr_seed import seed_hr
from app.seed.sales_seed import seed_sales
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
