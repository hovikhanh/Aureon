"""T-650: every mutating route (POST/PATCH/PUT/DELETE) commits its request transaction.

`get_db` yields a plain session without autocommit, so a write route that only flushes returns
200 and silently loses the change. The integration `api` fixture shares one rolled-back session,
so it cannot see this — the real stack E2E found EP-ADM-14, EP-AI-17 and EP-AI-19..21. This
static check walks each route body (and module-level helpers it calls) for `.commit(`; routes
whose service owns the commit are listed with the service method that must contain it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MODULES = Path(__file__).resolve().parents[2] / "src" / "app" / "modules"
MUTATING = {"post", "patch", "put", "delete"}
# route → (service file, method) that commits itself (auth session / DLQ replay before send)
SERVICE_COMMITS = {
    ("auth/routes/router.py", "login"): ("auth/services/auth_service.py", "login"),
    ("auth/routes/router.py", "refresh"): ("auth/services/auth_service.py", "refresh"),
    ("auth/routes/router.py", "logout"): ("auth/services/auth_service.py", "logout"),
    ("platform/routes/router.py", "replay_dead_letter"): (
        "platform/services/platform_service.py", "replay_dead_letter",
    ),
}  # fmt: skip

Fn = ast.FunctionDef | ast.AsyncFunctionDef


def _functions(tree: ast.AST) -> dict[str, Fn]:
    return {
        n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _commits(fn: Fn, helpers: dict[str, Fn], seen: set[str]) -> bool:
    if ".commit(" in ast.unparse(fn):
        return True
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name in helpers and name not in seen:
                seen.add(name)
                if _commits(helpers[name], helpers, seen):
                    return True
    return False


def _mutating_routes() -> list[tuple[str, Fn, dict[str, Fn]]]:
    out = []
    for f in sorted([*MODULES.glob("*/routes/*.py"), *MODULES.glob("*/routes.py")]):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        top = {
            n.name: n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        for fn in top.values():
            for d in fn.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                        and d.func.attr in MUTATING):  # fmt: skip
                    out.append((f.relative_to(MODULES).as_posix(), fn, top))
    return out


def test_routes_found() -> None:
    assert len(_mutating_routes()) > 50


def test_every_mutating_route_commits() -> None:
    missing = [
        f"{path}:{fn.lineno} {fn.name}"
        for path, fn, helpers in _mutating_routes()
        if (path, fn.name) not in SERVICE_COMMITS and not _commits(fn, helpers, set())
    ]
    assert missing == [], "write route without db.commit() (change is lost):\n" + "\n".join(missing)


@pytest.mark.parametrize(("route", "service"), sorted(SERVICE_COMMITS.items()))
def test_allowlisted_service_commits(route: tuple[str, str], service: tuple[str, str]) -> None:
    file, method = service
    fns = _functions(ast.parse((MODULES / file).read_text(encoding="utf-8")))
    assert method in fns, f"{route}: {file}::{method} missing"
    assert _commits(fns[method], fns, set()), f"{route}: {file}::{method} does not commit"
