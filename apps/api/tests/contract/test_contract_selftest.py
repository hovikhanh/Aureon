"""TC-SYS-003 — prove the contract suite actually FAILS on bad routes (meta-test).

A passing contract suite is only meaningful if it can fail. Each test here builds a throwaway
FastAPI app with one deliberate defect and asserts the matching `check_*` reports a violation, plus
one positive app that carries a correct `__aureon_roles__` marker and passes the role check.

These apps never touch the real create_app(); they only exercise the checks.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel

from tests.contract import checks
from tests.contract.spec_index import spec_endpoints

pytestmark = pytest.mark.contract

# EP-03 GET /api/v1/auth/me is a real non-public endpoint (ROLE-01..05) — the natural target for
# the role-marker self-tests (10 §1.10).
EP03_PATH = "/api/v1/auth/me"
EP03_ROLES = ("ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05")


class Envelope(BaseModel):
    """A valid 10 §1.2 success envelope `{ data }`."""

    data: dict[str, Any]


class NoEnvelope(BaseModel):
    """A 2xx body that is NOT a `{data, meta?}` envelope — a contract defect."""

    result: str


def _require_role(*roles: str) -> Callable[[], None]:
    """Minimal stand-in for T-104 `require_role`: a dependency carrying the role marker."""

    def dependency() -> None:
        return None

    dependency.__aureon_roles__ = frozenset(roles)  # type: ignore[attr-defined]
    return dependency


def test_undocumented_path_is_flagged() -> None:
    app = FastAPI()

    @app.get("/api/v1/not-in-spec", response_model=Envelope)
    def rogue() -> Envelope:
        return Envelope(data={})

    violations = checks.check_documented(app, spec_endpoints())
    assert any("undocumented endpoint" in v for v in violations), (
        f"check_documented must flag an endpoint absent from 10 §1.10; got {violations}"
    )


def test_missing_role_marker_is_flagged() -> None:
    app = FastAPI()

    @app.get(EP03_PATH, response_model=Envelope)
    def me() -> Envelope:  # non-public EP-03 with NO require_role dependency → defect
        return Envelope(data={})

    violations = checks.check_roles(app, spec_endpoints())
    assert any("EP-03" in v and checks.ROLE_MARKER in v for v in violations), (
        f"check_roles must flag the missing {checks.ROLE_MARKER} marker on EP-03; got {violations}"
    )


def test_non_envelope_2xx_is_flagged() -> None:
    app = FastAPI()

    @app.get(
        EP03_PATH,
        response_model=NoEnvelope,
        dependencies=[Depends(_require_role(*EP03_ROLES))],
    )
    def me() -> NoEnvelope:  # 2xx body lacks a `data` envelope → defect
        return NoEnvelope(result="x")

    violations = checks.check_response_envelopes(app, spec_endpoints())
    assert any("is not an envelope" in v for v in violations), (
        f"check_response_envelopes must flag a 2xx without a `data` envelope; got {violations}"
    )


def test_missing_response_model_is_flagged() -> None:
    app = FastAPI()

    @app.get(EP03_PATH, dependencies=[Depends(_require_role(*EP03_ROLES))])
    def me(response: Response) -> Response:  # Response return → no response_model inferred → defect
        return response

    violations = checks.check_response_envelopes(app, spec_endpoints())
    assert any("no response_model" in v for v in violations), (
        f"check_response_envelopes must flag a route without response_model; got {violations}"
    )


def test_correct_role_marker_passes() -> None:
    app = FastAPI()

    @app.get(
        EP03_PATH,
        response_model=Envelope,
        dependencies=[Depends(_require_role(*EP03_ROLES))],
    )
    def me() -> Envelope:  # correct marker: roles == 10's ROLE-01..05 for EP-03
        return Envelope(data={})

    spec = spec_endpoints()
    assert checks.check_roles(app, spec) == [], (
        "a correct __aureon_roles__ marker equal to 10's role column must pass check_roles"
    )
    assert checks.check_documented(app, spec) == [], (
        "EP-03 is documented, must pass check_documented"
    )
    assert checks.check_response_envelopes(app, spec) == [], (
        "a correct `{data}` envelope must pass check_response_envelopes"
    )


def test_role_markers_with_wrong_roles_are_flagged() -> None:
    app = FastAPI()

    @app.get(
        EP03_PATH,
        response_model=Envelope,
        dependencies=[Depends(_require_role("ROLE-01"))],  # too narrow vs 10 ROLE-01..05
    )
    def me() -> Envelope:
        return Envelope(data={})

    violations = checks.check_roles(app, spec_endpoints())
    assert any("EP-03 roles" in v for v in violations), (
        f"check_roles must flag a marker whose roles differ from 10's role column; got {violations}"
    )
