"""Public service interface of `dashboard` — EP-11/12/15/16/17 + pillar status (T-220..222).

Reads the metric store only through `platform` public services (DTOs). Pillar visibility
(02 §5.4): a pillar is visible when the caller holds `<domain>:query` of its module (aggregate
`○` included); out-of-scope pillars are **absent** from lists (CLAUDE §5.3) and 403 on detail.
VP_SALES / HR_MANAGER / CPO see only METRIC-FIN-01 of pillar F (their `finance:query ○`).
"""

import uuid
from dataclasses import asdict
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.envelope import Page
from app.core.errors import NotFoundError, ScopeDeniedError
from app.modules.dashboard.schemas import (
    AlertOut,
    BreakdownRow,
    DataSource,
    MetricDetail,
    MetricValueOut,
    Pillar,
    PillarCard,
    PillarState,
    Thresholds,
    TrendPoint,
)
from app.modules.platform.services.metric_query import AlertDTO, MetricQueryService

PILLAR_DOMAIN = {"F": "finance", "O": "hr", "C": "sales", "U": "product", "S": "risk"}
PILLARS = ("F", "O", "C", "U", "S")
FIN_FULL_ROLES = {"CEO", "CFO", "RISK_MANAGER"}
NO_DATA_RATIO = 0.5  # PILLAR_NO_DATA_RATIO (03 §4)
_RANK = {"ok": 0, "warning": 1, "critical": 2}
DATA_SOURCES = {
    "finance": ["ENT-Revenue", "ENT-Expense", "ENT-Invoice", "ENT-Budget", "ENT-CashPosition"],
    "sales": ["ENT-Deal", "ENT-SalesTarget", "ENT-Revenue"],
    "hr": ["ENT-Employee", "ENT-HiringPlan"],
    "product": ["ENT-Product", "ENT-ProductMetric", "ENT-RoadmapItem", "ENT-Release"],
    "risk": ["ENT-Risk", "ENT-Mitigation"],
    "execution": ["ENT-Task", "ENT-Project", "ENT-Decision", "ENT-Initiative"],
    "platform": ["ENT-MetricValue"],
}


def visible_pillars(user: Principal) -> set[str]:
    return {p for p, d in PILLAR_DOMAIN.items() if user.has(f"{d}:query")}


def metric_visible(user: Principal, code: str, pillar: str | None) -> bool:
    if pillar is None or pillar not in visible_pillars(user):
        return False
    if pillar == "F" and user.role not in FIN_FULL_ROLES:
        return code == "METRIC-FIN-01"
    return True


def pillar_status(statuses: list[str]) -> PillarState:
    if not statuses or statuses.count("no_data") / len(statuses) >= NO_DATA_RATIO:
        return "no_data"
    present = [s for s in statuses if s != "no_data"]
    return cast(PillarState, max(present, key=lambda s: _RANK[s]))


def alert_out(a: AlertDTO) -> AlertOut:
    d = asdict(a)
    d["message_key"] = f"alert.{a.alert_code.lower().replace('-', '_')}.{a.severity}"
    return AlertOut(**d)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.q = MetricQueryService(db)

    async def metrics(
        self, user: Principal, *, pillar: str | None = None, status: str | None = None
    ) -> list[MetricValueOut]:
        pillars = visible_pillars(user)
        if pillar is not None:
            pillars &= {pillar}
        rows = await self.q.current_values(pillars=pillars) if pillars else []
        out = [
            MetricValueOut(**asdict(v))
            for v in rows
            if metric_visible(user, v.metric_code, v.pillar)
        ]
        return [m for m in out if status is None or m.status == status]

    async def pillar_card(self, user: Principal, pillar: Pillar) -> PillarCard:
        ms = await self.metrics(user, pillar=pillar)
        alerts = await self.q.open_alert_count({pillar})
        return PillarCard(
            pillar=pillar, status=pillar_status([m.status for m in ms]),
            metrics_with_data=sum(m.status != "no_data" for m in ms), metrics_total=len(ms),
            open_alerts=alerts.get(pillar, 0),
        )  # fmt: skip

    async def detail(self, user: Principal, code: str, lang: str = "vi") -> MetricDetail:
        defs = {d.code: d for d in await self.q.definitions()}
        d = defs.get(code)
        if d is None:
            raise NotFoundError("metric not found", details={"metric_code": code})
        if not metric_visible(user, code, d.pillar):
            raise ScopeDeniedError("metric outside your pillars", details={"metric_code": code})
        cur = await self.q.current_values(codes={code})
        if not cur:
            raise NotFoundError("metric has no value yet", details={"metric_code": code})
        v = cur[0]
        alerts, _ = await self.q.list_alerts(
            pillars={d.pillar} if d.pillar else set(), status=None, severity=None,
            limit=10, offset=0, codes={code},
        )  # fmt: skip
        return MetricDetail(
            **asdict(v), name=d.name_en if lang == "en" else d.name_vi,
            formula_display=d.formula_ref or code,
            direction="up" if d.direction == "LOWER_IS_BAD" else "down",
            thresholds=Thresholds(warning=d.warning, critical=d.critical),
            trend=[TrendPoint(period_key=k, value=x) for k, x in await self.q.trend(code)],
            breakdown=[
                BreakdownRow(key=f"{t}:{i}", label=i, value=x, record_count=0)
                for t, i, x in await self.q.breakdown(code, v.period_key)
            ],
            related_alerts=[alert_out(a) for a in alerts],
            data_source=DataSource(
                module=d.source_module, entities=DATA_SOURCES.get(d.source_module, [])
            ),
        )  # fmt: skip

    async def alerts(
        self, user: Principal, *, status: str | None, severity: str | None, pillar: str | None,
        limit: int, offset: int,
    ) -> Page[AlertOut]:  # fmt: skip
        pillars = visible_pillars(user)
        if pillar is not None:
            pillars &= {pillar}
        codes = None
        if "F" in pillars and user.role not in FIN_FULL_ROLES:
            codes = {d.code for d in await self.q.definitions()
                     if metric_visible(user, d.code, d.pillar)}  # fmt: skip
        rows, total = await self.q.list_alerts(
            pillars=pillars, status=status, severity=severity, limit=limit, offset=offset,
            codes=codes,
        )  # fmt: skip
        return Page(items=[alert_out(a) for a in rows], total=total, limit=limit, offset=offset)

    async def _check_alert(self, user: Principal, id_: uuid.UUID) -> None:
        code, pillar = await self.q.alert_metric(id_)
        if not metric_visible(user, code, pillar):
            raise ScopeDeniedError("alert outside your pillars", details={"alert_id": str(id_)})

    async def acknowledge(self, user: Principal, id_: uuid.UUID, note: str | None) -> AlertOut:
        await self._check_alert(user, id_)
        return alert_out(await self.q.acknowledge(id_, user.user_id, note))

    async def dismiss(self, user: Principal, id_: uuid.UUID, reason: str) -> AlertOut:
        await self._check_alert(user, id_)
        return alert_out(await self.q.dismiss(id_, user.user_id, reason))
