"""Dashboard service: read current metric values + alerts, apply role scope (10 §4).

Reads precomputed values (``is_current = true``) per 02 §5.2 R8 — no recompute on read.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.modules.auth.models import User
from app.modules.dashboard.enums import (
    AlertSeverity,
    AlertStatus,
    MetricValueKind,
    ThresholdStatus,
)
from app.modules.dashboard.models import Alert, Metric, MetricValue
from app.modules.dashboard.schemas import (
    AlertOut,
    DashboardOut,
    GreetingOut,
    MetricValueOut,
    PillarOut,
    SummaryOut,
)
from app.modules.dashboard.scoping import (
    AccessLevel,
    metric_access,
    receives_alert_pillar,
    visible_metric_codes,
    visible_pillars,
)

_SEVERITY_ORDER = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1}
_HEALTH_ORDER = {ThresholdStatus.RED: 0, ThresholdStatus.YELLOW: 1, ThresholdStatus.GREEN: 2}


def _current_actual(db: Session, metric_id: UUID, period_key: str | None) -> MetricValue | None:
    stmt = (
        select(MetricValue)
        .where(
            MetricValue.metric_id == metric_id,
            MetricValue.value_kind == MetricValueKind.ACTUAL,
            MetricValue.is_current.is_(True),
            MetricValue.deleted_at.is_(None),
        )
        .order_by(MetricValue.computed_at.desc())
    )
    if period_key:
        stmt = stmt.where(MetricValue.period_key == period_key)
    return db.scalars(stmt).first()


def _current_target(db: Session, metric_id: UUID, period_key: str) -> MetricValue | None:
    stmt = select(MetricValue).where(
        MetricValue.metric_id == metric_id,
        MetricValue.value_kind == MetricValueKind.TARGET,
        MetricValue.is_current.is_(True),
        MetricValue.deleted_at.is_(None),
        MetricValue.period_key == period_key,
    )
    return db.scalars(stmt).first()


def _percent_of_target(value: float | None, target: float | None) -> float | None:
    if value is None or target in (None, 0):
        return None
    return round(float(value) / float(target) * 100, 1)


def build_metric_value_out(
    db: Session,
    metric: Metric,
    access: AccessLevel,
    period_key: str | None,
) -> MetricValueOut | None:
    """Serialize a metric's current ACTUAL value for a role at an access level."""
    actual = _current_actual(db, metric.id, period_key)
    if actual is None:
        return None
    target = _current_target(db, metric.id, actual.period_key)
    target_value = float(target.value) if target and target.value is not None else None
    value = float(actual.value) if actual.value is not None else None
    return MetricValueOut(
        metric_code=metric.code,
        pillar=metric.pillar,
        name_i18n_key=metric.name_i18n_key,
        unit=metric.unit,
        value_kind=MetricValueKind.ACTUAL,
        period_key=actual.period_key,
        period_type=actual.period_type.value,
        value=value,
        target_value=target_value,
        percent_of_target=_percent_of_target(value, target_value),
        status_color=actual.status_color,
        chart_type=metric.chart_type,
        computed_at=actual.computed_at,
        computation=actual.computation.value,
        access_level=access,
        sort_order=metric.sort_order,
    )


def build_alert_out(db: Session, alert: Alert) -> AlertOut:
    metric = alert.metric if alert.metric is not None else db.get(Metric, alert.metric_id)
    if metric is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Metric for alert {alert.id} not found")
    return AlertOut(
        id=alert.id,
        alert_code=metric.alert_code,
        metric_code=metric.code,
        pillar=metric.pillar,
        severity=alert.severity,
        status=alert.status,
        message_i18n_key=f"alert.{metric.alert_code}.message",
        message_params=alert.message_params or {},
        suggestion_i18n_key=metric.alert_suggestion_i18n_key,
        suggestion_level=alert.suggestion_level,
        period_key=alert.period_key,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        dismissed_at=alert.dismissed_at,
    )


def _open_alerts_for_role(db: Session, role_code: str) -> list[Alert]:
    """Open/acknowledged alerts whose pillar the role receives (02 §3.3)."""
    stmt = (
        select(Alert)
        .join(Metric, Alert.metric_id == Metric.id)
        .where(
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            Alert.deleted_at.is_(None),
        )
    )
    alerts = list(db.scalars(stmt))
    return [a for a in alerts if receives_alert_pillar(role_code, a.metric.pillar)]


def build_dashboard(db: Session, user: User, period_key: str | None) -> DashboardOut:
    """EP-10: role-scoped dashboard with pillars, headline metrics, top alerts, AI summary."""
    role_code = user.role.code
    scope = visible_metric_codes(role_code)
    if not scope:
        raise ApiError(ErrorCode.FORBIDDEN_ROLE, "This role has no dashboard")

    metrics = {m.code: m for m in db.scalars(select(Metric).where(Metric.deleted_at.is_(None)))}

    # Build pillar blocks
    open_alerts = _open_alerts_for_role(db, role_code)
    alerts_by_pillar: dict[str, list[Alert]] = {}
    for a in open_alerts:
        alerts_by_pillar.setdefault(a.metric.pillar, []).append(a)

    pillars: list[PillarOut] = []
    for pillar in visible_pillars(role_code):
        pillar_metrics: list[MetricValueOut] = []
        pillar_access: AccessLevel = "AGG"
        for code, metric in sorted(metrics.items(), key=lambda kv: kv[1].sort_order):
            if metric.pillar != pillar:
                continue
            access = metric_access(role_code, code)
            if access is None:
                continue
            if access == "FULL":
                pillar_access = "FULL"
            mv = build_metric_value_out(db, metric, access, period_key)
            if mv is not None:
                pillar_metrics.append(mv)
        if not pillar_metrics:
            continue
        pillar_alerts = alerts_by_pillar.get(pillar, [])
        health = min(
            (m.status_color for m in pillar_metrics if m.status_color is not None),
            key=lambda c: _HEALTH_ORDER[c],
            default=ThresholdStatus.GREEN,
        )
        headline = min(pillar_metrics, key=lambda m: m.sort_order)
        pillars.append(
            PillarOut(
                pillar=pillar,
                access_level=pillar_access,
                health_color=health,
                open_alert_count=len(pillar_alerts),
                headline_metric=headline,
                metrics=pillar_metrics,
            )
        )

    # Top alerts (<= 5, Critical first, then most recent)
    sorted_alerts = sorted(
        open_alerts,
        key=lambda a: (_SEVERITY_ORDER.get(a.severity, 9), -a.triggered_at.timestamp()),
    )
    alerts_top = [build_alert_out(db, a) for a in sorted_alerts[:5]]

    # AI summary (template from top alert, no LLM — 10 OQ-09)
    summary = _build_summary(role_code, sorted_alerts, metrics)

    return DashboardOut(
        role_code=role_code,
        greeting=GreetingOut(full_name=user.full_name, salutation=user.salutation),
        summary=summary,
        pillars=pillars,
        alerts_top=alerts_top,
    )


def _build_summary(role_code: str, alerts: list[Alert], metrics: dict[str, Metric]) -> SummaryOut:
    critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
    warning = [a for a in alerts if a.severity == AlertSeverity.WARNING]
    if critical:
        top = critical[0]
        params = {
            "critical_count": len(critical),
            "warning_count": len(warning),
            "top_metric_code": top.metric.code,
            **{k: v for k, v in (top.message_params or {}).items()},
        }
        return SummaryOut(i18n_key="dashboard.summary.has_critical", params=params)
    if warning:
        return SummaryOut(
            i18n_key="dashboard.summary.has_warning",
            params={"warning_count": len(warning)},
        )
    return SummaryOut(i18n_key="dashboard.summary.all_green", params={})


def list_metrics(
    db: Session, user: User, pillar: str | None, period_key: str | None
) -> list[MetricValueOut]:
    """EP-11: flat list of in-scope metric values, optionally filtered by pillar."""
    role_code = user.role.code
    scope = visible_metric_codes(role_code)
    if not scope:
        raise ApiError(ErrorCode.FORBIDDEN_ROLE, "This role has no dashboard")
    if pillar is not None and pillar not in ("FIN", "CUS", "OPS", "HR"):
        raise ApiError(ErrorCode.BAD_REQUEST, f"Invalid pillar: {pillar}")

    metrics = db.scalars(
        select(Metric).where(Metric.deleted_at.is_(None)).order_by(Metric.sort_order)
    )
    out: list[MetricValueOut] = []
    for metric in metrics:
        access = metric_access(role_code, metric.code)
        if access is None:
            continue
        if pillar is not None and metric.pillar != pillar:
            continue
        mv = build_metric_value_out(db, metric, access, period_key)
        if mv is not None:
            out.append(mv)
    return out
