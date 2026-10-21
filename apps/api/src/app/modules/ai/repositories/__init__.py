"""`ai` repositories."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import ModelCallLog


class ModelCallLogRepository:
    """ENT-ModelCallLog — append-only (insert + aggregate reads only)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, row: ModelCallLog) -> uuid.UUID:
        self.db.add(row)
        await self.db.flush()
        return row.id

    async def cost_since(self, since: datetime) -> int:
        stmt = select(func.coalesce(func.sum(ModelCallLog.estimated_cost_micro_usd), 0)).where(
            ModelCallLog.created_at >= since
        )
        return int((await self.db.execute(stmt)).scalar_one())


def month_start(now: datetime | None = None) -> datetime:
    n = now or datetime.now(UTC)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
