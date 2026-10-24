"""`uv run python -m app.seed` — the ONLY seed command (DEC-062), idempotent.

Seed v3 (T-603b, 08 §2–§5, R-DEC-23): 7 roles + 10 demo users + the AI actor, company ABC
(7 departments, ~150 employees), finance / sales / execution data for UC-01/02/03/04/06/07,
product & risk kept (frozen, R-DEC-16) and owned by the CEO, M1.4 goal layer (T-631),
metric catalog (33) + recompute.
`python -m app.seed.snapshot` exports `seed_snapshot.json` for the mock FE (T-604).
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.clock import business_today
from app.core.db import get_engine, get_sessionmaker
from app.core.tenant import tenant_scope
from app.modules.auth.models import User
from app.modules.hr.services.hiring_service import detect_delayed_hiring_plans
from app.modules.platform.services.metric_store import MetricStore, seed_catalog
from app.seed.auth_seed import SeedReport, seed_auth
from app.seed.execution_seed import seed_execution
from app.seed.finance_seed import seed_finance
from app.seed.goals_seed import seed_goals
from app.seed.hr_seed import seed_hr
from app.seed.product_seed import seed_product
from app.seed.risk_seed import seed_risk
from app.seed.sales_seed import seed_sales
from app.workers.consumers import load_metric_providers


async def _user(session: AsyncSession, email: str) -> uuid.UUID | None:
    return (await session.execute(select(User.id).where(User.email == email))).scalar()


__all__ = ["SeedReport", "main", "run"]


async def run() -> SeedReport:
    async with get_sessionmaker()() as session:
        report = await seed_auth(session)
        await session.flush()
        cfo = await _user(session, "cfo@abc.demo")
        hr, sales = await _user(session, "hr@abc.demo"), await _user(session, "sales@abc.demo")
        if cfo is not None:
            for group, n in (await seed_finance(session, cfo)).items():
                logging.info("seed finance.%s: %d", group, n)
        if hr is not None and cfo is not None:
            for group, n in (await seed_hr(session, hr, cfo)).items():
                logging.info("seed hr.%s: %d", group, n)
        if sales is not None:
            for group, n in (await seed_sales(session, sales)).items():
                logging.info("seed sales.%s: %d", group, n)
        ceo = await _user(session, "ceo@abc.demo")
        cpo = await _user(session, "cpo@abc.demo") or ceo
        groups = (
            ("product", seed_product(session, cpo)),
            ("risk", seed_risk(session, ceo)),
            ("execution", seed_execution(session, ceo)),
            ("execution", seed_goals(session, ceo)),  # M1.4 — upsert, not skip-flagged
        )
        for name, job in groups:
            for group, n in (await job).items():
                logging.info("seed %s.%s: %d", name, group, n)
        today = business_today()
        logging.info(
            "seed hr.late_hiring: %d", len(await detect_delayed_hiring_plans(session, today))
        )
        logging.info("seed platform.metrics: %d", await seed_catalog(session))
        load_metric_providers()
        logging.info("seed platform.recompute: %s", await MetricStore(session).recompute(today))
        await session.commit()
    await get_engine().dispose()
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with tenant_scope(DEFAULT_TENANT_ID):  # R-DEC-21: seed writes as the MVP system tenant
        report = asyncio.run(run())
    for outcome in ("created", "updated", "unchanged", "skipped"):
        logging.info("seed %s: %d", outcome, report.count(outcome))
