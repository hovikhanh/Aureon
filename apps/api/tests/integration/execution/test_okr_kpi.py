"""T-132 — EP-46 OKR, EP-47 KPI + measurements, EP-48 check-ins (TC-EXE-002)."""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.services.base import today
from app.modules.execution.services.kpi_rules import period_key_for
from tests.conftest import ApiClient
from tests.integration.execution.helpers import (
    as_user,
    audit_actions,
    make,
    make_task,
    outbox_for,
    patch,
    uniq,
)

pytestmark = pytest.mark.integration


def kr(owner: Any, **kw: Any) -> dict[str, Any]:
    return {"title": uniq("KR"), "baseline": 0, "target": 100, "unit": "%",
            "owner_id": str(owner), **kw}  # fmt: skip


async def test_objective_key_results(api: ApiClient, db_session: AsyncSession) -> None:
    owner, dept = uuid.uuid4(), uuid.uuid4()
    o = await make(api, "/execution/objectives", {
        "title": "Tăng trưởng", "owner_id": str(owner), "period_key": "2037-Q3",
        "department_id": str(dept)})  # fmt: skip
    assert o["status"] == "draft" and o["progress_pct"] == 0
    oid = o["id"]
    base = f"/execution/objectives/{oid}"
    early = await patch(api, base, 1, status="active")
    assert early.status_code == 422 and early.json()["error"]["details"]["key_results"] == 0
    k1 = await make(api, f"{base}/key-results", kr(owner, weight_pct=75))
    k2 = await make(api, f"{base}/key-results", kr(owner, weight_pct=25, current_value=100))
    assert k2["progress_pct"] == 100
    got = await api.call("GET", base, "CEO")
    assert got.json()["data"]["progress_pct"] == 25
    emp = await as_user(api, "PATCH", base, "EMPLOYEE", owner, json={"status": "active",
                                                                      "version": 1})  # fmt: skip
    assert emp.status_code == 403
    act = await patch(api, base, 1, status="active", title=None)
    assert act.status_code == 200 and act.json()["data"]["status"] == "active"
    for _ in range(3):
        await make(api, f"{base}/key-results", kr(owner))
    sixth = await api.call("POST", f"{base}/key-results", "CEO", json=kr(owner))
    assert sixth.status_code == 422
    lst = await api.call("GET", f"{base}/key-results", "CEO", params={"limit": 10})
    assert lst.json()["meta"]["pagination"]["total"] == 5
    one = await api.call("GET", f"{base}/key-results/{k1['id']}", "CEO")
    assert one.status_code == 200
    up = await patch(api, f"{base}/key-results/{k1['id']}", 1, target=200,
                     title=None)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["target"] == 200
    up_bad = await api.call("PATCH", f"{base}/key-results/{k1['id']}", "CEO",
                            json={"current_value": 3, "version": 2})  # fmt: skip
    assert up_bad.status_code == 422  # current_value only via check-in
    other = await make(api, "/execution/objectives", {
        "title": "x", "owner_id": str(owner), "period_key": "2037", "parent_id": oid})  # fmt: skip
    wrong = await api.call("GET", f"/execution/objectives/{other['id']}/key-results/{k1['id']}",
                           "CEO")  # fmt: skip
    assert wrong.status_code == 404
    wrong_del = await api.call(
        "DELETE", f"/execution/objectives/{other['id']}/key-results/{k1['id']}", "CEO")  # fmt: skip
    assert wrong_del.status_code == 404
    assert (await api.call("DELETE", base, "CEO")).status_code == 409
    selfp = await patch(api, base, 2, parent_id=oid)
    assert selfp.status_code == 422
    assert (await api.call("DELETE", f"{base}/key-results/{k1['id']}", "CEO")).status_code == 204
    flt = await api.call("GET", "/execution/objectives", "MANAGER", department_id=dept,
                         params={"period_key": "2037-Q3", "owner_id": str(owner)})  # fmt: skip
    assert [x["id"] for x in flt.json()["data"]] == [oid]
    mine = await as_user(api, "GET", "/execution/objectives", "EMPLOYEE", owner,
                         params={"period_key": "2037"})  # fmt: skip
    assert [x["id"] for x in mine.json()["data"]] == [other["id"]]
    assert (await api.call("DELETE", f"/execution/objectives/{other['id']}", "CEO")).status_code \
        == 204  # fmt: skip
    assert (await api.call("GET", f"/execution/objectives/{other['id']}", "CEO")).status_code \
        == 404  # fmt: skip
    assert "execution.key_result_delete" in await audit_actions(db_session, k1["id"])
    act_body = {"title": "x", "owner_id": str(owner), "period_key": "2037", "status": "active"}
    bad_active = await api.call("POST", "/execution/objectives", "CEO", json=act_body)
    assert bad_active.status_code == 422
    emp_kr = await as_user(api, "GET", f"{base}/key-results/{k2['id']}", "EMPLOYEE",
                           uuid.uuid4())  # fmt: skip
    assert emp_kr.status_code == 403
    nf = await api.call("GET", f"{base}/key-results/{uuid.uuid4()}", "CEO")
    assert nf.status_code == 404


async def test_kpi_measurements_and_event(api: ApiClient, db_session: AsyncSession) -> None:
    owner = uuid.uuid4()
    k = await make(api, "/execution/kpis", {
        "code": uniq("KPI"), "name": "Tỷ lệ giao đúng hạn", "unit": "%", "target": 95,
        "owner_id": str(owner), "metric_code": "METRIC-OPS-01"})  # fmt: skip
    assert k["target"] == 95 and k["direction"] == "HIGHER_IS_BETTER"
    kid = k["id"]
    url = f"/execution/kpis/{kid}/measurements"
    m = await api.call("POST", url, "CEO", json={"period_key": "2037-08", "actual_value": 76})
    assert m.status_code == 201, m.text
    md = m.json()["data"]
    assert md["achievement_pct"] == 80 and md["evaluation_band"] == "BELOW"
    again = await api.call("POST", url, "CEO", json={"period_key": "2037-08", "actual_value": 95})
    ad = again.json()["data"]
    assert ad["id"] == md["id"] and ad["evaluation_band"] == "MEETS"
    events = await outbox_for(db_session, kid)
    assert [e[0] for e in events] == ["execution.kpi_measured"] * 2
    assert events[1][1] == {"kpi_id": kid, "period_key": "2037-08",
                            "actual_value": "95", "achievement_pct": "100.0000"}  # fmt: skip
    q = await api.call("POST", url, "CEO", json={"period_key": "2037-Q3", "actual_value": 1})
    assert q.status_code == 422
    lst = await api.call("GET", url, "CEO")
    assert lst.json()["meta"]["pagination"]["total"] == 1
    up = await patch(api, f"/execution/kpis/{kid}", 1, target=100, direction="LOWER_IS_BETTER",
                     name=None)  # fmt: skip
    assert up.status_code == 200 and up.json()["data"]["target"] == 100
    dup_body = {"code": k["code"], "name": "x", "unit": "%", "target": 1, "owner_id": str(owner)}
    dup = await api.call("POST", "/execution/kpis", "CEO", json=dup_body)
    assert dup.status_code == 409
    flt = await api.call("GET", "/execution/kpis", "CEO",
                         params={"metric_code": "METRIC-OPS-01",
                                 "owner_id": str(owner)})  # fmt: skip
    assert [x["id"] for x in flt.json()["data"]] == [kid]
    child = await make(api, "/execution/kpis", {
        "code": uniq("KPI"), "name": "c", "unit": "%", "target": 1, "owner_id": str(owner),
        "parent_kpi_id": kid})  # fmt: skip
    assert (await api.call("DELETE", f"/execution/kpis/{kid}", "CEO")).status_code == 409
    selfp = await patch(api, f"/execution/kpis/{child['id']}", 1, parent_kpi_id=child["id"])
    assert selfp.status_code == 422
    t = await make_task(api, kpi_id=child["id"])
    assert (await api.call("DELETE", f"/execution/kpis/{child['id']}", "CEO")).status_code == 409
    await api.call("DELETE", f"/work/tasks/{t['id']}", "CEO")
    assert (await api.call("DELETE", f"/execution/kpis/{child['id']}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/execution/kpis/{child['id']}", "CEO")).status_code == 404
    emp = await as_user(api, "GET", f"/execution/kpis/{kid}", "EMPLOYEE", owner)
    assert emp.status_code == 200
    stranger = await as_user(api, "POST", url, "EMPLOYEE", uuid.uuid4(),
                             json={"period_key": "2037-09", "actual_value": 1})  # fmt: skip
    assert stranger.status_code == 403


async def test_check_ins(api: ApiClient, db_session: AsyncSession) -> None:
    owner = uuid.uuid4()
    o = await make(api, "/execution/objectives", {
        "title": "o", "owner_id": str(owner), "period_key": "2037"})  # fmt: skip
    k = await make(api, f"/execution/objectives/{o['id']}/key-results", kr(owner))
    both = await api.call("POST", "/execution/check-ins", "CEO", json={
        "key_result_id": k["id"], "kpi_id": str(uuid.uuid4()), "value": 1,
        "confidence": "HIGH"})  # fmt: skip
    assert both.status_code == 422
    c = await as_user(api, "POST", "/execution/check-ins", "EMPLOYEE", owner, json={
        "key_result_id": k["id"], "value": 40, "confidence": "MEDIUM",
        "blocker": "thiếu người"})  # fmt: skip
    assert c.status_code == 201, c.text
    assert c.json()["data"]["user_id"] == str(owner)
    kr_now = await api.call("GET", f"/execution/objectives/{o['id']}/key-results/{k['id']}", "CEO")
    assert kr_now.json()["data"]["current_value"] == 40
    assert kr_now.json()["data"]["confidence"] == "MEDIUM"
    obj = await api.call("GET", f"/execution/objectives/{o['id']}", "CEO")
    assert obj.json()["data"]["progress_pct"] == 40
    kpi = await make(api, "/execution/kpis", {
        "code": uniq("KPI"), "name": "n", "unit": "đ", "target": 10, "owner_id": str(owner),
        "period_type": "QUARTER"})  # fmt: skip
    ck = await api.call("POST", "/execution/check-ins", "CEO", json={
        "kpi_id": kpi["id"], "value": 12, "confidence": "HIGH"})  # fmt: skip
    assert ck.status_code == 201
    meas = await api.call("GET", f"/execution/kpis/{kpi['id']}/measurements", "CEO")
    row = meas.json()["data"][0]
    assert row["period_key"] == period_key_for("QUARTER", today())
    assert row["evaluation_band"] == "EXCEEDS"
    assert [e[0] for e in await outbox_for(db_session, kpi["id"])] == ["execution.kpi_measured"]
    mine = await as_user(api, "GET", "/execution/check-ins", "EMPLOYEE", owner)
    assert {x["id"] for x in mine.json()["data"]} == {c.json()["data"]["id"],
                                                      ck.json()["data"]["id"]}  # fmt: skip
    by_kpi = await api.call("GET", "/execution/check-ins", "CEO",
                            params={"kpi_id": kpi["id"],
                                    "owner_id": str(uuid.uuid4())})  # fmt: skip
    assert by_kpi.json()["data"] == []
    key = period_key_for("MONTH", today())
    by_p = await api.call("GET", "/execution/check-ins", "CEO",
                          params={"key_result_id": k["id"], "period_key": key})  # fmt: skip
    assert len(by_p.json()["data"]) == 1
    old = await api.call("GET", "/execution/check-ins", "CEO",
                         params={"key_result_id": k["id"], "period_key": "2001"})  # fmt: skip
    assert old.json()["data"] == []
    bad = await api.call("GET", "/execution/check-ins", "CEO", params={"period_key": "x"})
    assert bad.status_code == 422
    mgr = await api.call("GET", "/execution/check-ins", "MANAGER", department_id=uuid.uuid4())
    assert mgr.status_code == 200
    assert "execution.check_in_create" in await audit_actions(db_session, c.json()["data"]["id"])
