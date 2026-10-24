"""Platform consumers (10 §8.3): domain event → recompute dependent metrics → alerts (T-221).

One consumer per source module so each dedupes independently (`processed_events`). It recomputes
the metrics of the producing module (and the event's other platform-relevant module, e.g.
`finance.invoice_paid` → finance + sales NRR). Never re-publishes the event it handles.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.core.events.bus import consumer
from app.core.events.envelope import EventEnvelope
from app.modules.platform.services.metric_store import MetricStore

# event → provider modules to recompute (10 §8.3 "platform: …" column)
AFFECTS: dict[str, set[str]] = {
    "finance.budget_exceeded": {"finance"},
    "finance.burn_over_forecast": {"finance"},
    "finance.forecast_updated": {"finance"},
    "finance.invoice_created": {"finance"},
    "finance.invoice_paid": {"finance", "sales"},
    "finance.cash_flow_forecast_updated": {"finance"},
    "hr.employee_onboarded": {"hr"},
    "hr.employee_terminated": {"hr"},
    "hr.hiring_plan_delayed": {"hr"},
    "sales.deal_closed_won": {"sales"},
    "sales.deal_closed_lost": {"sales"},
    "product.metric_anomaly": {"product"},
    "product.feature_released": {"product"},
    "risk.risk_identified": {"risk"},
    "risk.risk_level_changed": {"risk"},
    "risk.risk_mitigated": {"risk"},
    "execution.task_overdue": {"execution"},
    "execution.task_created": {"execution"},  # R-DEC-47 — OPS-01 / HR-03
    "execution.task_completed": {"execution"},  # R-DEC-47 — OPS-01 / OPS-02
    "execution.kpi_measured": {"execution"},
    "idp.document_committed": {"finance", "sales", "hr", "product", "risk", "execution"},
    "idp.document_rolled_back": {"finance", "sales", "hr", "product", "risk", "execution"},
}


async def recompute_for(session: AsyncSession, event: EventEnvelope) -> None:
    await MetricStore(session).recompute(business_today(), AFFECTS[event.event_type])


def _group(prefix: str) -> tuple[str, ...]:
    return tuple(sorted(e for e in AFFECTS if e.startswith(prefix)))


@consumer("platform.on_finance_event", *_group("finance."))
async def on_finance_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_hr_event", *_group("hr."))
async def on_hr_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_sales_event", *_group("sales."))
async def on_sales_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_product_event", *_group("product."))
async def on_product_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_risk_event", *_group("risk."))
async def on_risk_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_execution_event", *_group("execution."))
async def on_execution_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)


@consumer("platform.on_idp_event", *_group("idp."))
async def on_idp_event(session: AsyncSession, event: EventEnvelope) -> None:
    await recompute_for(session, event)
