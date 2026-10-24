"""`execution` source of the onboarding `progress` (EP-ADM-13, `core/onboarding`) — counts only."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.repositories import KpiRepository, ObjectiveRepository


async def execution_progress(db: AsyncSession) -> dict[str, Any]:
    return {
        "kpis": await KpiRepository(db).count(),
        "objectives": await ObjectiveRepository(db).count(),
    }
