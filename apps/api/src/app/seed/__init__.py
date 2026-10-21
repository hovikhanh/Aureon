"""`uv run python -m app.seed` — the ONLY seed command (DEC-062), idempotent.

S0 (T-008): 10 roles + demo users. Domain data (08 company ABC) is added by S1+ tasks.
v1 data is not migrated — reset seed (DEC-178).
"""

import asyncio
import logging

from app.core.db import get_engine, get_sessionmaker
from app.seed.auth_seed import SeedReport, seed_auth

__all__ = ["SeedReport", "main", "run"]


async def run() -> SeedReport:
    async with get_sessionmaker()() as session:
        report = await seed_auth(session)
        await session.commit()
    await get_engine().dispose()
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = asyncio.run(run())
    for outcome in ("created", "updated", "unchanged", "skipped"):
        logging.info("seed %s: %d", outcome, report.count(outcome))
