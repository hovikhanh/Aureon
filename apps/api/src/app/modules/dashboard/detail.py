"""Metric drill-down services: EP-12 detail, EP-13 records, EP-14 lineage (10 §4)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.modules.auth.models import User
from app.modules.dashboard.enums import AlertStatus, MetricValueKind
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.dashboard.schemas import (
    BreakdownOut,
    BreakdownRowOut,
    HistoryPointOut,
    LineageDocumentOut,
    LineageFieldOut,
    LineagePanelOut,
    MetricDetailOut,
    RecordLineageOut,
    RecordOut,
)
from app.modules.dashboard.scoping import can_act_alert_pillar, metric_access
from app.modules.dashboard.service import build_alert_out, build_metric_value_out
from app.modules.idp.enums import SensitivityLabel
from app.modules.idp.models import BusinessRecord, ExtractedField, SourceDocument


def _get_metric_or_404(db: Session, metric_code: str) -> Metric:
    metric = db.scalars(
        select(Metric).where(Metric.code == metric_code, Metric.deleted_at.is_(None))
    ).first()
    if metric is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Metric {metric_code} not found")
    return metric


def get_metric_detail(
    db: Session, user: User, metric_code: str, period_key: str | None, history: int
) -> MetricDetailOut:
    """EP-12: metric detail with P01 lineage panel, history and breakdown."""
    role_code = user.role.code
    metric = _get_metric_or_404(db, metric_code)
    access = metric_access(role_code, metric_code)
    if access is None:
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, f"Metric {metric_code} out of scope")

    mv = build_metric_value_out(db, metric, access, period_key)
    if mv is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"No current value for {metric_code}")

    # Current ACTUAL row for lineage detail
    actual = db.scalars(
        select(MetricValue).where(
            MetricValue.metric_id == metric.id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
            MetricValue.period_key == mv.period_key,
        )
    ).first()

    source_record_count: int | None = None
    source_documents: list[dict[str, Any]] | None = None
    if access == "FULL" and actual is not None:
        source_record_count = len(actual.source_record_ids or [])
        source_documents = _resolve_source_documents(db, actual, role_code)

    lineage = LineagePanelOut(
        formula_display=metric.formula_display,
        formula_expr=metric.formula_expr,
        source_record_types=list(metric.source_record_types or []),
        computed_at=actual.computed_at if actual else None,
        computation=actual.computation.value if actual else None,
        source_record_count=source_record_count,
        source_documents=source_documents,
    )

    computation_inputs = None
    if actual is not None and actual.breakdown and "inputs" in actual.breakdown:
        computation_inputs = actual.breakdown["inputs"]

    history_points = _build_history(db, metric, history)
    breakdown = _build_breakdown(actual, access)
    alert = _current_alert(db, metric.id)

    return MetricDetailOut(
        metric=mv,
        lineage_panel=lineage,
        computation_inputs=computation_inputs,
        history=history_points,
        breakdown=breakdown,
        alert=(
            build_alert_out(
                db, alert, can_acknowledge=can_act_alert_pillar(role_code, metric.pillar)
            )
            if alert
            else None
        ),
    )


def _resolve_source_documents(
    db: Session, actual: MetricValue, role_code: str
) -> list[dict[str, Any]]:
    doc_ids = list(actual.source_document_ids or [])
    if not doc_ids:
        return []
    docs = db.scalars(select(SourceDocument).where(SourceDocument.id.in_(doc_ids))).all()
    out: list[dict[str, Any]] = []
    salary_view = role_code == "ROLE-04"
    for d in docs:
        restricted = False
        reason = None
        # Salary documents restricted for CEO/CFO (03 §4.4): only HR may open.
        if _doc_has_salary(db, d.id) and not salary_view:
            restricted = True
            reason = "SALARY"
        out.append(
            {
                "id": str(d.id),
                "original_filename": d.original_filename,
                "doc_type": d.doc_type.value if d.doc_type is not None else None,
                "restricted": restricted,
                "reason": reason,
            }
        )
    return out


def _doc_has_salary(db: Session, document_id: UUID) -> bool:
    field = db.scalars(
        select(ExtractedField).where(
            ExtractedField.source_document_id == document_id,
            ExtractedField.sensitivity == SensitivityLabel.SALARY,
        )
    ).first()
    return field is not None


def _build_history(db: Session, metric: Metric, history: int) -> list[HistoryPointOut]:
    rows = db.scalars(
        select(MetricValue)
        .where(
            MetricValue.metric_id == metric.id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
        )
        .order_by(MetricValue.period_key.desc())
        .limit(history)
    ).all()
    targets = {
        t.period_key: t.value
        for t in db.scalars(
            select(MetricValue).where(
                MetricValue.metric_id == metric.id,
                MetricValue.value_kind == MetricValueKind.TARGET,
                MetricValue.is_current.is_(True),
                MetricValue.deleted_at.is_(None),
            )
        )
    }
    points: list[HistoryPointOut] = []
    for r in reversed(rows):
        tv = targets.get(r.period_key)
        points.append(
            HistoryPointOut(
                period_key=r.period_key,
                value=float(r.value) if r.value is not None else None,
                target_value=float(tv) if tv is not None else None,
                value_state="OK" if r.value is not None else "NO_DATA",
                status_color=r.status_color,
            )
        )
    return points


def _build_breakdown(actual: MetricValue | None, access: str) -> BreakdownOut | None:
    if actual is None or access == "AGG":
        return None
    bd = actual.breakdown
    if not bd or "dimension" not in bd or "rows" not in bd:
        return None
    rows = [
        BreakdownRowOut(
            key=str(r.get("key", "")),
            label=str(r.get("label", "")),
            value=r.get("value"),
            share=r.get("share"),
            record_filter=r.get("record_filter"),
        )
        for r in bd["rows"]
    ]
    return BreakdownOut(dimension=str(bd["dimension"]), rows=rows)


def _current_alert(db: Session, metric_id: UUID) -> Alert | None:
    return db.scalars(
        select(Alert)
        .where(
            Alert.metric_id == metric_id,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            Alert.deleted_at.is_(None),
        )
        .order_by(Alert.triggered_at.desc())
    ).first()


def get_metric_records(
    db: Session,
    user: User,
    metric_code: str,
    period_key: str | None,
    record_filter: str | None,
    offset: int,
    limit: int,
) -> tuple[list[RecordOut], int]:
    """EP-13: source business records of a metric (requires FULL access)."""
    role_code = user.role.code
    metric = _get_metric_or_404(db, metric_code)
    access = metric_access(role_code, metric_code)
    if access is None:
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, f"Metric {metric_code} out of scope")
    if access != "FULL":
        raise ApiError(ErrorCode.FORBIDDEN_SCOPE, "Aggregated access cannot drill into records")

    actual_stmt = (
        select(MetricValue)
        .where(
            MetricValue.metric_id == metric.id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
        )
        .order_by(MetricValue.computed_at.desc())
    )
    if period_key is not None:
        actual_stmt = actual_stmt.where(MetricValue.period_key == period_key)
    actual = db.scalars(actual_stmt).first()
    record_ids = list(actual.source_record_ids or []) if actual else []
    if not record_ids:
        return [], 0

    total = len(record_ids)
    page_ids = record_ids[offset : offset + limit]
    records = db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(page_ids))).all()
    by_id = {r.id: r for r in records}
    out = [_record_out(by_id[rid]) for rid in page_ids if rid in by_id]
    return out, total


def _record_out(r: BusinessRecord) -> RecordOut:
    return RecordOut(
        id=r.id,
        record_type=r.record_type.value,
        code=r.code,
        name=r.name,
        period_key=r.period_key,
        issue_date=r.issue_date.isoformat() if r.issue_date else None,
        total_amount=r.total_amount,
        amount_due=r.amount_due,
        status=r.status,
        source_document_id=r.source_document_id,
        attributes=r.attributes or {},
    )


def get_record_lineage(db: Session, user: User, record_id: UUID) -> RecordLineageOut:
    """EP-14: lineage of one business record → extracted fields → source documents."""
    record = db.get(BusinessRecord, record_id)
    if record is None or record.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Record {record_id} not found")

    role_code = user.role.code
    salary_view = role_code == "ROLE-04"

    fields = db.scalars(
        select(ExtractedField).where(ExtractedField.business_record_id == record_id)
    ).all()

    field_out: list[LineageFieldOut] = []
    doc_ids: set[UUID] = set()
    for f in fields:
        if f.sensitivity == SensitivityLabel.SALARY and not salary_view:
            # Hide salary field values for roles without permission (03 §4.4).
            field_out.append(
                LineageFieldOut(
                    field_key=f.field_key,
                    value=None,
                    confidence=None,
                    source_location=None,
                )
            )
            continue
        field_out.append(
            LineageFieldOut(
                field_key=f.field_key,
                value=f.value,
                confidence=float(f.confidence) if f.confidence is not None else None,
                source_location=f.source_location,
            )
        )
        if f.source_document_id:
            doc_ids.add(f.source_document_id)

    if record.source_document_id:
        doc_ids.add(record.source_document_id)

    documents: list[LineageDocumentOut] = []
    for d in db.scalars(select(SourceDocument).where(SourceDocument.id.in_(doc_ids))):
        restricted = _doc_has_salary(db, d.id) and not salary_view
        documents.append(
            LineageDocumentOut(
                id=d.id,
                original_filename=d.original_filename,
                doc_type=d.doc_type.value if d.doc_type is not None else None,
                restricted=restricted,
                reason="SALARY" if restricted else None,
            )
        )

    return RecordLineageOut(record=_record_out(record), fields=field_out, documents=documents)
