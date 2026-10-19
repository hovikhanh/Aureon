"""Alert services: EP-15 list, EP-16 acknowledge, EP-17 dismiss (10 §4)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.enums import ActorType
from app.modules.audit.service import record_audit
from app.modules.auth.models import User
from app.modules.dashboard.enums import AlertStatus
from app.modules.dashboard.models import Alert, Metric
from app.modules.dashboard.schemas import AlertOut
from app.modules.dashboard.scoping import can_act_alert_pillar, receives_alert_pillar
from app.modules.dashboard.service import build_alert_out


def list_alerts(
    db: Session,
    user: User,
    status_filter: str | None,
    severity_filter: str | None,
    offset: int,
    limit: int,
) -> tuple[list[AlertOut], int]:
    """EP-15: alerts in the role's receiving pillars."""
    role_code = user.role.code
    stmt = (
        select(Alert).join(Metric, Alert.metric_id == Metric.id).where(Alert.deleted_at.is_(None))
    )
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if severity_filter:
        stmt = stmt.where(Alert.severity == severity_filter)
    stmt = stmt.order_by(Alert.triggered_at.desc())
    alerts = [a for a in db.scalars(stmt) if receives_alert_pillar(role_code, a.metric.pillar)]
    total = len(alerts)
    page = alerts[offset : offset + limit]
    return [
        build_alert_out(db, a, can_acknowledge=can_act_alert_pillar(role_code, a.metric.pillar))
        for a in page
    ], total


def _get_alert_for_action(db: Session, user: User, alert_id: UUID) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None or alert.deleted_at is not None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Alert {alert_id} not found")
    metric = alert.metric if alert.metric is not None else db.get(Metric, alert.metric_id)
    if metric is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Metric for alert {alert_id} not found")
    if not can_act_alert_pillar(user.role.code, metric.pillar):
        raise ApiError(
            ErrorCode.FORBIDDEN_SCOPE,
            f"Role {user.role.code} cannot act on {metric.pillar} alerts",
        )
    return alert


def acknowledge_alert(db: Session, user: User, alert_id: UUID, note: str | None) -> AlertOut:
    """EP-16: acknowledge an OPEN alert."""
    alert = _get_alert_for_action(db, user, alert_id)
    if alert.status != AlertStatus.OPEN:
        raise ApiError(ErrorCode.CONFLICT_STATE, "Alert is not OPEN")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by_id = user.id
    alert.acknowledged_at = datetime.now(UTC)
    record_audit(
        db,
        action="alert.acknowledge",
        target_type="alert",
        target_id=alert.id,
        actor_type=ActorType.USER,
        actor_user_id=user.id,
        actor_role_id=user.role_id,
        metadata={"note": note} if note else None,
    )
    db.flush()
    return build_alert_out(
        db, alert, can_acknowledge=can_act_alert_pillar(user.role.code, alert.metric.pillar)
    )


def dismiss_alert(db: Session, user: User, alert_id: UUID, reason: str) -> AlertOut:
    """EP-17: dismiss an alert (not RESOLVED/DISMISSED already)."""
    alert = _get_alert_for_action(db, user, alert_id)
    if alert.status in (AlertStatus.RESOLVED, AlertStatus.DISMISSED):
        raise ApiError(ErrorCode.CONFLICT_STATE, "Alert already closed")
    alert.status = AlertStatus.DISMISSED
    alert.dismissed_by_id = user.id
    alert.dismissed_at = datetime.now(UTC)
    record_audit(
        db,
        action="alert.dismiss",
        target_type="alert",
        target_id=alert.id,
        actor_type=ActorType.USER,
        actor_user_id=user.id,
        actor_role_id=user.role_id,
        metadata={"reason": reason},
    )
    db.flush()
    return build_alert_out(
        db, alert, can_acknowledge=can_act_alert_pillar(user.role.code, alert.metric.pillar)
    )
