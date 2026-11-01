"""M3.3 unit (T-822, R-DEC-136) — report export encoders (CSV/XLSX), no DB.

The `_csv` / `_xlsx` encoders and the catalogue are pure, so they run without a database. CSV is
written with a UTF-8 BOM so Excel opens Vietnamese text correctly; XLSX is a real openpyxl
workbook whose first row is the header. `export()` rejects an unknown format before any read.
"""

from __future__ import annotations

import io

import pytest

from app.core.errors import ValidationError
from app.modules.dashboard.services.report_service import (
    CATALOG,
    FORMATS,
    ReportExportService,
)


def test_catalog_codes_and_formats() -> None:
    svc = ReportExportService.__new__(ReportExportService)  # no DB needed for the catalogue
    items = svc.catalog()
    assert {i.code for i in items} == {c for c, _ in CATALOG}
    for i in items:
        assert i.formats == list(FORMATS)
        assert i.title_key.startswith("report.")


def test_csv_has_bom_header_and_rows() -> None:
    raw = ReportExportService._csv(["metric_code", "value"], [["METRIC-FIN-01", 12], ["x", None]])
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM for Excel
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "metric_code,value"
    assert lines[1] == "METRIC-FIN-01,12"


def test_xlsx_is_a_workbook_with_header_row() -> None:
    from openpyxl import load_workbook

    raw = ReportExportService._xlsx("metrics-health", ["code", "status"], [["M1", "ok"]])
    wb = load_workbook(io.BytesIO(raw))
    ws = wb.active
    assert ws.title == "metrics-health"
    assert [c.value for c in ws[1]] == ["code", "status"]
    assert [c.value for c in ws[2]] == ["M1", "ok"]


async def test_export_rejects_unknown_format() -> None:
    svc = ReportExportService.__new__(ReportExportService)
    with pytest.raises(ValidationError):
        await svc.export(None, "decisions", "pdf")  # type: ignore[arg-type]
