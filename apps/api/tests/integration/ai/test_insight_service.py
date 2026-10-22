"""T-303 — proactive insights, 9-part grounded structure. TC-AI-010, TC-AI-011.

Runs against the seeded dev DB inside the rolled-back `db_session`. Generation grounds every
number in `ENT-MetricValue` (DashboardService), assembles the 9 structured parts, and persists;
the grounding gate drops an insight with zero evidence. Reads apply `audience_roles` + pillar
scope (02 §6). A scripted gateway supplies only the one-sentence observation narration.
"""

import uuid

import pytest

from app.core.deps import Principal
from app.core.model_gateway.types import ChatRequest, ChatResponse
from app.modules.ai.services.insight_service import REQUIRED_PARTS, InsightService
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.integration


def principal(role: str) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        role=role,
        permissions=frozenset(ROLE_PERMISSIONS[role]),
    )


class NarratorGateway:
    async def chat(self, req: ChatRequest) -> ChatResponse:
        return ChatResponse(content="Chỉ số trụ đang lệch ngưỡng.", provider="fixture", model="x")


async def _generate_all(svc: InsightService, author: Principal) -> list:
    out = []
    for pillar in ("F", "C", "O", "U", "S"):
        ins = await svc.generate_for_pillar(author, pillar)
        if ins is not None:
            out.append(ins)
    return out


async def test_generated_insight_has_9_parts_all_grounded(db_session) -> None:
    svc = InsightService(db_session, NarratorGateway())
    insights = await _generate_all(svc, principal("CEO"))
    assert insights, "seeded data should breach at least one pillar"
    for ins in insights:
        assert ins.kind in ("anomaly", "recommendation")
        assert set(REQUIRED_PARTS) <= set(ins.structured), "all 9 parts required"
        # every evidence source is a real metric with a lineage url (grounding, P05)
        assert ins.sources, "insight must keep ≥ 1 evidence (GAP D-15)"
        for ev in ins.sources:
            assert ev["type"] == "metric_value"
            assert ev["lineage_url"]
        assert ins.severity in ("WARNING", "CRITICAL")
        assert ins.source == "AI"
        assert "AI" not in str(ins.structured["owner"]).upper() or ins.structured["owner"] != "AI"


async def test_insight_owner_is_never_ai(db_session) -> None:
    svc = InsightService(db_session)
    insights = await _generate_all(svc, principal("CEO"))
    for ins in insights:
        assert ins.structured["owner"] != "AI"  # 01 §5A — AI is never the owner


async def test_reads_filter_by_audience_and_scope(db_session) -> None:
    svc = InsightService(db_session)
    await _generate_all(svc, principal("CEO"))
    ceo = await svc.list_for(principal("CEO"))
    hr = await svc.list_for(principal("HR_MANAGER"))
    emp = await svc.list_for(principal("EMPLOYEE"))
    assert len(ceo) >= len(hr), "CEO sees at least as many insights as HR"
    assert len(emp) == 0, "EMPLOYEE has no pillar scope → no insights"
    # HR only sees O-pillar insights (its audience + scope)
    assert all(i.pillar == "O" for i in hr)


async def test_dismiss_removes_from_active_list(db_session) -> None:
    svc = InsightService(db_session)
    await _generate_all(svc, principal("CEO"))
    before = await svc.list_for(principal("CEO"))
    assert before
    dismissed = await svc.dismiss(principal("CEO"), before[0].id)
    assert dismissed.id == before[0].id
    after = await svc.list_for(principal("CEO"))
    assert len(after) == len(before) - 1


async def test_pillar_without_breach_yields_no_insight(db_session) -> None:
    svc = InsightService(db_session)
    # generate twice for the same pillar set; a healthy pillar returns None
    results = [await svc.generate_for_pillar(principal("CEO"), p) for p in ("F", "C")]
    # F/C are healthy in the official demo layout (F🟢 C🟢) → None
    assert results == [None, None]


async def test_output_shape_matches_ep114(db_session) -> None:
    svc = InsightService(db_session, NarratorGateway())
    await _generate_all(svc, principal("CEO"))
    out = await svc.list_for(principal("CEO"))
    assert out
    o = out[0]
    assert o.confidence.band in ("high", "medium", "low")
    assert o.severity in ("info", "warning", "critical")
    assert o.recommendations, "recommendations carry the Action parts"
    assert all(ev.lineage_url for ev in o.evidence)
