"""METRIC-DQ-02 "Bản ghi mới vào qua tài liệu/NL" (G3, 03 §2.6, R-DEC-68).

value = records created in the month whose provenance is `IDP` / `IMPORT` / `AI` ÷ all records
created in the month, over the lineage-whitelist tables each module registers with
`core.capture_share.register_capture_source` (C1 form rows are `MANUAL` → not captured). No row
created in the month → `no_data`. Provider key `capture` so `platform.capture_share`
(idp.document_committed / idp.document_rolled_back) recomputes only this metric.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capture_share import CAPTURE_SOURCES, capture_counts
from app.core.clock import month_key, month_range
from app.core.metrics import MetricReading, metric_provider

CODE = "METRIC-DQ-02"


async def capture_share(db: AsyncSession, period_key: str) -> tuple[int, int]:
    start, end = month_range(period_key)
    captured = total = 0
    for sources in CAPTURE_SOURCES.sources.values():
        c, n = await capture_counts(db, sources, start, end)
        captured, total = captured + c, total + n
    return captured, total


@metric_provider("capture")
async def compute(db: AsyncSession, as_of: date) -> list[MetricReading]:
    key = month_key(as_of)
    captured, total = await capture_share(db, key)
    if not total:
        return [MetricReading(CODE, None, key, status_reason="no records created")]
    return [MetricReading(CODE, round(captured / total * 100, 1), key)]
