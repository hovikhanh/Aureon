"""Metric provider contract (T-220, 03 §1.2, DEC-205).

Domain modules compute their METRIC-* values in `modules/<m>/services/metrics.py` and register
them with `@metric_provider("<module>")`. The platform metric store (T-220) iterates
`METRIC_PROVIDERS`, persists `platform.metric_values`, evaluates thresholds from
`platform.metrics` and raises alerts (T-221). `core` never imports modules: providers are loaded
by `app.workers.consumers.load_metric_providers()` (app level), so platform does not import any
domain module either (no module cycle).

A provider returns one `MetricReading` per metric (company scope) and optionally extra readings
for department/product scope. `threshold_input` is the number compared with the catalog
thresholds when it differs from `value` (e.g. METRIC-FIN-02 "drop vs 3-period avg" in points).
`status` forces a status when thresholds are not a single number (e.g. METRIC-RSK-01 counts by
level); `None` = evaluate from catalog. `value=None` → `no_data` (+ `status_reason`).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

MetricStatus = Literal["ok", "warning", "critical", "no_data"]
PeriodType = Literal["MONTH", "QUARTER", "YEAR", "ROLLING_12M"]
ScopeType = Literal["company", "department", "product"]


@dataclass(frozen=True)
class RecordRef:
    """A domain row that contributes to a metric value (lineage, EP-13)."""

    schema: str
    table: str
    id: str
    contribution: float | None = None


@dataclass(frozen=True)
class MetricReading:
    code: str  # "METRIC-FIN-03"
    value: float | None
    period_key: str  # "2026-10", "2026-Q3", "2026"
    period_type: PeriodType = "MONTH"
    scope_type: ScopeType = "company"
    scope_id: str | None = None
    threshold_input: float | None = None
    status: MetricStatus | None = None
    status_reason: str | None = None
    data_quality_pct: float | None = None
    records: tuple[RecordRef, ...] = field(default_factory=tuple)


Provider = Callable[[AsyncSession, date], Awaitable[list[MetricReading]]]


@dataclass
class ProviderRegistry:
    providers: dict[str, Provider] = field(default_factory=dict)

    def register(self, module: str, fn: Provider) -> None:
        old = self.providers.get(module)
        same = old is not None and (old.__module__, old.__qualname__) == (
            fn.__module__,
            fn.__qualname__,
        )  # a module re-import (same function) replaces; a second provider is a bug
        if old is not None and not same:
            raise ValueError(f"metric provider {module!r} registered twice")
        self.providers[module] = fn


METRIC_PROVIDERS = ProviderRegistry()


def metric_provider(module: str) -> Callable[[Provider], Provider]:
    """`@metric_provider("finance")` on `async def compute(db, as_of) -> list[MetricReading]`."""

    def deco(fn: Provider) -> Provider:
        METRIC_PROVIDERS.register(module, fn)
        return fn

    return deco
