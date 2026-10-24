"""Shared helpers for the per-phase route contract tests (TC-M13-14, TC-M14-05)."""

import re

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.main import API_PREFIX, create_app


def norm(path: str) -> str:
    """`/work/tasks/{task_id}` and `/work/tasks/{id}` compare equal."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def app_routes() -> dict[tuple[str, str], APIRoute]:
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
                    out[(m, norm(path.removeprefix(API_PREFIX)))] = r
    return out


def permissions(dep: Dependant) -> list[str]:
    """Every `require_permission(<perm>)` guard in the dependency tree of a route."""
    found: list[str] = []
    call = dep.call
    if getattr(call, "__name__", "") == "_check" and getattr(call, "__closure__", None):
        names = call.__code__.co_freevars
        found += [
            c.cell_contents for n, c in zip(names, call.__closure__, strict=True) if n == "perm"
        ]
    for sub in dep.dependencies:
        found += permissions(sub)
    return found
