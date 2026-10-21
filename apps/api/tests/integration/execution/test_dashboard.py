"""TC-EXE-007 (T-222): EP-49 `/execution/dashboard` — summary, heatmap, trend, scope, cache.

Data lives in a fresh department (MANAGER-scoped reads isolate it from seed / other tests).
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import business_today
from app.modules.execution.models import Task
from tests.conftest import ApiClient
from tests.integration.execution.helpers import make, make_task


async def test_execution_dashboard(api: ApiClient, db_session: AsyncSession) -> None:
    dept, alice, bob = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    today = business_today()
    start = date(today.year, today.month, 1)
    base = {"department_id": str(dept)}
    on_time = await make_task(api, assignee_id=str(alice), due_date=str(start), **base)
    late = await make_task(api, assignee_id=str(alice), due_date=str(start),
                           estimate_hours="45", **base)  # fmt: skip
    meeting = await make_task(api, assignee_id=str(bob), due_date=str(start),
                              task_source="meeting", **base)  # fmt: skip
    back = datetime.combine(start - timedelta(days=20), datetime.min.time(), tzinfo=UTC)
    ids = [uuid.UUID(t["id"]) for t in (on_time, late, meeting)]
    await db_session.execute(update(Task).where(Task.id.in_(ids)).values(created_at=back))
    await db_session.execute(update(Task).where(Task.id == ids[0])
                             .values(status="done", done_at=back))  # fmt: skip
    await make(api, "/execution/projects", {
        "code": f"P-{uuid.uuid4().hex[:6]}", "name": "Late", "owner_id": str(alice),
        "status": "active", "start_date": str(start - timedelta(days=60)),
        "due_date": str(start + timedelta(days=10)), **base,
    })  # fmt: skip

    r = await api.call("GET", "/execution/dashboard", "MANAGER", department_id=dept)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, max-age=60"
    assert r.headers["vary"] == "Authorization"
    d = r.json()["data"]
    assert d["pillar"] == "O" and d["period"]["type"] == "current_month"
    assert d["summary"] == {"tasks_on_time_pct": 33.3, "projects_late": 1,
                            "decision_execution_pct": 0.0, "overloaded_count": 1}  # fmt: skip
    # department-scoped readers get no company store values
    assert d["metrics"] == [] and d["open_alerts"] is None and d["status"] == "no_data"
    weeks = {c["week"] for c in d["workload_heatmap"]}
    assert len(weeks) == 4
    assert (
        max(c["load_pct"] for c in d["workload_heatmap"]) == 112.5
    )  # 45 h / 40 h (the done task left before)
    trend = d["ontime_trend"]
    assert len(trend) == 6 and trend[-1] == {"period_key": d["period"]["key"],
                                             "tasks_on_time_pct": 33.3}  # fmt: skip

    ceo = await api.call("GET", "/execution/dashboard", "CEO", params={"period": "2026-09"})
    assert ceo.status_code == 200 and isinstance(ceo.json()["data"]["open_alerts"], int)
    allowed = {"METRIC-OPS-01", "METRIC-OPS-02", "METRIC-OPS-03", "METRIC-HR-03"}
    assert {m["metric_code"] for m in ceo.json()["data"]["metrics"]} <= allowed
    other = await api.call("GET", "/execution/dashboard", "MANAGER", department_id=dept,
                           params={"department_id": str(uuid.uuid4())})  # fmt: skip
    assert other.status_code == 403 and other.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    bad = await api.call("GET", "/execution/dashboard", "CEO", params={"period": "x"})
    assert bad.status_code == 400
    assert (await api.call("GET", "/execution/dashboard", "ADMIN")).status_code == 403
