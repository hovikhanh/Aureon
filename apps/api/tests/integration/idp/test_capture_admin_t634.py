"""TC-M15-02 — capture catalog admin EP-DC-27..35 (T-634, DEC-133/162, FR-DC-16) and the
seeded P0 doc types #2/#3/#4 (TC-M15-01 seed part, migration 0019)."""

import copy
import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.core.audit import AUDIT_LOGS
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration
BASE = "/data-capture"


async def _types(api: ApiClient, role: str = "REVIEWER", **params: Any) -> dict[str, Any]:
    r = await api.call("GET", f"{BASE}/document-types", role, params=params)
    assert r.status_code == 200, r.text
    return {t["code"]: t for t in r.json()["data"]}


async def _schema(api: ApiClient, code: str, status: str = "published") -> dict[str, Any]:
    r = await api.call("GET", f"{BASE}/extraction-schemas", "ADMIN",
                       params={"document_type": code, "status": status})  # fmt: skip
    assert r.status_code == 200, r.text
    return dict(r.json()["data"][-1])


async def _draft(api: ApiClient, code: str = "PLAN_KPI_OKR") -> dict[str, Any]:
    pub = await _schema(api, code)
    r = await api.call("POST", f"{BASE}/extraction-schemas", "ADMIN",
                       json={"document_type": code, "clone_from_id": pub["id"]})  # fmt: skip
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def test_seeded_p0_types_listed_with_version(api: ApiClient) -> None:
    types = await _types(api, "REVIEWER")
    for code in ("PLAN_KPI_OKR", "PERIOD_REPORT", "HR_ROSTER"):
        assert types[code]["is_active"] and types[code]["current_schema_version"] >= 1
        assert isinstance(types[code]["version"], int)  # R-DEC-60bis
        assert "C5" in types[code]["channels_supported"]
    hr = await _schema(api, "HR_ROSTER")
    assert hr["action_names"] == ["ACT-create_department", "ACT-create_team",
                                  "ACT-create_position", "ACT-create_employee"]  # fmt: skip
    salary = next(f for f in hr["fields"] if f["name"] == "salary")
    assert salary["is_critical"] and salary["sensitivity_level"] == 4
    plan = await _schema(api, "PLAN_KPI_OKR")
    assert plan["action_names"][0] == "ACT-upsert_objective"


async def test_doc_type_patch_and_inactive_filter(api: ApiClient, db_session) -> None:
    t = (await _types(api))["PERIOD_REPORT"]
    url = f"{BASE}/document-types/{t['id']}"
    r = await api.call("PATCH", url, "ADMIN", json={"is_active": False,
                       "classifier_keywords": ["báo cáo"], "version": t["version"]})  # fmt: skip
    assert r.status_code == 200, r.text
    assert r.json()["data"]["version"] == t["version"] + 1
    # include_inactive only for idp:admin (ADM can list once R-DEC-76 grants it idp:read)
    assert "PERIOD_REPORT" not in await _types(api, "REVIEWER", include_inactive="true")
    stale = await api.call("PATCH", url, "ADMIN", json={"is_active": True, "version": 1})
    assert stale.status_code == 409
    assert (await api.call("PATCH", url, "REVIEWER", json={"version": 2})).status_code == 403
    audit = (await db_session.execute(select(AUDIT_LOGS.c.action).where(
        AUDIT_LOGS.c.target_id == uuid.UUID(t["id"])))).scalars().all()  # fmt: skip
    assert "idp.doctype_update" in audit


async def test_schema_lifecycle_draft_publish_retire(api: ApiClient) -> None:
    old = await _schema(api, "PLAN_KPI_OKR")
    d = await _draft(api)
    assert d["status"] == "draft" and d["schema_version"] == old["schema_version"] + 1
    url = f"{BASE}/extraction-schemas/{d['id']}"
    th = {"classification_confidence_min": 0.97, "required_field_min": 0.92}
    r = await api.call("PATCH", url, "ADMIN", json={"thresholds": th, "version": d["version"]})
    assert r.status_code == 200, r.text
    v = r.json()["data"]["version"]
    pub = await api.call("POST", f"{url}/publish", "ADMIN", json={"version": v})
    assert pub.status_code == 200, pub.text
    assert pub.json()["data"]["status"] == "published"
    assert (await _schema(api, "PLAN_KPI_OKR", "retired"))["id"] == old["id"]
    types = await _types(api)
    assert types["PLAN_KPI_OKR"]["current_schema_version"] == d["schema_version"]
    again = await api.call("PATCH", url, "ADMIN", json={"thresholds": th, "version": v + 1})
    assert again.status_code == 409  # DEC-162 immutable after publish


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (lambda b: b.update(thresholds={"classification_confidence_min": 0.9,
                                        "required_field_min": 0.9}),
         "thresholds.classification_confidence_min"),
        (lambda b: b.update(thresholds={"classification_confidence_min": 0.95,
                                        "required_field_min": 0.8}),
         "thresholds.required_field_min"),
        (lambda b: b.update(action_names=[*b["action_names"], "ACT-nope"]), "action_names"),
        (lambda b: next(f for f in b["fields"] if f["name"] == "salary").update(is_critical=False),
         "salary"),
        (lambda b: next(f for f in b["fields"] if f["name"] == "title")["target"].update(
            param="nope"), "title"),
    ],
)  # fmt: skip
async def test_schema_hard_rules_422(api: ApiClient, mutate, field) -> None:
    d = await _draft(api, "HR_ROSTER")
    body = copy.deepcopy({k: d[k] for k in ("fields", "thresholds", "action_names")})
    mutate(body)
    r = await api.call("PATCH", f"{BASE}/extraction-schemas/{d['id']}", "ADMIN",
                       json={**body, "version": d["version"]})  # fmt: skip
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["details"]["field"] == field


async def test_rules_crud(api: ApiClient) -> None:
    d = await _draft(api)
    expr = {"field": "target", "op": "gt", "value": 0}
    rule = {"extraction_schema_id": d["id"], "code": "VR-T-01", "kind": "field",
            "severity": "warn", "expression": expr}  # fmt: skip
    r = await api.call("POST", f"{BASE}/validation-rules", "ADMIN", json=rule)
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    dup = await api.call("POST", f"{BASE}/validation-rules", "ADMIN", json=rule)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    bad_rule = {**rule, "code": "VR-T-02", "expression": {"op": "eval"}}
    bad = await api.call("POST", f"{BASE}/validation-rules", "ADMIN", json=bad_rule)
    assert bad.status_code == 422
    listed = await api.call("GET", f"{BASE}/validation-rules", "ADMIN",
                            params={"extraction_schema_id": d["id"]})  # fmt: skip
    assert [x["code"] for x in listed.json()["data"]] == ["VR-T-01"]
    url = f"{BASE}/validation-rules/{created['id']}"
    p = await api.call("PATCH", url, "ADMIN", json={"severity": "fail", "version": 1})
    assert p.status_code == 200 and p.json()["data"]["severity"] == "fail"
    pub = await api.call("POST", f"{BASE}/extraction-schemas/{d['id']}/publish", "ADMIN",
                         json={"version": d["version"]})  # fmt: skip
    assert pub.status_code == 200, pub.text
    locked = await api.call("PATCH", url, "ADMIN", json={"is_active": False, "version": 2})
    assert locked.status_code == 409 and locked.json()["error"]["code"] == "CONFLICT_STATE"
    late = await api.call("POST", f"{BASE}/validation-rules", "ADMIN",
                          json={**rule, "code": "VR-T-03"})  # fmt: skip
    assert late.status_code == 409


async def test_admin_endpoints_need_idp_admin(api: ApiClient) -> None:
    for method, url in [("GET", "/extraction-schemas"), ("GET", "/validation-rules"),
                        ("POST", "/extraction-schemas")]:  # fmt: skip
        r = await api.call(method, f"{BASE}{url}", "REVIEWER", json={"document_type": "X"})
        assert r.status_code == 403, url
