"""T-646 — AI agents, autonomy ceiling + policies, kill switch (10 §7.2.5, R-DEC-71..73/77).

TC-M16-05 seed · TC-M16-06 effective tools · TC-M16-07 `resolve_level` decision table ·
TC-M16-08 EP-AI-18..21 · TC-M16-09 RBAC (agents/policies part) · TC-M16-17 `ai.policy_changed`.
Runs against the seeded dev DB inside the rolled-back `db_session`.
"""

import itertools
import uuid
from typing import Any

import pytest
from sqlalchemy import func, select, update

from app.core.deps import Principal
from app.core.errors import ValidationError
from app.core.events.registry import is_registered
from app.modules.ai.models import AgentProfile, AutonomyPolicy
from app.modules.ai.schemas import KillSwitchIn
from app.modules.ai.services.agent_catalog import AGENTS, seed_tools
from app.modules.ai.services.agent_service import AgentService
from app.modules.ai.services.autonomy import AUTONOMY_DEFAULTS, resolve_level
from app.modules.ai.services.kill_switch_service import KillSwitchService
from app.modules.ai.tools import get_tool
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.platform.models import AuditLog, OutboxEvent
from app.seed.ai_seed import seed_agents
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

ROLES = ("CEO", "DIR", "MGR", "EMP", "REV", "ADM")


def principal(role: str) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role,
                     permissions=frozenset(ROLE_PERMISSIONS[role]))  # fmt: skip


async def _level(db: Any, action: str = "ACT-create_task", *, role: str = "CEO",
                 agent: str = "ceo", amount: int | None = None) -> str:  # fmt: skip
    return await resolve_level(db, action_name=action, role=role, amount=amount, agent_code=agent)


def _policy(**kw: Any) -> AutonomyPolicy:
    base: dict[str, Any] = {
        "action_name": "ACT-create_task",
        "tool_name": "TOOL-create_task",
        "level": "L1",
        "max_level": "L2",
        "is_active": True,
        "reason": "t",
    }
    return AutonomyPolicy(**(base | kw))


async def _events(db: Any, event_type: str) -> list[OutboxEvent]:
    """Events of this test's (rolled-back) transaction only — `now()` is the transaction start,
    so rows committed earlier on the dev DB (e.g. the real-stack E2E) are ignored."""
    rows = await db.execute(
        select(OutboxEvent)
        .where(OutboxEvent.event_type == event_type, OutboxEvent.created_at >= func.now())
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
    )
    return list(rows.scalars().all())


# ---------- TC-M16-05 seed ----------
async def test_seed_six_agents_idempotent(db_session) -> None:
    await seed_agents(db_session)
    again = await seed_agents(db_session)
    assert again["created"] == 0
    rows = {a.code: a for a in (await db_session.execute(select(AgentProfile))).scalars()}
    assert set(rows) == {a.code for a in AGENTS}
    for spec in AGENTS:
        a = rows[spec.code]
        assert a.agent_ref == spec.agent_ref and a.max_autonomy_level == "L2"
        assert a.allowed_tools == seed_tools(spec)
        for name in a.allowed_tools:
            t = get_tool(name)
            assert t is not None and t.kind != "APPROVAL" and not t.p1_frozen


# ---------- TC-M16-06 effective tools ----------
async def test_effective_tools_is_agent_intersect_permissions(db_session) -> None:
    svc = AgentService(db_session)
    ceo = principal("CEO")
    ceo_tools = {t.name for t in await svc.effective_tools("ceo", ceo.permissions)}
    allowed = set((await svc.get("ceo")).allowed_tools)  # type: ignore[union-attr]
    assert ceo_tools <= allowed
    assert "TOOL-list_tasks" not in ceo_tools  # CEO may read tasks but the agent lacks the tool
    emp_tools = {t.name for t in await svc.effective_tools("ceo", principal("EMP").permissions)}
    assert emp_tools < ceo_tools  # narrower person ⇒ narrower tool set
    await db_session.execute(update(AgentProfile).where(AgentProfile.code == "ceo")
                             .values(is_enabled=False))  # fmt: skip
    assert await svc.effective_tools("ceo", ceo.permissions) == ()
    assert await svc.effective_tools("nope", ceo.permissions) == ()


# ---------- TC-M16-07 resolve_level ----------
async def test_ceiling_caps_every_seed_default(db_session) -> None:
    for action in AUTONOMY_DEFAULTS:
        assert await _level(db_session, action) in ("L0", "L1", "L2")


async def test_no_path_returns_l3_under_l2_ceiling(db_session) -> None:
    """Property-style: every seed default × policy level × role × agent max ≤ L2."""
    db_session.add(_policy(level="L3", max_level="L3", role_code="CEO"))
    db_session.add(_policy(level="L3", max_level="L3", agent_profile_code="task"))
    await db_session.execute(update(AgentProfile).values(max_autonomy_level="L3"))
    await db_session.flush()
    for action, role, agent in itertools.product(
        list(AUTONOMY_DEFAULTS)[:6], ROLES, ("ceo", "task", "assistant")
    ):
        assert await _level(db_session, action, role=role, agent=agent) != "L3"


async def test_policy_specificity_and_lowest_on_tie(db_session, ceiling_l3) -> None:
    db_session.add(_policy(level="L2", max_level="L3"))  # general
    db_session.add(_policy(level="L3", max_level="L3", role_code="CEO"))  # role
    await db_session.flush()
    assert await _level(db_session, role="CEO") == "L3"  # role beats general
    assert await _level(db_session, role="MGR") == "L2"  # only the general row matches
    db_session.add(_policy(level="L1", max_level="L3", agent_profile_code="ceo"))  # agent
    await db_session.flush()
    assert await _level(db_session, role="CEO") == "L1"  # agent beats role
    db_session.add(_policy(level="L0", max_level="L3", agent_profile_code="ceo",
                           max_amount=None, role_code=None, currency=None,
                           action_name="ACT-create_meeting",
                           tool_name="TOOL-create_meeting"))  # fmt: skip
    db_session.add(_policy(level="L2", max_level="L3", agent_profile_code="ceo",
                           action_name="ACT-create_meeting", role_code="MGR",
                           tool_name="TOOL-create_meeting"))  # fmt: skip
    db_session.add(_policy(level="L1", max_level="L3", agent_profile_code="ceo",
                           action_name="ACT-create_meeting", role_code="MGR", max_amount=5,
                           currency="VND", is_active=False,
                           tool_name="TOOL-create_meeting"))  # fmt: skip
    await db_session.flush()
    assert await _level(db_session, "ACT-create_meeting", role="MGR") == "L2"  # inactive ignored


async def test_tie_between_same_rank_rows_takes_lowest(db_session, ceiling_l3) -> None:
    db_session.add(_policy(level="L3", max_level="L3", role_code="CEO"))
    db_session.add(_policy(level="L1", max_level="L3", role_code="CEO", max_amount=10**12,
                           currency="VND"))  # fmt: skip
    db_session.add(_policy(level="L2", max_level="L3", role_code="CEO", max_amount=10**13,
                           currency="VND"))  # fmt: skip
    await db_session.flush()
    # amount fits both amount rows (same rank) → the lowest of them wins
    assert await _level(db_session, role="CEO", amount=1000) == "L1"
    # no amount → amount rows do not match → role row
    assert await _level(db_session, role="CEO") == "L3"


async def test_agent_max_caps_level(db_session, ceiling_l3) -> None:
    await db_session.execute(update(AgentProfile).where(AgentProfile.code == "ceo")
                             .values(max_autonomy_level="L1"))  # fmt: skip
    assert await _level(db_session) == "L1"
    assert await _level(db_session, agent="assistant") == "L3"  # legacy code: no agent cap


async def test_kill_switch_modes_and_scope(db_session, ceiling_l3) -> None:
    ks = KillSwitchService(db_session)
    adm = principal("ADM")
    await ks.set(adm, KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=[], reason="r"))
    assert await _level(db_session) == "L2"
    await ks.set(adm, KillSwitchIn(enabled=True, mode="L0", agents=["task"], reason="r"))
    assert await _level(db_session, agent="task") == "L0"
    assert await _level(db_session, agent="ceo") == "L3"
    await ks.set(adm, KillSwitchIn(enabled=False, mode="L0", agents=[], reason="r"))
    assert await _level(db_session) == "L3"


async def test_kill_switch_validates_agents_and_reason(db_session) -> None:
    ks = KillSwitchService(db_session)
    with pytest.raises(ValidationError):
        await ks.set(
            principal("ADM"),
            KillSwitchIn(enabled=True, mode="L0", agents=["reporter"], reason="r"),
        )
    with pytest.raises(ValidationError):
        await ks.set(principal("ADM"),
                     KillSwitchIn(enabled=True, mode="L0", agents=[], reason="  "))  # fmt: skip


async def test_kill_switch_emits_policy_changed(db_session) -> None:
    await KillSwitchService(db_session).set(
        principal("ADM"), KillSwitchIn(enabled=True, mode="WRITE_OFF", agents=["ceo"],
                                       reason="incident #7"),
    )  # fmt: skip
    ev = await _events(db_session, "ai.policy_changed")
    assert ev and ev[-1].payload["change"] == "kill_switch"
    assert ev[-1].payload["agent_code"] == "ceo" and "reason" not in ev[-1].payload
    st = await KillSwitchService(db_session).status()
    assert (st.autonomy_ceiling, st.reason) == ("L2", "incident #7")


# ---------- HTTP: EP-AI-12/16/17 ----------
async def test_agents_list_month_spend_only_for_admin(api: ApiClient) -> None:
    emp = (await api.call("GET", "/ai/agents", "EMP")).json()["data"]
    assert len(emp) == 6 and all("month_spend_usd" not in a for a in emp)
    adm = (await api.call("GET", "/ai/agents", "ADM")).json()["data"]
    assert all("month_spend_usd" in a for a in adm)
    ceo = next(a for a in adm if a["code"] == "ceo")
    assert ceo["agent_ref"] == "AGT-CEO" and ceo["effective_max_level"] == "L2"
    ks = (await api.call("GET", "/ai/kill-switch", "EMP")).json()["data"]
    assert ks["autonomy_ceiling"] == "L2"


async def test_patch_agent_rules(api: ApiClient, db_session) -> None:
    async def patch(body: dict[str, Any], role: str = "ADM", code: str = "task") -> Any:
        return await api.call("PATCH", f"/ai/agents/{code}", role,
                              json={"reason": "tune", "version": 1} | body)  # fmt: skip

    r = await patch({"max_autonomy_level": "L3"})
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "above_ceiling"
    for bad in ("TOOL-approve_request", "TOOL-upsert_risk", "TOOL-nope"):
        r = await patch({"allowed_tools": [bad]})
        assert r.json()["error"]["details"]["reason"] == "invalid_tool", bad
    assert (await patch({}, code="nope")).status_code == 404
    assert (await patch({"is_enabled": False}, role="DIR")).status_code == 403
    r = await patch({"is_enabled": False, "max_autonomy_level": "L1"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert (body["is_enabled"], body["max_autonomy_level"], body["version"]) == (False, "L1", 2)
    assert (await patch({"is_enabled": True})).status_code == 409  # stale version
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "ai.agent_update"))).scalars().all()  # fmt: skip
    assert audit and audit[-1].why == "tune"
    ev = await _events(db_session, "ai.policy_changed")
    assert ev[-1].payload == {"change": "agent", "ref_id": ev[-1].payload["ref_id"],
                              "agent_code": "task", "enabled": False, "level": "L1"}  # fmt: skip


# ---------- HTTP: EP-AI-18..21 ----------
async def test_policy_crud_and_rules(api: ApiClient, db_session) -> None:
    async def create(body: dict[str, Any], role: str = "ADM") -> Any:
        base = {"tool_name": "TOOL-create_task", "level": "L1", "max_level": "L2",
                "reason": "pilot"}  # fmt: skip
        return await api.call("POST", "/ai/autonomy-policies", role, json=base | body)

    def why(r: Any) -> str:
        return r.json()["error"]["details"].get("reason", r.json()["error"]["code"])

    assert why(await create({"tool_name": "TOOL-get_metric"})) == "not_configurable"
    assert why(await create({"tool_name": "TOOL-approve_request"})) == "not_configurable"
    assert why(await create({"level": "L2", "max_level": "L1"})) == "above_tool_max"
    assert why(await create({"tool_name": "TOOL-generate_report", "max_level": "L3"})) in (
        "above_tool_max", "above_ceiling")  # fmt: skip
    assert why(await create({"level": "L3", "max_level": "L3"})) == "above_ceiling"
    assert (await create({"reason": ""})).status_code == 422
    assert (await create({"max_amount": 5})).json()["error"]["code"] == "VALIDATION_ERROR"
    assert (await create({}, role="MGR")).status_code == 403
    no_idem = await api.http.post(
        "/api/v1/ai/autonomy-policies", headers=api.headers("ADM"),
        json={"tool_name": "TOOL-create_task", "level": "L1", "max_level": "L2", "reason": "x"},
    )  # fmt: skip
    assert no_idem.status_code == 400

    r = await create({"role_code": "MGR"})
    assert r.status_code == 201, r.text
    pol = r.json()["data"]
    assert pol["action_name"] == "ACT-create_task" and pol["version"] == 1
    assert (await create({"role_code": "MGR"})).status_code == 409  # duplicate live key

    listed = await api.call("GET", "/ai/autonomy-policies?tool_name=TOOL-create_task", "ADM")
    body = listed.json()
    assert body["meta"]["pagination"]["total"] >= 1
    d = next(x for x in body["meta"]["defaults"] if x["tool_name"] == "TOOL-create_task")
    assert d["default_level"] == "L2" and d["max_level"] == "L2"  # seed L3 after the L2 ceiling

    url = f"/ai/autonomy-policies/{pol['id']}"
    r = await api.call("PATCH", url, "ADM", json={"level": "L2", "reason": "ok", "version": 1})
    assert r.status_code == 200 and r.json()["data"]["version"] == 2
    r = await api.call("PATCH", url, "ADM", json={"level": "L0", "reason": "x", "version": 1})
    assert r.status_code == 409
    r = await api.call("PATCH", url, "ADM", json={"level": "L3", "reason": "x", "version": 2})
    assert r.status_code == 422
    assert (await api.call("DELETE", url, "ADM")).status_code == 422  # reason required
    assert (await api.call("DELETE", url, "ADM", params={"reason": "rollback"})).status_code == 204
    assert (await api.call("DELETE", url, "ADM", params={"reason": "again"})).status_code == 404
    assert (await create({"role_code": "MGR"})).status_code == 201  # key free after delete
    deleted = await api.call("GET", "/ai/autonomy-policies", "ADM",
                             params={"include_deleted": "true", "role_code": "MGR"})  # fmt: skip
    assert deleted.json()["meta"]["pagination"]["total"] == 2

    actions = {a.action for a in (await db_session.execute(select(AuditLog).where(
        AuditLog.action.like("ai.autonomy_policy_%")))).scalars()}  # fmt: skip
    assert actions == {"ai.autonomy_policy_create", "ai.autonomy_policy_update",
                       "ai.autonomy_policy_delete"}  # fmt: skip
    changes = [
        e.payload
        for e in await _events(db_session, "ai.policy_changed")
        if e.payload.get("change") == "autonomy_policy"
    ]
    assert len(changes) == 4
    assert all("reason" not in p for p in changes)


async def test_execution_and_finance_caps(api: ApiClient, ceiling_l3) -> None:
    async def create(body: dict[str, Any]) -> Any:
        return await api.call("POST", "/ai/autonomy-policies", "ADM",
                              json={"reason": "r", "level": "L2"} | body)  # fmt: skip

    r = await create({"tool_name": "TOOL-send_notification", "max_level": "L3"})
    assert r.json()["error"]["details"]["reason"] == "execution_max_l2"
    r = await create({"tool_name": "TOOL-create_invoice", "level": "L3", "max_level": "L3"})
    assert r.json()["error"]["details"]["reason"] in ("critical_field", "above_tool_max")


async def test_rbac_admin_endpoints(api: ApiClient) -> None:
    for role in ("DIR", "MGR", "EMP", "REV"):
        assert (await api.call("GET", "/ai/autonomy-policies", role)).status_code == 403
        assert (await api.call("PATCH", "/ai/agents/ceo", role,
                               json={"reason": "x", "version": 1})).status_code == 403  # fmt: skip
        assert (await api.call("GET", "/ai/agents", role)).status_code == 200
    for role in ("CEO", "ADM"):
        assert (await api.call("GET", "/ai/autonomy-policies", role)).status_code == 200


def test_policy_changed_registered() -> None:
    assert is_registered("ai.policy_changed")
    assert is_registered("platform.onboarding_completed")


async def test_tools_catalog_agents_and_effective_level(api: ApiClient) -> None:
    """EP-AI-14 (T-646 part): `agents[]` from live profiles, `effective_level` after ceiling."""
    rows = {t["name"]: t for t in (await api.call("GET", "/ai/tools", "CEO")).json()["data"]}
    ct = rows["TOOL-create_task"]
    assert {"ceo", "task", "meeting"} <= set(ct["agents"])
    assert ct["autonomy_default"] == "L3" and ct["effective_level"] == "L2"
    assert rows["TOOL-get_metric"]["effective_level"] == "L0"
    assert rows["TOOL-approve_request"]["effective_level"] is None
    only = (await api.call("GET", "/ai/tools", "CEO", params={"agent": "reporting"})).json()
    assert {t["name"] for t in only["data"]} <= {n for n, t in rows.items()
                                                  if "reporting" in t["agents"]}  # fmt: skip
    assert only["data"]


async def test_patch_agent_commits(api: ApiClient, db_session) -> None:
    """T-650 regression: EP-AI-17 must commit the request transaction."""
    from unittest.mock import AsyncMock, patch

    with patch.object(db_session, "commit", AsyncMock()) as commit:
        r = await api.call("PATCH", "/ai/agents/task", "ADM",
                           json={"reason": "tune", "version": 1, "is_enabled": False})  # fmt: skip
    assert r.status_code == 200, r.text
    commit.assert_awaited_once()
