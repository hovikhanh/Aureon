"""EP-RPT-08 MVP acceptance snapshot (M3.5, R-DEC-145, 09 §2.2 / BRD §19.1).

Lives in the `ai` module (the top aggregator — it already depends on dashboard/idp/platform) to
avoid a `dashboard → ai` cycle; the endpoint is still exposed at `/reporting/acceptance`.

Read-only aggregate of the four MVP acceptance gates G1–G4 from data that already exists — no new
entity, metric, event or recompute. Cross-module reads go through public services only (DEC-125):

- G1 (Briefing adoption, ≥ 4 days/week over the window): `BriefingService.history` → count the days
  the CEO actually opened a briefing in the last `weeks` weeks (average days/week).
- G2 (KPI/OKR updated on time, ≥ 80%): metric `METRIC-STR-01` latest company value.
- G3 (new records captured via document/NL, ≥ 60%): metric `METRIC-DQ-02` latest company value.
- G4 (critical-field write errors that slipped through, must be 0): count of **undetected**
  capture incidents (`IncidentService.list(undetected_only=True)`).

The true G1–G4 thresholds are confirmed at pilot (OQ-09-04); this page only reads instrumentation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.pagination import PageParams
from app.modules.dashboard.schemas.reporting import AcceptanceGateOut, AcceptanceSnapshotOut

G1_MIN_DAYS_PER_WEEK = 4.0
G2_WARN, G2_PASS = 60.0, 80.0
G3_WARN, G3_PASS = 40.0, 60.0


def pct_status(value: float | None, warn: float, passv: float) -> str:
    """Pure band for a percentage gate (G2/G3): None → no_data; ≥ pass → pass; ≥ warn → warning;
    else fail."""
    if value is None:
        return "no_data"
    if value >= passv:
        return "pass"
    if value >= warn:
        return "warning"
    return "fail"


def g1_status(opened_days: int, weeks: int, has_data: bool) -> tuple[str, float]:
    """Pure band for G1: average opened days/week over the window; ≥ 4/week → pass."""
    per_week = round(opened_days / weeks, 2) if weeks else 0.0
    if not has_data:
        return "no_data", per_week
    return ("pass" if per_week >= G1_MIN_DAYS_PER_WEEK else "warning"), per_week


class AcceptanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def snapshot(self, user: Principal, *, weeks: int = 4) -> AcceptanceSnapshotOut:
        weeks = max(1, min(weeks, 12))
        gates = [
            await self._g1(user, weeks),
            await self._metric_gate(user, "G2", "acceptance.g2", "METRIC-STR-01", G2_WARN, G2_PASS),
            await self._metric_gate(user, "G3", "acceptance.g3", "METRIC-DQ-02", G3_WARN, G3_PASS),
            await self._g4(user),
        ]
        return AcceptanceSnapshotOut(generated_at=datetime.now(UTC), gates=gates)

    async def _g1(self, user: Principal, weeks: int) -> AcceptanceGateOut:
        from app.modules.ai.services.briefing_service import BriefingService

        today = datetime.now(UTC).date()
        date_from = today - timedelta(days=weeks * 7 - 1)
        page = PageParams(limit=weeks * 7, offset=0)
        history = await BriefingService(self.db).history(
            user, page, date_from=date_from, date_to=today
        )
        opened_days = sum(1 for b in history.items if b.opened_at is not None)
        status, per_week = g1_status(opened_days, weeks, bool(history.items))
        return AcceptanceGateOut(
            gate="G1",
            label_key="acceptance.g1",
            status=status,
            value=per_week,
            unit="days_per_week",
            threshold_key="acceptance.g1_threshold",
            detail_key="acceptance.g1_detail",
            source_ref="/ai/briefings",
        )

    async def _metric_gate(
        self, user: Principal, gate: str, label_key: str, code: str, warn: float, passv: float
    ) -> AcceptanceGateOut:
        from app.modules.platform.services.metric_query import MetricQueryService

        rows = await MetricQueryService(self.db).current_values(codes={code})
        value = rows[0].value if rows else None
        return AcceptanceGateOut(
            gate=gate,
            label_key=label_key,
            status=pct_status(value, warn, passv),
            value=value,
            unit="pct",
            threshold_key=f"{label_key}_threshold",
            detail_key=f"{label_key}_detail",
            source_ref=code,
        )

    async def _g4(self, user: Principal) -> AcceptanceGateOut:
        from app.modules.idp.services.incident_service import IncidentService

        page = PageParams(limit=1, offset=0)
        _, total = await IncidentService(self.db).list(
            user, page, period=None, undetected_only=True
        )
        status = "pass" if total == 0 else "fail"
        return AcceptanceGateOut(
            gate="G4",
            label_key="acceptance.g4",
            status=status,
            value=float(total),
            unit="count",
            threshold_key="acceptance.g4_threshold",
            detail_key="acceptance.g4_detail",
            source_ref="/idp/incidents",
        )
