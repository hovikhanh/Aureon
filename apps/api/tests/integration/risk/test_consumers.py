"""TC-RSK-003 — event consumers auto-propose risks, idempotent (T-212, BR-RSK-03, DEC-218)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.events.bus import REGISTRY
from app.core.events.envelope import EventEnvelope
from app.modules.risk.models import Risk, RiskAssessment
from app.workers.consumers import load_consumers
from tests.integration.risk.helpers import outbox_for, types


def env(event_type: str, **payload: Any) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid.uuid4(), event_type=event_type, occurred_at=datetime.now(UTC),
        producer=event_type.split(".")[0], payload=payload,
        tenant_id=DEFAULT_TENANT_ID,
    )  # fmt: skip


async def run(db: AsyncSession, name: str, event: EventEnvelope) -> None:
    load_consumers()
    await REGISTRY.get(name)(db, event)
    await db.flush()


async def risks_for(db: AsyncSession, key: str, value: str) -> list[Risk]:
    stmt = select(Risk).where(Risk.linked_entities[key].astext == value)
    return list((await db.execute(stmt)).scalars().all())


async def test_hiring_plan_delayed_creates_proposed(db_session: AsyncSession) -> None:
    plan, dept = str(uuid.uuid4()), str(uuid.uuid4())
    e = env("hr.hiring_plan_delayed", hiring_plan_id=plan, department_id=dept, days_late=35,
            unfilled=2)  # fmt: skip
    await run(db_session, "risk.on_hiring_plan_delayed", e)
    [r] = await risks_for(db_session, "hiring_plan_id", plan)
    assert (r.status, r.risk_source, r.category, r.owner_id) == (
        "proposed",
        "event",
        "people",
        None,
    )
    assert r.source_event_id == e.event_id and str(r.department_id) == dept
    assert (r.likelihood, r.impact, r.severity) == (3, 3, "medium")
    ev = await outbox_for(db_session, str(r.id))
    assert types(ev) == ["risk.risk_proposed"] and ev[0][1]["risk_source"] == "event"
    await run(db_session, "risk.on_hiring_plan_delayed", e)  # same event replayed
    assert len(await risks_for(db_session, "hiring_plan_id", plan)) == 1
    later = env("hr.hiring_plan_delayed", hiring_plan_id=plan, department_id=dept, days_late=50)
    await run(db_session, "risk.on_hiring_plan_delayed", later)  # same aggregate → re-assess
    [r] = await risks_for(db_session, "hiring_plan_id", plan)
    await db_session.refresh(r)
    assert (r.likelihood, r.impact, r.severity, r.status) == (4, 3, "high", "proposed")
    n = select(func.count()).where(RiskAssessment.risk_id == r.id)
    assert (await db_session.execute(n)).scalar_one() == 1
    assert types(await outbox_for(db_session, str(r.id))) == ["risk.risk_proposed"]
    await run(db_session, "risk.on_hiring_plan_delayed", env("hr.hiring_plan_delayed",
              hiring_plan_id=plan, days_late=60))  # fmt: skip
    assert len(await risks_for(db_session, "hiring_plan_id", plan)) == 1  # no score change


async def test_finance_and_sales_events(db_session: AsyncSession) -> None:
    budget = str(uuid.uuid4())
    await run(db_session, "risk.on_budget_exceeded", env(
        "finance.budget_exceeded", budget_id=budget, department_id=str(uuid.uuid4()),
        budget_utilization_pct=120.0))  # fmt: skip
    [b] = await risks_for(db_session, "budget_id", budget)
    assert (b.category, b.likelihood, b.impact) == ("financial", 4, 3)
    key = f"2037-0{uuid.uuid4().int % 9 + 1}-{uuid.uuid4().hex[:6]}"
    await run(db_session, "risk.on_burn_over_forecast", env(
        "finance.burn_over_forecast", period_key=key, severity="critical"))  # fmt: skip
    [burn] = await risks_for(db_session, "burn_period_key", key)
    assert burn.severity == "critical"
    small, big = str(uuid.uuid4()), str(uuid.uuid4())
    await run(db_session, "risk.on_deal_closed_lost", env(
        "sales.deal_closed_lost", deal_id=small, deal_value=999_999_999))  # fmt: skip
    await run(db_session, "risk.on_deal_closed_lost", env(
        "sales.deal_closed_lost", deal_id=big, client_id=str(uuid.uuid4()),
        deal_value=6_000_000_000))  # fmt: skip
    assert await risks_for(db_session, "deal_id", small) == []
    [d] = await risks_for(db_session, "deal_id", big)
    assert d.category == "customer" and "client_id" in d.linked_entities and d.impact == 4


async def test_product_and_forecast_events(db_session: AsyncSession) -> None:
    prod = str(uuid.uuid4())
    await run(db_session, "risk.on_metric_anomaly", env(
        "product.metric_anomaly", product_id=prod, product_metric_id=str(uuid.uuid4()),
        metric="churn_rate_pct", value=9.0, baseline=3.0))  # fmt: skip
    [p] = await risks_for(db_session, "product_id", prod)
    assert p.category == "business"
    fc = str(uuid.uuid4())
    await run(db_session, "risk.on_forecast_updated", env(
        "finance.forecast_updated", forecast_id=fc, scenario="best",
        projected_net_profit_total=-1))  # fmt: skip
    await run(db_session, "risk.on_forecast_updated", env(
        "finance.forecast_updated", forecast_id=fc, scenario="base",
        projected_net_profit_total=500))  # fmt: skip
    assert await risks_for(db_session, "forecast_id", fc) == []
    await run(db_session, "risk.on_forecast_updated", env(
        "finance.forecast_updated", forecast_id=fc, scenario="base",
        projected_net_profit_total=-5))  # fmt: skip
    assert len(await risks_for(db_session, "forecast_id", fc)) == 1
    cf = str(uuid.uuid4())
    await run(db_session, "risk.on_cash_flow_forecast_updated", env(
        "finance.cash_flow_forecast_updated", forecast_id=cf, min_projected_cash=10))  # fmt: skip
    assert await risks_for(db_session, "forecast_id", cf) == []
    await run(db_session, "risk.on_cash_flow_forecast_updated", env(
        "finance.cash_flow_forecast_updated", forecast_id=cf, min_projected_cash=-10))  # fmt: skip
    [c] = await risks_for(db_session, "forecast_id", cf)
    assert c.severity == "critical" and c.status == "proposed"


async def test_missing_payload_ignored(db_session: AsyncSession) -> None:
    before = (await db_session.execute(select(func.count()).select_from(Risk))).scalar_one()
    await run(db_session, "risk.on_hiring_plan_delayed", env("hr.hiring_plan_delayed"))
    await run(db_session, "risk.on_metric_anomaly", env("product.metric_anomaly"))
    after = (await db_session.execute(select(func.count()).select_from(Risk))).scalar_one()
    assert after == before
