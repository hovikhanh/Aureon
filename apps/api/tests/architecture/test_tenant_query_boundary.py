"""TC-M11-05 (T-603, R-DEC-21, CLAUDE.md §4.3) — tenant-scoped queries only in repositories.

Layer 1 of tenant filtering lives in `BaseRepository` / module repositories. Any SQL built on a
business entity (`TenantMixin`) elsewhere — `select(Model…)`, `update(Model)`, `delete(Model)`,
`insert(Model)`, `session.get(Model, …)` — would bypass it (layer 2, the session guard, would
still filter, but defence in depth requires both). Static AST scan over every file of `app/`.
"""

import ast
from pathlib import Path

from app.core.base_model import Base, TenantMixin

APP = Path(__file__).resolve().parents[2] / "src" / "app"
SQL_BUILDERS = {"select", "update", "delete", "insert", "exists"}
ALLOWED = ("core/base_repository.py",)
# seed/ bootstraps the database before any tenant context exists; repositories would be circular
ALLOWED_PREFIXES = ("seed/",)


def _business_models() -> frozenset[str]:
    import app.main  # noqa: F401  # side effect: import every module's models into the registry

    return frozenset(
        m.class_.__name__ for m in Base.registry.mappers if issubclass(m.class_, TenantMixin)
    )


def _allowed(rel: str) -> bool:
    in_repo = "/repositories/" in f"/{rel}"
    in_seed = any(rel.startswith(p) for p in ALLOWED_PREFIXES)
    return rel in ALLOWED or in_repo or in_seed


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _names(nodes: list[ast.expr]) -> set[str]:
    return {n.id for arg in nodes for n in ast.walk(arg) if isinstance(n, ast.Name)}


def _violations(path: Path, models: frozenset[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in SQL_BUILDERS:
            hit = _names(list(node.args)) & models
        elif name == "get" and isinstance(node.func, ast.Attribute) and node.args:
            hit = _names([node.args[0]]) & models  # session.get(Model, id)
        else:
            continue
        if hit:
            out.append(f"{path.relative_to(APP)}:{node.lineno} {name}({', '.join(sorted(hit))})")
    return out


def test_business_models_discovered() -> None:
    models = _business_models()
    assert {"Invoice", "Employee", "Task", "SourceDocument", "AIAction"} <= models
    assert "OutboxEvent" not in models and "User" not in models


def test_no_business_query_outside_repositories() -> None:
    models = _business_models()
    found: list[str] = []
    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP).as_posix()
        if "__pycache__" in rel or _allowed(rel):
            continue
        found += _violations(path, models)
    assert found == [], "query business entities through a repository:\n" + "\n".join(found)
