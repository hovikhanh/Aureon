"""TC-M5-11 — what the KPI / Objective editors send, per role (EP-KPI-02/04, EP-OKR-02/04; 02 RACI).

The editors let the CEO pick an owner and a department (options from `/hr/departments`, no new
directory endpoint); an empty pick is left out so the API pins it. This pins the role matrix the UI
relies on: CEO any department or company level, and may move a goal; DIR's empty pick lands in
their own department; REV / ADM have no `execution:write`; EMP is refused (also TC-M14-15).
"""

import uuid
from typing import Any

import pytest

from tests.conftest import ApiClient
from tests.integration.execution.helpers import as_user, uniq
from tests.integration.goals.test_scope_t632 import _code
from tests.integration.hr.helpers import make_department

pytestmark = pytest.mark.integration


def _kpi(owner: uuid.UUID, dept: Any = None) -> dict[str, Any]:
    body = {"code": _code(), "name": "KPI", "unit": "%", "target": 90, "owner_id": str(owner)}
    return body if dept is None else {**body, "department_id": str(dept)}


def _okr(owner: uuid.UUID, period: str, dept: Any = None) -> dict[str, Any]:
    body = {"title": uniq("O"), "owner_id": str(owner), "period_key": period}
    return body if dept is None else {**body, "department_id": str(dept)}


async def test_ceo_picks_owner_and_department_and_can_move_to_company_level(
    api: ApiClient,
) -> None:
    dept = uuid.UUID((await make_department(api))["id"])
    ceo, owner = uuid.uuid4(), uuid.uuid4()
    period = f"{2300 + uuid.uuid4().int % 600}-Q2"
    for url, body in (("/kpis", _kpi(owner, dept)), ("/objectives", _okr(owner, period, dept))):
        r = await as_user(api, "POST", url, "CEO", ceo, json=body)
        assert r.status_code == 201, r.text
        row = r.json()["data"]
        assert (row["owner_id"], row["department_id"]) == (str(owner), str(dept)), url
        # "Toàn công ty" in the editor sends `department_id: null` only because it changed
        r = await as_user(api, "PATCH", f"{url}/{row['id']}", "CEO", ceo,
                          json={"version": row["version"], "department_id": None})  # fmt: skip
        assert r.status_code == 200, r.text
        assert r.json()["data"]["department_id"] is None, url
    # an empty pick (field left out) is company level for the CEO
    r = await as_user(api, "POST", "/kpis", "CEO", ceo, json=_kpi(owner))
    assert r.status_code == 201 and r.json()["data"]["department_id"] is None


async def test_dir_empty_pick_is_pinned_to_own_department(api: ApiClient) -> None:
    dept = uuid.UUID((await make_department(api))["id"])
    other = uuid.UUID((await make_department(api))["id"])
    d = uuid.uuid4()
    period = f"{2300 + uuid.uuid4().int % 600}-Q3"
    for url, body in (("/kpis", _kpi(d)), ("/objectives", _okr(d, period))):
        r = await as_user(api, "POST", url, "DIR", d, json=body, department_id=dept)
        assert r.status_code == 201, r.text
        assert r.json()["data"]["department_id"] == str(dept), url
    r = await as_user(api, "POST", "/kpis", "DIR", d, json=_kpi(d, other), department_id=dept)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


@pytest.mark.parametrize("role", ["REV", "ADM", "EMP"])
async def test_roles_without_goal_write_cannot_create(api: ApiClient, role: str) -> None:
    dept = uuid.UUID((await make_department(api))["id"])
    u = uuid.uuid4()
    period = f"{2300 + uuid.uuid4().int % 600}-Q4"
    for url, body in (("/kpis", _kpi(u)), ("/objectives", _okr(u, period))):
        r = await as_user(api, "POST", url, role, u, json=body, department_id=dept)
        assert r.status_code == 403, (role, url, r.text)
        assert r.json()["error"]["code"] == "FORBIDDEN_ROLE", (role, url)
