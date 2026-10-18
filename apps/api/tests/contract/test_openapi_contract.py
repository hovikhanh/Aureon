"""TC-SYS-003 — the real create_app() is contract-clean for every endpoint it already mounts.

Runs each `check_*` from `checks` against the live `create_app()` OpenAPI schema and asserts:
  * zero violations for the endpoints that exist today (EP-01 health),
  * `missing_endpoints` reports the not-yet-built EPs from 10 §1.10 as *progress*, never an error
    (the suite must not fail just because the backend is incomplete).
"""

import pytest

from app.main import create_app
from tests.contract import checks
from tests.contract.spec_index import spec_endpoints

pytestmark = pytest.mark.contract


def test_no_contract_violations_for_mounted_endpoints() -> None:
    app = create_app()
    spec = spec_endpoints()
    violations = checks.all_violations(app, spec)
    assert violations == [], "create_app() has contract violations:\n  " + "\n  ".join(violations)


def test_each_check_is_individually_clean() -> None:
    app = create_app()
    spec = spec_endpoints()
    assert checks.check_documented(app, spec) == [], "undocumented route(s) against 10 §1.10"
    assert checks.check_response_envelopes(app, spec) == [], "2xx envelope violation(s) (10 §1.2)"
    assert checks.check_roles(app, spec) == [], "role-marker violation(s) (DEC-080)"
    assert checks.check_error_codes(app) == [], "error-code violation(s) (10 §1.3)"


def test_ep01_health_is_actually_mounted_and_documented() -> None:
    app = create_app()
    spec = spec_endpoints()
    mounted = {(r.method, r.path) for r in checks.app_routes(app)}
    assert ("GET", "/api/v1/health") in mounted, (
        f"EP-01 GET /api/v1/health must be mounted; mounted routes: {sorted(mounted)}"
    )
    assert ("GET", "/api/v1/health") not in {
        (e.method, e.path) for e in spec if e.ep_id in checks.missing_endpoints(app, spec)
    }, "EP-01 is mounted, so it must NOT appear in missing_endpoints"


def test_missing_endpoints_reported_as_progress_not_error() -> None:
    app = create_app()
    spec = spec_endpoints()
    missing = checks.missing_endpoints(app, spec)
    # Current backend mounts only EP-01, so almost every EP in 10 is still outstanding.
    assert "EP-01" not in missing, "EP-01 is mounted and must not be listed as missing"
    assert "EP-02" not in missing, "EP-02 is mounted and must not be listed as missing"
    assert "EP-03" not in missing, "EP-03 is mounted and must not be listed as missing"
    assert "EP-04" not in missing, "EP-04 is mounted and must not be listed as missing"
    assert "EP-05" not in missing, "EP-05 is mounted and must not be listed as missing"
    assert "EP-20" not in missing, "EP-20 is mounted and must not be listed as missing"
    assert "EP-21" not in missing, "EP-21 is mounted and must not be listed as missing"
    assert "EP-22" not in missing, "EP-22 is mounted and must not be listed as missing"
    assert "EP-23" not in missing, "EP-23 is mounted and must not be listed as missing"
    assert "EP-24" not in missing, "EP-24 is mounted and must not be listed as missing"
    assert "EP-25" not in missing, "EP-25 is mounted and must not be listed as missing"
    assert "EP-27" not in missing, "EP-27 is mounted and must not be listed as missing"
    assert "EP-28" not in missing, "EP-28 is mounted and must not be listed as missing"
    assert "EP-29" not in missing, "EP-29 is mounted and must not be listed as missing"
    assert "EP-30" not in missing, "EP-30 is mounted and must not be listed as missing"
    assert "EP-31" not in missing, "EP-31 is mounted and must not be listed as missing"
    assert "EP-32" not in missing, "EP-32 is mounted and must not be listed as missing"
    assert "EP-33" not in missing, "EP-33 is mounted and must not be listed as missing"
    assert "EP-34" not in missing, "EP-34 is mounted and must not be listed as missing"
    assert "EP-35" not in missing, "EP-35 is mounted and must not be listed as missing"
    assert "EP-36" not in missing, "EP-36 is mounted and must not be listed as missing"
    assert "EP-40" not in missing, "EP-40 is mounted and must not be listed as missing"
    assert "EP-51" not in missing, "EP-51 is mounted and must not be listed as missing"
    assert "EP-10" in missing, f"EP-10 is not built yet and must be reported; got {missing}"
    assert len(missing) >= 10, (
        f"expected the bulk of 10 §1.10 to be reported as missing progress, got {len(missing)}: "
        f"{missing}"
    )
    # Missing endpoints are informational: they must not leak into the hard violation list.
    assert checks.all_violations(app, spec) == [], (
        "missing_endpoints must be progress-only and never raise a contract violation"
    )
