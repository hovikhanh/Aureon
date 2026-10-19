"""Dashboard endpoint integration tests — EP-10..EP-17 (10 §4, 03 §5.1, 08 §5.1).

TC-DASH-001 role-scoped dashboard, TC-DASH-002 metric list scope, TC-DASH-003 metric
detail + P01 lineage, TC-DASH-004 drill-down records/lineage, TC-DASH-005 alert list
scope, TC-DASH-006 acknowledge/dismiss state machine + role guard.

Each test runs inside the rolled-back ``db_session`` (conftest), which seeds the 18
metrics + 12 alerts. ``get_db`` is overridden to that session so mutations + audit rows
are visible and rolled back.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.db.session import get_db
from app.main import app
from app.modules.auth.models import User
from app.modules.auth.token import create_access_token
from app.modules.dashboard.enums import AlertStatus
from app.modules.dashboard.models import Alert, Metric

pytestmark = pytest.mark.integration


@pytest.fixture
def tokens(db_session: Session) -> dict[str, str]:
    cfg = get_config()
    emails = {
        "ROLE-01": "ceo@abc.demo",
        "ROLE-02": "cfo@abc.demo",
        "ROLE-03": "sales@abc.demo",
        "ROLE-04": "hr@abc.demo",
        "ROLE-05": "reviewer@abc.demo",
    }
    out: dict[str, str] = {}
    for role_code, email in emails.items():
        user = db_session.scalars(select(User).where(User.email == email)).first()
        assert user is not None, f"seed missing {email}"
        token, _ = create_access_token(user, cfg)
        out[role_code] = token
    return out


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- TC-DASH-001: role-scoped dashboard (EP-10) ------------------------------------------


def test_ceo_dashboard_four_pillars_and_critical_summary(client, tokens):
    r = client.get("/api/v1/dashboard", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["role_code"] == "ROLE-01"
    pillars = {p["pillar"]: p for p in data["pillars"]}
    assert set(pillars) == {"FIN", "CUS", "OPS", "HR"}
    assert len(pillars["FIN"]["metrics"]) == 6
    assert len(pillars["CUS"]["metrics"]) == 5
    assert len(pillars["OPS"]["metrics"]) == 4
    assert len(pillars["HR"]["metrics"]) == 3
    # 08 §5.1: 4 critical + 8 warning; summary flags critical.
    assert data["summary"]["i18n_key"] == "dashboard.summary.has_critical"
    assert data["summary"]["params"]["critical_count"] == 4
    assert data["summary"]["params"]["warning_count"] == 8
    # alerts_top: critical first, max 5.
    top = data["alerts_top"]
    assert len(top) <= 5
    assert top[0]["severity"] == "CRITICAL"


def test_sales_dashboard_scope_fin_only_fin01_no_hr(client, tokens):
    r = client.get("/api/v1/dashboard", headers=_auth(tokens["ROLE-03"]))
    assert r.status_code == 200
    data = r.json()["data"]
    pillars = {p["pillar"]: p for p in data["pillars"]}
    assert "HR" not in pillars  # ROLE-03 has no HR
    assert [m["metric_code"] for m in pillars["FIN"]["metrics"]] == ["METRIC-FIN-01"]
    assert pillars["FIN"]["access_level"] == "FULL"
    assert pillars["OPS"]["access_level"] == "AGG"
    # alerts_top only CUS-* (02 §3.3).
    assert all(a["pillar"] == "CUS" for a in data["alerts_top"])


def test_reviewer_dashboard_forbidden(client, tokens):
    r = client.get("/api/v1/dashboard", headers=_auth(tokens["ROLE-05"]))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


# --- TC-DASH-002: metric list (EP-11) ----------------------------------------------------


def test_metrics_list_scoped_and_pillar_filter(client, tokens):
    r = client.get("/api/v1/metrics", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200
    assert r.json()["meta"]["total"] == 18

    r2 = client.get("/api/v1/metrics?pillar=FIN", headers=_auth(tokens["ROLE-01"]))
    assert r2.json()["meta"]["total"] == 6

    r3 = client.get("/api/v1/metrics?pillar=NOPE", headers=_auth(tokens["ROLE-01"]))
    assert r3.status_code == 400


# --- TC-DASH-003: metric detail + P01 lineage (EP-12) ------------------------------------


def test_metric_detail_fin01_lineage_panel(client, tokens):
    r = client.get("/api/v1/metrics/METRIC-FIN-01", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["metric"]["value"] == 8_500_000_000
    assert data["metric"]["status_color"] == "YELLOW"
    lp = data["lineage_panel"]
    assert lp["formula_display"] == "metric.METRIC-FIN-01.formula"
    assert lp["source_record_types"] == ["INVOICE"]
    assert lp["computed_at"] is not None
    assert data["alert"]["severity"] == "WARNING"


def test_metric_detail_out_of_scope_forbidden(client, tokens):
    # ROLE-03 (Sales) has no HR scope -> FORBIDDEN_SCOPE.
    r = client.get("/api/v1/metrics/METRIC-HR-01", headers=_auth(tokens["ROLE-03"]))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


def test_metric_detail_unknown_code_404(client, tokens):
    r = client.get("/api/v1/metrics/METRIC-ZZZ-99", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 404


# --- TC-DASH-005: alert list (EP-15) -----------------------------------------------------


def test_alert_list_scope(client, tokens):
    r = client.get("/api/v1/alerts", headers=_auth(tokens["ROLE-01"]))
    assert r.json()["meta"]["total"] == 12  # all 12 open alerts for CEO

    # CFO receives only FIN + OPS alerts.
    r2 = client.get("/api/v1/alerts", headers=_auth(tokens["ROLE-02"]))
    assert all(a["pillar"] in ("FIN", "OPS") for a in r2.json()["data"])


# --- TC-DASH-006: acknowledge / dismiss state machine + guard (EP-16/EP-17) --------------


def _fin01_alert_id(db: Session) -> str:
    metric = db.scalars(select(Metric).where(Metric.code == "METRIC-FIN-01")).first()
    alert = db.scalars(select(Alert).where(Alert.metric_id == metric.id)).first()
    return str(alert.id)


def test_acknowledge_then_conflict(client, tokens, db_session):
    alert_id = _fin01_alert_id(db_session)
    r = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=_auth(tokens["ROLE-02"]),
        json={"note": "reviewing"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ACKNOWLEDGED"
    # second ack -> 409
    r2 = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=_auth(tokens["ROLE-02"]),
        json={},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "CONFLICT_STATE"


def test_cfo_cannot_ack_ops_alert(client, tokens, db_session):
    metric = db_session.scalars(select(Metric).where(Metric.code == "METRIC-OPS-02")).first()
    alert = db_session.scalars(select(Alert).where(Alert.metric_id == metric.id)).first()
    r = client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge",
        headers=_auth(tokens["ROLE-02"]),
        json={},
    )
    # CFO views OPS but may not acknowledge OPS alerts (02 §3.3).
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


def test_dismiss_requires_reason_and_sets_status(client, tokens, db_session):
    alert_id = _fin01_alert_id(db_session)
    # missing reason -> 422 validation
    r_bad = client.post(
        f"/api/v1/alerts/{alert_id}/dismiss", headers=_auth(tokens["ROLE-02"]), json={}
    )
    assert r_bad.status_code == 422
    r = client.post(
        f"/api/v1/alerts/{alert_id}/dismiss",
        headers=_auth(tokens["ROLE-02"]),
        json={"reason": "not relevant this quarter"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "DISMISSED"
