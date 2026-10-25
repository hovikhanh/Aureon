"""T-643 review fixes — EP-DC-05 `rows` / `planned_actions` / `can_commit`, REV role-pool scope,
level-4 masking in review, `version` bump on approve (R-DEC-60bis). TC-M15-07/17."""

import uuid

import pytest

from tests.conftest import ApiClient
from tests.integration.idp.test_import_c5_t635 import GOOD, _upload, _xlsx

pytestmark = pytest.mark.integration


async def _submitted(api: ApiClient) -> str:
    uid = uuid.uuid4()
    r = await _upload(api, "CEO", _xlsx(GOOD, tag=uuid.uuid4().hex), user_id=uid)
    p = r.json()["data"]
    sub = await api.http.post(
        f"/api/v1/data-capture/imports/{p['batch_id']}/submit",
        headers=api.headers("CEO", idem=True, user_id=uid), json={"version": p["version"]},
    )  # fmt: skip
    assert sub.status_code == 200, sub.text
    return str(sub.json()["data"]["document"]["id"])


async def test_rev_pool_sees_rows_plan_and_level4(api: ApiClient, db_session, idp_store) -> None:
    doc = await _submitted(api)
    rev = api.headers("REVIEWER", department_id=uuid.uuid4())  # other department, REV pool
    r = await api.http.get(f"/api/v1/idp/documents/{doc}/review", headers=rev)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert [row["row_index"] for row in d["rows"]] == [4, 5]
    plan = {p["action_name"]: p for p in d["planned_actions"]}
    assert plan["ACT-create_employee"]["count"] == 2
    assert plan["ACT-create_department"] == {"action_name": "ACT-create_department", "count": 2,
                                             "required_permission": "hr:admin",
                                             "permitted": False}  # fmt: skip
    assert d["can_commit"] is False
    salary = next(f for f in d["fields"] if f["field_name"] == "salary")
    assert salary["effective_value"] == 25000000  # assigned review session reads level 4
    q = await api.http.get("/api/v1/idp/review-queue", headers=rev)
    assert doc in {i["document_id"] for i in q.json()["data"]}


async def test_level4_masked_for_approver_without_level4(
    api: ApiClient, db_session, idp_store
) -> None:
    doc = await _submitted(api)
    cfo = api.headers("DIR", scope_pillars=("F",))  # no department → document visible
    r = await api.http.get(f"/api/v1/idp/documents/{doc}/review", headers=cfo)
    assert r.status_code == 200, r.text
    salary = next(f for f in r.json()["data"]["fields"] if f["field_name"] == "salary")
    assert salary["effective_value"] == {"masked": True}
    assert salary["ai_value"] == {"masked": True}


async def test_approve_bumps_version_and_stale_commit_conflicts(
    api: ApiClient, db_session, idp_store
) -> None:
    from tests.integration.idp.critical_helpers import approve_http

    doc = await _submitted(api)
    rev = api.headers("REVIEWER")
    d = (await api.http.get(f"/api/v1/idp/documents/{doc}/review", headers=rev)).json()["data"]
    v0 = d["document"]["version"]
    res = await approve_http(api, db_session, "REVIEWER", doc)
    assert res.status_code == 200, res.text  # type: ignore[attr-defined]
    out = res.json()  # type: ignore[attr-defined]
    assert out["meta"]["pending_permissions"] == ["hr:admin", "hr:write"]
    out = out["data"]
    assert out["document"]["status"] == "APPROVED" and out["document"]["version"] == v0 + 1
    hr = api.headers("DIR", scope_pillars=("O",), idem=True)
    stale = await api.http.post(f"/api/v1/data-capture/documents/{doc}/commit", headers=hr,
                                json={"version": v0})  # fmt: skip
    assert stale.status_code == 409
    d = (await api.http.get(f"/api/v1/idp/documents/{doc}/review", headers=hr)).json()["data"]
    assert d["can_commit"] is True
