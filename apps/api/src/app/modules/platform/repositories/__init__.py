"""Repositories of `platform` — used only inside this module (DEC-125)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, record_audit
from app.core.base_repository import BaseRepository
from app.core.tenant import require_tenant
from app.modules.platform.models import (
    Alert,
    ApprovalRequest,
    ApprovalRule,
    AuditLog,
    DataLineage,
    Metric,
    MetricValue,
    Notification,
    NotificationPreference,
    OutboxEvent,
    ProcessedEvent,
)

DeadLetterRow = tuple[ProcessedEvent, OutboxEvent]


class DeadLetterRepository:
    """DLQ = `processed_events.status = 'DLQ'` (10 §8.2 E4), joined to the outbox row.

    Tenant-scoped through `outbox_events.tenant_id` (05 §2.3, R-DEC-21): an admin only sees /
    replays dead letters of the current tenant.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base(self) -> Any:
        return (
            select(ProcessedEvent, OutboxEvent)
            .join(OutboxEvent, OutboxEvent.id == ProcessedEvent.event_id)
            .where(ProcessedEvent.status == "DLQ", OutboxEvent.tenant_id == require_tenant())
        )

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        consumer: str | None = None,
        event_type: str | None = None,
    ) -> tuple[Sequence[DeadLetterRow], int]:
        stmt = self._base()
        if consumer:
            stmt = stmt.where(ProcessedEvent.consumer == consumer)
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
        total = int(
            (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        )
        stmt = stmt.order_by(ProcessedEvent.processed_at.desc(), ProcessedEvent.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).all()
        return [(p, o) for p, o in rows], total

    async def get(self, id_: uuid.UUID) -> DeadLetterRow | None:
        row = (await self.db.execute(self._base().where(ProcessedEvent.id == id_))).first()
        return None if row is None else (row[0], row[1])

    async def dlq_count(self) -> int:
        stmt = select(func.count()).select_from(self._base().subquery())
        return int((await self.db.execute(stmt)).scalar_one())


class AuditRepository:
    """Append-only: `create` + `list` only — no update/delete by design (T-012 / brief T-007)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        action: str,
        target_schema: str | None = None,
        target_table: str | None = None,
        target_id: uuid.UUID | None = None,
        before: Any = None,
        after: Any = None,
        why: str | None = None,
        metadata: dict[str, Any] | None = None,
        actor: Actor | None = None,
    ) -> AuditLog:
        audit_id = await record_audit(
            self.db,
            action=action,
            target_schema=target_schema,
            target_table=target_table,
            target_id=target_id,
            before=before,
            after=after,
            why=why,
            metadata=metadata,
            actor=actor,
        )
        return (await self.db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one()

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        action: str | None = None,
        target_table: str | None = None,
        target_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        actor_type: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = select(AuditLog)
        if actor_type:
            stmt = stmt.where(AuditLog.actor_type == actor_type)
        if occurred_from is not None:
            stmt = stmt.where(AuditLog.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(AuditLog.occurred_at <= occurred_to)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if target_table:
            stmt = stmt.where(AuditLog.target_table == target_table)
        if target_id:
            stmt = stmt.where(AuditLog.target_id == target_id)
        if actor_user_id:
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        total = int(
            (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        )
        stmt = stmt.order_by(AuditLog.occurred_at.desc(), AuditLog.id).limit(limit).offset(offset)
        return (await self.db.execute(stmt)).scalars().all(), total


class ApprovalRequestRepository(BaseRepository[ApprovalRequest]):
    model = ApprovalRequest

    async def locked(self, request_id: uuid.UUID) -> ApprovalRequest | None:
        stmt = self._scoped(select(ApprovalRequest)).where(ApprovalRequest.id == request_id)
        return (await self.db.execute(stmt.with_for_update())).scalar_one_or_none()

    async def pending_for(self, target_kind: str, target_id: uuid.UUID) -> ApprovalRequest | None:
        stmt = self._live().where(
            ApprovalRequest.target_kind == target_kind, ApprovalRequest.target_id == target_id,
            ApprovalRequest.status == "PENDING",
        )  # fmt: skip
        return (await self.db.execute(stmt.limit(1))).scalars().first()

    async def where_one(self, *clauses: ColumnElement[bool]) -> ApprovalRequest | None:
        stmt = self._live().where(*clauses)
        return (await self.db.execute(stmt.limit(1))).scalars().first()

    async def count_where(self, *clauses: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(ApprovalRequest).where(*clauses)
        stmt = self._scoped(stmt).where(ApprovalRequest.deleted_at.is_(None))
        return int((await self.db.execute(stmt)).scalar_one())


class ApprovalRuleRepository(BaseRepository[ApprovalRule]):
    """Global config catalog (not tenant-scoped)."""

    model = ApprovalRule

    async def by_code(self, code: str) -> ApprovalRule | None:
        stmt = select(ApprovalRule).where(ApprovalRule.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_ids(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, ApprovalRule]:
        if not ids:
            return {}
        rows = await self.db.execute(select(ApprovalRule).where(ApprovalRule.id.in_(ids)))
        return {r.id: r for r in rows.scalars()}

    async def all_rules(self) -> Sequence[ApprovalRule]:
        return (await self.db.execute(select(ApprovalRule))).scalars().all()


class MetricValueRepository(BaseRepository[MetricValue]):
    """ENT-MetricValue (tenant-scoped) joined with the global `Metric` catalog."""

    model = MetricValue

    def joined(self, *cols: Any) -> Select[Any]:
        """`SELECT cols FROM metric_values JOIN metrics` scoped to the current tenant."""
        stmt = (
            select(*cols).select_from(MetricValue).join(Metric, MetricValue.metric_id == Metric.id)
        )
        return self._scoped(stmt)

    async def rows(self, stmt: Select[Any]) -> Sequence[Any]:
        return list((await self.db.execute(stmt)).all())

    async def lineage_count(self, *where: ColumnElement[bool]) -> int:
        stmt = self.joined(func.count(DataLineage.id)).join(
            DataLineage, DataLineage.metric_value_id == MetricValue.id
        )
        return int((await self.db.execute(stmt.where(*where))).scalar_one())

    async def retire_current(self, *where: ColumnElement[bool]) -> None:
        stmt = update(MetricValue).where(
            MetricValue.tenant_id == require_tenant(), MetricValue.is_current.is_(True), *where
        )
        await self.db.execute(stmt.values(is_current=False))


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    def with_metric(self) -> Select[Alert, Metric, MetricValue]:
        stmt = self._scoped(
            select(Alert, Metric, MetricValue)
            .join(Metric, Alert.metric_id == Metric.id)
            .join(MetricValue, Alert.metric_value_id == MetricValue.id)
            .where(Alert.deleted_at.is_(None))
        )
        return stmt

    async def page(self, stmt: Select[Any], order: Sequence[Any], *, limit: int, offset: int
                   ) -> tuple[Sequence[Any], int]:  # fmt: skip
        count = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(count)).scalar_one())
        rows = await self.db.execute(stmt.order_by(*order).limit(limit).offset(offset))
        return rows.all(), total

    async def first(self, stmt: Select[Any]) -> Any:
        return (await self.db.execute(stmt)).first()

    async def open_count_by_pillar(self, pillars: set[str]) -> Sequence[Any]:
        stmt = self._scoped(
            select(Metric.pillar, func.count(Alert.id))
            .join(Metric, Alert.metric_id == Metric.id)
            .where(Alert.deleted_at.is_(None), Alert.status.in_(("OPEN", "ACKNOWLEDGED")),
                   Metric.pillar.in_(pillars))
            .group_by(Metric.pillar)
        )  # fmt: skip
        return (await self.db.execute(stmt)).all()

    async def open_for(self, metric_id: uuid.UUID, period_key: str) -> Alert | None:
        stmt = self._live().where(
            Alert.metric_id == metric_id, Alert.period_key == period_key,
            Alert.status.in_(("OPEN", "ACKNOWLEDGED")),
        )  # fmt: skip
        return (await self.db.execute(stmt)).scalar_one_or_none()


class NotificationRepository:
    """EP-NTF (R-DEC-31): every query is pinned to `recipient_id` + current tenant."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _mine(self, user_id: uuid.UUID) -> Select[Notification]:
        return select(Notification).where(
            Notification.recipient_id == user_id, Notification.tenant_id == require_tenant()
        )

    async def page(
        self, user_id: uuid.UUID, *, unread_only: bool, kind: str | None, limit: int, offset: int
    ) -> tuple[Sequence[Notification], int, int]:
        stmt = self._mine(user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        if kind:
            stmt = stmt.where(Notification.kind == kind)
        total = int(await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        unread_q = self._mine(user_id).where(Notification.read_at.is_(None)).subquery()
        unread = int(await self.db.scalar(select(func.count()).select_from(unread_q)) or 0)
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id)
        rows = (await self.db.execute(stmt.limit(limit).offset(offset))).scalars().all()
        return rows, total, unread

    async def mine(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        stmt = self._mine(user_id).where(Notification.id == notification_id).with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def read_all(self, user_id: uuid.UUID, up_to: datetime, at: datetime) -> int:
        res = await self.db.execute(
            update(Notification)
            .where(Notification.recipient_id == user_id,
                   Notification.tenant_id == require_tenant(),
                   Notification.read_at.is_(None), Notification.created_at <= up_to)
            .values(read_at=at)
        )  # fmt: skip
        return int(getattr(res, "rowcount", 0) or 0)

    # ---------- e-mail channel (T-616b) ----------
    async def claim_email(self, notification_id: uuid.UUID) -> Notification | None:
        """Lock one row of the current tenant; a row held by another worker → `None`."""
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id, Notification.tenant_id == require_tenant())
            .with_for_update(skip_locked=True)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def pending_email(self, stale_before: datetime, *, limit: int) -> list[uuid.UUID]:
        """New PENDING rows, plus retried ones stuck since `stale_before` (worker died)."""
        stmt = (
            select(Notification.id)
            .where(Notification.tenant_id == require_tenant(),
                   Notification.email_status == "PENDING",
                   (Notification.email_attempts == 0) | (Notification.created_at <= stale_before))
            .order_by(Notification.created_at)
            .limit(limit)
        )  # fmt: skip
        return list((await self.db.execute(stmt)).scalars().all())


class NotificationPreferenceRepository(BaseRepository[NotificationPreference]):
    model = NotificationPreference

    async def of_user(self, user_id: uuid.UUID) -> dict[str, NotificationPreference]:
        stmt = self._scoped(select(NotificationPreference)).where(
            NotificationPreference.user_id == user_id
        )
        return {p.kind: p for p in (await self.db.execute(stmt)).scalars().all()}
