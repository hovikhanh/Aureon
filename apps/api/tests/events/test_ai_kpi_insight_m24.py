"""TC-M24-04 — AI consumer `ai.on_kpi_below_threshold` turns a KPI breach into a 9-part grounded
insight with an L2 recommendation (R-DEC-108, UC-03). Importing the module registers the consumer.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import REGISTRY
from app.core.events.envelope import EventEnvelope
from app.modules.ai.events import consumers as ai_consumers  # import registers the consumer
from app.modules.ai.models import Insight
from app.modules.ai.services.insight_service import REQUIRED_PARTS, InsightService

pytestmark = pytest.mark.integration

EVENT = "execution.kpi_below_threshold"


def _payload(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "kpi_id": str(uuid.uuid4()),
        "kpi_code": "KPI-REV",
        "period_key": "2037-06",
        "evaluation_id": str(uuid.uuid4()),
        "achievement_pct": "42.5",
        "band": "CRITICAL",
        "previous_band": "BELOW",
        "gap_value": "40.000000",
        "owner_id": None,
        "department_id": None,
    }
    base.update(over)
    return base


def _envelope(payload: dict[str, object]) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid.uuid4(), event_type=EVENT, occurred_at=datetime.now(UTC),
        version=1, tenant_id=None, producer="execution", payload=payload,
    )  # fmt: skip


def test_ai_consumer_is_registered_for_the_kpi_event() -> None:
    assert "ai.on_kpi_below_threshold" in REGISTRY.consumers_for(EVENT)


async def test_kpi_breach_creates_9part_insight_with_l2_recommendation(
    db_session: AsyncSession,
) -> None:
    await ai_consumers.on_kpi_below_threshold(db_session, _envelope(_payload()))
    rows = (await db_session.execute(select(Insight).where(Insight.source == "AI"))).scalars().all()
    ins = [i for i in rows if i.body.startswith("KPI KPI-REV")]
    assert ins, "a KPI breach must raise one AI insight"
    i = ins[-1]
    assert i.kind == "recommendation" and i.severity == "CRITICAL"
    assert set(REQUIRED_PARTS) <= set(i.structured), "all 9 parts present"
    assert i.sources and i.sources[0]["value"] == 42.5  # grounded on the KPI value
    # the recommendation is L2 — a task proposal the MGR must approve (never auto-executed)
    action = i.structured["action"][0]
    assert action["autonomy_level"] == "L2" and action["tool"] == "TOOL-create_task"
    assert i.structured["owner"] == "MGR"


async def test_missing_achievement_pct_yields_no_insight(db_session: AsyncSession) -> None:
    out = await InsightService(db_session).generate_for_kpi(_payload(achievement_pct=None))
    assert out is None


async def test_critical_vs_below_severity(db_session: AsyncSession) -> None:
    below = await InsightService(db_session).generate_for_kpi(
        _payload(band="BELOW", kpi_code="KPI-BELOW")
    )
    assert below is not None and below.severity == "WARNING"
