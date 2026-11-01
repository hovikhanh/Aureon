"""ReportExportService (M3.3, T-822, R-DEC-136) — basic report catalog + CSV/XLSX export.

Three reports, each assembled from data the caller is already allowed to see (no level-3/4 fields,
02 §5.3):

- ``executive-summary`` — the EP-RPT-01 headline tiles + SEI + counts (CEO/DIR).
- ``decisions``        — the Decision Log (reuses the execution `MeetingService`, EP-43 scope).
- ``metrics-health``   — every visible metric with its value / status / freshness.

CSV uses the stdlib ``csv`` module; XLSX uses ``openpyxl`` (already a runtime dependency,
DEC-120 / R-DEC-136). PDF is intentionally **not** implemented in M3.3 (needs a runtime PDF
engine — raise a DEC when a user needs it). Reads go through public services only (DEC-125).
"""

from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError, ValidationError
from app.core.pagination import PageParams
from app.modules.dashboard.schemas.reporting import ReportCatalogOut
from app.modules.dashboard.services.dashboard_service import DashboardService
from app.modules.dashboard.services.reporting_service import ReportingService

CATALOG: tuple[tuple[str, str], ...] = (
    ("executive-summary", "report.executive_summary"),
    ("decisions", "report.decisions"),
    ("metrics-health", "report.metrics_health"),
)
FORMATS = ("csv", "xlsx")


class ReportExportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def catalog(self) -> list[ReportCatalogOut]:
        return [
            ReportCatalogOut(code=code, title_key=title, formats=list(FORMATS))
            for code, title in CATALOG
        ]

    async def export(self, user: Principal, code: str, fmt: str) -> tuple[bytes, str, str]:
        """Return (content, media_type, filename) for the report / format."""
        if fmt not in FORMATS:
            raise ValidationError(f"unsupported format {fmt!r}")
        if code not in {c for c, _ in CATALOG}:
            raise NotFoundError("report not found")
        header, rows = await self._rows(user, code)
        if fmt == "csv":
            return self._csv(header, rows), "text/csv; charset=utf-8", f"{code}.csv"
        return (
            self._xlsx(code, header, rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{code}.xlsx",
        )

    # ---------- row builders (no level-3/4 fields) ----------
    async def _rows(self, user: Principal, code: str) -> tuple[list[str], list[list[Any]]]:
        if code == "executive-summary":
            return await self._executive_rows(user)
        if code == "decisions":
            return await self._decision_rows(user)
        return await self._metrics_rows(user)

    async def _executive_rows(self, user: Principal) -> tuple[list[str], list[list[Any]]]:
        dash = await ReportingService(self.db).executive(user)
        rows: list[list[Any]] = [
            [t.metric_code, _num(t.value), t.status, t.freshness] for t in dash.tiles
        ]
        if dash.sei is not None:
            rows.append(
                [dash.sei.metric_code, _num(dash.sei.value), dash.sei.status, dash.sei.freshness]
            )
        return ["metric_code", "value", "status", "freshness"], rows

    async def _decision_rows(self, user: Principal) -> tuple[list[str], list[list[Any]]]:
        from app.modules.execution.services.meeting_service import MeetingService

        items, _ = await MeetingService(self.db).list_decisions(
            user, PageParams(limit=100, offset=0), status=None,
            meeting_id=None, initiative_id=None, review_due=None,
        )  # fmt: skip
        rows = [
            [
                str(d.id),
                d.content,
                d.status,
                d.decided_at.isoformat() if d.decided_at else "",
                ";".join(r.isoformat() for r in d.review_at),
                d.outcome_verified_at.isoformat() if d.outcome_verified_at else "",
            ]
            for d in items
        ]
        return ["id", "content", "status", "decided_at", "review_at", "verified_at"], rows

    async def _metrics_rows(self, user: Principal) -> tuple[list[str], list[list[Any]]]:
        metrics = await DashboardService(self.db).metrics(user)
        rows = [
            [m.metric_code, _num(m.value), m.status, m.freshness, m.group or ""] for m in metrics
        ]
        return ["metric_code", "value", "status", "freshness", "group"], rows

    # ---------- encoders ----------
    @staticmethod
    def _csv(header: list[str], rows: list[list[Any]]) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8-sig")  # BOM → Excel opens UTF-8 correctly

    @staticmethod
    def _xlsx(code: str, header: list[str], rows: list[list[Any]]) -> bytes:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = code[:31]  # Excel sheet-name limit
        ws.append(header)
        for r in rows:
            ws.append(r)
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()


def _num(value: Any) -> Any:
    """Keep numeric cells numeric; pass through None / strings unchanged."""
    return value


__all__ = ["CATALOG", "FORMATS", "ReportExportService"]
