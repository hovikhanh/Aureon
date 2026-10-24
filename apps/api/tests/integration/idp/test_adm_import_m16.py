"""T-648 / TC-M16-14 — wizard import scope (R-DEC-76, R-DEC-30, 02 §5).

Complements `test_adm_scope_rdec76.py` (ADM #4 OK / other types 403) and
`test_import_c5_t635.py::test_mapping_update_and_level4_drop` (ADM: salary column dropped +
warning, never stored): ADM import of doc type #2 → 403; ADM roster import goes through to an
`APPROVED`/`COMMITTED` path only for an approver in khối O; a DIR outside khối O approving the
roster does **not** write the structure (ACT pillar check) and cannot EP-DC-23 commit it.
"""

import uuid

import pytest

from app.modules.hr.services.hr_service import HrService
from tests.conftest import ApiClient
from tests.integration.idp.critical_helpers import critical_ids
from tests.integration.idp.test_import_c5_t635 import XLSX, _xlsx

pytestmark = pytest.mark.integration


def _roster(tag: str) -> list[list[object]]:
    return [["PB-" + tag, "Phòng " + tag, "Trưởng phòng", "E-" + tag, "Nguyễn A", None,
             "01/02/2024", "active", 25000000]]  # fmt: skip


async def _adm_submit(api: ApiClient, tag: str) -> str:
    uid = uuid.uuid4()
    files = [("file", ("ds.xlsx", _xlsx(_roster(tag), tag=tag), XLSX))]
    h = api.headers("ADMIN", idem=True, user_id=uid)
    data = {"document_type": "HR_ROSTER"}
    r = await api.http.post("/api/v1/data-capture/imports", files=files, data=data, headers=h)
    assert r.status_code == 201, r.text
    p = r.json()["data"]
    sub = await api.http.post(f"/api/v1/data-capture/imports/{p['batch_id']}/submit",
                              headers=api.headers("ADMIN", idem=True, user_id=uid),
                              json={"version": p["version"]})  # fmt: skip
    assert sub.status_code == 200, sub.text
    return str(sub.json()["data"]["document"]["id"])


async def _approve(api: ApiClient, db, doc: str, pillars: tuple[str, ...]) -> dict:
    uid, base = uuid.uuid4(), f"/api/v1/idp/documents/{doc}"

    def h(**k: bool) -> dict[str, str]:
        return api.headers("DIR", user_id=uid, scope_pillars=pillars, **k)

    assert (await api.http.post(f"{base}/review/open", json={}, headers=h(idem=True))
            ).status_code == 200  # fmt: skip
    body = {"fields": [{"field_id": str(i), "action": "confirm"}
                       for i in await critical_ids(db, uuid.UUID(doc))]}  # fmt: skip
    assert (await api.http.patch(f"{base}/fields", json=body, headers=h())).status_code == 200
    r = await api.http.post(f"{base}/review/approve", json={}, headers=h(idem=True))
    assert r.status_code == 200, r.text
    return dict(r.json()["data"]["document"]) | {"_h": h(idem=True)}


async def test_adm_import_plan_kpi_okr_forbidden(api: ApiClient) -> None:
    files = [("file", ("kh.xlsx", b"x", XLSX))]
    r = await api.http.post("/api/v1/data-capture/imports", files=files,
                            data={"document_type": "PLAN_KPI_OKR"},
                            headers=api.headers("ADMIN", idem=True))  # fmt: skip
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


async def test_dir_outside_o_does_not_write_structure(
    api: ApiClient, db_session, idp_store
) -> None:
    tag = uuid.uuid4().hex[:6].upper()
    doc = await _adm_submit(api, tag)
    out = await _approve(api, db_session, doc, ("F",))
    assert out["status"] == "APPROVED"  # approval recorded, nothing written (R-DEC-61)
    assert await HrService(db_session).department_id_by_code("PB-" + tag) is None
    commit = await api.http.post(f"/api/v1/data-capture/documents/{doc}/commit", headers=out["_h"],
                                 json={"version": out["version"]})  # fmt: skip
    assert commit.status_code == 403
    assert await HrService(db_session).department_id_by_code("PB-" + tag) is None


async def test_dir_o_commits_adm_roster(api: ApiClient, db_session, idp_store) -> None:
    tag = uuid.uuid4().hex[:6].upper()
    doc = await _adm_submit(api, tag)
    out = await _approve(api, db_session, doc, ("O",))
    assert out["status"] == "COMMITTED"
    assert await HrService(db_session).department_id_by_code("PB-" + tag) is not None


async def test_adm_commits_and_undoes_roster_with_manager(
    api: ApiClient, db_session, idp_store
) -> None:
    """T-650 regression (UC-07): ADM (structure only, R-DEC-30) commits its own approved roster —
    incl. the manager pass — and undoes it; it still cannot read other employee records."""
    tag, uid = uuid.uuid4().hex[:6].upper(), uuid.uuid4()
    rows = [["PB-" + tag, "Phòng " + tag, "Trưởng phòng", "H-" + tag, "Nguyễn A", None,
             "01/02/2024", "active", None],
            ["PB-" + tag, "Phòng " + tag, "Chuyên viên", "S-" + tag, "Trần B", "H-" + tag,
             "01/03/2024", "active", None]]  # fmt: skip
    files = [("file", ("ds.xlsx", _xlsx(rows, tag=tag), XLSX))]

    def h(idem: bool = True) -> dict[str, str]:
        return api.headers("ADMIN", idem=idem, user_id=uid)

    r = await api.http.post("/api/v1/data-capture/imports", files=files,
                            data={"document_type": "HR_ROSTER"}, headers=h())  # fmt: skip
    p = r.json()["data"]
    sub = await api.http.post(f"/api/v1/data-capture/imports/{p['batch_id']}/submit",
                              headers=h(), json={"version": p["version"]})  # fmt: skip
    doc = str(sub.json()["data"]["document"]["id"])
    rev, base = uuid.uuid4(), f"/api/v1/idp/documents/{doc}"
    rh = api.headers("REVIEWER", idem=True, user_id=rev)
    for path in ("review/open", "review/approve"):
        ok = await api.http.post(f"{base}/{path}", json={}, headers=rh)
        assert ok.status_code == 200, ok.text
    version = ok.json()["data"]["document"]["version"]
    commit = await api.http.post(f"/api/v1/data-capture/documents/{doc}/commit",
                                 json={"version": version}, headers=h())  # fmt: skip
    assert commit.status_code == 200, commit.text
    hr = HrService(db_session)
    sub_id = await hr.employee_id_by_code("S-" + tag)
    head_id = await hr.employee_id_by_code("H-" + tag)
    assert sub_id and head_id
    row = await hr.employees.get(sub_id)
    assert row is not None and row.manager_id == head_id
    seeded = (await api.call("GET", "/hr/employees", "CEO", params={"limit": 1})).json()["data"][0]
    assert (await api.call("GET", f"/hr/employees/{seeded['id']}", "ADMIN")).status_code == 403
    body = {"reason": "x", "reason_code": "mistake"}
    undo = await api.http.post(f"/api/v1/data-capture/documents/{doc}/undo", json=body,
                               headers=h())  # fmt: skip
    assert undo.status_code == 200, undo.text
    assert await hr.employee_id_by_code("S-" + tag) is None
