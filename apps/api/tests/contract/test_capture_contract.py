"""TC-M15-04/18 contract part (M1.5 bước C) — `/idp/*`, `/data-capture/*`, `/lineage/*` match
10 §7.2.4 (R-DEC-39/64).

* every EP-DC-01..37 row of 10 §7.2.4 exists with the same method + path + permission and its
  OpenAPI `summary` starts with the EP code;
* each of those routes depends on exactly one `require_permission` guard;
* v2.1 `/idp/*` paths are kept (EP-DC-01..12), no other `/idp/*` route appears;
* contract stubs answer `501` in the 10 §1.3 error envelope (no new error code).
"""

import re
import uuid
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from app.core.config import REPO_ROOT
from tests.conftest import ApiClient
from tests.contract.route_map import app_routes, norm, permissions

pytestmark = pytest.mark.contract

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
ROW = re.compile(
    r"^\| (EP-DC-\d\d) \| (GET|POST|PATCH|DELETE) \| `([^`]+)` \| `([a-z]+:[a-z]+)` \|", re.M
)


@pytest.fixture(scope="module")
def routes() -> dict[tuple[str, str], APIRoute]:
    return app_routes()


def spec_rows() -> list[tuple[str, str, str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("#### 7.2.4.") : text.index("#### 7.2.5.")]
    return ROW.findall(section)


def test_spec_lists_every_m15_endpoint() -> None:
    assert sorted(r[0] for r in spec_rows()) == [f"EP-DC-{i:02d}" for i in range(1, 38)]


def test_routes_match_spec_with_one_permission(routes: dict[tuple[str, str], APIRoute]) -> None:
    for ep, method, path, perm in spec_rows():
        route = routes.get((method, norm(path)))
        assert route is not None, f"{ep} {method} {path} missing"
        assert (route.summary or "").startswith(ep + " "), (ep, route.summary)
        assert permissions(route.dependant) == [perm], (ep, permissions(route.dependant))


def test_no_unspecified_capture_route(routes: dict[tuple[str, str], APIRoute]) -> None:
    spec = {(m, norm(p)) for _, m, p, _ in spec_rows()}
    prefixes = ("/idp/", "/data-capture/", "/lineage/")
    extra = [k for k in routes if k[1].startswith(prefixes) and k not in spec]
    assert extra == []


async def test_stub_answers_501_envelope(api: ApiClient) -> None:
    r = await api.call("GET", f"/lineage/hr.employees/{uuid.uuid4()}", "CEO")
    assert r.status_code == 501
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert (await api.call("GET", "/data-capture/inbox", "ADMIN")).status_code == 403
