"""Tests for Confidence Routing and Celery Pipeline Coordinator (T-211).

Specs:
- FR-DC-15: Confidence routing S1–S7 (TC-IDP-017).
- FR-DC-07, ENT-ExtractionJob: Celery process_document idempotent coordinator (TC-IDP-035).
- FR-DC-22, US-DC-019: Retries and password protection failure IDP-E02 (TC-IDP-030).
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import Role, User
from app.modules.idp.enums import (
    DocType,
    DocumentKind,
    DocumentStatus,
    FieldValueType,
    InputChannel,
    JobStatus,
    RoutingDecision,
    SensitivityLabel,
    SourceLocationKind,
)
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.routing import evaluate_routing
from app.worker import celery_app
from app.workers.base import InMemoryIdempotencyStore
from app.workers.idp import process_document_task, run_document_pipeline


@pytest.fixture
def eager() -> Iterator[None]:
    """Run tasks in-process; restore conf afterwards."""
    prev = (celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates = prev


@pytest.fixture
def test_user(db_session: Session) -> User:
    role = db_session.execute(select(Role).where(Role.code == "ROLE-01")).scalar_one_or_none()
    if not role:
        role = Role(
            code="ROLE-01",
            name_i18n_key="shell.roles.ROLE-01",
            pillar_scope=["FIN", "CUS", "OPS", "HR"],
            pillar_agg_scope=[],
            review_pillars=["FIN", "CUS", "OPS", "HR"],
            home_route="/dashboard",
        )
        db_session.add(role)
        db_session.flush()

    user = db_session.execute(
        select(User).where(User.email == "user_t211@abc.demo")
    ).scalar_one_or_none()
    if not user:
        user = User(
            email="user_t211@abc.demo",
            password_hash="$fake_hash",
            full_name="User T211",
            salutation="anh",
            role_id=role.id,
            is_demo_account=True,
        )
        db_session.add(user)
        db_session.flush()
    return user


def create_test_doc_and_job(
    db: Session,
    user: User,
    doc_type: DocType = DocType.INVOICE,
    channel: InputChannel = InputChannel.C3,
    classification_conf: float = 0.98,
) -> tuple[SourceDocument, ExtractionJob]:
    doc = SourceDocument(
        id=uuid4(),
        channel=channel,
        kind=DocumentKind.FILE,
        original_filename="invoice_clean.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        doc_type=doc_type,
        status=DocumentStatus.VALIDATING,
        uploaded_by_id=user.id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        id=uuid4(),
        source_document_id=doc.id,
        attempt_no=1,
        doc_type=doc_type,
        classification_confidence=classification_conf,
        status=JobStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    db.refresh(doc)
    db.refresh(job)
    return doc, job


def add_field(
    db: Session,
    doc_id: Any,
    job_id: Any,
    field_key: str,
    value: Any,
    value_type: FieldValueType,
    confidence: float = 0.95,
) -> ExtractedField:
    field = ExtractedField(
        id=uuid4(),
        extraction_job_id=job_id,
        source_document_id=doc_id,
        field_key=field_key,
        value_type=value_type,
        value=value,
        raw_text=str(value),
        confidence=confidence,
        source_location={"kind": "cell", "sheet": "Sheet1", "row": 1, "col": 1},
        source_kind=SourceLocationKind.CELL,
        sensitivity=SensitivityLabel.NONE,
    )
    db.add(field)
    db.commit()
    return field


# ---------------------------------------------------------------------------
# TC-IDP-017: Confidence Routing S1–S7
# ---------------------------------------------------------------------------


def test_tc_idp_017_all_s1_s7_met_routes_to_stp(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017: All S1–S7 conditions met -> STP (AUTO_APPROVED)."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    # Required fields for INVOICE with confidence >= 0.90
    fields_data = [
        ("invoice_number", "HD-2026-0001", FieldValueType.TEXT, 0.98),
        ("issue_date", "2026-09-15", FieldValueType.DATE, 0.95),
        ("seller_name", "Công ty ABC", FieldValueType.ORG_NAME, 0.96),
        ("seller_tax_code", "0101234567", FieldValueType.TAX_CODE, 0.99),
        ("customer_name", "Công ty XYZ", FieldValueType.ORG_NAME, 0.92),
        ("subtotal", 10000000, FieldValueType.MONEY, 0.95),
        ("vat_rate", 0.10, FieldValueType.PERCENT, 0.95),
        ("vat_amount", 1000000, FieldValueType.MONEY, 0.95),
        ("total_amount", 11000000, FieldValueType.MONEY, 0.98),
    ]
    for key, val, vtype, conf in fields_data:
        add_field(db_session, doc.id, job.id, key, val, vtype, conf)

    # Autonomy override L3, kill switch OFF
    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.STP
    assert reason == "STP_CRITERIA_MET"
    assert doc.status == DocumentStatus.AUTO_APPROVED
    assert job.routing_decision == RoutingDecision.STP


def test_tc_idp_017_kill_switch_active_routes_to_review(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S1: Kill switch active -> forces REVIEW with KILL_SWITCH_ACTIVE."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=True,  # Kill switch ON!
    )

    assert decision == RoutingDecision.REVIEW
    assert reason == "KILL_SWITCH_ACTIVE"
    assert doc.status == DocumentStatus.NEEDS_REVIEW


def test_tc_idp_017_autonomy_below_l3_routes_to_review(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S1: Autonomy L2 -> forces REVIEW."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L2",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.REVIEW
    assert reason == "AUTONOMY_LEVEL:L2"
    assert doc.status == DocumentStatus.NEEDS_REVIEW


def test_tc_idp_017_channel_c2_never_stp(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S6: Channel C2 (natural language / speech) never STP in MVP."""
    doc, job = create_test_doc_and_job(
        db_session, test_user, DocType.INVOICE, channel=InputChannel.C2
    )

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.REVIEW
    assert reason == "CHANNEL_C2_NOT_STP"


def test_tc_idp_017_salary_and_employee_list_mandatory_review(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S7: EMPLOYEE_LIST or contains_salary -> mandatory REVIEW."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.EMPLOYEE_LIST)

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.REVIEW
    assert reason == "MANDATORY_REVIEW_SALARY"


def test_tc_idp_017_low_confidence_field_routes_to_review(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S3: Any required field confidence < 0.90 -> REVIEW with LOW_CONFIDENCE."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    # total_amount has confidence 0.85 (< 0.90)
    fields_data = [
        ("invoice_number", "HD-2026-0001", FieldValueType.TEXT, 0.98),
        ("issue_date", "2026-09-15", FieldValueType.DATE, 0.95),
        ("seller_name", "Công ty ABC", FieldValueType.ORG_NAME, 0.96),
        ("seller_tax_code", "0101234567", FieldValueType.TAX_CODE, 0.99),
        ("customer_name", "Công ty XYZ", FieldValueType.ORG_NAME, 0.92),
        ("subtotal", 10000000, FieldValueType.MONEY, 0.95),
        ("vat_rate", 0.10, FieldValueType.PERCENT, 0.95),
        ("vat_amount", 1000000, FieldValueType.MONEY, 0.95),
        ("total_amount", 11000000, FieldValueType.MONEY, 0.85),
    ]
    for key, val, vtype, conf in fields_data:
        add_field(db_session, doc.id, job.id, key, val, vtype, conf)

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.REVIEW
    assert "LOW_CONFIDENCE:total_amount" in reason


def test_tc_idp_017_cross_doc_conflict_routes_to_review(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-017 S4: Blocking cross-doc conflict -> REVIEW with CROSS_DOC_CONFLICT."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    job.cross_doc_results = [
        {
            "rule": "XD-01",
            "result": "MISMATCH",
            "severity": "blocking",
            "message": "Doanh thu không khớp",
        }
    ]
    db_session.commit()

    decision, reason = evaluate_routing(
        db_session,
        doc.id,
        job.id,
        autonomy_override="L3",
        kill_switch_override=False,
    )

    assert decision == RoutingDecision.REVIEW
    assert "CROSS_DOC_CONFLICT:XD-01" in reason


# ---------------------------------------------------------------------------
# TC-IDP-035: Celery process_document Idempotent Coordinator
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("eager")
def test_tc_idp_035_process_document_idempotency_and_no_duplicate_fields(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-035: Idempotent by task_id and retry does not create duplicate extracted fields."""
    doc, _job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    store = InMemoryIdempotencyStore()
    process_document_task.idempotency_store = store

    task_id = f"{doc.id}:extract:a1"

    # Run the pipeline first time
    with patch(
        "app.workers.idp.run_document_pipeline",
        return_value={"document_id": str(doc.id), "status": "NEEDS_REVIEW"},
    ) as mock_pipe:
        first = process_document_task.apply_async(
            args=[str(doc.id)],
            task_id=task_id,
        )
        assert first.get() == {"document_id": str(doc.id), "status": "NEEDS_REVIEW"}
        assert mock_pipe.call_count == 1

        # Second call with the same task_id is skipped due to idempotency!
        second = process_document_task.apply_async(
            args=[str(doc.id)],
            task_id=task_id,
        )
        assert second.state == "IGNORED"
        assert mock_pipe.call_count == 1  # Not run again!

    process_document_task.idempotency_store = None


def test_tc_idp_035_retry_clears_draft_fields(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-035: Re-running pipeline on retry clears draft fields without duplicates."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)

    # Add old draft fields
    add_field(db_session, doc.id, job.id, "old_key_1", "old_val", FieldValueType.TEXT)
    add_field(db_session, doc.id, job.id, "old_key_2", "old_val", FieldValueType.TEXT)

    stmt = select(ExtractedField).where(
        ExtractedField.source_document_id == doc.id,
        ExtractedField.extraction_job_id == job.id,
    )
    assert len(db_session.execute(stmt).scalars().all()) == 2

    # Running pipeline cleans old draft fields before extraction
    with (
        patch("app.workers.idp.preprocess_document"),
        patch("app.workers.idp.classify_document"),
        patch("app.workers.idp.extract_document_fields"),
        patch("app.workers.idp.evaluate_routing", return_value=(RoutingDecision.REVIEW, "test")),
    ):
        run_document_pipeline(db_session, doc.id, job.id)

    # Verified: old draft fields were wiped out and no duplicate fields remain
    remaining = db_session.execute(stmt).scalars().all()
    assert len(remaining) == 0


# ---------------------------------------------------------------------------
# TC-IDP-030: Error Handling & Retry Policy
# ---------------------------------------------------------------------------


def test_tc_idp_030_password_protected_file_fails_immediately_without_retry(
    db_session: Session,
    test_user: User,
) -> None:
    """TC-IDP-030: File with password protection fails with IDP-E02 without retry."""
    doc, job = create_test_doc_and_job(db_session, test_user, DocType.INVOICE)
    doc.manual_payload = {"is_password_protected": True}
    db_session.commit()

    res = run_document_pipeline(db_session, doc.id, job.id)

    assert res["status"] == "FAILED"
    assert res["error_code"] == "IDP-E02"

    db_session.refresh(doc)
    db_session.refresh(job)
    assert doc.status == DocumentStatus.FAILED
    assert job.status == JobStatus.FAILED
    assert job.error_code == "IDP-E02"
