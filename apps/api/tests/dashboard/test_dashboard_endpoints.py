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
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.db.session import get_db
from app.main import app
from app.modules.auth.models import User
from app.modules.auth.token import create_access_token
from app.modules.dashboard.enums import MetricValueKind
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.idp.enums import (
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RecordType,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import (
    BusinessRecord,
    ExtractedField,
    ExtractionJob,
    SourceDocument,
)

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


# --- TC-DASH-004: drill-down records (EP-13) + lineage (EP-14) ----------------------------


def _seed_record_with_lineage(db_session: Session, uploader: User) -> BusinessRecord:
    """Create a SourceDocument + ExtractionJob + BusinessRecord + ExtractedFields and wire the
    record into METRIC-FIN-01's current ACTUAL MetricValue so EP-13/EP-14 return real data."""
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="invoice-fin01.pdf",
        mime_type="application/pdf",
        doc_type=None,
        status=DocumentStatus.COMMITTED,
        uploaded_by_id=uploader.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(doc)
    db_session.flush()

    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        status=JobStatus.SUCCEEDED,
        started_at=datetime.now(UTC),
    )
    db_session.add(job)
    db_session.flush()

    record = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code="INV-FIN-001",
        name="Hóa đơn doanh thu T9",
        period_key="2026-09",
        issue_date=date(2026, 9, 15),
        total_amount=8_500_000_000,
        paid_amount=8_500_000_000,
        status="PAID",
        source_document_id=doc.id,
        attributes={"note": "demo"},
    )
    db_session.add(record)
    db_session.flush()

    # A normal field + a salary-sensitive field to exercise the hide-salary branch.
    db_session.add(
        ExtractedField(
            id=uuid4(),
            extraction_job_id=job.id,
            source_document_id=doc.id,
            business_record_id=record.id,
            field_key="total_amount",
            value=8_500_000_000,
            raw_text="8.500.000.000",
            value_type=FieldValueType.MONEY,
            confidence=0.97,
            source_location={"kind": "BOUNDING_BOX", "page": 1, "x": 10, "y": 20, "w": 30, "h": 5},
            source_kind=SourceLocationKind.PDF_REGION,
            sensitivity=SensitivityLabel.NONE,
        )
    )
    db_session.add(
        ExtractedField(
            id=uuid4(),
            extraction_job_id=job.id,
            source_document_id=doc.id,
            business_record_id=record.id,
            field_key="net_salary",
            value=42_000_000,
            raw_text="42.000.000",
            value_type=FieldValueType.MONEY,
            confidence=0.91,
            source_location={"kind": "BOUNDING_BOX", "page": 1, "x": 10, "y": 40, "w": 30, "h": 5},
            source_kind=SourceLocationKind.PDF_REGION,
            sensitivity=SensitivityLabel.SALARY,
        )
    )
    db_session.flush()

    # Wire the record into METRIC-FIN-01's current ACTUAL value.
    metric = db_session.scalars(select(Metric).where(Metric.code == "METRIC-FIN-01")).first()
    assert metric is not None
    mv = db_session.scalars(
        select(MetricValue).where(
            MetricValue.metric_id == metric.id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
        )
    ).first()
    assert mv is not None
    mv.source_record_ids = [record.id]
    db_session.add(mv)
    db_session.commit()
    return record


def test_metric_records_full_access_returns_records(client, tokens, db_session):
    """EP-13: CEO (FULL on FIN-01) drills from the metric into its source records."""
    uploader = db_session.scalars(select(User).where(User.email == "ceo@abc.demo")).first()
    record = _seed_record_with_lineage(db_session, uploader)

    r = client.get("/api/v1/metrics/METRIC-FIN-01/records", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["id"] == str(record.id)
    assert body["data"][0]["code"] == "INV-FIN-001"


def test_metric_records_aggregated_access_forbidden(client, tokens, db_session):
    """EP-13: a role with only AGG access on the metric cannot drill into records."""
    uploader = db_session.scalars(select(User).where(User.email == "ceo@abc.demo")).first()
    _seed_record_with_lineage(db_session, uploader)
    # ROLE-03 (Sales) has FIN-01 FULL; use ROLE-04 (HR) which has FIN-01 = AGG (03 §5.1).
    r = client.get("/api/v1/metrics/METRIC-FIN-01/records", headers=_auth(tokens["ROLE-04"]))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_SCOPE"


def test_metric_records_out_of_scope_forbidden(client, tokens, db_session):
    """EP-13: a role with no access to the metric is rejected."""
    r = client.get("/api/v1/metrics/METRIC-HR-01/records", headers=_auth(tokens["ROLE-03"]))
    assert r.status_code == 403


def test_record_lineage_hides_salary_for_non_hr(client, tokens, db_session):
    """EP-14: lineage returns fields + documents; salary field value is hidden for non-ROLE-04."""
    uploader = db_session.scalars(select(User).where(User.email == "ceo@abc.demo")).first()
    record = _seed_record_with_lineage(db_session, uploader)

    r = client.get(
        f"/api/v1/business-records/{record.id}/lineage", headers=_auth(tokens["ROLE-01"])
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["record"]["id"] == str(record.id)
    by_key = {f["field_key"]: f for f in data["fields"]}
    assert by_key["total_amount"]["value"] == 8_500_000_000
    # CEO is not ROLE-04 → the salary field value is masked.
    assert by_key["net_salary"]["value"] is None
    # The source document is marked restricted (contains salary) for a non-HR viewer.
    assert len(data["documents"]) == 1
    assert data["documents"][0]["restricted"] is True
    assert data["documents"][0]["reason"] == "SALARY"


def test_record_lineage_hr_sees_salary(client, tokens, db_session):
    """EP-14: ROLE-04 (HR) sees the salary field value and the document is not restricted."""
    uploader = db_session.scalars(select(User).where(User.email == "ceo@abc.demo")).first()
    record = _seed_record_with_lineage(db_session, uploader)

    r = client.get(
        f"/api/v1/business-records/{record.id}/lineage", headers=_auth(tokens["ROLE-04"])
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    by_key = {f["field_key"]: f for f in data["fields"]}
    assert by_key["net_salary"]["value"] == 42_000_000
    assert data["documents"][0]["restricted"] is False


def test_record_lineage_unknown_record_404(client, tokens):
    """EP-14: unknown record id → 404."""
    r = client.get(f"/api/v1/business-records/{uuid4()}/lineage", headers=_auth(tokens["ROLE-01"]))
    assert r.status_code == 404
