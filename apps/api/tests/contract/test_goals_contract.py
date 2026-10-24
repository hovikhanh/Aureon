"""TC-M14-05 (T-626C, contract) — `/goals/*`, `/kpis/*`, `/objectives/*`, `/key-results/*`
match 10 §7.2.3 (R-DEC-39/58).

* every EP-STR-01..22 / EP-KPI-01..10 / EP-OKR-01..11 / EP-PRF-01..06 row of 10 §7.2.3 exists
  with the same method + path + permission (ranges `EP-STR-17..21` expanded), and its OpenAPI
  `summary` starts with the EP code;
* each of those routes depends on exactly one `require_permission` guard;
* the old `/execution/{kpis,objectives,key-results,check-ins,initiatives}*` paths are gone (no
  alias), `/execution/{meetings,decisions,dashboard}` stay;
* contract stubs answer `501` in the 10 §1.3 error envelope (no new error code).
"""

import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.core.config import REPO_ROOT
from tests.conftest import ApiClient
from tests.contract.route_map import app_routes, norm, permissions

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def routes() -> dict[tuple[str, str], APIRoute]:
    return app_routes()


SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
ROW = re.compile(
    r"^\| (EP-(?:STR|KPI|OKR|PRF)-\d\d) \| (GET|POST|PATCH|DELETE) \| `([^`]+)` \| "
    r"`([a-z]+:[a-z]+)`",
    re.M,
)
# EP-STR-17..21 is a single 10 row (`GET/POST/GET/PATCH/DELETE`, `…/milestones[/{milestone_id}]`).
MS = "/goals/initiatives/{id}/milestones"
EP_STR_17_21 = [
    ("EP-STR-17", "GET", MS, "execution:read"),
    ("EP-STR-18", "POST", MS, "execution:write"),
    ("EP-STR-19", "GET", MS + "/{milestone_id}", "execution:read"),
    ("EP-STR-20", "PATCH", MS + "/{milestone_id}", "execution:write"),
    ("EP-STR-21", "DELETE", MS + "/{milestone_id}", "execution:write"),
]


def spec_rows() -> list[tuple[str, str, str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("#### 7.2.3.") : text.index("#### 7.2.4.")]
    return [*ROW.findall(section), *EP_STR_17_21]


def test_spec_lists_every_m14_endpoint() -> None:
    codes = sorted(r[0] for r in spec_rows())
    expected = sorted(
        [f"EP-STR-{i:02d}" for i in range(1, 23)]
        + [f"EP-KPI-{i:02d}" for i in range(1, 11)]
        + [f"EP-OKR-{i:02d}" for i in range(1, 12)]
        + [f"EP-PRF-{i:02d}" for i in range(1, 7)]
    )
    assert codes == expected


def test_routes_match_spec_with_one_permission(routes: dict[tuple[str, str], APIRoute]) -> None:
    for ep, method, path, perm in spec_rows():
        route = routes.get((method, norm(path)))
        assert route is not None, f"{ep} {method} {path} missing"
        assert (route.summary or "").startswith(ep + " "), (ep, route.summary)
        assert route.response_model is not None or route.status_code == 204, ep
        assert permissions(route.dependant) == [perm], (ep, permissions(route.dependant))


def test_old_paths_removed(routes: dict[tuple[str, str], APIRoute]) -> None:
    old = tuple(
        f"/execution/{p}" for p in ("kpis", "objectives", "key-results", "check-ins", "initiatives")
    )
    assert [p for _, p in routes if p.startswith(old)] == []
    kept = {p for _, p in routes if p.startswith("/execution/")}
    assert {"/execution/meetings", "/execution/decisions", "/execution/dashboard"} <= kept


async def test_old_paths_404_and_stub_501(api: ApiClient) -> None:
    for url in ("/execution/kpis", "/execution/objectives", "/execution/check-ins",
                "/execution/initiatives"):  # fmt: skip
        assert (await api.call("GET", url, "CEO")).status_code == 404, url
    r = await api.call("GET", "/goals/tree", "CEO")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "EP-STR-01" in r.json()["error"]["message"]
