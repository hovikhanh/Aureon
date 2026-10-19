"""Dynamic metric & alert engine tests — T-302..T-305.

Covers:
- classify_status threshold logic for both directions (03 §2).
- recompute_metric for METRIC-FIN-01 from committed INVOICE business records:
  value = SUM(subtotal), status + versioning (supersede previous ACTUAL) + lineage.
- alert lifecycle: YELLOW opens a WARNING, GREEN resolves it, and at most one open
  alert per metric (T-305, 03 §3).
- recompute_for_record_type trigger routing.

Runs inside the rolled-back ``db_session`` (conftest) which seeds the 18 metrics +
their SEED values and 12 alerts.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.dashboard.engine import (
    classify_status,
    recompute_for_record_type,
    recompute_metric,
    recompute_metrics,
)
from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricValueKind,
    ThresholdStatus,
)
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.idp.enums import DocumentKind, InputChannel, RecordType
from app.modules.idp.models import BusinessRecord, SourceDocument

pytestmark = pytest.mark.integration


def _metric(db: Session, code: str) -> Metric:
    m = db.execute(select(Metric).where(Metric.code == code)).scalars().first()
    assert m is not None, f"seed missing metric {code}"
    return m


def _uploader(db: Session) -> User:
    user = db.execute(select(User).where(User.email == "ceo@abc.demo")).scalars().first()
    assert user is not None, "seed missing ceo@abc.demo"
    return user


def _current_actual(db: Session, metric_id, period_key: str) -> MetricValue | None:
    return db.execute(
        select(MetricValue).where(
            and_(
                MetricValue.metric_id == metric_id,
                MetricValue.value_kind == MetricValueKind.ACTUAL,
                MetricValue.period_key == period_key,
                MetricValue.is_current.is_(True),
            )
        )
    ).scalars().first()


def _add_invoice(
    db: Session,
    *,
    subtotal: int,
    issue: date,
    due: date,
    paid: int = 0,
) -> BusinessRecord:
    doc = SourceDocument(
        id=uuid4(),
        channel=InputChannel.C3,
        kind=DocumentKind.FILE,
        original_filename="inv.xlsx",
        mime_type="application/vnd.ms-excel",
        uploaded_by_id=_uploader(db).id,
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)
    db.flush()
    rec = BusinessRecord(
        id=uuid4(),
        record_type=RecordType.INVOICE,
        pillar="FIN",
        code=f"HV-{uuid4().hex[:6]}",
        name="Khách demo",
        issue_date=issue,
        due_date=due,
        period_key=issue.strftime("%Y-%m"),
        subtotal=subtotal,
        vat_rate=Decimal("0.10"),
        total_amount=int(subtotal * 1.1),
        paid_amount=paid,
        status="UNPAID" if paid == 0 else "PAID",
        source_document_id=doc.id,
        created_by_action="invoice.create",
    )
    db.add(rec)
    db.flush()
    return rec


# ---------------------------------------------------------------------------
# classify_status
# ---------------------------------------------------------------------------


def test_classify_status_lower_is_bad(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-01")  # LOWER_IS_BAD warn=90 crit=80
    assert classify_status(m, 95.0) == ThresholdStatus.GREEN
    assert classify_status(m, 88.5) == ThresholdStatus.YELLOW
    assert classify_status(m, 70.0) == ThresholdStatus.RED
    assert classify_status(m, None) == ThresholdStatus.GREEN


def test_classify_status_higher_is_bad(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-05")  # HIGHER_IS_BAD (overdue ratio)
    warn = float(m.warning_threshold)
    crit = float(m.critical_threshold)
    assert classify_status(m, warn - 1) == ThresholdStatus.GREEN
    assert classify_status(m, (warn + crit) / 2) == ThresholdStatus.YELLOW
    assert classify_status(m, crit + 1) == ThresholdStatus.RED


# ---------------------------------------------------------------------------
# recompute METRIC-FIN-01 from invoices
# ---------------------------------------------------------------------------


def test_recompute_fin01_value_and_versioning(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-01")
    prev = _current_actual(db_session, m.id, "2026-09")
    assert prev is not None  # seed baseline exists
    prev_id = prev.id

    _add_invoice(db_session, subtotal=5_000_000_000, issue=date(2026, 9, 2), due=date(2026, 10, 2))
    _add_invoice(db_session, subtotal=3_500_000_000, issue=date(2026, 9, 5), due=date(2026, 10, 5))

    mv = recompute_metric(db_session, m, "2026-09")
    assert mv is not None
    # value = SUM(subtotal) = 8.5B
    assert float(mv.value) == pytest.approx(8_500_000_000)
    assert mv.is_current is True
    assert str(mv.computation) == "COMPUTED"
    # lineage captured
    assert len(mv.source_record_ids) == 2

    # previous ACTUAL superseded
    db_session.refresh(prev)
    assert prev.is_current is False
    assert prev.superseded_by_id == mv.id
    assert prev_id != mv.id

    # only one current ACTUAL remains for the period
    current = db_session.execute(
        select(MetricValue).where(
            and_(
                MetricValue.metric_id == m.id,
                MetricValue.value_kind == MetricValueKind.ACTUAL,
                MetricValue.period_key == "2026-09",
                MetricValue.is_current.is_(True),
            )
        )
    ).scalars().all()
    assert len(current) == 1


def test_recompute_fin01_noop_without_records(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-01")
    before = _current_actual(db_session, m.id, "2026-09")
    before_id = before.id if before else None
    # No invoices committed in a fresh (seed-only) period "2099-01" -> not computable.
    mv = recompute_metric(db_session, m, "2099-01")
    assert mv is None
    after = _current_actual(db_session, m.id, "2026-09")
    assert after is not None and after.id == before_id  # untouched


# ---------------------------------------------------------------------------
# alert lifecycle (T-305)
# ---------------------------------------------------------------------------


def _open_alerts(db: Session, metric_id) -> list[Alert]:
    return list(
        db.execute(
            select(Alert).where(
                and_(
                    Alert.metric_id == metric_id,
                    Alert.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)),
                    Alert.deleted_at.is_(None),
                )
            )
        ).scalars().all()
    )


def test_alert_opens_on_yellow_and_resolves_on_green(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-01")  # plan target 9.6B

    # 8.5B / 9.6B = 88.5% < 90% warn -> YELLOW -> WARNING alert
    _add_invoice(db_session, subtotal=8_500_000_000, issue=date(2026, 9, 2), due=date(2026, 10, 2))
    recompute_metric(db_session, m, "2026-09")
    opens = _open_alerts(db_session, m.id)
    assert len(opens) == 1
    assert opens[0].severity == AlertSeverity.WARNING

    # Add more revenue -> 12B / 9.6B = 125% >= 90% -> GREEN -> resolve the alert.
    _add_invoice(db_session, subtotal=3_500_000_000, issue=date(2026, 9, 9), due=date(2026, 10, 9))
    recompute_metric(db_session, m, "2026-09")
    assert _open_alerts(db_session, m.id) == []


def test_at_most_one_open_alert_on_repeated_recompute(db_session: Session) -> None:
    m = _metric(db_session, "METRIC-FIN-01")
    _add_invoice(db_session, subtotal=8_500_000_000, issue=date(2026, 9, 2), due=date(2026, 10, 2))
    for _ in range(3):
        recompute_metric(db_session, m, "2026-09")
    assert len(_open_alerts(db_session, m.id)) == 1


# ---------------------------------------------------------------------------
# trigger routing
# ---------------------------------------------------------------------------


def test_recompute_for_record_type_invoice(db_session: Session) -> None:
    _add_invoice(db_session, subtotal=8_500_000_000, issue=date(2026, 9, 2), due=date(2026, 10, 2))
    recomputed = recompute_for_record_type(db_session, RecordType.INVOICE)
    assert "METRIC-FIN-01" in recomputed


def test_recompute_metrics_defaults_to_all_computers(db_session: Session) -> None:
    _add_invoice(db_session, subtotal=8_500_000_000, issue=date(2026, 9, 2), due=date(2026, 10, 2))
    recomputed = recompute_metrics(db_session)
    # FIN-01 and FIN-05 are computable from the single invoice above.
    assert "METRIC-FIN-01" in recomputed
    assert "METRIC-FIN-05" in recomputed
