"""Revenue target registry — `finance` reads the team target of a period (METRIC-FIN-01).

`finance` may not import `sales` (`sales → finance` already exists for revenue by client), so
`sales` registers its public `team_revenue_target` here at import time (`app.modules.sales`
package init) — the `core/client_directory` pattern. Only the amount crosses the boundary. Without
a provider (a process that never imported `sales`) there is no target: FIN-01 reads `no_data`.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

TargetLookup = Callable[[AsyncSession, str], Awaitable[int | None]]

_LOOKUP: list[TargetLookup] = []


def register_revenue_target(lookup: TargetLookup) -> None:
    """Install the lookup (re-registration replaces it — idempotent on re-import)."""
    _LOOKUP[:] = [lookup]


async def team_revenue_target(db: AsyncSession, period_key: str) -> int | None:
    """Company team target of a period key (`YYYY-MM`, `YYYY-Qn`), or `None`."""
    return await _LOOKUP[0](db, period_key) if _LOOKUP else None
