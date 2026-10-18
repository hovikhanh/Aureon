"""Integration tests for IDP Autonomy L0-L3, Kill Switch, and EP-51 /ai-config.

Test Cases:
- TC-IDP-027: INVOICE at L3 + clean Excel -> AUTO_APPROVED -> COMMITTED with audit actor ai:idp.
- TC-IDP-028: Kill switch L0 (no model, C2 -> 423, ai_state=L0), mode L2 (no STP), ai_state L0..L3.
- TC-IDP-038: EP-51 /ai-config read-only (ROLE-01, ROLE-05 allow; ROLE-02..04 403; PUT/PATCH 405).
"""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import ConfigService, get_config
from app.db.enums import ActorType
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Role, User
from app.modules.auth.token import create_access_token
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import (
    BusinessRecord,
    ExtractedField,
    ExtractionJob,
    SourceDocument,
)
from app.modules.idp.routing import evaluate_routing
from app.workers.idp import run_document_pipeline


@pytest.fixture
def app_client(db_session: Session) -> Generator[TestClient, None, None]:
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def seed_test_users(db_session: Session) -> dict[str, tuple[User, str]]:
    cfg = get_config()
    demo_emails = {
        "ROLE-01": "ceo@abc.demo",
        "ROLE-02": "cfo@abc.demo",
        "ROLE-03": "sales@abc.demo",
        "ROLE-04": "hr@abc.demo",
        "ROLE-05": "reviewer@abc.demo",
    }

    user_tokens: dict[str, tuple[User, str]] = {}
    for role_code, email in demo_emails.items():
        stmt = (
            select(User)
            .options(joinedload(User.role))
            .where(User.email == email, User.deleted_at.is_(None))
        )
        user = db_session.execute(stmt).scalar_one_or_none()
        if not user:
            stmt_role = select(Role).where(Role.code == role_code)
            role = db_session.execute(stmt_role).scalar_one_or_none()
            if not role:
                all_p = ["FIN", "CUS", "OPS", "HR"]
                scope = (
                    all_p
                    if role_code in ("ROLE-01", "ROLE-05")
                    else [role_code.replace("ROLE-0", "")]
                )
                if role_code == "ROLE-02":
                    scope = ["FIN"]
                elif role_code == "ROLE-03":
                    scope = ["CUS"]
                elif role_code == "ROLE-04":
                    scope = ["HR"]
                role = Role(
                    code=role_code,
                    name_i18n_key=f"shell.roles.{role_code}",
                    pillar_scope=scope,
                    pillar_agg_scope=[],
                    review_pillars=scope,
                    can_view_salary=(role_code in ("ROLE-04", "ROLE-05")),
                    home_route="/dashboard",
                )
                db_session.add(role)
                db_session.flush()

            user = User(
                email=email,
                password_hash="$fake_hash",
                full_name=f"User {role_code}",
                salutation="anh",
                role_id=role.id,
                is_demo_account=True,
            )
            db_session.add(user)
            db_session.flush()

        token, _ = create_access_token(user, cfg)
        user_tokens[role_code] = (user, token)

    db_session.commit()
    return user_tokens


# ---------------------------------------------------------------------------
# TC-IDP-027: INVOICE at L3 + Excel sạch -> AUTO_APPROVED -> COMMITTED (ai:idp)
# ---------------------------------------------------------------------------


def test_tc_idp_027_stp_auto_approved_to_committed(
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-027: Clean invoice at L3 autonomy is auto-approved and committed via ai:idp."""
    reviewer_user, _ = seed_test_users["ROLE-05"]
    now = datetime.now(UTC)

    # Create an invoice document from Excel spreadsheet (C3)
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="hoa_don_thang_10.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=15360,
        page_count=1,
        storage_key=f"documents/{uuid4()}.xlsx",
        doc_type=DocType.INVOICE,
        pillars=["FIN"],
        autonomy_level="L3",
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=reviewer_user.id,
        uploaded_at=now,
    )
    db_session.add(doc)
    db_session.commit()

    # Mock extract_document_fields and preprocess_document to simulate clean extraction
    def mock_extract(db: Session, doc_id: Any) -> ExtractionJob:
        job = ExtractionJob(
            id=uuid4(),
            source_document_id=doc.id,
            attempt_no=1,
            doc_type=DocType.INVOICE,
            status=JobStatus.SUCCEEDED,
            classification_confidence=0.99,
            avg_confidence=0.98,
            started_at=datetime.now(UTC),
        )
        db.add(job)
        db.flush()

        # Add all required fields for INVOICE with confidence >= 0.90
        clean_fields = [
            ("invoice_number", "INV-2026-9999", FieldValueType.TEXT, 0.99),
            ("issue_date", "2026-10-15", FieldValueType.DATE, 0.97),
            ("seller_name", "Công ty Thiết Bị A", FieldValueType.ORG_NAME, 0.95),
            ("seller_tax_code", "0101234567", FieldValueType.TAX_CODE, 0.98),
            ("customer_name", "Công ty TNHH Khách Hàng", FieldValueType.ORG_NAME, 0.96),
            ("subtotal", 40909091, FieldValueType.MONEY, 0.98),
            ("vat_rate", 0.10, FieldValueType.PERCENT, 0.99),
            ("vat_amount", 4090909, FieldValueType.MONEY, 0.97),
            ("total_amount", 45000000, FieldValueType.MONEY, 0.99),
        ]
        for k, v, vt, c in clean_fields:
            f = ExtractedField(
                id=uuid4(),
                extraction_job_id=job.id,
                source_document_id=doc.id,
                field_key=k,
                value=v,
                raw_text=str(v),
                value_type=vt,
                confidence=c,
                source_location={"kind": "table_cell", "sheet": "Sheet1", "row": 2, "col": 1},
                source_kind=SourceLocationKind.CELL,
                sensitivity=SensitivityLabel.NONE,
            )
            db.add(f)
        db.flush()
        return job

    with (
        patch("app.workers.idp.preprocess_document", return_value=doc),
        patch("app.workers.idp.classify_document", return_value=doc),
        patch("app.workers.idp.extract_document_fields", side_effect=mock_extract),
    ):
        result = run_document_pipeline(
            db=db_session,
            doc_id=doc.id,
            autonomy_override="L3",
            kill_switch_override=False,
        )

    assert result["routing_decision"] == "STP"
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.COMMITTED
    assert doc.committed_at is not None
    assert doc.undo_deadline is not None
    assert "STP" in (doc.status_reason or "")

    # Business record created automatically (INVOICE + side-effect FINANCIAL_LINE)
    recs = (
        db_session.execute(
            select(BusinessRecord).where(BusinessRecord.source_document_id == doc.id)
        )
        .scalars()
        .all()
    )
    assert len(recs) >= 1
    invoice_rec = next(r for r in recs if r.code == "INV-2026-9999")
    assert invoice_rec.total_amount == 45000000

    # Audit log actor is ai:idp (ActorType.AI)
    audit = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == doc.id,
            AuditLog.action == "review.auto_approve",
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.actor_type == ActorType.AI
    assert audit.actor_user_id is None
    assert audit.metadata_["actor"] == "ai:idp"


# ---------------------------------------------------------------------------
# TC-IDP-028: Kill Switch L0 (no model, C2 -> 423), Mode L2 (no STP), ai_state
# ---------------------------------------------------------------------------


def test_tc_idp_028_kill_switch_l0_and_mode_l2(
    app_client: TestClient,
    db_session: Session,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-028: Kill switch L0 stops model calls and blocks C2; mode L2 prevents STP."""
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]
    cfo_user, _ = seed_test_users["ROLE-02"]

    # 1. Kill switch L0 -> pipeline does not call model, marks document NEEDS_REVIEW
    doc_l0 = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="invoice_l0.pdf",
        mime_type="application/pdf",
        size_bytes=10240,
        page_count=1,
        storage_key=f"documents/{uuid4()}.pdf",
        doc_type=DocType.INVOICE,
        pillars=["FIN"],
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=cfo_user.id,
        uploaded_at=datetime.now(UTC),
    )
    db_session.add(doc_l0)
    db_session.commit()

    with patch("app.workers.idp.preprocess_document") as mock_prep:
        res_pipeline = run_document_pipeline(
            db=db_session,
            doc_id=doc_l0.id,
            kill_switch_override=True,  # Kill switch L0 active
        )
        assert res_pipeline["routing_decision"] == "REVIEW"
        assert res_pipeline["routing_reason"] == "KILL_SWITCH_L0_ACTIVE"
        mock_prep.assert_not_called()

    # 2. C2 endpoint returns 423 AI_DISABLED when ai_kill_switch is active
    cfg_mock = ConfigService(ai_kill_switch=True, ai_kill_switch_mode="L0")
    with patch("app.modules.idp.service.get_config", return_value=cfg_mock):
        res_c2 = app_client.post(
            "/api/v1/documents/natural-language",
            headers={"Authorization": f"Bearer {reviewer_token}"},
            json={
                "text": "Hóa đơn số 0001234 của Công ty ABC số tiền 25 triệu",
                "doc_type": "INVOICE",
            },
        )
        assert res_c2.status_code == 423
        assert res_c2.json()["error"]["code"] == "AI_DISABLED"

    # 3. Mode L2 -> evaluate_routing does NOT allow STP even with L3 autonomy
    decision, reason = evaluate_routing(
        db=db_session,
        doc_id=doc_l0.id,
        autonomy_override="L3",
        kill_switch_override=True,  # Active kill switch
    )
    assert decision.value == "REVIEW"
    assert "KILL_SWITCH" in reason

    # 4. Check ai_state across DocumentOut responses
    # When kill switch L0 is active -> ai_state = "L0"
    with patch("app.modules.idp.router.get_config", return_value=cfg_mock):
        res_doc = app_client.get(
            f"/api/v1/documents/{doc_l0.id}",
            headers={"Authorization": f"Bearer {reviewer_token}"},
        )
        assert res_doc.status_code == 200
        assert res_doc.json()["data"]["document"]["ai_state"] == "L0"

    # When kill switch is off and doc has autonomy L2 -> ai_state = "L2"
    cfg_normal = ConfigService(ai_kill_switch=False)
    with patch("app.modules.idp.router.get_config", return_value=cfg_normal):
        res_doc_normal = app_client.get(
            f"/api/v1/documents/{doc_l0.id}",
            headers={"Authorization": f"Bearer {reviewer_token}"},
        )
        assert res_doc_normal.status_code == 200
        assert res_doc_normal.json()["data"]["document"]["ai_state"] == "L2"


# ---------------------------------------------------------------------------
# TC-IDP-038: EP-51 /ai-config Read-Only Endpoint
# ---------------------------------------------------------------------------


def test_tc_idp_038_ep51_ai_config_permissions_and_schema(
    app_client: TestClient,
    seed_test_users: dict[str, tuple[User, str]],
) -> None:
    """TC-IDP-038: EP-51 allows ROLE-01/05; forbids ROLE-02..04 (403); rejects PUT/PATCH (405)."""
    _ceo_user, ceo_token = seed_test_users["ROLE-01"]
    _cfo_user, cfo_token = seed_test_users["ROLE-02"]
    _sales_user, sales_token = seed_test_users["ROLE-03"]
    _hr_user, hr_token = seed_test_users["ROLE-04"]
    _reviewer_user, reviewer_token = seed_test_users["ROLE-05"]

    # 1. ROLE-01 (CEO) -> 200 OK
    res_ceo = app_client.get(
        "/api/v1/ai-config",
        headers={"Authorization": f"Bearer {ceo_token}"},
    )
    assert res_ceo.status_code == 200
    data = res_ceo.json()["data"]

    # Verify response schema
    assert "kill_switch" in data
    assert "enabled" in data["kill_switch"]
    assert "doc_types" in data
    assert len(data["doc_types"]) >= 7
    assert "thresholds" in data
    assert data["thresholds"]["field_high"] == 0.90
    assert data["thresholds"]["field_low"] == 0.70
    assert data["thresholds"]["classification_min"] == 0.80
    assert data["thresholds"]["stp_classification"] == 0.95
    assert data["source"] == "SEED"

    # Verify doc_types entries have required fields
    invoice_cfg = next(d for d in data["doc_types"] if d["doc_type"] == "INVOICE")
    assert invoice_cfg["autonomy_level"] in ("L2", "L3")
    assert invoice_cfg["max_autonomy_level"] == "L3"

    contract_cfg = next(d for d in data["doc_types"] if d["doc_type"] == "CONTRACT")
    assert contract_cfg["autonomy_level"] == "L2"
    assert contract_cfg["max_autonomy_level"] == "L2"

    # 2. ROLE-05 (Reviewer) -> 200 OK
    res_reviewer = app_client.get(
        "/api/v1/ai-config",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert res_reviewer.status_code == 200

    # 3. ROLE-02, ROLE-03, ROLE-04 -> 403 FORBIDDEN_ROLE
    for tok, r_code in [(cfo_token, "ROLE-02"), (sales_token, "ROLE-03"), (hr_token, "ROLE-04")]:
        res_forbidden = app_client.get(
            "/api/v1/ai-config",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert res_forbidden.status_code == 403, f"{r_code} must receive 403 on /ai-config"
        assert res_forbidden.json()["error"]["code"] == "FORBIDDEN_ROLE"

    # 4. Mutation methods -> 405 Method Not Allowed
    res_post = app_client.post(
        "/api/v1/ai-config",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json={"kill_switch": {"enabled": True}},
    )
    assert res_post.status_code == 405

    res_put = app_client.put(
        "/api/v1/ai-config",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json={"kill_switch": {"enabled": True}},
    )
    assert res_put.status_code == 405

    res_patch = app_client.patch(
        "/api/v1/ai-config",
        headers={"Authorization": f"Bearer {ceo_token}"},
        json={"kill_switch": {"enabled": True}},
    )
    assert res_patch.status_code == 405
