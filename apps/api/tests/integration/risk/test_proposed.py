"""TC-RSK-006 — proposed lifecycle: `proposed → identified | rejected` (EP-106, T-215, DEC-148)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessRuleError
from app.modules.risk.services.risk_service import RiskService
from tests.conftest import ApiClient
from tests.integration.risk.helpers import OWNER, audit_actions, outbox_for, set_status, types


async def _propose(db: AsyncSession, **kw: object) -> str:
    args: dict[str, object] = {
        "title": "Tuyển dụng trễ", "category": "people", "likelihood": 4, "impact": 3,
        "risk_source": "event", "linked_entities": {"hiring_plan_id": str(uuid.uuid4())},
        "source_event_id": uuid.uuid4(), **kw,
    }  # fmt: skip
    risk = await RiskService(db).propose(**args)
    return str(risk.id)


async def test_propose_then_confirm(api: ApiClient, db_session: AsyncSession) -> None:
    rid = await _propose(db_session)
    got = (await api.call("GET", f"/risk/risks/{rid}", "CEO")).json()["data"]
    assert got["status"] == "proposed" and got["owner_id"] is None
    assert got["risk_source"] == "event" and got["proposed_at"] and got["level"] == "high"
    params = {"status": "proposed", "risk_source": "event", "limit": 100}
    queue = await api.call("GET", "/risk/risks", "RISK_MANAGER", params=params)
    assert rid in [x["id"] for x in queue.json()["data"]]
    ev = await outbox_for(db_session, rid)
    assert types(ev) == ["risk.risk_proposed"]
    assert ev[0][1]["risk_source"] == "event" and "hiring_plan_id" in ev[0][1]["linked_entities"]
    assert (await set_status(api, rid, "identified")).status_code == 422  # owner required
    assert (await set_status(api, rid, "mitigating", owner_id=OWNER)).status_code == 409
    ok = await set_status(api, rid, "identified", owner_id=OWNER)
    d = ok.json()["data"]
    assert ok.status_code == 200 and d["status"] == "identified"
    assert d["confirmed_by"] and d["confirmed_at"] and d["owner_id"] == OWNER
    assert types(await outbox_for(db_session, rid)) == [
        "risk.risk_proposed",
        "risk.risk_identified",
    ]
    assert await audit_actions(db_session, rid) == ["risk.risk_propose", "risk.risk_status_change"]


async def test_propose_reject_requires_reason(api: ApiClient, db_session: AsyncSession) -> None:
    rid = await _propose(db_session, risk_source="ai", source_event_id=None, likelihood=1)
    assert (await set_status(api, rid, "rejected")).status_code == 422
    assert (await set_status(api, rid, "rejected", reason="  ")).status_code == 422
    res = await set_status(api, rid, "rejected", reason="Không phải rủi ro")
    assert res.status_code == 200 and res.json()["data"]["status"] == "rejected"
    assert (await set_status(api, rid, "identified", owner_id=OWNER)).status_code == 409
    accept = await api.call("POST", f"/risk/risks/{rid}/accept", "CEO", json={"reason": "abc"})
    assert accept.status_code == 409
    p = await api.call(
        "PATCH", f"/risk/risks/{rid}", "RISK_MANAGER", json={"title": "x", "version": 2}
    )
    assert p.status_code == 409
    low = await _propose(db_session, source_event_id=None, likelihood=1, impact=1)
    res = await set_status(api, low, "identified", owner_id=OWNER)
    assert types(await outbox_for(db_session, low)) == ["risk.risk_proposed"]  # low: no event


async def test_propose_guards_and_document_source(db_session: AsyncSession) -> None:
    with pytest.raises(BusinessRuleError):
        await _propose(db_session, risk_source="manual")
    with pytest.raises(BusinessRuleError):
        await _propose(db_session, category="market")
    rid = await _propose(db_session, risk_source="document", source_event_id=None,
                         source_document_id=uuid.uuid4())  # fmt: skip
    assert rid
