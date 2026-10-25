"""TC-M13-14 (T-619C, contract) — `/work/*`, `/workflow/*` match 10 §7.2.2 (R-DEC-40).

* every EP-TASK-01..19 / EP-WF-01..03 row of 10 §7.2.2 exists with the same method + path +
  permission, and its OpenAPI `summary` starts with the EP code;
* each of those routes depends on exactly one `require_permission` guard;
* the old `/execution/{tasks,projects}*` and `/platform/approvals*` paths are gone (no alias);
* contract stubs answer `501` in the 10 §1.3 error envelope (no new error code).
"""

import re
from pathlib import Path

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.core.config import REPO_ROOT
from app.main import API_PREFIX, create_app

pytestmark = pytest.mark.contract

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
ROW = re.compile(
    r"^\| (EP-(?:TASK|WF)-\d\d) \| (GET|POST|PATCH|DELETE) \| `([^`]+)` \| `([a-z]+:[a-z]+)` \|",
    re.M,
)
# EP-TASK-19 is specified as a bullet (10 §7.2.2), not a table row.
EP_TASK_19 = ("EP-TASK-19", "POST", "/work/tasks/{id}/reassign-requests", "execution:write")


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


def test_no_m13_stub_left() -> None:
    """T-619..T-622 replaced every `501` stub of 10 §7.2.2 with a real handler."""
    src = REPO_ROOT / "apps/api/src/app/modules"
    for f in ("execution/routes/work.py", "platform/routes/workflow.py"):
        assert "not_implemented" not in (src / f).read_text(encoding="utf-8"), f
