"""Seed the 18 dashboard metrics, their SEED metric values and the 12 open alerts.

Encodes docs/2.PRODUCT/03-DASHBOARD-SPEC.md §2 (metric definitions + thresholds),
§3.2 (18 alerts) and docs/3.EXECUTION/08-DEMO-DATA-SPEC.md §5.1 (computed demo values,
company ABC, DEMO_REFERENCE_DATE 20/10/2026). Idempotent: UPSERT by natural key
(``metrics.code``) and one current ``metric_values`` row per (metric, kind, period).

Covers T-301 (migration consumers + metric/alert seed) and T-403 (demo values).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricUnit,
    MetricValueKind,
    PeriodType,
    ThresholdDirection,
    ThresholdStatus,
    ValueOrigin,
)
from app.modules.dashboard.models import Alert, Metric, MetricValue

_METRIC_NAMESPACE = uuid.UUID("b22e0000-0000-4000-8000-000000000001")
#: Fixed "computed_at" for deterministic demo (08 §5.1 reference 20/10/2026 08:30).
DEMO_COMPUTED_AT = datetime(2026, 10, 20, 8, 30, tzinfo=UTC)


def _metric_id(code: str) -> uuid.UUID:
    return uuid.uuid5(_METRIC_NAMESPACE, code)


def _value_id(code: str, kind: str, period: str) -> uuid.UUID:
    return uuid.uuid5(_METRIC_NAMESPACE, f"{code}:{kind}:{period}")


def _alert_id(code: str, period: str) -> uuid.UUID:
    return uuid.uuid5(_METRIC_NAMESPACE, f"alert:{code}:{period}")


@dataclass(frozen=True)
class MetricSeed:
    code: str
    pillar: str
    unit: MetricUnit
    direction: ThresholdDirection
    warning_threshold: float | None
    critical_threshold: float | None
    chart_type: str
    refresh_policy: str
    alert_code: str
    alert_recipient_role_codes: list[str]
    alert_suggestion_i18n_key: str
    agg_visible_role_codes: list[str]
    sort_order: int
    source_record_types: list[str]
    formula_expr: str
    threshold_rule: dict[str, Any] | None = None
    # SEED demo value (08 §5.1)
    period_type: PeriodType = PeriodType.MONTH
    period_key: str = "2026-09"
    value: float | None = None
    status_color: ThresholdStatus = ThresholdStatus.GREEN
    target_value: float | None = None
    target_period_key: str | None = None
    target_period_type: PeriodType | None = None
    breakdown: dict[str, Any] | None = None
    message_params: dict[str, Any] = field(default_factory=dict)
    alert_severity: AlertSeverity | None = None  # None => no open alert (green)


# ---------------------------------------------------------------------------
# 18 metric definitions + demo SEED values (03 §2/§3.2, 08 §5.1)
# name_i18n_key = metric.<code>.name ; formula_display i18n = metric.<code>.formula
# ---------------------------------------------------------------------------
METRICS: list[MetricSeed] = [
    # --- FIN (6) ---
    MetricSeed(
        code="METRIC-FIN-01",
        pillar="FIN",
        unit=MetricUnit.VND,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=90,
        critical_threshold=80,
        chart_type="bar",
        refresh_policy="ON_COMMIT,DAILY",
        alert_code="ALERT-FIN-01",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-01.suggestion",
        agg_visible_role_codes=[],
        sort_order=1,
        source_record_types=["INVOICE"],
        formula_expr="SUM(Invoice.amount_before_vat) / plan_month * 100",
        value=8_500_000_000,
        status_color=ThresholdStatus.YELLOW,
        target_value=9_600_000_000,
        message_params={"value": 8_500_000_000, "percent_of_plan": 88.5, "plan": 9_600_000_000},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-FIN-02",
        pillar="FIN",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=15,
        critical_threshold=10,
        chart_type="line",
        refresh_policy="ON_COMMIT",
        alert_code="ALERT-FIN-02",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-02.suggestion",
        agg_visible_role_codes=[],
        sort_order=2,
        source_record_types=["FINANCIAL_LINE"],
        formula_expr="(revenue - cogs) / revenue * 100",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q3",
        value=18.4,
        status_color=ThresholdStatus.GREEN,
        target_value=18.0,
        message_params={"value": 18.4},
    ),
    MetricSeed(
        code="METRIC-FIN-03",
        pillar="FIN",
        unit=MetricUnit.MONTHS,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=9,
        critical_threshold=6,
        chart_type="gauge",
        refresh_policy="ON_COMMIT,WEEKLY",
        alert_code="ALERT-FIN-03",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-03.suggestion",
        agg_visible_role_codes=[],
        sort_order=3,
        source_record_types=["FINANCIAL_LINE"],
        formula_expr="cash_end_of_period / avg_net_cash_outflow_3m",
        value=8.0,
        status_color=ThresholdStatus.YELLOW,
        target_value=9.0,
        message_params={"value": 8.0},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-FIN-04",
        pillar="FIN",
        unit=MetricUnit.DAYS,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=45,
        critical_threshold=60,
        chart_type="line",
        refresh_policy="DAILY",
        alert_code="ALERT-FIN-04",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-04.suggestion",
        agg_visible_role_codes=[],
        sort_order=4,
        source_record_types=["INVOICE"],
        formula_expr="receivables / revenue * 90",
        value=47.8,
        status_color=ThresholdStatus.YELLOW,
        target_value=40,
        message_params={"value": 47.8},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-FIN-05",
        pillar="FIN",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=10,
        critical_threshold=20,
        chart_type="stacked_bar",
        refresh_policy="DAILY",
        alert_code="ALERT-FIN-05",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-05.suggestion",
        agg_visible_role_codes=[],
        sort_order=5,
        source_record_types=["INVOICE"],
        formula_expr="overdue_amount / total_receivable * 100",
        threshold_rule={"critical_if": "has_bucket_over_90_days"},
        value=23.9,
        status_color=ThresholdStatus.RED,
        target_value=10,
        message_params={"value": 23.9, "amount": 1_306_000_000},
        alert_severity=AlertSeverity.CRITICAL,
    ),
    MetricSeed(
        code="METRIC-FIN-06",
        pillar="FIN",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=5,
        critical_threshold=10,
        chart_type="bar",
        refresh_policy="ON_COMMIT,MONTHLY",
        alert_code="ALERT-FIN-06",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-FIN-06.suggestion",
        agg_visible_role_codes=[],
        sort_order=6,
        source_record_types=["BUDGET_LINE"],
        formula_expr="(actual_opex - budget_opex) / budget_opex * 100",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q3",
        value=7.9,
        status_color=ThresholdStatus.YELLOW,
        target_value=5,
        message_params={"value": 7.9, "amount": 250_000_000},
        alert_severity=AlertSeverity.WARNING,
    ),
    # --- CUS (5) ---
    MetricSeed(
        code="METRIC-CUS-01",
        pillar="CUS",
        unit=MetricUnit.RATIO,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=3.0,
        critical_threshold=2.0,
        chart_type="funnel",
        refresh_policy="ON_COMMIT,WEEKLY",
        alert_code="ALERT-CUS-01",
        alert_recipient_role_codes=["ROLE-01", "ROLE-03"],
        alert_suggestion_i18n_key="alert.ALERT-CUS-01.suggestion",
        agg_visible_role_codes=[],
        sort_order=1,
        source_record_types=["OPPORTUNITY"],
        formula_expr="SUM(value*probability open, close in Q) / (quota_Q - revenue_Q)",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q4",
        value=0.77,
        status_color=ThresholdStatus.RED,
        target_value=3.0,
        message_params={"value": 0.77},
        alert_severity=AlertSeverity.CRITICAL,
    ),
    MetricSeed(
        code="METRIC-CUS-02",
        pillar="CUS",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=25,
        critical_threshold=15,
        chart_type="line",
        refresh_policy="ON_COMMIT,WEEKLY",
        alert_code="ALERT-CUS-02",
        alert_recipient_role_codes=["ROLE-01", "ROLE-03"],
        alert_suggestion_i18n_key="alert.ALERT-CUS-02.suggestion",
        agg_visible_role_codes=[],
        sort_order=2,
        source_record_types=["OPPORTUNITY"],
        formula_expr="COUNT(WON) / COUNT(WON+LOST) * 100",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q3",
        value=24.0,
        status_color=ThresholdStatus.YELLOW,
        target_value=25,
        message_params={"value": 24.0},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-CUS-03",
        pillar="CUS",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=100,
        critical_threshold=90,
        chart_type="line",
        refresh_policy="MONTHLY",
        alert_code="ALERT-CUS-03",
        alert_recipient_role_codes=["ROLE-01", "ROLE-03"],
        alert_suggestion_i18n_key="alert.ALERT-CUS-03.suggestion",
        agg_visible_role_codes=[],
        sort_order=3,
        source_record_types=["INVOICE", "CUSTOMER"],
        formula_expr="revenue_this_period_existing / revenue_base_period * 100",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q3",
        value=104.5,
        status_color=ThresholdStatus.GREEN,
        target_value=100,
        message_params={"value": 104.5},
    ),
    MetricSeed(
        code="METRIC-CUS-04",
        pillar="CUS",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=40,
        critical_threshold=50,
        chart_type="pareto",
        refresh_policy="ON_COMMIT,MONTHLY",
        alert_code="ALERT-CUS-04",
        alert_recipient_role_codes=["ROLE-01", "ROLE-03"],
        alert_suggestion_i18n_key="alert.ALERT-CUS-04.suggestion",
        agg_visible_role_codes=[],
        sort_order=4,
        source_record_types=["INVOICE", "CUSTOMER"],
        formula_expr="SUM(top5_revenue) / total_revenue * 100 (rolling 12m)",
        threshold_rule={
            "warning_if_single_customer_over": 15,
            "critical_if_single_customer_over": 25,
        },
        period_type=PeriodType.ROLLING_12M,
        period_key="2025-10_2026-09",
        value=51.0,
        status_color=ThresholdStatus.RED,
        target_value=40,
        message_params={"value": 51.0},
        alert_severity=AlertSeverity.CRITICAL,
    ),
    MetricSeed(
        code="METRIC-CUS-05",
        pillar="CUS",
        unit=MetricUnit.SCORE,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=30,
        critical_threshold=0,
        chart_type="gauge",
        refresh_policy="MONTHLY",
        alert_code="ALERT-CUS-05",
        alert_recipient_role_codes=["ROLE-01", "ROLE-03"],
        alert_suggestion_i18n_key="alert.ALERT-CUS-05.suggestion",
        agg_visible_role_codes=[],
        sort_order=5,
        source_record_types=["SURVEY_RESPONSE"],
        formula_expr="pct_promoter - pct_detractor",
        period_type=PeriodType.QUARTER,
        period_key="2026-Q3",
        value=32,
        status_color=ThresholdStatus.GREEN,
        target_value=30,
        message_params={"value": 32},
    ),
    # --- OPS (4) ---
    MetricSeed(
        code="METRIC-OPS-01",
        pillar="OPS",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=85,
        critical_threshold=70,
        chart_type="line",
        refresh_policy="ON_COMMIT,DAILY",
        alert_code="ALERT-OPS-01",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-OPS-01.suggestion",
        agg_visible_role_codes=[],
        sort_order=1,
        source_record_types=["TASK"],
        formula_expr="COUNT(done on time) / COUNT(task with due_date) * 100",
        value=60.0,
        status_color=ThresholdStatus.RED,
        target_value=85,
        message_params={"value": 60.0},
        alert_severity=AlertSeverity.CRITICAL,
    ),
    MetricSeed(
        code="METRIC-OPS-02",
        pillar="OPS",
        unit=MetricUnit.COUNT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=1,
        critical_threshold=3,
        chart_type="bar",
        refresh_policy="DAILY",
        alert_code="ALERT-OPS-02",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-OPS-02.suggestion",
        agg_visible_role_codes=[],
        sort_order=2,
        source_record_types=["PROJECT"],
        formula_expr="COUNT(Project open AND late milestone)",
        threshold_rule={"critical_if_project_late_over_days": 30},
        value=2,
        status_color=ThresholdStatus.YELLOW,
        target_value=1,
        message_params={"value": 2},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-OPS-03",
        pillar="OPS",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=80,
        critical_threshold=60,
        chart_type="gauge",
        refresh_policy="ON_COMMIT,DAILY",
        alert_code="ALERT-OPS-03",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-OPS-03.suggestion",
        agg_visible_role_codes=[],
        sort_order=3,
        source_record_types=["DECISION"],
        formula_expr="COUNT(decision done on time) / COUNT(decision due) * 100",
        value=66.7,
        status_color=ThresholdStatus.YELLOW,
        target_value=80,
        message_params={"value": 66.7},
        alert_severity=AlertSeverity.WARNING,
    ),
    MetricSeed(
        code="METRIC-OPS-04",
        pillar="OPS",
        unit=MetricUnit.TASKS_PER_PERSON,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=6,
        critical_threshold=8,
        chart_type="bar",
        refresh_policy="DAILY",
        alert_code="ALERT-OPS-04",
        alert_recipient_role_codes=["ROLE-01", "ROLE-02"],
        alert_suggestion_i18n_key="alert.ALERT-OPS-04.suggestion",
        agg_visible_role_codes=[],
        sort_order=4,
        source_record_types=["TASK"],
        formula_expr="COUNT(open task) / COUNT(DISTINCT assignee)",
        threshold_rule={"warning_if_people_over_8": 1, "critical_if_people_over_8": 3},
        value=5.4,
        status_color=ThresholdStatus.YELLOW,
        target_value=6,
        message_params={"value": 5.4, "overloaded_people": 2},
        alert_severity=AlertSeverity.WARNING,
    ),
    # --- HR (3) ---
    MetricSeed(
        code="METRIC-HR-01",
        pillar="HR",
        unit=MetricUnit.VND_PER_PERSON,
        direction=ThresholdDirection.LOWER_IS_BAD,
        warning_threshold=2_000_000_000,
        critical_threshold=1_700_000_000,
        chart_type="line",
        refresh_policy="ON_COMMIT,MONTHLY",
        alert_code="ALERT-HR-01",
        alert_recipient_role_codes=["ROLE-01", "ROLE-04"],
        alert_suggestion_i18n_key="alert.ALERT-HR-01.suggestion",
        agg_visible_role_codes=[],
        sort_order=1,
        source_record_types=["INVOICE", "EMPLOYEE"],
        formula_expr="revenue_rolling_12m / avg_headcount",
        period_type=PeriodType.ROLLING_12M,
        period_key="2025-10_2026-09",
        value=2_180_000_000,
        status_color=ThresholdStatus.GREEN,
        target_value=2_000_000_000,
        message_params={"value": 2_180_000_000},
    ),
    MetricSeed(
        code="METRIC-HR-02",
        pillar="HR",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=15,
        critical_threshold=25,
        chart_type="line",
        refresh_policy="ON_COMMIT,MONTHLY",
        alert_code="ALERT-HR-02",
        alert_recipient_role_codes=["ROLE-01", "ROLE-04"],
        alert_suggestion_i18n_key="alert.ALERT-HR-02.suggestion",
        agg_visible_role_codes=[],
        sort_order=2,
        source_record_types=["EMPLOYEE"],
        formula_expr="COUNT(terminated 12m) / avg_headcount_12m * 100",
        period_type=PeriodType.ROLLING_12M,
        period_key="2025-10_2026-09",
        value=13.3,
        status_color=ThresholdStatus.GREEN,
        target_value=15,
        message_params={"value": 13.3},
    ),
    MetricSeed(
        code="METRIC-HR-03",
        pillar="HR",
        unit=MetricUnit.PERCENT,
        direction=ThresholdDirection.HIGHER_IS_BAD,
        warning_threshold=10,
        critical_threshold=20,
        chart_type="gauge",
        refresh_policy="DAILY",
        alert_code="ALERT-HR-03",
        alert_recipient_role_codes=["ROLE-01", "ROLE-04"],
        alert_suggestion_i18n_key="alert.ALERT-HR-03.suggestion",
        agg_visible_role_codes=[],
        sort_order=3,
        source_record_types=["TASK", "EMPLOYEE"],
        formula_expr="COUNT(employee overloaded) / COUNT(active employee) * 100",
        value=8.9,
        status_color=ThresholdStatus.GREEN,
        target_value=10,
        message_params={"value": 8.9},
    ),
]


@dataclass(frozen=True)
class DashboardSeedResult:
    metrics: int
    values: int
    alerts: int


def seed_dashboard(db: Session) -> DashboardSeedResult:
    """Idempotently seed metrics, SEED metric values and open alerts."""
    metrics_count = 0
    values_count = 0
    alerts_count = 0

    for m in METRICS:
        mid = _metric_id(m.code)
        existing = db.get(Metric, mid)
        if existing is None:
            db.add(
                Metric(
                    id=mid,
                    code=m.code,
                    pillar=m.pillar,
                    name_i18n_key=f"metric.{m.code}.name",
                    formula_display=f"metric.{m.code}.formula",
                    formula_expr=m.formula_expr,
                    source_record_types=m.source_record_types,
                    unit=m.unit,
                    direction=m.direction,
                    warning_threshold=m.warning_threshold,
                    critical_threshold=m.critical_threshold,
                    threshold_rule=m.threshold_rule,
                    chart_type=m.chart_type,
                    refresh_policy=m.refresh_policy,
                    alert_code=m.alert_code,
                    alert_recipient_role_codes=m.alert_recipient_role_codes,
                    alert_suggestion_i18n_key=m.alert_suggestion_i18n_key,
                    agg_visible_role_codes=m.agg_visible_role_codes,
                    sort_order=m.sort_order,
                )
            )
            metrics_count += 1
        else:
            existing.pillar = m.pillar
            existing.unit = m.unit
            existing.direction = m.direction
            existing.warning_threshold = m.warning_threshold
            existing.critical_threshold = m.critical_threshold
            existing.threshold_rule = m.threshold_rule
            existing.chart_type = m.chart_type
            existing.refresh_policy = m.refresh_policy
            existing.alert_recipient_role_codes = m.alert_recipient_role_codes
            existing.agg_visible_role_codes = m.agg_visible_role_codes
            existing.sort_order = m.sort_order
            existing.source_record_types = m.source_record_types
            existing.formula_expr = m.formula_expr

        # ACTUAL value
        if m.value is not None:
            av_id = _value_id(m.code, "ACTUAL", m.period_key)
            if db.get(MetricValue, av_id) is None:
                db.add(
                    MetricValue(
                        id=av_id,
                        metric_id=mid,
                        value_kind=MetricValueKind.ACTUAL,
                        period_type=m.period_type,
                        period_key=m.period_key,
                        value=m.value,
                        breakdown=m.breakdown,
                        computation=ValueOrigin.SEED,
                        source_record_ids=[],
                        source_document_ids=[],
                        status_color=m.status_color,
                        is_current=True,
                        computed_at=DEMO_COMPUTED_AT,
                        computed_by_action="seed",
                    )
                )
                values_count += 1

        # TARGET value
        if m.target_value is not None:
            tkey = m.target_period_key or m.period_key
            tptype = m.target_period_type or m.period_type
            tv_id = _value_id(m.code, "TARGET", tkey)
            if db.get(MetricValue, tv_id) is None:
                db.add(
                    MetricValue(
                        id=tv_id,
                        metric_id=mid,
                        value_kind=MetricValueKind.TARGET,
                        period_type=tptype,
                        period_key=tkey,
                        value=m.target_value,
                        computation=ValueOrigin.SEED,
                        source_record_ids=[],
                        source_document_ids=[],
                        status_color=None,
                        is_current=True,
                        computed_at=DEMO_COMPUTED_AT,
                        computed_by_action="seed",
                    )
                )
                values_count += 1

    # Flush metrics + values before alerts so the metric_value FK resolves.
    db.flush()

    for m in METRICS:
        # Open alert (12 of 18 metrics breach a threshold)
        if m.alert_severity is not None and m.value is not None:
            a_id = _alert_id(m.alert_code, m.period_key)
            if db.get(Alert, a_id) is None:
                db.add(
                    Alert(
                        id=a_id,
                        metric_id=_metric_id(m.code),
                        metric_value_id=_value_id(m.code, "ACTUAL", m.period_key),
                        period_key=m.period_key,
                        severity=m.alert_severity,
                        status=AlertStatus.OPEN,
                        message_params=m.message_params,
                        suggestion_level="L1",
                        triggered_at=DEMO_COMPUTED_AT,
                    )
                )
                alerts_count += 1

    return DashboardSeedResult(metrics_count, values_count, alerts_count)
