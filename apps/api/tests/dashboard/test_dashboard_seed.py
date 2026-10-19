"""Dashboard seed verification — TC-DASH-007 (08 §5.1, 03 §2/§3.2).

Verifies the seed produces exactly the demo state: 18 metrics, 36 current metric
values (18 ACTUAL + 18 TARGET), 12 open alerts (4 Critical + 8 Warning), and the key
demo metric values from 08 §5.1. Runs inside the rolled-back ``db_session``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricValueKind,
    ThresholdStatus,
)
from app.modules.dashboard.models import Alert, Metric, MetricValue

pytestmark = pytest.mark.integration


def test_eighteen_metrics_seeded(db_session: Session):
    metrics = db_session.scalars(select(Metric)).all()
    assert len(metrics) == 18
    pillars = {}
    for m in metrics:
        pillars.setdefault(m.pillar, 0)
        pillars[m.pillar] += 1
    assert pillars == {"FIN": 6, "CUS": 5, "OPS": 4, "HR": 3}


def test_metric_values_actual_and_target(db_session: Session):
    actual = db_session.scalars(
        select(MetricValue).where(MetricValue.value_kind == MetricValueKind.ACTUAL)
    ).all()
    target = db_session.scalars(
        select(MetricValue).where(MetricValue.value_kind == MetricValueKind.TARGET)
    ).all()
    assert len(actual) == 18
    assert len(target) == 18


def test_twelve_open_alerts_four_critical_eight_warning(db_session: Session):
    alerts = db_session.scalars(
        select(Alert).where(Alert.status == AlertStatus.OPEN)
    ).all()
    assert len(alerts) == 12
    crit = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
    warn = [a for a in alerts if a.severity == AlertSeverity.WARNING]
    assert len(crit) == 4
    assert len(warn) == 8


@pytest.mark.parametrize(
    ("code", "value", "color"),
    [
        ("METRIC-FIN-01", 8_500_000_000, ThresholdStatus.YELLOW),
        ("METRIC-FIN-05", 23.9, ThresholdStatus.RED),
        ("METRIC-CUS-01", 0.77, ThresholdStatus.RED),
        ("METRIC-CUS-04", 51.0, ThresholdStatus.RED),
        ("METRIC-OPS-01", 60.0, ThresholdStatus.RED),
        ("METRIC-FIN-02", 18.4, ThresholdStatus.GREEN),
        ("METRIC-CUS-03", 104.5, ThresholdStatus.GREEN),
    ],
)
def test_demo_metric_values_match_spec(
    db_session: Session, code: str, value: float, color: ThresholdStatus
):
    metric = db_session.scalars(select(Metric).where(Metric.code == code)).first()
    assert metric is not None
    mv = db_session.scalars(
        select(MetricValue).where(
            MetricValue.metric_id == metric.id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
        )
    ).first()
    assert mv is not None
    assert float(mv.value) == pytest.approx(value)
    assert mv.status_color == color
