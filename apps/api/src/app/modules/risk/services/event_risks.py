"""BR-RSK-03 (T-212, DEC-148, DEC-218): domain events → `proposed` risks with `risk_source=event`.

Idempotency, two layers:
1. `processed_events (event_id, consumer)` in `core.events.consumer` + UQ `source_event_id`
   (a replayed event never creates a second risk);
2. an open (non-terminal) risk of the same category linked to the same source aggregate is
   re-assessed (score only goes up) instead of creating a new one.
Default likelihood × impact per event = `RISK_EVENT_SCORING` below (03 BR-RSK-03 config).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.envelope import EventEnvelope
from app.modules.risk.models import Risk
from app.modules.risk.repositories import RiskRepository
from app.modules.risk.schemas import AssessmentIn
from app.modules.risk.services.risk_service import RiskService

RISK_LOST_DEAL_MIN_VALUE = 1_000_000_000  # 03 BR-RSK-03 default (1 tỷ VND)
FORECAST_PROFIT_DROP_PCT = 20.0
# event_type → (category, likelihood, impact, escalated likelihood, escalated impact)
RISK_EVENT_SCORING: dict[str, tuple[str, int, int, int, int]] = {
    "hr.hiring_plan_delayed": ("people", 3, 3, 4, 3),
    "finance.budget_exceeded": ("financial", 3, 3, 4, 3),
    "finance.burn_over_forecast": ("financial", 3, 3, 4, 4),
    "finance.forecast_updated": ("financial", 3, 4, 4, 4),
    "finance.cash_flow_forecast_updated": ("financial", 3, 4, 4, 5),
    "sales.deal_closed_lost": ("customer", 3, 3, 3, 4),
    "product.metric_anomaly": ("business", 3, 3, 4, 3),  # 10 "market" → `business` (05)
}


@dataclass(frozen=True)
class Proposal:
    title: str
    dedupe_key: str  # linked_entities key identifying the source aggregate
    escalated: bool = False
    links: dict[str, str] = field(default_factory=dict)
    department_id: str | None = None


def _s(p: dict[str, Any], key: str) -> str | None:
    v = p.get(key)
    return str(v) if v not in (None, "") else None


def _links(**kw: str | None) -> dict[str, str]:
    return {k: v for k, v in kw.items() if v is not None}


def proposal_for(event_type: str, p: dict[str, Any]) -> Proposal | None:
    """Pure mapping of one event payload to a proposal (`None` = below threshold / no data)."""
    if event_type == "hr.hiring_plan_delayed" and _s(p, "hiring_plan_id"):
        return Proposal(
            "Kế hoạch tuyển dụng trễ hạn", "hiring_plan_id", int(p.get("days_late") or 0) > 45,
            _links(hiring_plan_id=_s(p, "hiring_plan_id"), department_id=_s(p, "department_id")),
            _s(p, "department_id"),
        )  # fmt: skip
    if event_type == "finance.budget_exceeded" and _s(p, "budget_id"):
        return Proposal(
            "Chi tiêu vượt ngân sách", "budget_id",
            float(p.get("budget_utilization_pct") or 0) > 110,
            _links(budget_id=_s(p, "budget_id"), department_id=_s(p, "department_id")),
            _s(p, "department_id"),
        )  # fmt: skip
    if event_type == "finance.burn_over_forecast" and _s(p, "period_key"):
        return Proposal("Tốc độ đốt tiền vượt dự báo", "burn_period_key",
                        p.get("severity") == "critical",
                        {"burn_period_key": str(p["period_key"])})  # fmt: skip
    if event_type == "sales.deal_closed_lost" and _s(p, "deal_id"):
        if int(p.get("deal_value") or 0) < RISK_LOST_DEAL_MIN_VALUE:
            return None
        return Proposal("Mất deal giá trị lớn", "deal_id",
                        int(p["deal_value"]) >= 5 * RISK_LOST_DEAL_MIN_VALUE,
                        _links(deal_id=_s(p, "deal_id"), client_id=_s(p, "client_id")))  # fmt: skip
    if event_type == "product.metric_anomaly" and _s(p, "product_id"):
        return Proposal("Chỉ số sản phẩm bất thường", "product_id", False,
                        _links(product_id=_s(p, "product_id"),
                               product_metric_id=_s(p, "product_metric_id")))  # fmt: skip
    if event_type == "finance.forecast_updated" and p.get("scenario") == "base":
        profit = p.get("projected_net_profit_total")
        baseline = p.get("previous_net_profit_total")
        if profit is None or not _profit_dropped(int(profit), baseline):
            return None
        return Proposal("Dự báo lợi nhuận kịch bản cơ sở giảm mạnh", "forecast_scenario",
                        int(profit) < 0, {"forecast_scenario": "base",
                                          **_links(forecast_id=_s(p, "forecast_id"))})  # fmt: skip
    if event_type == "finance.cash_flow_forecast_updated" and _s(p, "forecast_id"):
        if int(p.get("min_projected_cash") or 0) >= 0:
            return None
        links = {"cash_flow": "13w", **_links(forecast_id=_s(p, "forecast_id"))}
        return Proposal("Dòng tiền 13 tuần dự báo âm", "cash_flow", True, links)
    return None


def _profit_dropped(profit: int, baseline: Any) -> bool:
    """> 20% drop vs the previous base forecast when the payload carries it; otherwise a
    projected loss is the only signal available (DEC-218)."""
    if baseline is None:
        return profit < 0
    base = int(baseline)
    if base <= 0:
        return profit < base
    return (base - profit) * 100 / base > FORECAST_PROFIT_DROP_PCT


async def handle_event(db: AsyncSession, event: EventEnvelope) -> Risk | None:
    """Create or re-assess the proposed risk for `event`; returns the risk touched (or None)."""
    prop = proposal_for(event.event_type, event.payload)
    if prop is None:
        return None
    repo = RiskRepository(db)
    if (dup := await repo.by_source_event(event.event_id)) is not None:
        return dup
    category, li, im, eli, eim = RISK_EVENT_SCORING[event.event_type]
    likelihood, impact = (eli, eim) if prop.escalated else (li, im)
    svc = RiskService(db)
    existing = await repo.open_for_link(category, prop.dedupe_key, prop.links[prop.dedupe_key])
    if existing is not None:
        await repo.lock(existing)
        new_l, new_i = max(existing.likelihood, likelihood), max(existing.impact, impact)
        unowned = existing.status != "proposed" and existing.owner_id is None
        if (new_l, new_i) != (existing.likelihood, existing.impact) and not (
            unowned and new_l * new_i >= 5
        ):
            note = f"event {event.event_type}"
            await svc.apply_assessment(existing, AssessmentIn(likelihood=new_l, impact=new_i,
                                                              note=note), actor=None)  # fmt: skip
        return existing
    dept = uuid.UUID(prop.department_id) if prop.department_id else None
    return await svc.propose(
        title=prop.title, category=category, likelihood=likelihood, impact=impact,
        risk_source="event", linked_entities=prop.links, department_id=dept,
        description=f"Tự sinh từ {event.event_type}", source_event_id=event.event_id,
    )  # fmt: skip
