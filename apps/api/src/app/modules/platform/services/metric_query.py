"""Public metric/alert read + alert lifecycle (EP-11/12/15/16/17 backends; T-220/T-221).

Returns DTOs only (other modules — dashboard, domain dashboards — never see platform models).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.errors import ConflictStateError, NotFoundError
from app.modules.platform.models import Alert, Metric, MetricValue
from app.modules.platform.repositories import AlertRepository, MetricValueRepository

STATUS_FROM_THRESHOLD = {"GREEN": "ok", "YELLOW": "warning", "RED": "critical"}
UNIT_OUT = {"PERCENT": "PCT", "VND_PER_PERSON": "VND", "INDEX": "SCORE"}
STALE_AFTER = timedelta(days=7)  # FRESHNESS_STALE_DAYS default for monthly metrics (03 §1.3)


@dataclass(frozen=True)
class MetricValueDTO:
    metric_code: str
    pillar: str | None
    value: float | None
    unit: str
    currency: str | None
    status: str
    status_reason: str | None
    period_key: str
    computed_at: datetime
    freshness: str
    data_quality_pct: float | None
    lineage_url: str


@dataclass(frozen=True)
class MetricDefDTO:
    code: str
    pillar: str | None
    name_vi: str
    name_en: str
    unit: str
    direction: str
    warning: float
    critical: float
    source_module: str
    formula_ref: str | None


@dataclass(frozen=True)
class AlertDTO:
    id: uuid.UUID
    alert_code: str
    metric_code: str
    pillar: str | None
    severity: str
    status: str
    value: float | None
    threshold: float
    period_key: str
    raised_at: datetime
    acknowledged_by: uuid.UUID | None
    message_params: dict[str, Any]


def _f(x: Any) -> float | None:
    return None if x is None else float(x)


def value_dto(m: Metric, v: MetricValue, now: datetime) -> MetricValueDTO:
    unit = UNIT_OUT.get(m.unit, m.unit)
    status = (
        "no_data"
        if v.value is None
        else STATUS_FROM_THRESHOLD.get(v.threshold_status or "", "no_data")
    )
    reason = None
    if v.value is None and v.threshold_status == "GREEN":
        # e.g. FIN-03 profitable (BR-FIN-03); 05 has no reason column → generic code (DEC-205)
        status, reason = "ok", "NOT_APPLICABLE"
    return MetricValueDTO(
        metric_code=m.code, pillar=m.pillar, value=_f(v.value), unit=unit,
        currency="VND" if unit == "VND" else None, status=status,
        status_reason=reason, period_key=v.period_key, computed_at=v.computed_at,
        freshness="stale" if now - v.computed_at > STALE_AFTER else "fresh",
        data_quality_pct=_f(v.data_quality_score),
        lineage_url=f"/dashboard/metrics/{m.code}",
    )  # fmt: skip


def def_dto(m: Metric) -> MetricDefDTO:
    return MetricDefDTO(
        code=m.code, pillar=m.pillar, name_vi=m.name_vi, name_en=m.name_en, unit=m.unit,
        direction=m.direction, warning=float(m.warning_threshold),
        critical=float(m.critical_threshold), source_module=m.source_module,
        formula_ref=m.formula_ref,
    )  # fmt: skip


class MetricQueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.values = MetricValueRepository(db)
        self.alerts = AlertRepository(db)

    async def definitions(self) -> list[MetricDefDTO]:
        rows = (await self.db.execute(select(Metric).order_by(Metric.code))).scalars()
        return [def_dto(m) for m in rows]

    async def current_values(
        self, *, codes: set[str] | None = None, pillars: set[str] | None = None
    ) -> list[MetricValueDTO]:
        """Latest current company value per metric (most recent period)."""
        stmt = (
            self.values.joined(Metric, MetricValue)
            .where(
                MetricValue.is_current.is_(True), MetricValue.kind == "ACTUAL",
                MetricValue.scope_type == "company", MetricValue.deleted_at.is_(None),
            )
            .order_by(Metric.code, MetricValue.period_key.desc(), MetricValue.computed_at.desc())
        )  # fmt: skip
        if codes is not None:
            stmt = stmt.where(Metric.code.in_(codes))
        if pillars is not None:
            stmt = stmt.where(Metric.pillar.in_(pillars))
        now = datetime.now(UTC)
        seen: dict[str, MetricValueDTO] = {}
        for m, v in await self.values.rows(stmt):
            seen.setdefault(m.code, value_dto(m, v, now))
        return list(seen.values())

    async def trend(self, code: str, limit: int = 12) -> list[tuple[str, float | None]]:
        stmt = (
            self.values.joined(MetricValue.period_key, MetricValue.value)
            .where(
                Metric.code == code, MetricValue.is_current.is_(True),
                MetricValue.scope_type == "company", MetricValue.kind == "ACTUAL",
            )
            .order_by(MetricValue.period_key.desc())
            .limit(limit)
        )  # fmt: skip
        rows = await self.values.rows(stmt)
        return [(k, _f(v)) for k, v in reversed(rows)]

    async def breakdown(self, code: str, period_key: str) -> list[tuple[str, str, float | None]]:
        stmt = self.values.joined(
            MetricValue.scope_type, MetricValue.scope_id, MetricValue.value
        ).where(
            Metric.code == code, MetricValue.is_current.is_(True),
            MetricValue.period_key == period_key, MetricValue.scope_type != "company",
        )  # fmt: skip
        return [(t, str(i), _f(v)) for t, i, v in await self.values.rows(stmt)]

    async def record_count(self, code: str) -> int:
        return await self.values.lineage_count(
            Metric.code == code, MetricValue.is_current.is_(True),
            MetricValue.scope_type == "company",
        )  # fmt: skip

    # ---------- alerts ----------
    def _alerts(self) -> Any:
        return self.alerts.with_metric()

    @staticmethod
    def alert_dto(a: Alert, m: Metric, v: MetricValue) -> AlertDTO:
        crit = a.severity == "CRITICAL"
        return AlertDTO(
            id=a.id, alert_code=m.alert_code, metric_code=m.code, pillar=m.pillar,
            severity=a.severity.lower(), status=a.status.lower(), value=_f(v.value),
            threshold=float(m.critical_threshold if crit else m.warning_threshold),
            period_key=a.period_key, raised_at=a.raised_at, acknowledged_by=a.acknowledged_by,
            message_params={"metric_code": m.code, "value": _f(v.value),
                            "period_key": a.period_key},
        )  # fmt: skip

    async def list_alerts(
        self, *, pillars: set[str], status: str | None, severity: str | None,
        limit: int, offset: int, codes: set[str] | None = None,
    ) -> tuple[list[AlertDTO], int]:  # fmt: skip
        stmt = self._alerts().where(Metric.pillar.in_(pillars))
        if codes is not None:
            stmt = stmt.where(Metric.code.in_(codes))
        if status:
            stmt = stmt.where(Alert.status == status.upper())
        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())
        rows, total = await self.alerts.page(
            stmt, (Alert.raised_at.desc(), Alert.id), limit=limit, offset=offset
        )
        return [self.alert_dto(a, m, v) for a, m, v in rows], total

    async def open_alert_count(self, pillars: set[str]) -> dict[str, int]:
        rows = await self.alerts.open_count_by_pillar(pillars)
        return {p: int(n) for p, n in rows if p is not None}

    async def _get_alert(self, id_: uuid.UUID) -> tuple[Alert, Metric, MetricValue]:
        row = await self.alerts.first(self._alerts().where(Alert.id == id_))
        if row is None:
            raise NotFoundError("alert not found")
        return row[0], row[1], row[2]

    async def alert_metric(self, id_: uuid.UUID) -> tuple[str, str | None]:
        _, m, _ = await self._get_alert(id_)
        return m.code, m.pillar

    async def acknowledge(self, id_: uuid.UUID, user_id: uuid.UUID, note: str | None) -> AlertDTO:
        a, m, v = await self._get_alert(id_)
        if a.status != "OPEN":
            raise ConflictStateError(f"alert is {a.status.lower()}, expected open")
        a.status, a.acknowledged_by, a.acknowledged_at = "ACKNOWLEDGED", user_id, datetime.now(UTC)
        await record_audit(
            self.db, action="dashboard.alert_acknowledge", target_schema="platform",
            target_table="alerts", target_id=a.id, before={"status": "OPEN"},
            after={"status": "ACKNOWLEDGED", "note": note},
        )  # fmt: skip
        await self.db.flush()
        return self.alert_dto(a, m, v)

    async def dismiss(self, id_: uuid.UUID, user_id: uuid.UUID, reason: str) -> AlertDTO:
        a, m, v = await self._get_alert(id_)
        if a.status not in ("OPEN", "ACKNOWLEDGED"):
            raise ConflictStateError(f"alert is {a.status.lower()}, cannot dismiss")
        before = a.status
        a.status, a.dismissed_by, a.dismissed_at = "DISMISSED", user_id, datetime.now(UTC)
        a.dismiss_reason = reason
        await record_audit(
            self.db, action="dashboard.alert_dismiss", target_schema="platform",
            target_table="alerts", target_id=a.id, before={"status": before},
            after={"status": "DISMISSED", "reason": reason},
        )  # fmt: skip
        await self.db.flush()
        return self.alert_dto(a, m, v)
