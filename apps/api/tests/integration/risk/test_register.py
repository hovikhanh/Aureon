"""TC-RSK-001/002 — EP-101 register, EP-102 assessments (T-211)."""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import ApiClient
from tests.integration.risk.helpers import (
    OWNER,
    audit_actions,
    make_risk,
    outbox_for,
    risk_body,
    types,
)


async def test_create_generates_score_level_code(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api, likelihood=4, impact=4, linked_entities={"deal_id": str(uuid.uuid4())})
    assert r["risk_score"] == 16 and r["level"] == "critical"
    assert r["status"] == "identified" and r["risk_source"] == "manual"
    assert re.match(r"^RSK-\d{4}-\d{3}$", r["code"])
    r2 = await make_risk(api, likelihood=1, impact=2, owner_id=None)
    assert r2["level"] == "low" and r2["code"] > r["code"]
    assert await audit_actions(db_session, r["id"]) == ["risk.risk_create"]
    ev = await outbox_for(db_session, r["id"])
    assert types(ev) == ["risk.risk_identified"]
    assert ev[0][1]["severity"] == "critical" and ev[0][1]["risk_source"] == "manual"
    assert await outbox_for(db_session, r2["id"]) == []  # low → register only


async def test_create_validation(api: ApiClient) -> None:
    r = await api.call("POST", "/risk/risks", "RISK_MANAGER", json=risk_body(owner_id=None))
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    r = await api.call("POST", "/risk/risks", "RISK_MANAGER", json=risk_body(likelihood=6))
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await api.call("POST", "/risk/risks", "RISK_MANAGER", json=risk_body(category="market"))
    assert r.status_code == 422
    bad = risk_body(linked_entities={"Deal": str(uuid.uuid4())})
    r = await api.call("POST", "/risk/risks", "RISK_MANAGER", json=bad)
    assert r.status_code == 422
    r = await api.call("POST", "/risk/risks", "CFO", json=risk_body())
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_ROLE"


async def test_get_list_filters_and_update(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api, category="legal", likelihood=2, impact=2, owner_id=None)
    got = await api.call("GET", f"/risk/risks/{r['id']}", "CEO")
    assert got.status_code == 200 and got.json()["data"]["code"] == r["code"]
    lst = await api.call("GET", "/risk/risks", "CFO", params={"category": "legal", "level": "low"})
    assert lst.status_code == 200 and r["id"] in [x["id"] for x in lst.json()["data"]]
    assert lst.json()["meta"]["pagination"]["total"] >= 1
    p = await api.call(
        "PATCH", f"/risk/risks/{r['id']}", "RISK_MANAGER",
        json={"version": r["version"], "title": "Renamed", "linked_entities": {}},
    )  # fmt: skip
    assert p.status_code == 200 and p.json()["data"]["title"] == "Renamed"
    assert p.json()["data"]["version"] == r["version"] + 1
    stale = await api.call(
        "PATCH", f"/risk/risks/{r['id']}", "RISK_MANAGER", json={"version": r["version"]}
    )
    assert stale.status_code == 409
    assert "risk.risk_update" in await audit_actions(db_session, r["id"])
    missing = await api.call("GET", f"/risk/risks/{uuid.uuid4()}", "CEO")
    assert missing.status_code == 404


async def test_assessment_level_change(api: ApiClient, db_session: AsyncSession) -> None:
    r = await make_risk(api, likelihood=2, impact=3)  # 6 medium
    url = f"/risk/risks/{r['id']}/assessments"
    a = await api.call(
        "POST", url, "RISK_MANAGER", json={"likelihood": 2, "impact": 4, "note": "x"}
    )
    assert a.status_code == 201 and a.json()["data"]["level"] == "medium"
    a = await api.call("POST", url, "RISK_MANAGER", json={"likelihood": 4, "impact": 4})
    assert a.json()["data"]["risk_score"] == 16 and a.json()["data"]["level"] == "critical"
    lst = await api.call("GET", url, "CEO")
    assert len(lst.json()["data"]) == 2 and lst.json()["data"][1]["note"] == "x"
    got = (await api.call("GET", f"/risk/risks/{r['id']}", "CEO")).json()["data"]
    assert got["status"] == "assessed" and got["level"] == "critical"
    ev = await outbox_for(db_session, r["id"])
    assert types(ev) == ["risk.risk_level_changed"]
    assert ev[0][1] == {"risk_id": r["id"], "from_severity": "medium", "to_severity": "critical"}
    low = await make_risk(api, likelihood=1, impact=1, owner_id=None)
    bad = await api.call(
        "POST", f"/risk/risks/{low['id']}/assessments", "RISK_MANAGER",
        json={"likelihood": 3, "impact": 3},
    )  # fmt: skip
    assert bad.status_code == 422  # medium without owner


async def test_patch_owner_rule(api: ApiClient) -> None:
    r = await make_risk(api)
    p = await api.call(
        "PATCH", f"/risk/risks/{r['id']}", "RISK_MANAGER",
        json={"version": r["version"], "owner_id": None},
    )  # fmt: skip
    assert p.status_code == 422
    assert r["owner_id"] == OWNER
