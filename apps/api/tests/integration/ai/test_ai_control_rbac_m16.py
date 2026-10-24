"""TC-M16-09 — RBAC of the AI Control Center (02 §5.3, 10 §7.2.5, R-DEC-74; T-651 review).

DIR/MGR/EMP/REV → `403 FORBIDDEN_ROLE` on every `ai:admin` endpoint (EP-AI-13/15/17..23) —
checked before body validation, so empty bodies are enough. Every role reads EP-AI-12/14/16.
CEO + ADM reach the admin reads. Another tenant sees no policy (`404`) on PATCH/DELETE.
"""

import uuid

import pytest

from tests.conftest import ApiClient

pytestmark = pytest.mark.integration

ADMIN_CALLS = (
    ("PUT", "/ai/kill-switch"), ("GET", "/ai/usage"), ("PATCH", "/ai/agents/ceo"),
    ("GET", "/ai/autonomy-policies"), ("POST", "/ai/autonomy-policies"),
    ("PATCH", f"/ai/autonomy-policies/{uuid.uuid4()}"),
    ("DELETE", f"/ai/autonomy-policies/{uuid.uuid4()}?reason=x"),
    ("GET", "/ai/tool-calls"), ("GET", "/ai/model-calls"),
)  # fmt: skip
READS = ("/ai/kill-switch", "/ai/tools", "/ai/agents")


async def test_non_admin_roles_get_forbidden_role(api: ApiClient) -> None:
    for role in ("DIR", "MGR", "EMP", "REV"):
        for method, url in ADMIN_CALLS:
            r = await api.call(method, url, role, json={})
            assert r.status_code == 403, (role, method, url, r.text)
            assert r.json()["error"]["code"] == "FORBIDDEN_ROLE", (role, url)


async def test_every_role_reads_status_tools_agents(api: ApiClient) -> None:
    for role in ("CEO", "DIR", "MGR", "EMP", "REV", "ADM"):
        for url in READS:
            assert (await api.call("GET", url, role)).status_code == 200, (role, url)
    for role in ("CEO", "ADM"):
        for url in ("/ai/usage", "/ai/autonomy-policies", "/ai/tool-calls", "/ai/model-calls"):
            assert (await api.call("GET", url, role)).status_code == 200, (role, url)


async def test_policy_of_another_tenant_is_not_found(api: ApiClient) -> None:
    body = {"tool_name": "TOOL-create_task", "level": "L1", "max_level": "L2",
            "is_active": True, "reason": "tc-m16-09"}  # fmt: skip
    r = await api.call("POST", "/ai/autonomy-policies", "ADM", json=body)
    assert r.status_code == 201, r.text
    pid = r.json()["data"]["id"]
    other = uuid.uuid4()
    r = await api.call("PATCH", f"/ai/autonomy-policies/{pid}", "ADM", tenant_id=other,
                       json={"version": 1, "reason": "x", "level": "L0"})  # fmt: skip
    assert r.status_code == 404, r.text
    r = await api.call("GET", "/ai/autonomy-policies", "ADM", tenant_id=other)
    assert all(p["id"] != pid for p in r.json()["data"])
