"""TC-M13-14 (T-619C, contract) — `/work/*`, `/workflow/*` match 10 §7.2.2 (R-DEC-40).

* every EP-TASK-01..19 / EP-WF-01..03 row of 10 §7.2.2 exists with the same method + path +
  permission, and its OpenAPI `summary` starts with the EP code;
* each of those routes depends on exactly one `require_permission` guard;
* the old `/execution/{tasks,projects}*` and `/platform/approvals*` paths are gone (no alias);
* contract stubs answer `501` in the 10 §1.3 error envelope (no new error code).
"""

import re
import uuid
from pathlib import Path

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import REPO_ROOT
from app.core.security import sign_access_token
from app.main import API_PREFIX, create_app
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS

pytestmark = pytest.mark.contract

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
ROW = re.compile(
    r"^\| (EP-(?:TASK|WF)-\d\d) \| (GET|POST|PATCH|DELETE) \| `([^`]+)` \| `([a-z]+:[a-z]+)` \|",
    re.M,
)
# EP-TASK-19 is specified as a bullet (10 §7.2.2), not a table row.
EP_TASK_19 = ("EP-TASK-19", "POST", "/work/tasks/{id}/reassign-requests", "execution:write")
# Shrinks as T-619..T-622 replace the stubs with real handlers.
STUBS = {
    "EP-TASK-14", "EP-TASK-15", "EP-TASK-16", "EP-TASK-17", "EP-TASK-18", "EP-TASK-19",
    "EP-WF-01", "EP-WF-02",
}  # fmt: skip


def _norm(path: str) -> str:
    """`/work/tasks/{task_id}` and `/work/tasks/{id}` compare equal."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def spec_rows() -> list[tuple[str, str, str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("#### 7.2.2.")
    section = text[start : text.index("#### 7.2.3.")]
    return [*ROW.findall(section), EP_TASK_19]


@pytest.fixture(scope="module")
def routes() -> dict[tuple[str, str], APIRoute]:
    """(method, normalised path) → APIRoute; walks FastAPI ≥ 0.14x included routers."""
    out: dict[tuple[str, str], APIRoute] = {}
    for top in create_app().routes:
        contexts = (
            top.effective_route_contexts() if hasattr(top, "effective_route_contexts") else []
        )
        pairs = [(c.path, c.original_route) for c in contexts]
        if isinstance(top, APIRoute):
            pairs.append((top.path, top))
        for path, r in pairs:
            if isinstance(r, APIRoute):
                for m in r.methods:
                    out[(m, _norm(path.removeprefix(API_PREFIX)))] = r
    return out


def _permissions(dep: Dependant) -> list[str]:
    found: list[str] = []
    call = dep.call
    if getattr(call, "__name__", "") == "_check" and getattr(call, "__closure__", None):
        names = call.__code__.co_freevars
        found += [
            c.cell_contents for n, c in zip(names, call.__closure__, strict=True) if n == "perm"
        ]
    for sub in dep.dependencies:
        found += _permissions(sub)
    return found


def test_spec_lists_every_m13_endpoint() -> None:
    codes = [r[0] for r in spec_rows()]
    expected = [f"EP-TASK-{i:02d}" for i in range(1, 20)] + [f"EP-WF-0{i}" for i in (1, 2, 3)]
    assert sorted(codes) == sorted(expected)


def test_routes_match_spec_with_one_permission(routes: dict[tuple[str, str], APIRoute]) -> None:
    for ep, method, path, perm in spec_rows():
        route = routes.get((method, _norm(path)))
        assert route is not None, f"{ep} {method} {path} missing"
        assert (route.summary or "").startswith(ep + " "), (ep, route.summary)
        assert _permissions(route.dependant) == [perm], (ep, _permissions(route.dependant))


def test_old_paths_removed(routes: dict[tuple[str, str], APIRoute]) -> None:
    old = (
        "/execution/tasks",
        "/execution/projects",
        "/execution/milestones",
        "/platform/approvals",
    )
    leftovers = [p for _, p in routes if p.startswith(old)]
    assert leftovers == []


def test_stubs_answer_501_envelope(routes: dict[tuple[str, str], APIRoute]) -> None:
    token, _ = sign_access_token(
        user_id=uuid.uuid4(), email="ceo@abc.test", role="CEO", role_id="CEO",
        permissions=list(ROLE_PERMISSIONS["CEO"]), department_id=None, scope_pillars=(),
        tenant_id=DEFAULT_TENANT_ID,
    )  # fmt: skip
    client = TestClient(create_app())
    hdr = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}
    bodies = {
        "EP-TASK-07": {"depends_on_task_id": str(uuid.uuid4())},
        "EP-TASK-15": {"title": "M", "due_date": "2026-11-30"},
        "EP-TASK-16": {"version": 1},
        "EP-TASK-19": {"to_assignee_id": str(uuid.uuid4()), "reason": "r"},
    }
    for ep, method, path, _ in spec_rows():
        if ep not in STUBS:
            continue
        url = API_PREFIX + re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        res = client.request(method, url, headers=hdr, json=bodies.get(ep))
        assert res.status_code == 501, (ep, res.status_code, res.text)
        assert set(res.json()["error"]) == {"code", "message", "details"}
