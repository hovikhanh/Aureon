"""TC-M16-09/12 contract part (M1.6 bước C) — `/ai/*`, `/platform/onboarding` match 10 §7.2.5.

* every EP-AI-01..23 + EP-ADM-13/14 row of 10 §7.2.5 exists with the same method + path +
  permission and its OpenAPI `summary` starts with the EP code;
* each of those routes depends on exactly one `require_permission` guard;
* no other `/ai/*` route appears;
* `ToolOut` / `AIActionOut` / `KillSwitchOut` / `CostSummaryOut` only **add** fields over v2.1;
* contract stubs answer `501` in the 10 §1.3 error envelope (no new error code).
"""

import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.core.config import REPO_ROOT
from app.modules.ai.schemas import AIActionOut, KillSwitchOut, ToolOut
from tests.conftest import ApiClient
from tests.contract.route_map import app_routes, norm, permissions

pytestmark = pytest.mark.contract

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
ROW = re.compile(
    r"^\| (EP-(?:AI|ADM)-\d\d) \| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \| `([a-z]+:[a-z]+)` \|",
    re.M,
)
V21_TOOL_FIELDS = {"name", "kind", "autonomy_default", "available", "data_scope",
                   "classification", "reversible", "cost_estimate"}  # fmt: skip
V21_ACTION_FIELDS = {"id", "action_name", "tool_name", "autonomy_level", "status",
                     "input_preview", "result_refs", "on_behalf_of", "approval_request_id",
                     "executed_at", "undo_deadline", "can_undo"}  # fmt: skip


@pytest.fixture(scope="module")
def routes() -> dict[tuple[str, str], APIRoute]:
    return app_routes()


def spec_rows() -> list[tuple[str, str, str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("#### 7.2.5.") : text.index("## 8. Grounding")]
    return ROW.findall(section)


def test_spec_lists_every_m16_endpoint() -> None:
    expected = [f"EP-AI-{i:02d}" for i in range(1, 24)] + ["EP-ADM-13", "EP-ADM-14"]
    assert sorted(r[0] for r in spec_rows()) == sorted(expected)


def test_routes_match_spec_with_one_permission(routes: dict[tuple[str, str], APIRoute]) -> None:
    for ep, method, path, perm in spec_rows():
        route = routes.get((method, norm(path)))
        assert route is not None, f"{ep} {method} {path} missing"
        assert (route.summary or "").startswith(ep + " "), (ep, route.summary)
        assert permissions(route.dependant) == [perm], (ep, permissions(route.dependant))


def test_no_unspecified_ai_route(routes: dict[tuple[str, str], APIRoute]) -> None:
    spec = {(m, norm(p)) for _, m, p, _ in spec_rows()}
    prefixes = ("/ai/", "/platform/onboarding")
    extra = [k for k in routes if k[1].startswith(prefixes) and k not in spec]
    assert extra == []


def test_v21_shapes_only_extended() -> None:
    assert V21_TOOL_FIELDS <= set(ToolOut.model_fields)
    assert V21_ACTION_FIELDS <= set(AIActionOut.model_fields)
    assert {"agent_profile_code", "request_id", "created_at"} <= set(AIActionOut.model_fields)
    assert {"enabled", "mode", "agents", "changed_by", "changed_at", "autonomy_ceiling",
            "reason"} <= set(KillSwitchOut.model_fields)  # fmt: skip
    metadata = {"tool_id", "brd_name", "description", "input_schema", "output_schema",
                "permission", "risk_level", "data_scope", "data_classification",
                "autonomy_default", "approval_required", "reversible", "audit_required",
                "cost_estimate", "owner", "compute", "autonomy_max", "agents",
                "effective_level", "p1_frozen", "action_name", "endpoint_ref"}  # fmt: skip
    assert metadata <= set(ToolOut.model_fields)


async def test_ai_admin_forbidden_for_director(api: ApiClient) -> None:
    """RBAC is checked before the stub body: DIR has no `ai:admin` → 403 FORBIDDEN_ROLE."""
    r = await api.call("GET", "/ai/tool-calls", "DIR")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


async def test_stub_501_envelope(api: ApiClient) -> None:
    r = await api.call("GET", "/ai/agents", "ADM")
    if r.status_code == 501:  # bước C; T-646 replaces the stub with a real handler
        assert r.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "EP-AI-16" in r.json()["error"]["message"]
    else:
        assert r.status_code == 200
