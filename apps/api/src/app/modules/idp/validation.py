"""Internal Document Validation & Prompt Injection Defense (T-209).

Specs:
- FR-DC-13: Validation rules (VR-INV-01..03, VR-BCTC-01..02, VR-CON-01, VR-MST-01).
- FR-DC-10, US-DC-018: Prompt injection defense (PI-01..05):
  - PI-01: Document content wrapped in <document_content id="..."> data delimiters.
  - PI-04: Detection of injection patterns ("ignore previous instructions", "bỏ qua hướng dẫn",
    "approve this"), flag SUSPICIOUS_CONTENT, block STP, route to NEEDS_REVIEW.
  - PI-05: Values kept as plain sanitized text.
"""

import re
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.idp.enums import DocType, DocumentStatus, RoutingDecision
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument

# Prompt injection patterns per PI-04 / US-DC-018
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?(?:previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"bỏ\s*qua\s*(?:mọi\s*)?hướng\s*dẫn", re.IGNORECASE),
    re.compile(r"bỏ\s*qua\s*(?:các\s*)?chỉ\s*thị", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"approve\s+(?:this\s+)?(?:invoice|document|contract|all)", re.IGNORECASE),
    re.compile(r"phê\s*duyệt\s*tài\s*liệu\s*này", re.IGNORECASE),
]


def wrap_document_content(text: str, doc_id: str | UUID) -> str:
    """PI-01: Wrap document content in explicit data delimiters."""
    return f'<document_content id="{doc_id}">\n{text}\n</document_content>'


def detect_prompt_injection(corpus: str | None) -> tuple[bool, str | None]:
    """PI-04: Scan corpus for prompt injection signatures.

    Returns (is_suspicious, matched_text).
    """
    if not corpus:
        return False, None
    for pattern in INJECTION_PATTERNS:
        m = pattern.search(corpus)
        if m:
            return True, m.group(0)
    return False, None


def check_and_apply_prompt_injection_defense(
    db: Session,
    doc_id: UUID,
    corpus: str,
    job_id: UUID | None = None,
) -> bool:
    """PI-04: Scan for injection; flag SUSPICIOUS_CONTENT, block STP, set NEEDS_REVIEW."""
    detected, matched_cue = detect_prompt_injection(corpus)
    if not detected:
        return False

    doc = db.get(SourceDocument, doc_id)
    if doc:
        payload = dict(doc.manual_payload or {})
        payload["suspicious_content"] = True
        payload["suspicious_match"] = matched_cue
        doc.manual_payload = payload
        doc.status = DocumentStatus.NEEDS_REVIEW
        reason_msg = f"Tài liệu bị gắn cờ SUSPICIOUS_CONTENT do phát hiện: '{matched_cue}'"
        doc.status_reason = reason_msg

    if job_id:
        job = db.get(ExtractionJob, job_id)
        if job:
            summary = dict(job.validation_summary or {})
            rules = list(summary.get("rules", []))
            rules.append(
                {
                    "rule": "PI-04",
                    "status": "warn",
                    "message": (
                        f"Phát hiện nội dung đáng ngờ '{matched_cue}': "
                        "tài liệu bị gắn cờ SUSPICIOUS_CONTENT, chặn STP, yêu cầu review"
                    ),
                    "severity": "SUSPICIOUS_CONTENT",
                }
            )
            summary["rules"] = rules
            summary["suspicious_content"] = True
            job.validation_summary = summary
            job.routing_decision = RoutingDecision.REVIEW
            job.routing_reason = "SUSPICIOUS_CONTENT"

    db.flush()
    return True


def _adjust_confidence(field: ExtractedField, factor: float) -> None:
    """Adjust field confidence by factor (e.g. 0.5 for fail, 0.85 for warn)."""
    current = float(field.confidence) if field.confidence is not None else 1.0
    field.confidence = max(0.1, round(current * factor, 4))


def validate_internal_rules(
    db: Session,
    doc_id: UUID,
    job_id: UUID | None = None,
) -> dict[str, Any]:
    """Apply internal document validation rules (FR-DC-13) and update field confidences."""
    doc = db.get(SourceDocument, doc_id)
    if not doc:
        return {"rules": [], "has_errors": False, "has_warnings": False}

    # Fetch all non-table extracted fields for this document
    stmt = select(ExtractedField).where(
        ExtractedField.source_document_id == doc_id,
        ExtractedField.table_key.is_(None),
    )
    if job_id:
        stmt = stmt.where(ExtractedField.extraction_job_id == job_id)

    fields = db.execute(stmt).scalars().all()
    f_map = {f.field_key: f for f in fields}

    rule_results: list[dict[str, Any]] = []

    # 1. Tax code validation (VR-MST-01)
    tax_fields = (
        "tax_code",
        "seller_tax_code",
        "customer_tax_code",
        "party_a_tax_code",
        "party_b_tax_code",
    )
    for tax_key in tax_fields:
        if tax_key in f_map and f_map[tax_key].value is not None:
            raw_tc = str(f_map[tax_key].value)
            digits = re.sub(r"[^\d]", "", raw_tc)
            if len(digits) not in (10, 13):
                rule_results.append(
                    {
                        "rule": "VR-MST-01",
                        "status": "fail",
                        "field_key": tax_key,
                        "message": f"Mã số thuế '{raw_tc}' không hợp lệ (phải 10 hoặc 13 số)",
                    }
                )
                _adjust_confidence(f_map[tax_key], 0.5)
            else:
                rule_results.append(
                    {
                        "rule": "VR-MST-01",
                        "status": "pass",
                        "field_key": tax_key,
                        "message": f"Mã số thuế '{raw_tc}' hợp lệ 10/13 số",
                    }
                )

    # 2. INVOICE validation (VR-INV-01, VR-INV-02, VR-INV-03)
    if doc.doc_type == DocType.INVOICE:
        # VR-INV-01: total_amount = subtotal + vat_amount
        if "total_amount" in f_map and f_map["total_amount"].value is not None:
            tot = f_map["total_amount"].value
            sub = f_map["subtotal"].value if "subtotal" in f_map else None
            vat = f_map["vat_amount"].value if "vat_amount" in f_map else None

            if sub is not None and vat is not None:
                calc_tot = sub + vat
                if abs(tot - calc_tot) <= 1000:
                    rule_results.append(
                        {
                            "rule": "VR-INV-01",
                            "status": "pass",
                            "field_key": "total_amount",
                            "message": "Tổng tiền thanh toán khớp Subtotal + Thuế GTGT",
                        }
                    )
                else:
                    rule_results.append(
                        {
                            "rule": "VR-INV-01",
                            "status": "fail",
                            "field_key": "total_amount",
                            "message": (
                                f"Tổng tiền thanh toán {tot:,} đ không khớp "
                                f"Subtotal ({sub:,} đ) + Thuế GTGT ({vat:,} đ) = {calc_tot:,} đ"
                            ),
                        }
                    )
                    _adjust_confidence(f_map["total_amount"], 0.5)

        # VR-INV-02: vat_amount ≈ subtotal * vat_rate
        if (
            "vat_amount" in f_map
            and f_map["vat_amount"].value is not None
            and "subtotal" in f_map
            and f_map["subtotal"].value is not None
            and "vat_rate" in f_map
            and f_map["vat_rate"].value is not None
        ):
            sub = f_map["subtotal"].value
            rate = f_map["vat_rate"].value
            vat = f_map["vat_amount"].value
            expected_vat = round(sub * rate)
            if abs(vat - expected_vat) <= 1000:
                rule_results.append(
                    {
                        "rule": "VR-INV-02",
                        "status": "pass",
                        "field_key": "vat_amount",
                        "message": "Tiền thuế GTGT khớp tỷ lệ thuế suất",
                    }
                )
            else:
                warn_msg = (
                    f"Tiền thuế GTGT {vat:,} đ lệch so với subtotal × rate = {expected_vat:,} đ"
                )
                rule_results.append(
                    {
                        "rule": "VR-INV-02",
                        "status": "warn",
                        "field_key": "vat_amount",
                        "message": warn_msg,
                    }
                )
                _adjust_confidence(f_map["vat_amount"], 0.85)

        # VR-INV-03: due_date >= issue_date
        if (
            "due_date" in f_map
            and f_map["due_date"].value is not None
            and "issue_date" in f_map
            and f_map["issue_date"].value is not None
        ):
            due_str = str(f_map["due_date"].value)
            issue_str = str(f_map["issue_date"].value)
            if due_str < issue_str:
                rule_results.append(
                    {
                        "rule": "VR-INV-03",
                        "status": "fail",
                        "field_key": "due_date",
                        "message": f"Hạn thanh toán ({due_str}) trước ngày phát hành ({issue_str})",
                    }
                )
                _adjust_confidence(f_map["due_date"], 0.5)
            else:
                rule_results.append(
                    {
                        "rule": "VR-INV-03",
                        "status": "pass",
                        "field_key": "due_date",
                        "message": "Hạn thanh toán hợp lệ (sau ngày phát hành)",
                    }
                )

    # 3. FINANCIAL_REPORT validation (VR-BCTC-01, VR-BCTC-02)
    elif doc.doc_type == DocType.FINANCIAL_REPORT:
        # VR-BCTC-01: gross_profit = revenue - cogs (tolerance 0.5%)
        if (
            "gross_profit" in f_map
            and f_map["gross_profit"].value is not None
            and "revenue" in f_map
            and f_map["revenue"].value is not None
            and "cogs" in f_map
            and f_map["cogs"].value is not None
        ):
            rev = f_map["revenue"].value
            cogs = f_map["cogs"].value
            gross = f_map["gross_profit"].value
            calc_gross = rev - cogs
            tolerance = max(1000.0, 0.005 * abs(rev))
            if abs(gross - calc_gross) <= tolerance:
                rule_results.append(
                    {
                        "rule": "VR-BCTC-01",
                        "status": "pass",
                        "field_key": "gross_profit",
                        "message": "Lợi nhuận gộp khớp Doanh thu − Giá vốn",
                    }
                )
            else:
                rule_results.append(
                    {
                        "rule": "VR-BCTC-01",
                        "status": "fail",
                        "field_key": "gross_profit",
                        "message": (
                            f"Lợi nhuận gộp ({gross:,} đ) không khớp "
                            f"Doanh thu ({rev:,} đ) − Giá vốn ({cogs:,} đ) = {calc_gross:,} đ"
                        ),
                    }
                )
                _adjust_confidence(f_map["gross_profit"], 0.5)

        # VR-BCTC-02: net_profit <= gross_profit
        if (
            "net_profit" in f_map
            and f_map["net_profit"].value is not None
            and "gross_profit" in f_map
            and f_map["gross_profit"].value is not None
        ):
            net = f_map["net_profit"].value
            gross = f_map["gross_profit"].value
            if net > gross:
                warn_msg = f"Lợi nhuận sau thuế ({net:,} đ) lớn hơn lợi nhuận gộp ({gross:,} đ)"
                rule_results.append(
                    {
                        "rule": "VR-BCTC-02",
                        "status": "warn",
                        "field_key": "net_profit",
                        "message": warn_msg,
                    }
                )
                _adjust_confidence(f_map["net_profit"], 0.85)
            else:
                rule_results.append(
                    {
                        "rule": "VR-BCTC-02",
                        "status": "pass",
                        "field_key": "net_profit",
                        "message": "Lợi nhuận sau thuế hợp lý (≤ lợi nhuận gộp)",
                    }
                )

    # 4. CONTRACT validation (VR-CON-01, VR-CON-02)
    elif doc.doc_type == DocType.CONTRACT:
        # VR-CON-01: expiry_date >= effective_date
        if (
            "expiry_date" in f_map
            and f_map["expiry_date"].value is not None
            and "effective_date" in f_map
            and f_map["effective_date"].value is not None
        ):
            exp_str = str(f_map["expiry_date"].value)
            eff_str = str(f_map["effective_date"].value)
            if exp_str < eff_str:
                rule_results.append(
                    {
                        "rule": "VR-CON-01",
                        "status": "fail",
                        "field_key": "expiry_date",
                        "message": f"Ngày hết hạn ({exp_str}) trước ngày hiệu lực ({eff_str})",
                    }
                )
                _adjust_confidence(f_map["expiry_date"], 0.5)
            else:
                rule_results.append(
                    {
                        "rule": "VR-CON-01",
                        "status": "pass",
                        "field_key": "expiry_date",
                        "message": "Ngày hết hạn hợp lệ (sau ngày hiệu lực)",
                    }
                )

        # VR-CON-02: sign_date <= today
        if "sign_date" in f_map and f_map["sign_date"].value is not None:
            sign_str = str(f_map["sign_date"].value)
            today_str = date.today().isoformat()
            if sign_str > today_str:
                rule_results.append(
                    {
                        "rule": "VR-CON-02",
                        "status": "warn",
                        "field_key": "sign_date",
                        "message": f"Ngày ký ({sign_str}) ở tương lai",
                    }
                )
            else:
                rule_results.append(
                    {
                        "rule": "VR-CON-02",
                        "status": "pass",
                        "field_key": "sign_date",
                        "message": "Ngày ký hợp lệ",
                    }
                )

    has_errors = any(r["status"] == "fail" for r in rule_results)
    has_warnings = any(r["status"] == "warn" for r in rule_results)

    summary = {
        "rules": rule_results,
        "has_errors": has_errors,
        "has_warnings": has_warnings,
    }

    # Update ExtractionJob if present
    if job_id:
        job = db.get(ExtractionJob, job_id)
        if job:
            prev = dict(job.validation_summary or {})
            combined_rules = list(prev.get("rules", [])) + rule_results
            job.validation_summary = {
                **prev,
                "rules": combined_rules,
                "has_errors": has_errors or prev.get("has_errors", False),
                "has_warnings": has_warnings or prev.get("has_warnings", False),
            }

    # If validation has errors and doc is in EXTRACTING or VALIDATING, transition to NEEDS_REVIEW
    if has_errors and doc.status in (DocumentStatus.EXTRACTING, DocumentStatus.VALIDATING):
        doc.status = DocumentStatus.NEEDS_REVIEW
        failed_rules = [r["rule"] for r in rule_results if r["status"] == "fail"]
        doc.status_reason = f"Vi phạm rule nội tài liệu: {', '.join(failed_rules)}"

    db.flush()
    return summary
