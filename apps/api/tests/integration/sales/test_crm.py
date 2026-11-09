"""R-DEC-176 (D-08, D-21) — EP-SAL-10..13 Lead / Contact / Activity + convert (TC-V4-CRM-01..10)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_LOGS
from app.modules.sales.services.crm_service import split_name
from tests.conftest import ApiClient
from tests.integration.sales.helpers import (
    FUTURE,
    audit_actions,
    make_client,
    make_deal,
    outbox_for,
    uniq,
)

pytestmark = pytest.mark.integration

DIR = "VP_SALES"  # Sales-DIR (khối C)
NOW = datetime.now(UTC).replace(microsecond=0)


def mail() -> str:
    return f"{uuid.uuid4().hex[:12]}@lead.test"


def phone() -> str:
    return "09" + str(uuid.uuid4().int)[:8]


def lead_body(**kw: Any) -> dict[str, Any]:
    return {"full_name": "Nguyễn Văn Bình", "company_name": uniq("Cty Lead"), "email": mail(),
            "budget": 500_000_000, "score": 40, **kw}  # fmt: skip


async def make_lead(api: ApiClient, role: str = DIR, dept: Any = None, **kw: Any) -> Any:
    r = await api.call("POST", "/sales/leads", role, json=lead_body(**kw), department_id=dept)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_lead_crud_as_ceo_with_code_audit_and_mask(
    api: ApiClient, db_session: AsyncSession
) -> None:
    """TC-V4-CRM-01: CEO full CRUD (D-21); `LD-` code; audit masks e-mail; soft delete."""
    email = mail()
    lead = await make_lead(api, "CEO", email=email, phone="0901 234 567")
    assert lead["code"].startswith("LD-") and len(lead["code"]) == 9
    assert lead["status"] == "new" and lead["currency"] == "VND" and lead["version"] == 1
    lid = lead["id"]
    got = await api.call("GET", f"/sales/leads/{lid}", "CEO")
    assert got.status_code == 200 and got.json()["data"]["email"] == email
    p = await api.call(
        "PATCH", f"/sales/leads/{lid}", "CEO",
        json={"status": "qualified", "score": 80, "next_action": "Gửi báo giá", "version": 1},
    )  # fmt: skip
    assert p.status_code == 200, p.text
    assert p.json()["data"]["status"] == "qualified" and p.json()["data"]["version"] == 2
    stale = await api.call("PATCH", f"/sales/leads/{lid}", "CEO", json={"score": 1, "version": 1})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"
    bad = await api.call("PATCH", f"/sales/leads/{lid}", "CEO", json={"status": "converted"})
    assert bad.status_code == 422  # converted only through EP-SAL-13
    rows = await db_session.execute(
        select(AUDIT_LOGS.c.after).where(
            AUDIT_LOGS.c.target_id == uuid.UUID(lid), AUDIT_LOGS.c.action == "sales.lead_create"
        )
    )
    assert email not in str(rows.scalar_one())
    assert (await api.call("DELETE", f"/sales/leads/{lid}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/sales/leads/{lid}", "CEO")).status_code == 404
    listed = await api.call("GET", "/sales/leads", "CEO", params={"q": email})
    assert listed.json()["data"] == []
    assert await audit_actions(db_session, lid) == [
        "sales.lead_create", "sales.lead_delete", "sales.lead_update",
    ]  # fmt: skip
    assert await outbox_for(db_session, lid) == []  # no registry event for leads (10 §9.2)


async def test_lead_rules_and_list(api: ApiClient) -> None:
    """TC-V4-CRM-02: e-mail or phone required; score range; search + filter + sort whitelist."""
    no_channel = await api.call("POST", "/sales/leads", DIR, json=lead_body(email=None))
    assert no_channel.status_code == 422
    assert no_channel.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert no_channel.json()["error"]["details"]["field"] == "email"
    assert (await api.call("POST", "/sales/leads", DIR, json=lead_body(score=101))).status_code \
        == 422  # fmt: skip
    tag = uuid.uuid4().hex[:10]
    a = await make_lead(api, company_name=f"Đại Phát {tag}", status="engaged")
    await make_lead(api, company_name=f"Khác {tag}")
    r = await api.call("GET", "/sales/leads", DIR, params={"q": f"Đại Phát {tag}"})
    assert [x["id"] for x in r.json()["data"]] == [a["id"]]
    r = await api.call("GET", "/sales/leads", DIR, params={"q": tag, "status": "engaged"})
    assert [x["id"] for x in r.json()["data"]] == [a["id"]]
    srt = await api.call("GET", "/sales/leads", DIR, params={"sort_by": "score", "order": "asc"})
    assert srt.status_code == 200
    assert (await api.call("GET", "/sales/leads", DIR, params={"sort_by": "email"})).status_code \
        == 400  # fmt: skip


async def test_lead_duplicate_warns_then_confirms(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-V4-CRM-03: same e-mail / phone → 409 + `details.similar`; confirm → 201 + audit."""
    email, tel = mail(), phone()
    first = await make_lead(api, email=email, phone=tel)
    dup = await api.call("POST", "/sales/leads", DIR, json=lead_body(email=email.upper()))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    similar = dup.json()["error"]["details"]["similar"]
    assert similar[0]["id"] == first["id"] and similar[0]["match"] == ["email"]
    spaced = f"{tel[:4]} {tel[4:7]}-{tel[7:]}"
    by_phone = await api.call("POST", "/sales/leads", DIR, json=lead_body(phone=spaced))
    assert by_phone.status_code == 409
    assert by_phone.json()["error"]["details"]["similar"][0]["match"] == ["phone"]
    ok = await api.call(
        "POST", "/sales/leads", DIR, json=lead_body(email=email, confirm_duplicate=True)
    )
    assert ok.status_code == 201, ok.text
    assert "sales.lead_duplicate_confirmed" in await audit_actions(
        db_session, ok.json()["data"]["id"]
    )


async def test_contact_crud_and_duplicate(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-V4-CRM-04: contact CRUD (`CT-`), roles array, client required, duplicate warning."""
    client = await make_client(api)
    email = mail()
    body = {"client_id": client["id"], "first_name": "Lan", "last_name": "Trần Thị",
            "email": email, "roles": ["decision_maker", "economic_buyer", "decision_maker"],
            "influence_level": "high"}  # fmt: skip
    r = await api.call("POST", "/sales/contacts", "CEO", json=body)
    assert r.status_code == 201, r.text
    c = r.json()["data"]
    assert c["code"].startswith("CT-") and c["full_name"] == "Trần Thị Lan"
    assert c["roles"] == ["decision_maker", "economic_buyer"]
    dup = await api.call("POST", "/sales/contacts", DIR, json={**body, "first_name": "Khác"})
    assert dup.status_code == 409 and dup.json()["error"]["details"]["similar"][0]["id"] == c["id"]
    bad_role = await api.call("POST", "/sales/contacts", DIR, json={**body, "roles": ["boss"]})
    assert bad_role.status_code == 422
    no_client = {**body, "client_id": str(uuid.uuid4()), "email": mail()}
    missing = await api.call("POST", "/sales/contacts", DIR, json=no_client)
    assert missing.status_code == 422 and missing.json()["error"]["details"]["field"] == "client_id"
    p = await api.call(
        "PATCH", f"/sales/contacts/{c['id']}", DIR,
        json={"roles": ["champion"], "job_title": "CFO", "version": 1},
    )  # fmt: skip
    assert p.status_code == 200 and p.json()["data"]["roles"] == ["champion"]
    listed = await api.call("GET", "/sales/contacts", DIR, params={"client_id": client["id"]})
    assert [x["id"] for x in listed.json()["data"]] == [c["id"]]
    assert (await api.call("DELETE", f"/sales/contacts/{c['id']}", "CEO")).status_code == 204
    assert (await api.call("GET", f"/sales/contacts/{c['id']}", DIR)).status_code == 404
    assert await audit_actions(db_session, c["id"]) == [
        "sales.contact_create", "sales.contact_delete", "sales.contact_update",
    ]  # fmt: skip


async def test_activity_crud_links_and_rules(api: ApiClient, db_session: AsyncSession) -> None:
    """TC-V4-CRM-05: activity (`SA-`) on a deal inherits client + department; link required;
    end ≥ start; timeline filters."""
    dept = uuid.uuid4()
    client = await make_client(api)
    deal = await make_deal(api, client["id"], department_id=dept)
    start = NOW.isoformat()
    body = {"type": "meeting", "subject": "Đàm phán", "deal_id": deal["id"], "start_at": start}
    r = await api.call("POST", "/sales/activities", "CEO", json=body)
    assert r.status_code == 201, r.text
    a = r.json()["data"]
    assert a["code"].startswith("SA-") and a["status"] == "planned"
    assert a["client_id"] == client["id"]  # inherited from the deal
    no_link = await api.call(
        "POST", "/sales/activities", DIR, json={"type": "call", "subject": "x", "start_at": start}
    )
    assert no_link.status_code == 422 and no_link.json()["error"]["details"]["field"] == "client_id"
    early = (NOW - timedelta(hours=1)).isoformat()
    back = await api.call("POST", "/sales/activities", DIR, json={**body, "end_at": early})
    assert back.status_code == 422 and back.json()["error"]["details"]["field"] == "end_at"
    naive = await api.call(
        "POST", "/sales/activities", DIR, json={**body, "start_at": "2026-11-10T09:00:00"}
    )
    assert naive.status_code == 422  # timezone required (ISO 8601 UTC)
    for q in ({"deal_id": deal["id"]}, {"client_id": client["id"]}):
        listed = await api.call("GET", "/sales/activities", DIR, params=q)
        assert [x["id"] for x in listed.json()["data"]] == [a["id"]]
    p = await api.call(
        "PATCH", f"/sales/activities/{a['id']}", DIR,
        json={"status": "completed", "outcome": "Đồng ý giá", "version": 1},
    )  # fmt: skip
    assert p.status_code == 200 and p.json()["data"]["status"] == "completed"
    typed = await api.call("GET", "/sales/activities", DIR,
                           params={"deal_id": deal["id"], "type": "call"})  # fmt: skip
    assert typed.json()["data"] == []
    assert (await api.call("DELETE", f"/sales/activities/{a['id']}", DIR)).status_code == 204
    assert (await api.call("GET", f"/sales/activities/{a['id']}", DIR)).status_code == 404
    assert await audit_actions(db_session, a["id"]) == [
        "sales.activity_create", "sales.activity_delete", "sales.activity_update",
    ]  # fmt: skip


async def test_convert_creates_client_contact_deal(
    api: ApiClient, db_session: AsyncSession
) -> None:
    """TC-V4-CRM-06: convert → Client + Contact + Deal in one transaction; lead read-only."""
    lead = await make_lead(api, full_name="Võ Thị Hồng Lan", phone=phone(), job_title="KTT")
    r = await api.call(
        "POST", f"/sales/leads/{lead['id']}/convert", DIR,
        json={"create_deal": True, "expected_close_date": FUTURE, "probability_pct": 25},
    )  # fmt: skip
    assert r.status_code == 200, r.text
    out = r.json()["data"]
    assert out["client_created"] is True and out["client"]["name"] == lead["company_name"]
    assert out["client"]["status"] == "prospect"
    assert out["contact"]["client_id"] == out["client"]["id"]
    assert (out["contact"]["first_name"], out["contact"]["last_name"]) == ("Lan", "Võ Thị Hồng")
    deal = out["deal"]
    assert deal["deal_value"] == 500_000_000 and deal["stage"] == "lead"
    assert deal["client_id"] == out["client"]["id"]
    converted = out["lead"]
    assert converted["status"] == "converted" and converted["converted_at"]
    assert (converted["converted_client_id"], converted["converted_contact_id"],
            converted["converted_deal_id"]) == (out["client"]["id"], out["contact"]["id"],
                                                deal["id"])  # fmt: skip
    again = await api.call("POST", f"/sales/leads/{lead['id']}/convert", DIR, json={})
    assert again.status_code == 409 and again.json()["error"]["code"] == "CONFLICT_STATE"
    edit = await api.call(
        "PATCH", f"/sales/leads/{lead['id']}", DIR, json={"score": 5, "version": 2}
    )
    assert edit.status_code == 409
    assert "sales.lead_convert" in await audit_actions(db_session, lead["id"])
    assert await audit_actions(db_session, out["contact"]["id"]) == ["sales.contact_create"]
    assert await outbox_for(db_session, lead["id"]) == []


async def test_convert_links_existing_client_and_rules(api: ApiClient) -> None:
    """TC-V4-CRM-07: link an existing client (no deal); deal needs a close date; disqualified."""
    client = await make_client(api)
    lead = await make_lead(api, budget=None)
    no_date = await api.call(
        "POST", f"/sales/leads/{lead['id']}/convert", DIR, json={"create_deal": True}
    )
    assert no_date.status_code == 422
    assert no_date.json()["error"]["details"]["field"] == "expected_close_date"
    no_value = await api.call(
        "POST", f"/sales/leads/{lead['id']}/convert", DIR,
        json={"create_deal": True, "expected_close_date": FUTURE},
    )  # fmt: skip
    assert no_value.json()["error"]["details"]["field"] == "deal_value"
    ghost = await api.call(
        "POST", f"/sales/leads/{lead['id']}/convert", DIR, json={"client_id": str(uuid.uuid4())}
    )
    assert ghost.status_code == 422 and ghost.json()["error"]["details"]["field"] == "client_id"
    r = await api.call(
        "POST", f"/sales/leads/{lead['id']}/convert", DIR, json={"client_id": client["id"]}
    )
    assert r.status_code == 200, r.text
    out = r.json()["data"]
    assert out["client_created"] is False and out["client"]["id"] == client["id"]
    assert out["deal"] is None and out["lead"]["converted_deal_id"] is None
    dq = await make_lead(api, status="disqualified")
    refused = await api.call("POST", f"/sales/leads/{dq['id']}/convert", DIR, json={})
    assert refused.status_code == 409


async def test_manager_department_scope(api: ApiClient) -> None:
    """TC-V4-CRM-08: MGR pinned to own department for leads / activities; contacts read +
    create only (no department, like clients)."""
    mine, other = uuid.uuid4(), uuid.uuid4()
    foreign = await api.call("POST", "/sales/leads", "MANAGER", department_id=mine,
                             json=lead_body(department_id=str(other)))  # fmt: skip
    assert foreign.status_code == 403 and foreign.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    lead = await make_lead(api, "MANAGER", dept=mine)
    assert lead["department_id"] == str(mine)  # pinned to the manager's department
    theirs = await make_lead(api, DIR, department_id=str(other))
    own = await api.call("GET", f"/sales/leads/{lead['id']}", "MANAGER", department_id=mine)
    assert own.status_code == 200
    out = await api.call("GET", f"/sales/leads/{theirs['id']}", "MANAGER", department_id=mine)
    assert out.status_code == 403 and out.json()["error"]["code"] == "FORBIDDEN_SCOPE"
    listed = await api.call("GET", "/sales/leads", "MANAGER", department_id=mine,
                            params={"limit": 100})  # fmt: skip
    assert {x["department_id"] for x in listed.json()["data"]} == {str(mine)}
    patch = await api.call("PATCH", f"/sales/leads/{theirs['id']}", "MANAGER",
                           json={"score": 1, "version": 1}, department_id=mine)  # fmt: skip
    assert patch.status_code == 403
    conv = await api.call("POST", f"/sales/leads/{theirs['id']}/convert", "MANAGER",
                          json={}, department_id=mine)  # fmt: skip
    assert conv.status_code == 403
    # activities: deal of another department → 403; own lead → pinned to my department
    client = await make_client(api)
    deal = await make_deal(api, client["id"], department_id=other)
    body = {"type": "call", "subject": "x", "start_at": NOW.isoformat()}
    denied = await api.call("POST", "/sales/activities", "MANAGER",
                            json={**body, "deal_id": deal["id"]}, department_id=mine)  # fmt: skip
    assert denied.status_code == 403
    act = await api.call("POST", "/sales/activities", "MANAGER",
                         json={**body, "lead_id": lead["id"]}, department_id=mine)  # fmt: skip
    assert act.status_code == 201 and act.json()["data"]["department_id"] == str(mine)
    # contacts: read + create allowed, update / delete refused
    c = await api.call(
        "POST",
        "/sales/contacts",
        "MANAGER",
        department_id=mine,
        json={"client_id": client["id"], "first_name": "An", "phone": phone()},
    )
    assert c.status_code == 201, c.text
    cid = c.json()["data"]["id"]
    assert (await api.call("GET", f"/sales/contacts/{cid}", "MANAGER")).status_code == 200
    upd = await api.call(
        "PATCH", f"/sales/contacts/{cid}", "MANAGER", json={"notes": "x", "version": 1}
    )
    assert upd.status_code == 403
    assert (await api.call("DELETE", f"/sales/contacts/{cid}", "MANAGER")).status_code == 403


async def test_reviewer_and_other_pillars_refused(api: ApiClient) -> None:
    """TC-V4-CRM-09: REV → 403 FORBIDDEN_SCOPE on every CRM read; DIR outside khối C → 403;
    EMP has no sales permission."""
    lead = await make_lead(api)
    for path in ("/sales/leads", "/sales/contacts", "/sales/activities",
                 f"/sales/leads/{lead['id']}"):  # fmt: skip
        r = await api.call("GET", path, "REVIEWER")
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN_SCOPE", path
        assert (await api.call("GET", path, "CFO")).status_code == 403, path
        assert (await api.call("GET", path, "EMPLOYEE")).status_code == 403, path
    w = await api.call("POST", "/sales/leads", "REVIEWER", json=lead_body())
    assert w.status_code == 403


async def test_create_is_idempotent(api: ApiClient) -> None:
    """TC-V4-CRM-10: same Idempotency-Key + body → same lead; missing key → 400."""
    body = lead_body()
    h = api.headers(DIR, idem=True)
    first = await api.http.post("/api/v1/sales/leads", json=body, headers=h)
    second = await api.http.post("/api/v1/sales/leads", json=body, headers=h)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    other = await api.http.post("/api/v1/sales/leads", json={**body, "score": 99}, headers=h)
    assert other.status_code == 409
    no_key = await api.http.post("/api/v1/sales/leads", json=lead_body(), headers=api.headers(DIR))
    assert no_key.status_code == 400


async def test_convert_moves_lead_activities_and_client_delete_guard(api: ApiClient) -> None:
    """TC-V4-CRM-13: the lead's activities follow it to the new account; a client with live
    contacts / activities cannot be deleted (no orphans) — CEO included (D-21)."""
    lead = await make_lead(api)
    body = {"type": "call", "subject": "Gọi lần đầu", "start_at": NOW.isoformat()}
    act = await api.call("POST", "/sales/activities", DIR, json={**body, "lead_id": lead["id"]})
    assert act.status_code == 201, act.text
    r = await api.call("POST", f"/sales/leads/{lead['id']}/convert", "CEO", json={})
    assert r.status_code == 200, r.text
    out = r.json()["data"]
    moved = (await api.call("GET", f"/sales/activities/{act.json()['data']['id']}", DIR)).json()
    assert moved["data"]["client_id"] == out["client"]["id"]
    assert moved["data"]["contact_id"] == out["contact"]["id"]
    assert moved["data"]["version"] == act.json()["data"]["version"] + 1
    blocked = await api.call("DELETE", f"/sales/clients/{out['client']['id']}", "CEO")
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "CONFLICT_STATE"


def test_split_name() -> None:
    assert split_name("Nguyễn Văn An") == ("An", "Nguyễn Văn")
    assert split_name("Mai") == ("Mai", None)
