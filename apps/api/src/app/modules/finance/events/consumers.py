"""Finance consumers (10 §8.3): recompute the 13-week cash flow (EP-128) on invoice / salary
changes. Idempotency is handled by `processed_events` in `core.events.consumer`; never
re-publishes the event being processed (it publishes `cash_flow_forecast_updated`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import consumer
from app.core.events.envelope import EventEnvelope
from app.modules.finance.services.cash_flow_service import recompute_on_event


@consumer("finance.on_invoice_created", "finance.invoice_created")
async def on_invoice_created(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_on_event(session, reason=event.event_type)


@consumer("finance.on_invoice_paid", "finance.invoice_paid")
async def on_invoice_paid(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_on_event(session, reason=event.event_type)


@consumer("finance.on_salary_updated", "hr.salary_updated")
async def on_salary_updated(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_on_event(session, reason=event.event_type)
