"""T-640 / TC-M15-13 — critical fields (FR-DC-16, R-DEC-69) + G4 incidents EP-DC-36/37."""

import uuid

import pytest

from app.core.errors import ActionRejectedError
from app.modules.idp.schemas import FieldPatchIn
from app.modules.idp.services.admin_service import check_schema_body
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.critical import forced_critical, is_critical, unconfirmed
from app.modules.idp.services.review_service import ReviewService
from tests.integration.idp.critical_helpers import confirm_critical
from tests.integration.idp.test_review_workflow import _committer, _ingest_invoice

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"name": "salary", "value_type": "text"}, True),
        ({"name": "note", "value_type": "money"}, True),
        ({"name": "mst", "value_type": "tax_code"}, True),
        ({"name": "date_of_birth", "value_type": "date", "sensitivity_level": 4}, True),
        ({"name": "title", "value_type": "text", "sensitivity_level": 2}, False),
        ({"name": "title", "value_type": "text", "is_critical": True}, True),
    ],
)
def test_is_critical_rule(spec: dict, expected: bool) -> None:
    assert is_critical(spec) is expected
    assert forced_critical(spec) is (expected and not spec.get("is_critical"))


def test_admin_cannot_clear_level4_critical() -> None:
    from app.core.errors import ValidationError

    th = {"classification_confidence_min": 0.95, "required_field_min": 0.9}
    field = {"name": "address", "value_type": "text", "sensitivity_level": 4,
             "is_critical": False}  # fmt: skip
    with pytest.raises(ValidationError) as exc:
        check_schema_body([field], th, [])
    assert exc.value.details["reason"] == "FR-DC-16"


def test_unconfirmed_ignores_manual_and_confirmed() -> None:
    class F:
        def __init__(self, name: str, crit: bool, by: object, kind: str = "page") -> None:
            self.field_name, self.is_critical, self.corrected_by = name, crit, by
            self.source_location = {"kind": kind}

    rows = [F("amount", True, None), F("vat", True, uuid.uuid4()), F("x", False, None),
            F("salary", True, None, "manual"), F("amount", True, None)]  # fmt: skip
    assert unconfirmed(rows) == ["amount"]


async def test_high_confidence_critical_not_stp_and_blocks_approve(db_session, idp_store) -> None:
    user = _committer()
    doc_id = await _ingest_invoice(db_session, user)  # 0.95+ confidence money → NEEDS_REVIEW
    svc = ReviewService(db_session)
    await svc.open(user, doc_id)
    await svc.patch_fields(user, doc_id, FieldPatchIn(accept_all_high=True))
    with pytest.raises(ActionRejectedError) as exc:  # accept_all_high skipped criticals
        await CommitService(db_session).approve(user, doc_id)
    assert exc.value.details["reason"] == "critical_unconfirmed"
    assert exc.value.details["fields"] == ["seller_tax_code", "subtotal", "total_amount",
                                           "vat_amount"]  # fmt: skip
    await confirm_critical(db_session, user, doc_id, opened=True)
    out = (await CommitService(db_session).approve(user, doc_id)).out
    assert out.document.status == "COMMITTED"


async def test_incidents_report_and_list(api, db_session, idp_store) -> None:
    from sqlalchemy import select

    from app.modules.idp.models import ExtractedField, ExtractionJob
    from app.modules.platform.models import AuditLog

    user = _committer()
    doc_id = await _ingest_invoice(db_session, user)
    fid = (await db_session.execute(select(ExtractedField.id).join(
        ExtractionJob, ExtractionJob.id == ExtractedField.extraction_job_id).where(
        ExtractionJob.source_document_id == doc_id,
        ExtractedField.field_name == "vat_amount"))).scalar_one()  # fmt: skip
    await db_session.commit()
    body = {"source_document_id": str(doc_id), "extracted_field_id": str(fid),
            "field_name": "vat_amount", "target_table": "finance.invoices",
            "description": "VAT sai 1 chữ số"}  # fmt: skip
    reporter = uuid.uuid4()  # EP-DC-37 is row-scoped: the reporter lists its own incidents
    r = await api.http.post(
        "/api/v1/data-capture/incidents",
        json=body,
        headers=api.headers("HR_MANAGER", idem=True, user_id=reporter),
    )
    assert r.status_code == 201, r.text
    inc = r.json()["data"]
    assert inc["is_critical"] and inc["undetected"] and inc["detected_by"] == "post_commit"
    audit = (await db_session.execute(select(AuditLog.action).where(
        AuditLog.target_id == uuid.UUID(inc["id"])))).scalars().all()  # fmt: skip
    assert audit == ["idp.incident_report"]
    minor = {**body, "extracted_field_id": None, "field_name": "invoice_number"}
    m = await api.call("POST", "/data-capture/incidents", "HR_MANAGER", json=minor)
    assert m.json()["data"]["is_critical"] is False
    lst = await api.http.get(
        "/api/v1/data-capture/incidents",
        headers=api.headers("HR_MANAGER", user_id=reporter),
        params={"undetected_only": "true", "period": "current_month"},
    )
    assert lst.status_code == 200, lst.text
    assert inc["id"] in {i["id"] for i in lst.json()["data"]}
    old = await api.call("GET", "/data-capture/incidents", "HR_MANAGER",
                         params={"period": "2020-01"})  # fmt: skip
    assert old.json()["data"] == []
    bad = await api.call("GET", "/data-capture/incidents", "HR_MANAGER",
                         params={"period": "yesterday"})  # fmt: skip
    assert bad.status_code == 422
    mismatch = {**body, "field_name": "subtotal"}
    assert (await api.call("POST", "/data-capture/incidents", "HR_MANAGER",
                           json=mismatch)).status_code == 422  # fmt: skip
    ghost = {**body, "source_document_id": str(uuid.uuid4()), "extracted_field_id": None}
    assert (await api.call("POST", "/data-capture/incidents", "HR_MANAGER",
                           json=ghost)).status_code == 404  # fmt: skip
    assert (await api.call("POST", "/data-capture/incidents", "EMPLOYEE",
                           json=body)).status_code == 403  # fmt: skip
    hdr = api.headers("HR_MANAGER")  # no Idempotency-Key
    assert (await api.http.post("/api/v1/data-capture/incidents", json=body,
                                headers=hdr)).status_code == 400  # fmt: skip
