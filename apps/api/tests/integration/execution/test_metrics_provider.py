"""T-133 — `compute(db, as_of)` over real rows in a far-future month (TC-EXE-006)."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services.metrics import compute
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make, make_strategic_objective, make_task, uniq

pytestmark = pytest.mark.integration
AS_OF = date(2041, 3, 20)


async def test_compute_execution_metrics(api: ApiClient, db_session: AsyncSession) -> None:
    empty = {r.code: r for r in await compute(db_session, date(2041, 2, 10))}
    assert empty["METRIC-OPS-01"].value is None and empty["METRIC-RSK-06"].value is None
    emp = uuid.uuid4()
    late = await make_task(api, due_date="2041-03-05", assignee_id=str(emp), estimate_hours="50")
    await make_task(api, due_date="2041-03-06", status="cancelled")
    await make_task(api, due_date="2041-03-25")  # not yet due at AS_OF
    m = await make(api, "/execution/meetings", {"title": "h", "held_at": "2041-03-01T08:00:00Z"})
    await make_task(api, due_date="2041-03-07", meeting_id=m["id"], task_source="meeting")
    p = await make(api, "/work/projects", {
        "code": uniq("PRJ"), "name": "p", "owner_id": str(emp), "status": "active",
        "start_date": "2041-01-01", "due_date": "2041-03-31"})  # fmt: skip
    await make_task(api, project_id=p["id"], due_date="2041-04-30")
    o = await make(api, "/objectives", {"title": "o", "owner_id": str(emp),
                                                  "period_key": "2041"})  # fmt: skip
    i = await make(api, "/goals/initiatives", {
        "code": uniq("INI"), "title": "i", "objective_id": o["id"], "owner_id": str(emp),
        "strategic_objective_id": (await make_strategic_objective(api))["id"],
        "start_date": "2041-01-01", "planned_end_date": "2041-12-31", "status": "active",
        "weight_pct": 10})  # fmt: skip
    got = {r.code: r for r in await compute(db_session, AS_OF)}
    assert set(got) == {"METRIC-OPS-01", "METRIC-OPS-02", "METRIC-OPS-03", "METRIC-HR-03",
                        "METRIC-RSK-06"}  # fmt: skip
    assert all(r.period_key == "2041-03" and r.scope_type == "company" for r in got.values())
    ops1 = got["METRIC-OPS-01"]
    assert ops1.value == 0.0 and late["id"] in {x.id for x in ops1.records}
    assert got["METRIC-OPS-03"].value == 0.0
    assert p["id"] in {x.id for x in got["METRIC-OPS-02"].records}
    assert got["METRIC-HR-03"].value is not None
    assert i["id"] in {x.id for x in got["METRIC-RSK-06"].records}
    assert all(len(r.records) <= 50 for r in got.values())
