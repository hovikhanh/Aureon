"""EP-105 what-if (FR-RSK-06, T-214, DEC-219).

Each domain is computed through that module's PUBLIC service only, wrapped in
`asyncio.wait_for(…, DOMAIN_TIMEOUT_S)`; timeout or any error → `{status: "unavailable"}` and
the other domains still answer. Result saved as `ENT-Scenario` (L0: no business data change).

Heuristic (no spec formula): every selected risk contributes `weight × likelihood/5 × impact/5`
of its category profile below; `assumptions` override the aggregated percentages.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.modules.hr.services.dashboard_service import HrDashboardService
from app.modules.hr.services.metrics import resolve_period
from app.modules.risk.models import Scenario
from app.modules.risk.repositories import RiskRepository
from app.modules.risk.schemas import (
    FinanceImpact,
    HrImpact,
    ProductImpact,
    SalesImpact,
    ScenarioAssumptions,
    ScenarioImpacts,
    ScenarioIn,
    ScenarioOut,
    SourceRef,
)
from app.modules.risk.services import scope
from app.modules.risk.services.common import audit, now_utc
from app.modules.sales.services.analytics import SalesAnalytics

DOMAIN_TIMEOUT_S = 5.0
# category → (revenue %, expense %, pipeline %, headcount %) lost at likelihood = impact = 5.
CATEGORY_PROFILE: dict[str, tuple[float, float, float, float]] = {
    "financial": (-10, 10, 0, 0), "operational": (-5, 5, 0, -2), "strategic": (-10, 0, -10, 0),
    "people": (-3, 5, 0, -10), "business": (-15, 0, -15, 0), "customer": (-15, 0, -20, 0),
    "product": (-5, 5, -5, 0), "technology": (-5, 10, 0, 0), "security": (-5, 10, 0, 0),
    "compliance": (0, 5, 0, 0), "legal": (0, 5, 0, 0), "partner_supplier": (-5, 5, 0, 0),
    "ai": (-3, 5, 0, 0),
}  # fmt: skip


@dataclass(frozen=True)
class Shock:
    revenue_pct: float
    expense_pct: float
    pipeline_pct: float
    headcount_pct: float
    extra_cost: int


def build_shock(risks: list[tuple[str, int, int]], a: ScenarioAssumptions | None) -> Shock:
    """Aggregate per-category profile (pure; clamped to −100..)."""
    tot = [0.0, 0.0, 0.0, 0.0]
    for category, li, im in risks:
        w = (li / 5) * (im / 5)
        for k, v in enumerate(CATEGORY_PROFILE[category]):
            tot[k] += v * w
    a = a or ScenarioAssumptions()

    def pick(over: float | None, val: float) -> float:
        return round(max(-100.0, over if over is not None else val), 2)

    return Shock(
        pick(a.revenue_change_pct, tot[0]), pick(a.expense_change_pct, tot[1]),
        pick(None, tot[2]), pick(a.headcount_change_pct, tot[3]), a.extra_monthly_cost or 0,
    )  # fmt: skip


async def guarded[T](call: Callable[[], Awaitable[T]]) -> T | None:
    """One domain call with the 5 s budget; any failure → `None` (= unavailable)."""
    try:
        return await asyncio.wait_for(call(), DOMAIN_TIMEOUT_S)
    except Exception:  # every domain failure degrades to `unavailable` (FR-RSK-06)
        return None


class ScenarioService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.risks = RiskRepository(db)

    async def run(self, user: Principal, body: ScenarioIn) -> ScenarioOut:
        ids = list(dict.fromkeys(body.risk_ids))
        rows = {r.id: r for r in await self.risks.scoped(*scope.read_filter(user))
                if r.id in set(ids)}  # fmt: skip
        if missing := [str(i) for i in ids if i not in rows]:
            raise NotFoundError("risk not found", details={"risk_ids": ",".join(missing)})
        shock = build_shock([(rows[i].category, rows[i].likelihood, rows[i].impact)
                             for i in ids], body.assumptions)  # fmt: skip
        sources: list[SourceRef] = []
        fin = await self._finance(shock, body.horizon_months, sources)
        sales = await self._sales(user, shock)
        hr = await self._hr(user, shock)
        impacts = ScenarioImpacts(finance=fin, sales=sales, hr=hr,
                                  product=ProductImpact(status="unavailable"))  # fmt: skip
        a = body.assumptions
        default_name = f"What-if {len(ids)} rủi ro × {body.horizon_months}T"
        obj = Scenario(
            name=(a.name if a and a.name else default_name),
            risk_ids=ids, horizon_months=body.horizon_months,
            assumptions=(a.model_dump(exclude_none=True) if a else {}),
            impact_domains=["finance", "sales", "hr", "product"],
            results={"impacts": impacts.model_dump(mode="json"),
                     "sources": [s.model_dump(mode="json") for s in sources]},
            run_at=now_utc(), source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self.db.flush()
        await audit(self.db, "risk.scenario_run", "scenarios", obj)
        return ScenarioOut(scenario_id=obj.id, impacts=impacts, sources=sources)

    async def _finance(self, s: Shock, horizon: int, sources: list[SourceRef]) -> FinanceImpact:
        svc = FinanceAnalyticsService(self.db)

        async def both() -> tuple[Any, Any]:
            base = await svc.what_if_runway(as_of=None, revenue_change_pct=0,
                                            expense_change_pct=0, extra_monthly_cost=0)  # fmt: skip
            shocked = await svc.what_if_runway(
                as_of=None, revenue_change_pct=s.revenue_pct, expense_change_pct=s.expense_pct,
                extra_monthly_cost=s.extra_cost,
            )  # fmt: skip
            return base, shocked

        got = await guarded(both)
        if got is None or got[0].avg_revenue_3m is None:
            return FinanceImpact(status="unavailable")
        base, shocked = got
        sources.extend(SourceRef.model_validate(x.model_dump()) for x in shocked.sources)
        runway = (None if base.runway_months is None or shocked.runway_months is None
                  else round(shocked.runway_months - base.runway_months, 1))  # fmt: skip
        return FinanceImpact(
            status="ok",
            revenue_delta=round(base.avg_revenue_3m * s.revenue_pct / 100 * horizon),
            expense_delta=round((base.avg_expense_3m * s.expense_pct / 100 + s.extra_cost)
                                * horizon),
            runway_delta_months=runway,
        )  # fmt: skip

    async def _sales(self, user: Principal, s: Shock) -> SalesImpact:
        got = await guarded(lambda: SalesAnalytics(self.db).pipeline(user, None, None))
        if got is None:
            return SalesImpact(status="unavailable")
        total = sum(st.value for st in got.stages if not st.stage.startswith("closed_"))
        return SalesImpact(status="ok", pipeline_delta=round(total * s.pipeline_pct / 100))

    async def _hr(self, user: Principal, s: Shock) -> HrImpact:
        today = now_utc().date()
        got = await guarded(lambda: HrDashboardService(self.db).dashboard(
            user, resolve_period(None, today), today))  # fmt: skip
        if got is None or got.summary.get("headcount") is None:
            return HrImpact(status="unavailable")
        hc = int(got.summary["headcount"])
        return HrImpact(status="ok", headcount_delta=round(hc * s.headcount_pct / 100))
