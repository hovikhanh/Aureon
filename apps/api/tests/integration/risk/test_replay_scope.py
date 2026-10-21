"""TC-RSK-002 (bổ sung) — Idempotency-Key replay on every risk POST, scope edge cases."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.modules.risk.services.dashboard_service import RiskDashboardService
from tests.conftest import ApiClient
from tests.integration.risk.helpers import OWNER, make_risk, risk_body

Data = dict[str, object]


async def _twice(
    api: ApiClient, url: str, json: Data, role: str = "RISK_MANAGER"
) -> tuple[Data, Data]:
    h = api.headers(role, user_id=uuid.uuid4(), idem=True)  # same user + key twice
    first = await api.call("POST", url, role, json=json, headers=h)
    second = await api.call("POST", url, role, json=json, headers=h)
    assert first.status_code in (200, 201), first.text
    assert second.status_code == first.status_code
    return first.json()["data"], second.json()["data"]


async def test_idempotent_replays(api: ApiClient) -> None:
    a, b = await _twice(api, "/risk/risks", risk_body())
    assert a["id"] == b["id"]
    rid = str(a["id"])
    a, b = await _twice(api, f"/risk/risks/{rid}/assessments", {"likelihood": 4, "impact": 4})
    assert a["id"] == b["id"]
    mit = {"risk_id": rid, "title": "m", "owner_id": OWNER, "due_date": "2037-12-31"}
    a, b = await _twice(api, "/risk/mitigations", mit)
    assert a["id"] == b["id"]
    a, b = await _twice(api, f"/risk/risks/{rid}/status", {"to_status": "monitoring"})
    assert a["version"] == b["version"]
    a, b = await _twice(api, "/risk/scenarios", {"risk_ids": [rid], "horizon_months": 3}, "CEO")
    assert a["scenario_id"] == b["scenario_id"]
    a, b = await _twice(api, f"/risk/risks/{rid}/accept", {"reason": "đồng ý"}, "CEO")
    assert a["status"] == b["status"] == "accepted"


async def test_manager_write_scope_and_linked_reader(
    api: ApiClient, db_session: AsyncSession
) -> None:
    dept = uuid.uuid4()
    foreign = await make_risk(api, likelihood=1, impact=1, owner_id=None)
    patch = await api.call("PATCH", f"/risk/risks/{foreign['id']}", "MANAGER", department_id=dept,
                           json={"version": foreign["version"], "title": "x"})  # fmt: skip
    assert patch.status_code == 403
    mine = await make_risk(api, "MANAGER", department_id=dept, likelihood=1, impact=1,
                           owner_id=None)  # fmt: skip
    body = {"version": mine["version"], "department_id": str(dept)}
    url = f"/risk/risks/{mine['id']}"
    moved = await api.call("PATCH", url, "MANAGER", department_id=dept, json=body)
    assert moved.status_code == 200
    unlinked = await make_risk(api, category="legal", likelihood=1, impact=1, owner_id=None)
    assert (await api.call("GET", f"/risk/risks/{unlinked['id']}", "CPO")).status_code == 403
    cpo = Principal(user_id=uuid.uuid4(), role="CPO")
    dash = await RiskDashboardService(db_session).dashboard(cpo, None, today=date(2037, 1, 1))
    assert dash.pillar == "S"  # scoped register path (linked filter applied)
