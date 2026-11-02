"""AI event consumers (M2.4, R-DEC-108). Observe the event backbone (10 §9) to produce proactive
insights — the AI side of UC-03.

`ai.on_kpi_below_threshold` listens to the existing `execution.kpi_below_threshold` event (no new
event) and turns a KPI breach into a 9-part grounded `ENT-Insight` carrying an **L2** recommendation
(a task tied to the KPI that the MGR must approve — never auto-executed). `ai.on_okr_at_risk` does
the same for the existing `execution.okr_at_risk` event (M3.4, UC-04, R-DEC-143): a KR at-risk
transition → blocker analysis (the KR's reasons + the owner's overdue workload) → an L2
intervention recommendation. Dedupe + the single commit are handled by the consumer runner via
`processed_events (event_id, consumer)`; the handler only does the work and never republishes the
event it is handling.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import consumer
from app.core.events.envelope import EventEnvelope
from app.modules.ai.services.insight_service import InsightService


@consumer("ai.on_kpi_below_threshold", "execution.kpi_below_threshold")
async def on_kpi_below_threshold(session: AsyncSession, event: EventEnvelope) -> None:
    await InsightService(session).generate_for_kpi(event.payload)


@consumer("ai.on_okr_at_risk", "execution.okr_at_risk")
async def on_okr_at_risk(session: AsyncSession, event: EventEnvelope) -> None:
    await InsightService(session).generate_for_okr(event.payload)
