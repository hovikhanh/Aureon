"""Contract checks: FastAPI app/OpenAPI vs 10-API-SPECIFICATION.md (T-009, DEC-101, TC-SYS-003).

Every `check_*` function takes a FastAPI app and returns a list of human-readable violations
(empty = compliant). They are used against the real `create_app()` in test_openapi_contract.py and
against deliberately broken throwaway apps in test_contract_selftest.py, so the suite is proven to
fail on bad routes.

The checks only look at routes that exist, so they apply automatically to each new endpoint. They
do not require that every EP in 10 is already implemented (`missing_endpoints` reports progress).

ROLE-MARKER PROTOCOL (contract for T-104 `require_role`)
--------------------------------------------------------
`require_role(*roles)` must return a dependency callable carrying the attribute

    __aureon_roles__: frozenset[str]

containing the allowed roles, as role codes (`"ROLE-01"`..`"ROLE-05"`) or role keys (`"CEO"`,
`"CFO"`, `"SALES_DIRECTOR"`, `"HR_MANAGER"`, `"REVIEWER"` — 10 §1.4; both are normalised to codes).
It may be attached anywhere in the route's dependency tree: `Depends(require_role(...))` in the
endpoint signature, in `dependencies=[...]` of the route or of an `APIRouter`, or nested inside
another dependency. If several markers are found the effective allow-list is their intersection
(every gate must pass). Minimal shape:

    def require_role(*roles: str) -> Callable[..., CurrentUser]:
        allowed = frozenset(roles)
        def dependency(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
            if user.role_code not in allowed:
                raise ApiError(ErrorCode.FORBIDDEN_ROLE)
            return user
        dependency.__aureon_roles__ = allowed  # type: ignore[attr-defined]
        return dependency

Rules enforced: non-public endpoints (all but EP-01/EP-02, DEC-080) must carry a marker whose
roles equal 10's role column (superset allowed only when 10 adds a non-role principal, e.g.
EP-34 `(+ người upload ...)`); public endpoints must not carry one.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import iter_route_contexts

from app.core.errors import ERROR_HTTP_STATUS, ErrorCode

from .spec_index import BASE_PATH, SpecEndpoint, role_key_to_code, spec_detail_sections

ROLE_MARKER = "__aureon_roles__"
PAGE_META_FIELDS = frozenset({"page", "page_size", "total", "total_pages"})
_ERROR_CODE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
_SPEC_RESPONSE_STATUS = re.compile(r"^\| Response (\d{3}) \|", re.M)


@dataclass(frozen=True, slots=True)
class AppRoute:
    method: str
    path: str
    endpoint_name: str
    response_model: Any
    dependant: Dependant | None
    include_in_schema: bool


def _framework_paths(app: FastAPI) -> set[str]:
    paths = {app.openapi_url, app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url}
    return {p for p in paths if p}


def app_routes(app: FastAPI) -> list[AppRoute]:
    """Every (method, path) HTTP operation of the app, incl. include_in_schema=False routes."""
    framework = _framework_paths(app)
    routes: list[AppRoute] = []
    for ctx in iter_route_contexts(app.routes):
        path = ctx.path
        if path is None or path in framework:
            continue
        methods = ctx.methods or set()
        endpoint = ctx.endpoint
        for method in sorted(methods - {"HEAD", "OPTIONS"}) or ["<non-http>"]:
            routes.append(
                AppRoute(
                    method=method,
                    path=path,
                    endpoint_name=getattr(endpoint, "__qualname__", repr(endpoint)),
                    response_model=getattr(ctx, "response_model", None),
                    dependant=getattr(ctx, "dependant", None),
                    include_in_schema=bool(getattr(ctx, "include_in_schema", True)),
                )
            )
    return routes


def _spec_by_route(spec: tuple[SpecEndpoint, ...]) -> dict[tuple[str, str], SpecEndpoint]:
    return {(e.method, e.path): e for e in spec}


def _iter_calls(dependant: Dependant) -> Iterator[Callable[..., Any]]:
    for sub in dependant.dependencies:
        if sub.call is not None:
            yield sub.call
        yield from _iter_calls(sub)


def normalise_roles(raw: Any, where: str) -> tuple[frozenset[str] | None, list[str]]:
    keys = role_key_to_code()
    codes = set(keys.values())
    if isinstance(raw, str) or not hasattr(raw, "__iter__"):
        return None, [f"{where}: {ROLE_MARKER} must be a collection of roles, got {raw!r}"]
    out: set[str] = set()
    errors: list[str] = []
    for role in raw:
        value = getattr(role, "value", role)
        if value in codes:
            out.add(value)
        elif value in keys:
            out.add(keys[value])
        else:
            errors.append(f"{where}: unknown role {role!r} in {ROLE_MARKER} (10 §1.4)")
    return (frozenset(out) if not errors else None), errors


def declared_roles(route: AppRoute) -> tuple[frozenset[str] | None, list[str]]:
    """Effective role allow-list from `__aureon_roles__` markers (None = no marker)."""
    if route.dependant is None:
        return None, []
    where = f"{route.method} {route.path}"
    effective: frozenset[str] | None = None
    errors: list[str] = []
    for call in _iter_calls(route.dependant):
        if not hasattr(call, ROLE_MARKER):
            continue
        roles, errs = normalise_roles(getattr(call, ROLE_MARKER), where)
        errors += errs
        if roles is not None:
            effective = roles if effective is None else effective & roles
    return effective, errors


# --- checks ---------------------------------------------------------------------------------


def check_documented(app: FastAPI, spec: tuple[SpecEndpoint, ...]) -> list[str]:
    """Every route is under /api/v1 and listed in 10 §1.10 (incl. hidden routes)."""
    by_route = _spec_by_route(spec)
    errors: list[str] = []
    for r in app_routes(app):
        where = f"{r.method} {r.path} ({r.endpoint_name})"
        if not r.path.startswith(BASE_PATH + "/"):
            errors.append(f"{where}: path is not under {BASE_PATH} (10 §1.1)")
        elif (r.method, r.path) not in by_route:
            same_path = sorted(e.method for e in spec if e.path == r.path)
            hint = f"; 10 has {same_path} for this path" if same_path else ""
            errors.append(f"{where}: undocumented endpoint, not in 10 §1.10{hint}")
    return errors


def _resolve(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    while "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/components/schemas/") or ref in seen:
            raise ValueError(f"unresolvable $ref {ref!r}")
        seen.add(ref)
        schema = components[ref.rsplit("/", 1)[1]]
    return schema


def _envelope_errors(
    where: str, schema: dict[str, Any], components: dict[str, Any], paginated: bool
) -> list[str]:
    try:
        resolved = _resolve(schema, components)
    except (ValueError, KeyError) as exc:
        return [f"{where}: {exc}"]
    props = resolved.get("properties") or {}
    required = set(resolved.get("required") or [])
    errors: list[str] = []
    if resolved.get("type") != "object" or "data" not in props:
        return [f"{where}: 2xx schema is not an envelope {{data, meta?}} (10 §1.2): {resolved!r}"]
    if "data" not in required:
        errors.append(f"{where}: envelope `data` must be required (10 §1.2)")
    extra = set(props) - {"data", "meta"}
    if extra:
        errors.append(f"{where}: envelope has fields outside {{data, meta}}: {sorted(extra)}")
    if paginated:
        if "meta" not in props or "meta" not in required:
            errors.append(f"{where}: paginated list must declare required `meta` (10 §1.5)")
        else:
            try:
                meta = _resolve(props["meta"], components)
            except (ValueError, KeyError) as exc:
                return [*errors, f"{where}: meta {exc}"]
            missing = PAGE_META_FIELDS - set(meta.get("properties") or {})
            if missing:
                errors.append(f"{where}: `meta` lacks pagination fields {sorted(missing)}")
        data = props["data"]
        if "$ref" not in data and data.get("type") != "array":
            errors.append(f"{where}: paginated `data` must be an array (10 §1.5)")
    return errors


def check_response_envelopes(app: FastAPI, spec: tuple[SpecEndpoint, ...]) -> list[str]:
    """Every operation declares response_model; its 2xx schema is an envelope with the 10 status."""
    by_route = _spec_by_route(spec)
    errors: list[str] = []
    for r in app_routes(app):
        if r.response_model is None:
            errors.append(
                f"{r.method} {r.path} ({r.endpoint_name}): no response_model (CLAUDE.md § API)"
            )
    openapi = app.openapi()
    components = openapi.get("components", {}).get("schemas", {})
    for path, item in openapi.get("paths", {}).items():
        for method_lower, op in item.items():
            method = method_lower.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            where = f"{method} {path}"
            ep = by_route.get((method, path))
            ok = {k: v for k, v in op.get("responses", {}).items() if str(k).startswith("2")}
            if not ok:
                errors.append(f"{where}: no 2xx response declared")
                continue
            if ep is not None:
                statuses = set(_SPEC_RESPONSE_STATUS.findall(spec_detail_sections()[ep.ep_id]))
                if statuses and not statuses & set(ok):
                    errors.append(
                        f"{where}: 2xx status {sorted(ok)} ≠ 10 {ep.ep_id} Response "
                        f"{sorted(statuses)}"
                    )
            for status, resp in ok.items():
                schema = (resp.get("content") or {}).get("application/json", {}).get("schema")
                if not schema:
                    errors.append(f"{where} {status}: no JSON response schema (response_model)")
                    continue
                paginated = ep.paginated if ep is not None else False
                errors += _envelope_errors(f"{where} {status}", schema, components, paginated)
    return errors


def check_roles(app: FastAPI, spec: tuple[SpecEndpoint, ...]) -> list[str]:
    """Non-public routes carry a `__aureon_roles__` marker equal to 10's role column (DEC-080)."""
    by_route = _spec_by_route(spec)
    errors: list[str] = []
    for r in app_routes(app):
        where = f"{r.method} {r.path} ({r.endpoint_name})"
        ep = by_route.get((r.method, r.path))
        roles, errs = declared_roles(r)
        errors += errs
        if ep is None:
            if roles is None and not errs:
                errors.append(f"{where}: no require_role dependency ({ROLE_MARKER} marker)")
            continue
        if ep.public:
            if roles is not None:
                errors.append(f"{where}: {ep.ep_id} is public (DEC-080) but has require_role")
            continue
        assert ep.roles is not None
        if roles is None:
            if not errs:
                errors.append(
                    f"{where}: {ep.ep_id} needs Depends(require_role(...)) → "
                    f"{sorted(ep.roles)} (10: {ep.role_text!r}); no {ROLE_MARKER} marker found"
                )
            continue
        if ep.extra_principal:
            if not ep.roles <= roles:
                errors.append(
                    f"{where}: {ep.ep_id} roles {sorted(roles)} must include {sorted(ep.roles)} "
                    f"(10: {ep.role_text!r})"
                )
        elif roles != ep.roles:
            errors.append(
                f"{where}: {ep.ep_id} roles {sorted(roles)} ≠ 10 {sorted(ep.roles)} "
                f"(10: {ep.role_text!r})"
            )
    return errors


def check_error_codes(app: FastAPI) -> list[str]:
    """Error codes named in OpenAPI `responses` descriptions exist in ErrorCode with that HTTP."""
    errors: list[str] = []
    known = {c.value: c for c in ErrorCode}
    for path, item in app.openapi().get("paths", {}).items():
        for method, op in item.items():
            if not isinstance(op, dict):
                continue
            for status, resp in op.get("responses", {}).items():
                where = f"{method.upper()} {path} {status}"
                for token in _ERROR_CODE_TOKEN.findall(resp.get("description") or ""):
                    code = known.get(token)
                    if code is None:
                        errors.append(f"{where}: {token!r} is not an ErrorCode (10 §1.3)")
                    elif str(status).isdigit() and ERROR_HTTP_STATUS[code] != int(status):
                        errors.append(
                            f"{where}: {token} has HTTP {ERROR_HTTP_STATUS[code]} in 10 §1.3"
                        )
    return errors


def all_violations(app: FastAPI, spec: tuple[SpecEndpoint, ...]) -> list[str]:
    return [
        *check_documented(app, spec),
        *check_response_envelopes(app, spec),
        *check_roles(app, spec),
        *check_error_codes(app),
    ]


def missing_endpoints(app: FastAPI, spec: tuple[SpecEndpoint, ...]) -> list[str]:
    """EP ids from 10 not yet mounted (informational — not a contract violation)."""
    mounted = {(r.method, r.path) for r in app_routes(app)}
    return [e.ep_id for e in spec if (e.method, e.path) not in mounted]
