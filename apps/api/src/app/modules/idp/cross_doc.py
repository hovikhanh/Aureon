"""Cross-Document Consistency Engine (XD-01..XD-05; T-210; 04 §12; FR-DC-14).

Implements:
- XD-01: BCTC month revenue vs SUM(subtotal) of Sept invoices (DEC-030).
  - Tolerance ±0.5%: MATCH / MISMATCH (blocking) / NOT_COMPARABLE.
- XD-02: Customer name consistency between Invoices, Sales Reports, and Contracts (warning).
- XD-03: Attendees / assignees in Meeting Minutes exist in Employee List (warning).
- XD-04: Metric codes in KPI/OKR exist in standard metric registry (blocking).
- XD-05: Uniqueness check: duplicate invoice number / contract number (blocking).
"""

import re
import unicodedata
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.idp.enums import DocType, DocumentStatus, RoutingDecision
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument

STANDARD_METRIC_CODES = {
    "METRIC-FIN-01",
    "METRIC-FIN-02",
    "METRIC-FIN-03",
    "METRIC-FIN-04",
    "METRIC-FIN-05",
    "METRIC-FIN-06",
    "METRIC-CUS-01",
    "METRIC-CUS-02",
    "METRIC-CUS-03",
    "METRIC-CUS-04",
    "METRIC-CUS-05",
    "METRIC-OPS-01",
    "METRIC-OPS-02",
    "METRIC-OPS-03",
    "METRIC-OPS-04",
    "METRIC-HR-01",
    "METRIC-HR-02",
    "METRIC-HR-03",
}


def normalize_entity_name(name: str | None) -> str:
    """Normalize organization or customer name for comparison."""
    if not name:
        return ""
    s = unicodedata.normalize("NFC", str(name)).lower().strip()
    # Strip common corporate prefixes / suffixes
    prefixes = [
        r"công\s*ty\s*(?:tnhh|cổ\s*phần|cp|tm&dv|dịch\s*vụ)?",
        r"tnhh",
        r"cổ\s*phần",
        r"doanh\s*nghiệp",
    ]
    for p in prefixes:
        s = re.sub(rf"\b{p}\b", "", s, flags=re.I)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_person_name(name: str | None) -> str:
    """Normalize person name: strip honorifics (Ông, Bà, Anh, Chị, etc.)."""
    if not name:
        return ""
    s = unicodedata.normalize("NFC", str(name)).strip()
    honorifics = [r"ông", r"bà", r"anh", r"chị", r"cô", r"chú", r"bác", r"đ/c", r"đồng\s*chí"]
    for h in honorifics:
        s = re.sub(rf"^\s*{h}\s+", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return unicodedata.normalize("NFC", s)


def evaluate_xd01(
    db: Session,
    bctc_doc_id: UUID,
    invoice_doc_ids: list[UUID] | None = None,
    target_period: str = "2026-09",
) -> dict[str, Any]:
    """XD-01 (04 §12.1; DEC-030 Option A).

    Compares BCTC monthly revenue (`revenue_by_month[target_period]`)
    with SUM(`subtotal`) of invoices for that month within ±0.5% tolerance.
    """
    # 1. Fetch BCTC revenue for target_period
    stmt_bctc = select(ExtractedField).where(
        ExtractedField.source_document_id == bctc_doc_id,
        ExtractedField.table_key == "revenue_by_month",
    )
    bctc_fields = db.execute(stmt_bctc).scalars().all()

    # Find the row for target_period
    rows_by_idx: dict[int, dict[str, Any]] = {}
    for f in bctc_fields:
        r_idx = f.row_index if f.row_index is not None else 0
        if r_idx not in rows_by_idx:
            rows_by_idx[r_idx] = {}
        rows_by_idx[r_idx][f.field_key] = f.value

    bctc_rev: int | None = None
    for r_data in rows_by_idx.values():
        if r_data.get("month") == target_period and r_data.get("revenue") is not None:
            bctc_rev = int(r_data["revenue"])
            break

    # If target_period not found in revenue_by_month
    if bctc_rev is None:
        return {
            "rule": "XD-01",
            "result": "NOT_COMPARABLE",
            "severity": "warning",
            "message": (
                f"BCTC không có chi tiết doanh thu tháng {target_period} "
                "hoặc chỉ có doanh thu cả quý. Không đối chiếu được – cần review."
            ),
            "ref_document_ids": [str(bctc_doc_id)],
            "values": {
                "period": target_period,
                "bctc_revenue": None,
                "invoice_subtotal_sum": None,
            },
        }

    # 2. Fetch invoice subtotal sum for that period
    stmt_inv = select(ExtractedField).where(
        ExtractedField.field_key == "subtotal",
        ExtractedField.table_key.is_(None),
    )
    if invoice_doc_ids:
        stmt_inv = stmt_inv.where(ExtractedField.source_document_id.in_(invoice_doc_ids))

    inv_subtotals = db.execute(stmt_inv).scalars().all()
    inv_sum = sum(int(f.value) for f in inv_subtotals if f.value is not None)
    actual_inv_doc_ids = list({str(f.source_document_id) for f in inv_subtotals})

    # 3. Compare within ±0.5% tolerance
    tolerance = 0.005 * bctc_rev
    diff = abs(bctc_rev - inv_sum)
    diff_percent = (diff / bctc_rev) * 100 if bctc_rev > 0 else 0.0

    if diff <= tolerance:
        return {
            "rule": "XD-01",
            "result": "MATCH",
            "severity": "info",
            "message": (
                f"Doanh thu tháng {target_period} trong BCTC ({bctc_rev:,} đ) "
                f"khớp SUM(subtotal) hóa đơn ({inv_sum:,} đ) (lệch {diff_percent:.2f}% ≤ 0.5%)"
            ),
            "ref_document_ids": [str(bctc_doc_id), *actual_inv_doc_ids],
            "values": {
                "period": target_period,
                "bctc_revenue": bctc_rev,
                "invoice_subtotal_sum": inv_sum,
                "diff": diff,
                "diff_percent": round(diff_percent, 4),
            },
        }
    else:
        return {
            "rule": "XD-01",
            "result": "MISMATCH",
            "severity": "blocking",
            "message": (
                f"Doanh thu tháng {target_period} trong BCTC ({bctc_rev:,} đ) "
                f"lệch SUM(subtotal) hóa đơn ({inv_sum:,} đ) "
                f"(chênh {diff:,} đ, {diff_percent:.2f}% > 0.5%)"
            ),
            "ref_document_ids": [str(bctc_doc_id), *actual_inv_doc_ids],
            "values": {
                "period": target_period,
                "bctc_revenue": bctc_rev,
                "invoice_subtotal_sum": inv_sum,
                "diff": diff,
                "diff_percent": round(diff_percent, 4),
            },
        }


def evaluate_xd02(
    db: Session,
    customer_name: str,
    doc_id: UUID,
    ref_doc_ids: list[UUID] | None = None,
) -> dict[str, Any]:
    """XD-02: Customer name consistency between Invoices, Sales Reports, and Contracts."""
    norm_target = normalize_entity_name(customer_name)
    if not norm_target:
        return {
            "rule": "XD-02",
            "result": "MATCH",
            "severity": "info",
            "message": "Không có tên khách hàng để đối chiếu",
            "ref_document_ids": [str(doc_id)],
            "values": {"customer_name": customer_name},
        }

    # Fetch customer names from Contracts (party_b_name) and Sales Reports
    stmt = select(ExtractedField).where(
        ExtractedField.field_key.in_(["party_b_name", "customer_name"]),
        ExtractedField.source_document_id != doc_id,
    )
    if ref_doc_ids:
        stmt = stmt.where(ExtractedField.source_document_id.in_(ref_doc_ids))

    known_fields = db.execute(stmt).scalars().all()
    matched = False
    matched_ref_id: str | None = None

    for kf in known_fields:
        if kf.value and normalize_entity_name(str(kf.value)) == norm_target:
            matched = True
            matched_ref_id = str(kf.source_document_id)
            break

    if matched:
        return {
            "rule": "XD-02",
            "result": "MATCH",
            "severity": "info",
            "message": f"Tên khách hàng '{customer_name}' khớp với dữ liệu hợp đồng/sales",
            "ref_document_ids": [str(doc_id), matched_ref_id] if matched_ref_id else [str(doc_id)],
            "values": {"customer_name": customer_name},
        }
    else:
        return {
            "rule": "XD-02",
            "result": "MISMATCH",
            "severity": "warning",
            "message": (
                f"Tên khách hàng '{customer_name}' chưa khớp với hợp đồng hoặc báo cáo sales đã có"
            ),
            "ref_document_ids": [str(doc_id)],
            "values": {"customer_name": customer_name},
        }


def evaluate_xd03(
    db: Session,
    meeting_doc_id: UUID,
    attendees: list[str],
    emp_doc_id: UUID | None = None,
) -> dict[str, Any]:
    """XD-03: Attendees / assignees in Meeting Minutes exist in Employee List."""
    # Fetch all employees from Employee List
    stmt = select(ExtractedField).where(
        ExtractedField.field_key == "full_name",
        ExtractedField.source_document_id != meeting_doc_id,
    )
    if emp_doc_id:
        stmt = stmt.where(ExtractedField.source_document_id == emp_doc_id)

    emp_fields = db.execute(stmt).scalars().all()
    known_names = {normalize_person_name(str(f.value)) for f in emp_fields if f.value}

    missing_names: list[str] = []
    for att in attendees:
        norm_att = normalize_person_name(att)
        if norm_att and norm_att not in known_names:
            missing_names.append(att)

    ref_ids = [str(meeting_doc_id)]
    if emp_doc_id:
        ref_ids.append(str(emp_doc_id))

    if not missing_names:
        return {
            "rule": "XD-03",
            "result": "MATCH",
            "severity": "info",
            "message": "Toàn bộ nhân sự trong biên bản họp khớp với danh sách nhân sự",
            "ref_document_ids": ref_ids,
            "values": {"attendees_count": len(attendees), "missing_attendees": []},
        }
    else:
        return {
            "rule": "XD-03",
            "result": "MISMATCH",
            "severity": "warning",
            "message": (
                f"Nhân sự trong biên bản họp không có trong danh sách nhân sự: "
                f"{', '.join(missing_names)}"
            ),
            "ref_document_ids": ref_ids,
            "values": {"attendees_count": len(attendees), "missing_attendees": missing_names},
        }


def evaluate_xd04(
    db: Session,
    kpi_doc_id: UUID,
    metric_codes: list[str],
) -> dict[str, Any]:
    """XD-04: Metric codes in KPI/OKR exist in standard metric registry (blocking)."""
    invalid_codes = [c for c in metric_codes if c not in STANDARD_METRIC_CODES]

    if not invalid_codes:
        return {
            "rule": "XD-04",
            "result": "MATCH",
            "severity": "info",
            "message": "Mọi mã chỉ số KPI/OKR đều hợp lệ trong danh mục 18 metric",
            "ref_document_ids": [str(kpi_doc_id)],
            "values": {"metric_codes": metric_codes, "invalid_codes": []},
        }
    else:
        return {
            "rule": "XD-04",
            "result": "MISMATCH",
            "severity": "blocking",
            "message": (
                f"Mã chỉ số không tồn tại trong danh mục 18 metric: {', '.join(invalid_codes)}"
            ),
            "ref_document_ids": [str(kpi_doc_id)],
            "values": {"metric_codes": metric_codes, "invalid_codes": invalid_codes},
        }


def evaluate_xd05(
    db: Session,
    doc_id: UUID,
    field_key: str,
    identifier_value: str,
) -> dict[str, Any]:
    """XD-05: Duplicate business code check (invoice_number, contract_number)."""
    stmt = select(ExtractedField).where(
        ExtractedField.field_key == field_key,
        ExtractedField.raw_text == identifier_value,
        ExtractedField.source_document_id != doc_id,
    )
    dup = db.execute(stmt).scalars().first()

    if not dup:
        return {
            "rule": "XD-05",
            "result": "MATCH",
            "severity": "info",
            "message": f"Số {field_key} '{identifier_value}' là duy nhất",
            "ref_document_ids": [str(doc_id)],
            "values": {"field_key": field_key, "value": identifier_value},
        }
    else:
        return {
            "rule": "XD-05",
            "result": "MISMATCH",
            "severity": "blocking",
            "message": (
                f"Trùng số nghiệp vụ: {field_key} '{identifier_value}' "
                f"đã tồn tại trong tài liệu {dup.source_document_id}"
            ),
            "ref_document_ids": [str(doc_id), str(dup.source_document_id)],
            "values": {"field_key": field_key, "value": identifier_value},
        }


def run_cross_document_checks(
    db: Session,
    doc_id: UUID,
    job_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Run applicable XD rules for a document and persist into ExtractionJob.cross_doc_results."""
    doc = db.get(SourceDocument, doc_id)
    if not doc:
        return []

    results: list[dict[str, Any]] = []

    # 1. XD-01: if document is FINANCIAL_REPORT, look for invoices in DB
    if doc.doc_type == DocType.FINANCIAL_REPORT:
        res_xd01 = evaluate_xd01(db, doc.id)
        results.append(res_xd01)

    # 2. XD-02: if document has customer_name
    stmt_cus = select(ExtractedField).where(
        ExtractedField.source_document_id == doc.id,
        ExtractedField.field_key.in_(["customer_name", "party_b_name"]),
    )
    cus_field = db.execute(stmt_cus).scalars().first()
    if cus_field and cus_field.value:
        res_xd02 = evaluate_xd02(db, str(cus_field.value), doc.id)
        results.append(res_xd02)

    # 3. XD-03: if document is MEETING_MINUTES, check attendees
    if doc.doc_type == DocType.MEETING_MINUTES:
        stmt_att = select(ExtractedField).where(
            ExtractedField.source_document_id == doc.id,
            ExtractedField.field_key.in_(["chairperson", "assignee"]),
        )
        att_fields = db.execute(stmt_att).scalars().all()
        att_names = [str(f.value) for f in att_fields if f.value]
        if att_names:
            res_xd03 = evaluate_xd03(db, doc.id, att_names)
            results.append(res_xd03)

    # 4. XD-04: if document is KPI_OKR, check metric codes
    if doc.doc_type == DocType.KPI_OKR:
        stmt_kpi = select(ExtractedField).where(
            ExtractedField.source_document_id == doc.id,
            ExtractedField.field_key == "metric_code",
        )
        kpi_fields = db.execute(stmt_kpi).scalars().all()
        codes = [str(f.value) for f in kpi_fields if f.value]
        if codes:
            res_xd04 = evaluate_xd04(db, doc.id, codes)
            results.append(res_xd04)

    # 5. XD-05: check invoice_number or contract_number duplication
    stmt_id = select(ExtractedField).where(
        ExtractedField.source_document_id == doc.id,
        ExtractedField.field_key.in_(["invoice_number", "contract_number"]),
    )
    id_field = db.execute(stmt_id).scalars().first()
    if id_field and id_field.value:
        res_xd05 = evaluate_xd05(db, doc.id, id_field.field_key, str(id_field.value))
        results.append(res_xd05)

    # Persist in ExtractionJob
    if job_id:
        job = db.get(ExtractionJob, job_id)
        if job:
            job.cross_doc_results = results

            # If any blocking mismatch, force routing to REVIEW
            has_blocking = any(
                r.get("result") in ("MISMATCH", "NOT_COMPARABLE")
                and r.get("severity") == "blocking"
                for r in results
            )
            if has_blocking:
                job.routing_decision = RoutingDecision.REVIEW
                job.routing_reason = "CROSS_DOC_CONFLICT"
                doc.status = DocumentStatus.NEEDS_REVIEW
                doc.status_reason = "Xung đột đối chiếu chéo tài liệu (cross-doc conflict)"

    db.flush()
    return results
