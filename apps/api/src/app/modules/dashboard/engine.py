"""Dynamic metric & alert engine (T-302 → T-305).

Recomputes metric *actual* values from committed ``business_records`` instead of
relying only on seed values, versions the resulting ``MetricValue`` rows (supersede
the previous ``is_current``), derives the ``status_color`` from the metric thresholds,
and drives the alert lifecycle (open / resolve, at most one open alert per metric).

The engine is the single place that turns raw business records into dashboard numbers.
It is called:

- synchronously after the IDP Action Registry commits a record (``recompute_for_record_type``),
- and by the Celery task ``recompute_metrics`` (T-304), which is idempotent.

Design notes
------------
* Only metrics whose ``source_record_types`` have committed business records for the
  target period are recomputed; metrics backed solely by seed history keep their SEED
  baseline (``computation=SEED``) untouched. This keeps the demo dashboard stable while
  letting freshly-committed documents move the needle (03 §2, 08 §5.1).
* Thresholds come from ``Metric.warning_threshold`` / ``critical_threshold`` /
  ``direction`` (03 §2). The compared quantity depends on the metric (percent-of-plan,
  ratio, raw value) and is produced by the per-metric computation functions below.
* Every write goes through ``_upsert_actual`` which supersedes the prior current value
  and copies lineage (``source_record_ids`` / ``source_document_ids``) so P01 drill-down
  keeps working.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricValueKind,
    PeriodType,
    ThresholdDirection,
    ThresholdStatus,
    ValueOrigin,
)
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.idp.enums import RecordType
from app.modules.idp.models import BusinessRecord

DEFAULT_PERIOD_KEY = "2026-09"
DEFAULT_QUARTER_KEY = "2026-Q3"


@dataclass
class ComputationResult:
    """Outcome of a per-metric computation from business records."""

    value: float | None
    compared: float | None  # quantity compared against thresholds (may differ from value)
    source_record_ids: list[UUID] = field(default_factory=list)
    source_document_ids: list[UUID] = field(default_factory=list)
    breakdown: dict[str, object] | None = None
    # When False the metric cannot be computed from records now -> engine leaves it as is.
    computable: bool = True


def _to_float(v: object) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Record queries
# ---------------------------------------------------------------------------


def _live_records(db: Session, record_type: RecordType) -> list[BusinessRecord]:
    """Non-deleted business records of a type."""
    stmt = select(BusinessRecord).where(
        and_(
            BusinessRecord.record_type == record_type,
            BusinessRecord.deleted_at.is_(None),
        )
    )
    return list(db.execute(stmt).scalars().all())


def _in_month(rec: BusinessRecord, period_key: str) -> bool:
    if rec.period_key == period_key:
        return True
    if rec.issue_date is not None and rec.issue_date.strftime("%Y-%m") == period_key:
        return True
    return False


# ---------------------------------------------------------------------------
# Per-metric computations (from business_records)
# ---------------------------------------------------------------------------


def _compute_fin01(db: Session, metric: Metric, period_key: str) -> ComputationResult:
    """METRIC-FIN-01 — monthly revenue vs plan (%).

    value = SUM(INVOICE.subtotal in month) ; compared = value / plan_month * 100.
    plan_month is read from the metric's current TARGET value (seeded from DOC-03).
    """
    invoices = [r for r in _live_records(db, RecordType.INVOICE) if _in_month(r, period_key)]
    if not invoices:
        return ComputationResult(value=None, compared=None, computable=False)
    total = sum(_to_float(r.subtotal) for r in invoices)
    plan = _current_target_value(db, metric.id, period_key) or 9_600_000_000.0
    compared = (total / plan * 100.0) if plan else None
    return ComputationResult(
        value=total,
        compared=compared,
        source_record_ids=[r.id for r in invoices],
        source_document_ids=_doc_ids(invoices),
        breakdown={"plan": plan, "percent_of_plan": compared, "invoice_count": len(invoices)},
    )


def _compute_fin05(db: Session, metric: Metric, period_key: str) -> ComputationResult:
    """METRIC-FIN-05 — overdue receivables ratio (%).

    value = SUM(amount_due of overdue UNPAID/PARTIAL invoices) / SUM(amount_due all open) * 100.
    """
    invoices = _live_records(db, RecordType.INVOICE)
    open_inv = [r for r in invoices if _to_float(r.amount_due) > 0]
    if not open_inv:
        return ComputationResult(value=None, compared=None, computable=False)
    ref = date(2026, 10, 20)
    total_open = sum(_to_float(r.amount_due) for r in open_inv)
    overdue = sum(
        _to_float(r.amount_due)
        for r in open_inv
        if r.due_date is not None and r.due_date < ref
    )
    compared = (overdue / total_open * 100.0) if total_open else 0.0
    return ComputationResult(
        value=compared,
        compared=compared,
        source_record_ids=[r.id for r in open_inv],
        source_document_ids=_doc_ids(open_inv),
        breakdown={"overdue": overdue, "total_open": total_open},
    )


def _compute_ops01(db: Session, metric: Metric, period_key: str) -> ComputationResult:
    """METRIC-OPS-01 — tasks completed on time (%).

    value = DONE-on-time / total tasks * 100. ``attributes.on_time`` marks on-time done.
    """
    tasks = [r for r in _live_records(db, RecordType.TASK)]
    if not tasks:
        return ComputationResult(value=None, compared=None, computable=False)
    total = len(tasks)
    done_on_time = sum(
        1
        for r in tasks
        if (r.status or "").upper() == "DONE" and bool((r.attributes or {}).get("on_time", False))
    )
    compared = done_on_time / total * 100.0
    return ComputationResult(
        value=compared,
        compared=compared,
        source_record_ids=[r.id for r in tasks],
        source_document_ids=_doc_ids(tasks),
        breakdown={"done_on_time": done_on_time, "total": total},
    )


def _compute_hr01(db: Session, metric: Metric, period_key: str) -> ComputationResult:
    """METRIC-HR-01 — revenue per active employee (VND/person).

    value = SUM(INVOICE.subtotal in month) / COUNT(active employees).
    """
    employees = [
        r for r in _live_records(db, RecordType.EMPLOYEE) if (r.status or "").upper() == "ACTIVE"
    ]
    if not employees:
        return ComputationResult(value=None, compared=None, computable=False)
    invoices = [r for r in _live_records(db, RecordType.INVOICE) if _in_month(r, period_key)]
    revenue = sum(_to_float(r.subtotal) for r in invoices)
    headcount = len(employees)
    value = revenue / headcount if headcount else 0.0
    return ComputationResult(
        value=value,
        compared=value,
        source_record_ids=[r.id for r in employees],
        source_document_ids=_doc_ids(employees),
        breakdown={"revenue": revenue, "headcount": headcount},
    )


# Registry: metric code -> computation function. Only these metrics are recomputed
# from records; all others keep their seed baseline.
COMPUTERS: dict[str, Callable[[Session, Metric, str], ComputationResult]] = {
    "METRIC-FIN-01": _compute_fin01,
    "METRIC-FIN-05": _compute_fin05,
    "METRIC-OPS-01": _compute_ops01,
    "METRIC-HR-01": _compute_hr01,
}

# Which metric codes depend on each committed record type (reverse index for triggers).
RECORD_TYPE_TO_METRICS: dict[RecordType, list[str]] = {
    RecordType.INVOICE: ["METRIC-FIN-01", "METRIC-FIN-05", "METRIC-HR-01"],
    RecordType.FINANCIAL_LINE: ["METRIC-FIN-01"],
    RecordType.TASK: ["METRIC-OPS-01"],
    RecordType.EMPLOYEE: ["METRIC-HR-01"],
}


def _doc_ids(records: Iterable[BusinessRecord]) -> list[UUID]:
    seen: list[UUID] = []
    for r in records:
        if r.source_document_id and r.source_document_id not in seen:
            seen.append(r.source_document_id)
    return seen


# ---------------------------------------------------------------------------
# Thresholds & status
# ---------------------------------------------------------------------------


def classify_status(metric: Metric, compared: float | None) -> ThresholdStatus:
    """Map a compared quantity to a status color using the metric thresholds (03 §2)."""
    if compared is None:
        return ThresholdStatus.GREEN
    warn = _to_float(metric.warning_threshold) if metric.warning_threshold is not None else None
    crit = _to_float(metric.critical_threshold) if metric.critical_threshold is not None else None
    if metric.direction == ThresholdDirection.LOWER_IS_BAD:
        # Lower is worse: below critical -> RED, below warning -> YELLOW.
        if crit is not None and compared < crit:
            return ThresholdStatus.RED
        if warn is not None and compared < warn:
            return ThresholdStatus.YELLOW
        return ThresholdStatus.GREEN
    # HIGHER_IS_BAD: above critical -> RED, above warning -> YELLOW.
    if crit is not None and compared > crit:
        return ThresholdStatus.RED
    if warn is not None and compared > warn:
        return ThresholdStatus.YELLOW
    return ThresholdStatus.GREEN


def _current_actual(db: Session, metric_id: UUID, period_key: str) -> MetricValue | None:
    stmt = select(MetricValue).where(
        and_(
            MetricValue.metric_id == metric_id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.period_key == period_key,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
        )
    )
    return db.execute(stmt).scalars().first()


def _current_target_value(db: Session, metric_id: UUID, period_key: str) -> float | None:
    stmt = select(MetricValue).where(
        and_(
            MetricValue.metric_id == metric_id,
            MetricValue.value_kind == MetricValueKind.TARGET,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
        )
    )
    mv = db.execute(stmt).scalars().first()
    return _to_float(mv.value) if mv and mv.value is not None else None


# ---------------------------------------------------------------------------
# Versioned write + alert lifecycle
# ---------------------------------------------------------------------------


def _upsert_actual(
    db: Session,
    metric: Metric,
    period_key: str,
    period_type: PeriodType,
    result: ComputationResult,
    status_color: ThresholdStatus,
) -> MetricValue:
    """Supersede the current ACTUAL value for the period and insert a fresh COMPUTED one."""
    prev = _current_actual(db, metric.id, period_key)
    now = datetime.now(UTC)
    new_mv = MetricValue(
        metric_id=metric.id,
        value_kind=MetricValueKind.ACTUAL,
        period_type=period_type,
        period_key=period_key,
        value=result.value,
        breakdown=result.breakdown,
        computation=ValueOrigin.COMPUTED,
        source_record_ids=result.source_record_ids,
        source_document_ids=result.source_document_ids,
        status_color=status_color,
        is_current=True,
        computed_at=now,
        computed_by_action="engine.recompute",
    )
    if prev is not None:
        prev.is_current = False
        db.flush()
        prev.superseded_by_id = None  # set after new id exists
    db.add(new_mv)
    db.flush()
    if prev is not None:
        prev.superseded_by_id = new_mv.id
    return new_mv


def _sync_alert(
    db: Session,
    metric: Metric,
    metric_value: MetricValue,
    status_color: ThresholdStatus,
) -> Alert | None:
    """Open / resolve the metric's alert so at most one is OPEN (T-305, 03 §3).

    - RED -> CRITICAL open ; YELLOW -> WARNING open ; GREEN -> resolve any open alert.
    - An existing open alert of the same severity is kept (idempotent); severity change
      resolves the old and opens a new one.
    """
    # OPEN and ACKNOWLEDGED both count as "active" (the uq_alerts_open index covers both),
    # so we never create a second active alert for the same metric/period.
    open_stmt = select(Alert).where(
        and_(
            Alert.metric_id == metric.id,
            Alert.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)),
            Alert.deleted_at.is_(None),
        )
    )
    open_alert = db.execute(open_stmt).scalars().first()

    desired: AlertSeverity | None
    if status_color == ThresholdStatus.RED:
        desired = AlertSeverity.CRITICAL
    elif status_color == ThresholdStatus.YELLOW:
        desired = AlertSeverity.WARNING
    else:
        desired = None

    if desired is None:
        if open_alert is not None:
            open_alert.status = AlertStatus.RESOLVED
            open_alert.resolved_at = datetime.now(UTC)
            db.flush()
        return None

    if open_alert is not None:
        if open_alert.severity == desired:
            # Keep but re-point to the latest metric value.
            open_alert.metric_value_id = metric_value.id
            open_alert.period_key = metric_value.period_key
            db.flush()
            return open_alert
        open_alert.status = AlertStatus.RESOLVED
        open_alert.resolved_at = datetime.now(UTC)
        db.flush()

    new_alert = Alert(
        metric_id=metric.id,
        metric_value_id=metric_value.id,
        period_key=metric_value.period_key,
        severity=desired,
        status=AlertStatus.OPEN,
        message_params=metric_value.breakdown or {},
        triggered_at=datetime.now(UTC),
    )
    db.add(new_alert)
    db.flush()
    return new_alert


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def recompute_metric(
    db: Session, metric: Metric, period_key: str | None = None
) -> MetricValue | None:
    """Recompute one metric from business records; returns the new value or None."""
    computer = COMPUTERS.get(metric.code)
    if computer is None:
        return None
    # FIN-01/FIN-05/OPS-01/HR-01 are all monthly in the demo seed (08 §5.1).
    pkey = period_key or DEFAULT_PERIOD_KEY
    result = computer(db, metric, pkey)
    if not result.computable:
        return None
    status_color = classify_status(metric, result.compared)
    mv = _upsert_actual(db, metric, pkey, PeriodType.MONTH, result, status_color)
    _sync_alert(db, metric, mv, status_color)
    return mv


def recompute_metrics(
    db: Session, metric_codes: Iterable[str] | None = None, period_key: str | None = None
) -> list[str]:
    """Recompute a set of metrics (default: all with a computer). Returns codes recomputed."""
    codes = list(metric_codes) if metric_codes is not None else list(COMPUTERS.keys())
    recomputed: list[str] = []
    for code in codes:
        metric = db.execute(
            select(Metric).where(and_(Metric.code == code, Metric.deleted_at.is_(None)))
        ).scalars().first()
        if metric is None:
            continue
        mv = recompute_metric(db, metric, period_key)
        if mv is not None:
            recomputed.append(code)
    return recomputed


def recompute_for_record_type(
    db: Session, record_type: RecordType, period_key: str | None = None
) -> list[str]:
    """Recompute the metrics that depend on a just-committed record type (trigger hook)."""
    codes = RECORD_TYPE_TO_METRICS.get(record_type, [])
    if not codes:
        return []
    return recompute_metrics(db, codes, period_key)
