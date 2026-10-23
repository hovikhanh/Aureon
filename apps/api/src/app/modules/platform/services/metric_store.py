"""Metric store + alert engine (T-220, T-221; 03 §1.2, §3.1; DEC-205).

`recompute(as_of, modules=None)` runs the registered domain metric providers
(`app.core.metrics.METRIC_PROVIDERS`), writes `platform.metric_values` (the previous current
value for the same metric/kind/period/scope becomes `is_current=false`), lineage
(`METRIC_FROM_RECORD`) and evaluates thresholds from `platform.metrics`:
- warning/critical → open alert (max 1 open per metric+period — DB partial UQ), escalate
  warning → critical in place, publish `platform.alert_raised` on raise/escalate;
- back to ok → resolve the open alert (`ALERT_AUTO_RESOLVE_PERIODS` = 1).
A provider that raises is isolated (logged, its metrics untouched — FR-DSH-07).
Only company-scope readings drive alerts (one alert per metric+period: 05 UQ).
"""

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.events.outbox import publish_in_tx
from app.core.metrics import METRIC_PROVIDERS, MetricReading
from app.modules.platform.models import Alert, DataLineage, Metric, MetricValue, SystemSetting
from app.modules.platform.repositories import AlertRepository, MetricValueRepository
from app.modules.platform.services.catalog import BY_CODE, CATALOG, evaluate

log = logging.getLogger(__name__)

STATUS_TO_THRESHOLD = {"ok": "GREEN", "warning": "YELLOW", "critical": "RED"}
SEVERITY = {"warning": "WARNING", "critical": "CRITICAL"}
MAX_LINEAGE = 50


async def seed_catalog(db: AsyncSession) -> int:
    """Upsert the 32 catalog rows; existing thresholds are kept (configurable — NFR-19)."""
    existing = {m.code: m for m in (await db.execute(select(Metric))).scalars()}
    created = 0
    for d in CATALOG:
        row = existing.get(d.code)
        if row is None:
            db.add(Metric(
                code=d.code, alert_code=d.alert_code, pillar=d.pillar, name_vi=d.name_vi,
                name_en=d.name_en, unit=d.unit, direction=d.direction,
                warning_threshold=d.warning, critical_threshold=d.critical,
                source_module=d.source_module, formula_ref=f"03 §2 {d.code}",
                refresh_events=list(d.refresh_events),
            ))  # fmt: skip
            created += 1
        else:
            row.pillar, row.unit, row.direction = d.pillar, d.unit, d.direction
            row.refresh_events = list(d.refresh_events)
    await db.flush()
    return created


def setting_key(code: str, level: str) -> str:
    """`METRIC-FIN-03` → `THR_FIN_03_WARN` (03 §1.3)."""
    return "THR_" + code.removeprefix("METRIC-").replace("-", "_") + f"_{level}"


async def threshold_settings(db: AsyncSession) -> dict[str, float]:
    """ENT-SystemSetting `THR_<ID>_WARN/CRIT` (03 §1.3, NFR-19) — override catalog defaults."""
    rows = (await db.execute(
        select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.like("THR_%"))
    )).all()  # fmt: skip
    return {k: float(v) for k, v in rows if isinstance(v, int | float) and not isinstance(v, bool)}


def status_of(m: Metric, r: MetricReading, thr: dict[str, float] | None = None) -> str:
    if r.status is not None:
        return r.status
    if r.value is None:
        return "no_data"
    x = r.threshold_input if r.threshold_input is not None else r.value
    d = BY_CODE.get(m.code)
    thr = thr or {}
    warn = thr.get(setting_key(m.code, "WARN"), float(m.warning_threshold))
    crit = thr.get(setting_key(m.code, "CRIT"), float(m.critical_threshold))
    return evaluate(
        m.direction, float(x), warn, crit,
        d.inclusive if d else False,
    )  # fmt: skip


class MetricStore:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.thr: dict[str, float] = {}

    async def catalog(self) -> dict[str, Metric]:
        rows = (await self.db.execute(select(Metric))).scalars()
        return {m.code: m for m in rows}

    async def recompute(self, as_of: date, modules: set[str] | None = None) -> dict[str, int]:
        cat = await self.catalog()
        if not cat:
            await seed_catalog(self.db)
            cat = await self.catalog()
        self.thr = await threshold_settings(self.db)
        stats = {"values": 0, "raised": 0, "resolved": 0, "failed_providers": 0}
        for name, provider in sorted(METRIC_PROVIDERS.providers.items()):
            if modules is not None and name not in modules:
                continue
            try:
                async with self.db.begin_nested():
                    readings = await provider(self.db, as_of)
            except Exception:  # isolate one failing domain (FR-DSH-07)
                log.exception("metric provider %s failed", name)
                stats["failed_providers"] += 1
                continue
            for r in readings:
                m = cat.get(r.code)
                if m is None:
                    log.warning("provider %s returned unknown metric %s", name, r.code)
                    continue
                mv, status = await self._store(m, r)
                stats["values"] += 1
                if r.scope_type == "company":
                    raised, resolved = await self._alert(m, mv, r, status)
                    stats["raised"] += raised
                    stats["resolved"] += resolved
        await self.db.flush()
        return stats

    async def _store(self, m: Metric, r: MetricReading) -> tuple[MetricValue, str]:
        scope = uuid.UUID(r.scope_id) if r.scope_id else None
        await MetricValueRepository(self.db).retire_current(
            MetricValue.metric_id == m.id, MetricValue.kind == "ACTUAL",
            MetricValue.period_key == r.period_key, MetricValue.scope_type == r.scope_type,
            MetricValue.scope_id.is_(None) if scope is None else MetricValue.scope_id == scope,
        )  # fmt: skip
        status = status_of(m, r, self.thr)
        mv = MetricValue(
            metric_id=m.id, kind="ACTUAL", period_type=r.period_type, period_key=r.period_key,
            scope_type=r.scope_type, scope_id=scope,
            value=None if r.value is None else Decimal(str(round(r.value, 6))),
            threshold_status=STATUS_TO_THRESHOLD.get(status), origin="COMPUTED",
            computed_at=datetime.now(UTC), is_current=True,
            data_quality_score=None if r.data_quality_pct is None
            else Decimal(str(round(r.data_quality_pct, 2))),
            source="EVENT",
        )  # fmt: skip
        self.db.add(mv)
        await self.db.flush()
        self.db.add_all(
            DataLineage(
                link_kind="METRIC_FROM_RECORD", metric_value_id=mv.id, target_schema=ref.schema,
                target_table=ref.table, target_id=uuid.UUID(ref.id),
                contribution=None if ref.contribution is None else Decimal(str(ref.contribution)),
            )
            for ref in r.records[:MAX_LINEAGE]
        )  # fmt: skip
        return mv, status

    async def open_alert(self, metric_id: uuid.UUID, period_key: str) -> Alert | None:
        return await AlertRepository(self.db).open_for(metric_id, period_key)

    async def _alert(
        self, m: Metric, mv: MetricValue, r: MetricReading, status: str
    ) -> tuple[int, int]:
        current = await self.open_alert(m.id, r.period_key)
        if status in ("ok",):
            if current is not None:
                current.status, current.resolved_at = "RESOLVED", datetime.now(UTC)
                current.metric_value_id = mv.id
                await record_audit(
                    self.db, action="platform.alert_resolve", target_schema="platform",
                    target_table="alerts", target_id=current.id, after={"reason": "auto"},
                )  # fmt: skip
                return 0, 1
            return 0, 0
        if status == "no_data":
            return 0, 0
        severity = SEVERITY[status]
        if current is not None:
            current.metric_value_id = mv.id
            if current.severity == "WARNING" and severity == "CRITICAL":
                current.severity = "CRITICAL"
                await self._raised(m, current, r, escalated=True)
                return 1, 0
            return 0, 0
        params = _message_params(m, r)
        alert = Alert(
            metric_id=m.id, metric_value_id=mv.id, severity=severity, status="OPEN",
            period_key=r.period_key,
            message_vi=f"{m.name_vi}: {params['value']} ({status})",
            message_en=f"{m.name_en}: {params['value']} ({status})",
            raised_at=datetime.now(UTC), source="EVENT",
        )  # fmt: skip
        self.db.add(alert)
        await self.db.flush()
        await self._raised(m, alert, r, escalated=False)
        return 1, 0

    async def _raised(self, m: Metric, a: Alert, r: MetricReading, *, escalated: bool) -> None:
        await record_audit(
            self.db, action="platform.alert_raise", target_schema="platform",
            target_table="alerts", target_id=a.id,
            after={"alert_code": m.alert_code, "severity": a.severity, "escalated": escalated},
        )  # fmt: skip
        await publish_in_tx(
            self.db, event_type="platform.alert_raised", producer="platform",
            aggregate_schema="platform", aggregate_table="alerts", aggregate_id=a.id,
            payload={
                "alert_id": str(a.id), "alert_code": m.alert_code, "metric_code": m.code,
                "pillar": m.pillar, "severity": a.severity.lower(), "period_key": r.period_key,
                "escalated": escalated,
            },
        )  # fmt: skip


def _message_params(m: Metric, r: MetricReading) -> dict[str, Any]:
    value = "—" if r.value is None else f"{r.value:g}"
    return {"metric_code": m.code, "value": value, "period_key": r.period_key}
