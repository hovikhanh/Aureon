"""TC-M4-01..04 (contract) — the whole catalog in `docs/` and the running code agree.

Why this module exists: the per-phase contract tests (`test_api_contract.py`,
`test_capture_contract.py`, …) hard-code the endpoints of one milestone, so a route or a
registry entry added outside that milestone could drift from the spec unnoticed. The 2026-11-02
audit found 69 live routes with no `EP-*` row at all, no `TOOL-*` table in the v3 doc set (code
had 54 tools), no `METRIC-*` listing (code had 34) and 5 permission mismatches.

This module closes the loop in **both** directions and over the **whole** catalog:

* `TC-M4-01` every `EP-*` declared in `10` §7 resolves to a real route (spec → code);
* `TC-M4-02` every route of the app is covered by an `EP-*` declaration (code → spec);
* `TC-M4-03` the permission a route really guards is one the `EP-*` row lists;
* `TC-M4-04` the `TOOL-*` table (`10` §2.3) and the `METRIC-*` table (`03` §4.2) are exact
  mirrors of `registry.TOOLS` / `catalog.CATALOG`, and every `ACT-*` named in the v3 docs
  exists in code.

The doc tables are rendered from code by the very functions used here (`tool_row`,
`metric_row`), so a failure prints the row to paste into the spec.
"""

import re
from pathlib import Path

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.core.config import REPO_ROOT
from app.main import API_PREFIX, create_app
from app.modules.ai.tools.registry import all_tools
from app.modules.ai.tools.spec import ToolDef
from app.modules.idp.services.actions.registry import action_names
from app.modules.platform.services.catalog import CATALOG, FROZEN_CODES, GROUP_OF, MetricDef
from tests.contract.route_map import norm, permissions

pytestmark = pytest.mark.contract

DOCS = Path(REPO_ROOT) / "docs"
SPEC_API = DOCS / "3.EXECUTION" / "10-API-SPECIFICATION.md"
SPEC_DASH = DOCS / "2.PRODUCT" / "03-DASHBOARD-SPEC.md"

ALL_METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE")
# `EP-ORG-01`, legacy `EP-24`, `EP-DC-14b`, and range rows such as `EP-STR-17..21` (one row
# declaring several ids over the same resource — missing this form once produced a duplicate id).
EP_ID = r"EP-(?:[A-Z]+-)?\d+[a-z]?(?:\.\.\d+)?"
# `| EP-ORG-01 | GET | `/org/organizations` | `hr:read` | … |` — the §7.2/§7.3 tables.
EP_ROW = re.compile(rf"^\|\s*({EP_ID})\s*\|\s*([A-Z/* ]+?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|", re.M)
# `- **EP-TASK-19 (mới, R-DEC-45) — `POST /work/tasks/{id}/reassign-requests` · `execution:write`…`
EP_BULLET = re.compile(rf"^[-*] \*\*({EP_ID})\b(.*)$", re.M)
METHOD_PATH = re.compile(r"`(GET|POST|PATCH|PUT|DELETE) (/[^`]+)`")
PERM = re.compile(r"([a-z_]+:[a-z]+)")

# Routes outside the `EP-*` numbering by design: FastAPI/Starlette built-ins are not in the app
# router, so nothing else is expected here. Add an entry only together with a spec row.
ROUTE_EXEMPT: frozenset[tuple[str, str]] = frozenset()


def _expand_optional(path: str) -> list[str]:
    """`/finance/revenues[/{id}]` → both the collection and the item path."""
    opt = re.search(r"\[([^\]]+)\]", path)
    if not opt:
        return [path]
    return [
        path[: opt.start()] + path[opt.end() :],
        path[: opt.start()] + opt.group(1) + path[opt.end() :],
    ]


def ep_declarations() -> list[tuple[str, list[str], list[str], set[str]]]:
    """(ep_id, methods, normalised paths, permissions) for every EP declared in 10 §7."""
    text = SPEC_API.read_text(encoding="utf-8")
    out: list[tuple[str, list[str], list[str], set[str]]] = []
    for ep, method_cell, path_cell, perm_cell in EP_ROW.findall(text):
        methods = (
            list(ALL_METHODS)
            if "*" in method_cell
            else [m.strip() for m in method_cell.split("/") if m.strip() in ALL_METHODS]
        )
        tokens = [t for t in re.findall(r"`([^`]+)`", path_cell) if t.startswith("/")]
        if not methods or not tokens:
            continue
        paths: list[str] = []
        prev: str | None = None
        root = "/" + tokens[0].strip("/").split("/")[0]
        for token in tokens:
            if not token.startswith(root) and prev is not None:
                # a relative sub-path such as `/pay` or `/stage-history`
                candidates = [prev + token, prev.rsplit("/", 1)[0] + token]
            else:
                candidates = _expand_optional(token)
            paths += candidates
            prev = candidates[-1]
        out.append((ep, methods, [norm(p) for p in paths], set(PERM.findall(perm_cell))))
    for ep, rest in EP_BULLET.findall(text):
        pairs = METHOD_PATH.findall(rest)
        if not pairs:
            continue
        out.append(
            (
                ep,
                [m for m, _ in pairs],
                [norm(p) for _, p in pairs],
                set(re.findall(r"`([a-z_]+:[a-z]+)`", rest)),
            )
        )
    return out


def app_route_map() -> dict[tuple[str, str], APIRoute]:
    """(method, normalised path) → route, for every route the app really serves."""
    out: dict[tuple[str, str], APIRoute] = {}
    for top in create_app().routes:
        contexts = (
            top.effective_route_contexts() if hasattr(top, "effective_route_contexts") else []
        )
        pairs = [(c.path, c.original_route) for c in contexts]
        if isinstance(top, APIRoute):
            pairs.append((top.path, top))
        for path, route in pairs:
            if isinstance(route, APIRoute):
                for method in route.methods:
                    out[(method, norm(path.removeprefix(API_PREFIX)))] = route
    return out


def _route_permissions(dependant: Dependant) -> set[str]:
    return set(permissions(dependant))


# --------------------------------------------------------------- EP ↔ route


def test_every_spec_ep_has_a_route() -> None:
    """TC-M4-01 — an `EP-*` row in 10 §7 without a live route means the spec promises a lie."""
    routes = app_route_map()
    orphans = [
        f"{ep} ({'/'.join(methods)} {paths})"
        for ep, methods, paths, _ in ep_declarations()
        if not any((m, p) in routes for m in methods for p in paths)
    ]
    assert not orphans, "EP declared in 10 §7 with no route:\n  " + "\n  ".join(orphans)


def test_every_route_has_an_ep() -> None:
    """TC-M4-02 — a route with no `EP-*` row is undocumented (10 §7.3 exists for exactly this)."""
    routes = app_route_map()
    covered = {
        (m, p)
        for _, methods, paths, _ in ep_declarations()
        for m in methods
        for p in paths
        if (m, p) in routes
    }
    missing = sorted(set(routes) - covered - ROUTE_EXEMPT)
    assert not missing, "routes without an EP row in 10 §7:\n  " + "\n  ".join(
        f"{m:6} {p} perm={sorted(_route_permissions(routes[(m, p)].dependant)) or '-'}"
        for m, p in missing
    )


def test_route_permissions_match_spec() -> None:
    """TC-M4-03 — the permission guarding a route must be one its `EP-*` row lists."""
    routes = app_route_map()
    bad: list[str] = []
    for ep, methods, paths, spec_perms in ep_declarations():
        if not spec_perms:
            continue  # public / `(token)` rows carry no permission to compare
        for method in methods:
            for path in paths:
                route = routes.get((method, path))
                if route is None:
                    continue
                have = _route_permissions(route.dependant)
                if have and not have <= spec_perms:
                    bad.append(
                        f"{ep} {method} {path}: code={sorted(have)} ⊄ spec={sorted(spec_perms)}"
                    )
    assert not bad, "permission drift between code and 10 §7:\n  " + "\n  ".join(bad)


# --------------------------------------------------------------- registries


def tool_row(tool: ToolDef) -> str:
    """The §2.3 table row for one tool — the renderer the spec table was generated with."""
    perms = " + ".join(f"`{p}`" for p in tool.required_permissions) or "—"
    reversible = {True: "✔", False: "✘", None: "n/a"}[tool.reversible]
    flags = []
    if tool.p1_frozen:
        flags.append("**P1-frozen**")
    if not tool.declare_to_model:
        flags.append("không gửi model")
    if tool.compute:
        flags.append("compute")
    action = f"`{tool.action_name}`" if tool.action_name else "—"
    return (
        f"| `{tool.name}` | {tool.kind} | {tool.domain} | {perms} | {tool.risk_level} | "
        f"{tool.data_classification[:4]} | {tool.autonomy_default}/{tool.autonomy_max} | "
        f"{tool.approval_required or '—'} | {reversible} | {tool.cost_estimate} | {action} | "
        f"{', '.join(flags) or tool.endpoint_ref} |"
    )


def metric_row(metric: MetricDef) -> str:
    """The §4.2 table row for one metric — the renderer the spec table was generated with."""
    events = ", ".join(f"`{e}`" for e in metric.refresh_events) or "— (job `recompute_metrics`)"
    frozen = " **(P1-frozen)**" if metric.code in FROZEN_CODES else ""
    return (
        f"| `{metric.code}`{frozen} | {metric.name_vi} | {GROUP_OF[metric.code]} | "
        f"{metric.pillar} | {metric.unit} | {metric.direction} | "
        f"{metric.warning}/{metric.critical} | `{metric.source_module}` | {events} |"
    )


def _doc_rows(doc: Path, heading: str, prefix: str) -> set[str]:
    """Data rows of the mirror table under `heading` (other sections list the same ids too)."""
    text = doc.read_text(encoding="utf-8")
    start = text.index(heading)
    end = re.search(r"\n## ", text[start:])
    section = text[start : start + (end.start() if end else len(text) - start)]
    row = re.compile(rf"^\| `{prefix}[A-Za-z0-9_-]+`")
    return {line.rstrip() for line in section.splitlines() if row.match(line)}


def test_tool_registry_table_mirrors_code() -> None:
    """TC-M4-04a — 10 §2.3 lists exactly the tools in `registry.TOOLS`, with the same metadata."""
    want = {tool_row(t) for t in all_tools()}
    have = _doc_rows(SPEC_API, "### 2.3. Danh mục đầy đủ", "TOOL-")
    assert want == have, (
        "10 §2.3 `TOOL-*` table out of sync with registry.py.\n"
        f"missing from doc ({len(want - have)}):\n  " + "\n  ".join(sorted(want - have)) + "\n"
        f"stale in doc ({len(have - want)}):\n  " + "\n  ".join(sorted(have - want))
    )


def test_metric_catalog_table_mirrors_code() -> None:
    """TC-M4-04b — 03 §4.2 lists exactly the metrics in `catalog.CATALOG`."""
    want = {metric_row(m) for m in CATALOG}
    have = _doc_rows(SPEC_DASH, "### 4.2. Danh mục đầy đủ", "METRIC-")
    assert want == have, (
        "03 §4.2 `METRIC-*` table out of sync with catalog.py.\n"
        f"missing from doc ({len(want - have)}):\n  " + "\n  ".join(sorted(want - have)) + "\n"
        f"stale in doc ({len(have - want)}):\n  " + "\n  ".join(sorted(have - want))
    )


def test_every_documented_action_exists_in_code() -> None:
    """TC-M4-04c — an `ACT-*` named in the v3 docs must be runnable somewhere in code.

    Three places legitimately own an `ACT-*`: the IDP Action Registry (commit chains), a
    `ToolDef.action_name` (AI write/execution tools) and the review service (`reassign`/`merge`,
    EP-DC-11/12 — operations on the review itself, not on a business table).
    """
    review_owned = {"ACT-reassign_review", "ACT-merge_review"}
    in_code = set(action_names()) | {t.action_name for t in all_tools() if t.action_name}
    in_code |= review_owned
    documented: set[str] = set()
    for path in DOCS.rglob("*.md"):
        if "_archive" in str(path):
            continue
        documented |= set(re.findall(r"ACT-[a-z_]+", path.read_text(encoding="utf-8")))
    unknown = sorted(documented - in_code)
    assert not unknown, f"`ACT-*` documented but not implemented: {unknown}"


def test_event_registry_is_documented_both_ways() -> None:
    """TC-M4-14 — `core/events/registry.py` and 10 §9.2/§9.2bis list the same event types.

    CLAUDE.md §5.4 only allows publishing an event that the docs register, so an event type the
    code accepts but no v3 doc names is a contract hole (the M4 audit found 7, now in 10 §9.2bis).
    An event may be registered in 10 §9.2 (catalog, BRD name + code name in brackets) or named as
    a metric refresh trigger in 03 §4.2 — both count, so the whole v3 doc set is scanned.
    """
    from app.core.events.registry import EVENT_TYPES, EXTENSION_EVENT_TYPES

    in_code = set(EVENT_TYPES) | set(EXTENSION_EVENT_TYPES)
    documented: set[str] = set()
    for path in DOCS.rglob("*.md"):
        if "_archive" in str(path):
            continue
        documented |= set(re.findall(r"`([a-z_]+\.[a-z_]+)`", path.read_text(encoding="utf-8")))
    undocumented = sorted(in_code - documented)
    assert not undocumented, (
        f"event types accepted by publish_in_tx but named in no v3 doc: {undocumented}"
    )


def _legacy_ids(route: APIRoute) -> set[str]:
    """The v2.1 EP number a route carries in code — what 10 §7.3's "EP v2.1" column must quote.

    Looked up in the order the codebase annotates routes: the `summary="EP-56 …"` of the
    decorator, else the endpoint docstring (`\"\"\"EP-90 (10 §5) …\"\"\"`), else the nearest
    `# ---------- EP-83 salary history ----------` section header above the function, else the
    module docstring (`\"\"\"EP-95 product metric snapshots …`).
    """
    import inspect

    legacy = re.compile(r"\bEP-(\d+)\b")
    if route.summary and (m := legacy.match(route.summary)):
        return {f"EP-{m.group(1)}"}
    fn = inspect.unwrap(route.endpoint)  # `core/routing.py` wraps endpoints (route commit)
    if (doc := inspect.getdoc(fn)) and (m := legacy.match(doc)):
        return {f"EP-{m.group(1)}"}
    start = inspect.getsourcelines(fn)[1]
    source = Path(inspect.getsourcefile(fn) or "").read_text(encoding="utf-8").splitlines()
    for line in reversed(source[: start - 1]):
        if line.startswith("# -") and (m := legacy.search(line)):
            return {f"EP-{m.group(1)}"}
    module = inspect.getmodule(fn)
    if module and (doc := inspect.getdoc(module)) and (m := legacy.match(doc)):
        return {f"EP-{m.group(1)}"}  # a file holding one resource names it in its docstring
    return set()


def test_legacy_ep_column_matches_route_annotations() -> None:
    """TC-M4-16 — 10 §7.3 quotes the v2.1 EP number each route is annotated with in code.

    The first §7.3 draft filled this column from number ranges and got 17 of 29 rows wrong;
    this pins every row to the annotation on the routes it covers.
    """
    text = SPEC_API.read_text(encoding="utf-8")
    start = text.index("### 7.3. EP catalog nền v2.1")
    end = text.index("\n## ", start)
    routes = app_route_map()
    rows = re.findall(
        rf"^\|\s*({EP_ID})\s*\|\s*([A-Z/* ]+?)\s*\|\s*(.+?)\s*\|\s*[^|]*\|\s*([^|]*?)\s*\|",
        text[start:end],
        re.M,
    )
    assert rows, "10 §7.3 table not found"
    bad: list[str] = []
    for ep, method_cell, path_cell, legacy_cell in rows:
        methods = [m.strip() for m in method_cell.split("/") if m.strip() in ALL_METHODS]
        paths = [norm(p) for p in re.findall(r"`(/[^`]+)`", path_cell)]
        hits = [routes[(m, p)] for m in methods for p in paths if (m, p) in routes]
        want = set().union(*(_legacy_ids(r) for r in hits)) if hits else set()
        have = set(re.findall(r"EP-\d+", legacy_cell))
        if not want:
            bad.append(f"{ep}: no route annotation found in code")
        elif have != want:
            bad.append(f"{ep}: doc says {sorted(have)}, code annotates {sorted(want)}")
    assert not bad, "10 §7.3 'EP v2.1' column drifts from code:\n  " + "\n  ".join(bad)
