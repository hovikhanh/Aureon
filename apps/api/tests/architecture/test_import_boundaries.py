"""TC-ARCH-001 (T-004, DEC-125, CLAUDE.md §4.3) — import boundaries via static AST scan.

Rules:
1. `core/` never imports `app.modules`.
2. A module may use another module only via its public `services` / `schemas` (DTOs) /
   `events` — never its `models`, `repositories` or `routes`.
3. Inside a module, layers point downward only: routes → services → repositories → models.
4. No import cycle between modules (module-level graph over every import, incl. lazy ones).

AST scan (no `import-linter` dependency): includes imports inside functions, so a lazy
import cannot dodge the rules. `TYPE_CHECKING` imports count too (stricter by design).
"""

import ast
from collections import defaultdict
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "src" / "app"
MODULES = sorted(
    p.name for p in (APP / "modules").iterdir() if p.is_dir() and not p.name.startswith("_")
)
PUBLIC_LAYERS = {"services", "schemas", "events"}
LAYER_RANK = {"models": 0, "repositories": 1, "services": 2, "routes": 3}
# Allowed upward/peer edges inside a module (none for now).
INTRA_ALLOW: set[tuple[str, str]] = set()


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.append((node.module, node.lineno))
            out += [(f"{node.module}.{a.name}", node.lineno) for a in node.names]
    return out


def _py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _owner(path: Path) -> tuple[str, str] | None:
    """(module, layer) of a file under app/modules."""
    rel = path.relative_to(APP).parts
    if rel[0] != "modules" or len(rel) < 3:
        return None
    layer = rel[2].removesuffix(".py")
    return rel[1], layer


def _target(name: str) -> tuple[str, str | None] | None:
    parts = name.split(".")
    if parts[:2] != ["app", "modules"] or len(parts) < 3:
        return None
    return parts[2], parts[3] if len(parts) > 3 else None


def test_modules_discovered() -> None:
    assert MODULES == [
        "ai", "auth", "dashboard", "execution", "finance", "hr", "idp", "platform", "product",
        "risk", "sales",
    ]  # fmt: skip


def test_core_does_not_import_modules() -> None:
    bad = [
        f"{p.relative_to(APP)}:{ln} {name}"
        for p in _py_files(APP / "core")
        for name, ln in _imports(p)
        if name.startswith("app.modules")
    ]
    assert bad == []


def test_cross_module_only_public_layers() -> None:
    bad = []
    for p in _py_files(APP / "modules"):
        owner = _owner(p)
        if owner is None:
            continue
        for name, ln in _imports(p):
            tgt = _target(name)
            if tgt is None or tgt[0] == owner[0] or tgt[1] is None:
                continue
            if tgt[1] not in PUBLIC_LAYERS:
                bad.append(f"{p.relative_to(APP)}:{ln} → {name}")
    assert bad == [], "cross-module import of non-public layer (DEC-125)"


def test_layers_point_downward() -> None:
    bad = []
    for p in _py_files(APP / "modules"):
        owner = _owner(p)
        if owner is None or owner[1] not in LAYER_RANK:
            continue
        for name, ln in _imports(p):
            tgt = _target(name)
            if tgt is None or tgt[0] != owner[0] or tgt[1] not in LAYER_RANK:
                continue
            if LAYER_RANK[tgt[1]] > LAYER_RANK[owner[1]] and (owner[1], tgt[1]) not in INTRA_ALLOW:
                bad.append(f"{p.relative_to(APP)}:{ln} → {name}")
    assert bad == [], "layer imports upward (routes → services → repositories → models)"


def _module_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for p in _py_files(APP / "modules"):
        owner = _owner(p)
        if owner is None:
            continue
        for name, _ in _imports(p):
            tgt = _target(name)
            if tgt and tgt[0] != owner[0]:
                graph[owner[0]].add(tgt[0])
    return graph


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        stack.append(n)
        for m in sorted(graph.get(n, ())):
            if state.get(m) == 1:
                return [*stack[stack.index(m) :], m]
            if m not in state and (c := visit(m)):
                return c
        stack.pop()
        state[n] = 2
        return None

    for n in sorted(graph):
        if n not in state and (c := visit(n)):
            return c
    return None


def test_no_cycles_between_modules() -> None:
    assert _find_cycle(_module_graph()) is None


def test_cycle_detector_works() -> None:
    assert _find_cycle({"a": {"b"}, "b": {"c"}, "c": {"a"}}) == ["a", "b", "c", "a"]
    assert _find_cycle({"a": {"b"}, "b": set()}) is None


@pytest.mark.parametrize("module", MODULES)
def test_every_module_imports_cleanly(module: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Runtime check: each module imports with no other module pre-loaded (real cycles fail).

    `app.modules.*` is evicted from `sys.modules` (restored after the test by monkeypatch),
    so the import starts cold; SQLAlchemy mappers are not re-registered (models stay cached
    via `app.model_registry` — only routes/services/schemas/repositories are re-imported).
    """
    import importlib
    import sys

    for name in list(sys.modules):
        if name.startswith("app.modules.") and ".models" not in name:
            monkeypatch.delitem(sys.modules, name)
    importlib.import_module(f"app.modules.{module}.routes.router")
    importlib.import_module(f"app.modules.{module}.services")


def test_scanner_sees_lazy_and_from_imports(tmp_path: Path) -> None:
    src = tmp_path / "x.py"
    src.write_text(
        "from app.modules.finance import models\n"
        "def f():\n"
        "    from app.modules.hr.repositories import EmployeeRepository\n"
        "    import app.modules.sales.models\n",
        encoding="utf-8",
    )
    names = {n for n, _ in _imports(src)}
    assert "app.modules.finance.models" in names
    assert "app.modules.hr.repositories.EmployeeRepository" in names
    assert "app.modules.sales.models" in names
    assert _target("app.modules.hr.repositories.EmployeeRepository") == ("hr", "repositories")
    assert _target("app.modules.hr.services")[1] in PUBLIC_LAYERS  # type: ignore[index]
    assert _owner(APP / "modules" / "risk" / "services" / "risk_service.py") == ("risk", "services")
