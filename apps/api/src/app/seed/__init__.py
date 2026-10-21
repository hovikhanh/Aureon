"""`uv run python -m app.seed` — the ONLY seed command (DEC-062), idempotent.

S0 (T-008): 10 roles + demo users. S1 (T-101..106): finance data of company ABC (08).
v1 data is not migrated — reset seed (DEC-178).
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.db import get_engine, get_sessionmaker
from app.modules.auth.models import User
from app.seed.auth_seed import SeedReport, seed_auth
from app.seed.finance_seed import seed_finance

__all__ = ["SeedReport", "main", "run"]


async def run() -> SeedReport:
    async with get_sessionmaker()() as session:
        report = await seed_auth(session)
        await session.flush()
        cfo = (await session.execute(select(User.id).where(User.email == "cfo@abc.demo"))).scalar()
        if cfo is not None:
            for group, n in (await seed_finance(session, cfo)).items():
                logging.info("seed finance.%s: %d", group, n)
        await session.commit()
    await get_engine().dispose()
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = asyncio.run(run())
    for outcome in ("created", "updated", "unchanged", "skipped"):
        logging.info("seed %s: %d", outcome, report.count(outcome))
