"""Risk consumers (10 §8.3, BR-RSK-03, T-212): auto-propose risks from domain events.

Idempotency: `processed_events` in `core.events.consumer` + `source_event_id` / source-aggregate
dedupe in `services/event_risks.py`. Publishes `risk.risk_proposed` (never re-publishes the
consumed event). `hr.employee_terminated` is not handled: key-person risk needs a "key person"
flag that 05 does not have (DEC-218).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import consumer
from app.core.events.envelope import EventEnvelope
from app.modules.risk.services.event_risks import handle_event


@consumer("risk.on_hiring_plan_delayed", "hr.hiring_plan_delayed")
async def on_hiring_plan_delayed(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_budget_exceeded", "finance.budget_exceeded")
async def on_budget_exceeded(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_burn_over_forecast", "finance.burn_over_forecast")
async def on_burn_over_forecast(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_forecast_updated", "finance.forecast_updated")
async def on_forecast_updated(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_cash_flow_forecast_updated", "finance.cash_flow_forecast_updated")
async def on_cash_flow_forecast_updated(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_deal_closed_lost", "sales.deal_closed_lost")
async def on_deal_closed_lost(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)


@consumer("risk.on_metric_anomaly", "product.metric_anomaly")
async def on_metric_anomaly(session: AsyncSession, event: EventEnvelope) -> None:
    await handle_event(session, event)
