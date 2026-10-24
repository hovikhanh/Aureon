#!/usr/bin/env python3
"""Generate the realistic demo business documents for Công ty TNHH TM&DV ABC.

Run from repo root:
    cd /home/vika/Aureon && uv run --group demo python scripts/gen_demo_docs.py

Outputs (all under data/):
    DOC-01  bao-cao-tai-chinh-q3-2026.pdf      (reportlab, multi-page P&L)
    DOC-02  danh-sach-hoa-don-t9-2026.xlsx     (openpyxl, 47 invoices + summary)
    DOC-03  bao-cao-sales-t9-2026.pdf          (reportlab, sales report)
    DOC-04  hop-dong-mau.pdf                   (reportlab, 2 contracts)
    DOC-05  bien-ban-hop-giao-ban.docx         (python-docx, 3 meetings)
    DOC-06  danh-sach-nhan-su.xlsx             (openpyxl, C5 import #4 HR_ROSTER: 45 active +
                                                3 intentional error rows; leavers on sheet 2)
    DOC-07  kpi-okr-q4-2026.xlsx / .docx       (openpyxl + python-docx, #2 PLAN_KPI_OKR 2026-Q4)
    DOC-08  bao-cao-ket-qua-q3-2026.pdf        (reportlab, #3 PERIOD_REPORT Q3/2026)
    UC-07   ABC_DanhSachNhanSu_Onboarding.xlsx (openpyxl, #4 HR_ROSTER onboarding roster with
            intentional error rows — R-DEC-79, TC-M16-22)

Re-running is idempotent: OOXML zips get fixed timestamps and reportlab runs in invariant mode,
so every file is byte-identical across runs (T-641, TC-M15-15).

Only openpyxl / python-docx / reportlab / Pillow + stdlib are used. No network.
All monetary amounts are VND integers. Reference date = 20/10/2026.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Final

# --- python-docx ------------------------------------------------------------
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

# --- openpyxl ---------------------------------------------------------------
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

# --- reportlab --------------------------------------------------------------
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Constants / company context
# ---------------------------------------------------------------------------
ROOT: Final[Path] = Path(__file__).resolve().parent.parent
rl_config.invariant = 1  # PDFs without timestamp / random ID → identical on re-run
DATA_DIR: Final[Path] = ROOT / "data"

COMPANY: Final[str] = "Công ty TNHH TM&DV ABC"
COMPANY_TAX: Final[str] = "0301234567"
COMPANY_DESC: Final[str] = "Phân phối thiết bị văn phòng — 45 nhân sự"
REF_DATE: Final[str] = "20/10/2026"

# Vietnamese-capable TTF fonts (full Unicode coverage).
FONT_DIR: Final[Path] = Path("/usr/share/fonts/truetype/dejavu")
FONT_REGULAR: Final[str] = "VNFont"
FONT_BOLD: Final[str] = "VNFont-Bold"
FONT_OBLIQUE: Final[str] = "VNFont-Oblique"


# ---------------------------------------------------------------------------
# Deterministic output (T-641: re-running gives byte-identical files)
# ---------------------------------------------------------------------------
_FIXED_ZIP_TIME: Final[tuple[int, int, int, int, int, int]] = (2026, 10, 20, 8, 0, 0)
_FIXED_ISO: Final[str] = "2026-10-20T08:00:00Z"


def _stable_zip(data: bytes) -> bytes:
    """Rewrite an OOXML zip with fixed entry timestamps and fixed core.xml dates."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                body = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*",
                              rb"\g<1>" + _FIXED_ISO.encode(), body)
            entry = zipfile.ZipInfo(info.filename, date_time=_FIXED_ZIP_TIME)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o600 << 16
            dst.writestr(entry, body)
    return out.getvalue()


def _save_wb(wb: Workbook, path: Path) -> None:
    buf = io.BytesIO()
    wb.save(buf)
    path.write_bytes(_stable_zip(buf.getvalue()))


def _save_docx(document: Any, path: Path) -> None:
    buf = io.BytesIO()
    document.save(buf)
    path.write_bytes(_stable_zip(buf.getvalue()))


def _register_fonts() -> None:
    """Register DejaVuSans (Vietnamese-capable) for reportlab, once."""
    mapping = {
        FONT_REGULAR: FONT_DIR / "DejaVuSans.ttf",
        FONT_BOLD: FONT_DIR / "DejaVuSans-Bold.ttf",
        FONT_OBLIQUE: FONT_DIR / "DejaVuSans-Oblique.ttf",
    }
    for name, path in mapping.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))


# ---------------------------------------------------------------------------
# Number formatting helpers
# ---------------------------------------------------------------------------
def vnd(amount: int) -> str:
    """Format an integer VND amount with dot thousands separators + ' đ'."""
    return f"{amount:,}".replace(",", ".") + " đ"


def num(amount: int) -> str:
    """Format an integer with dot thousands separators (no currency suffix)."""
    return f"{amount:,}".replace(",", ".")


# ===========================================================================
# DOC-01 — Financial report Q3/2026 (reportlab, multi-page)
# ===========================================================================
def gen_doc01(path: Path) -> str:
    _register_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VNTitle", parent=styles["Title"], fontName=FONT_BOLD, fontSize=15, leading=19
    )
    h2 = ParagraphStyle(
        "VNH2", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=12, leading=15
    )
    body = ParagraphStyle(
        "VNBody", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14
    )
    small = ParagraphStyle(
        "VNSmall", parent=styles["Normal"], fontName=FONT_OBLIQUE, fontSize=8.5, leading=12
    )

    revenue = 24_500_000_000
    cogs = 20_000_000_000
    gross_profit = 4_500_000_000
    operating_expenses = 3_400_000_000
    profit_before_tax = 1_100_000_000
    income_tax = 220_000_000
    net_profit = 880_000_000
    budget_opex = 3_150_000_000
    cash_end = 6_800_000_000
    receivables = 13_000_000_000

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="BÁO CÁO TÀI CHÍNH Q3/2026",
    )
    story: list = []

    story.append(Paragraph("BÁO CÁO TÀI CHÍNH Q3/2026 — Công ty TNHH TM&DV ABC", title_style))
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"Đơn vị báo cáo: {COMPANY} — MST: {COMPANY_TAX}<br/>"
            f"Lĩnh vực: {COMPANY_DESC}<br/>"
            f"Kỳ báo cáo: Quý 3/2026 (01/07/2026 – 30/09/2026)<br/>"
            f"Ngày lập: {REF_DATE}. Đơn vị tiền: đồng (VND).",
            body,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # --- P&L table ---
    story.append(Paragraph("1. Báo cáo kết quả kinh doanh (P&L)", h2))
    story.append(Spacer(1, 2 * mm))
    pnl_rows = [
        ["Chỉ tiêu", "Giá trị", "Ghi chú"],
        ["Doanh thu thuần (cả quý)", vnd(revenue), "Tổng 3 tháng T7–T9"],
        ["Giá vốn hàng bán (COGS)", vnd(cogs), ""],
        ["Lợi nhuận gộp", vnd(gross_profit), "Biên lợi nhuận gộp 18,4%"],
        ["Chi phí hoạt động (OPEX)", vnd(operating_expenses), f"Ngân sách: {vnd(budget_opex)}"],
        ["Lợi nhuận trước thuế (EBT)", vnd(profit_before_tax), ""],
        ["Thuế TNDN", vnd(income_tax), "Thuế suất 20%"],
        ["Lợi nhuận sau thuế", vnd(net_profit), "Net profit"],
    ]
    pnl = Table(pnl_rows, colWidths=[62 * mm, 55 * mm, 48 * mm], repeatRows=1)
    pnl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1F8")]),
                ("FONTNAME", (0, 3), (0, 3), FONT_BOLD),  # Lợi nhuận gộp
                ("FONTNAME", (0, 7), (0, 7), FONT_BOLD),  # Lợi nhuận sau thuế
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(pnl)
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            f"Chi phí hoạt động thực tế {vnd(operating_expenses)} vượt ngân sách "
            f"{vnd(budget_opex)} là {vnd(operating_expenses - budget_opex)} "
            "(+7,9% so với kế hoạch).",
            small,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # --- Revenue by month ---
    story.append(Paragraph("2. Doanh thu theo tháng (Q3/2026)", h2))
    story.append(Spacer(1, 2 * mm))
    rbm = [
        ["Tháng", "Doanh thu"],
        ["T7/2026", vnd(7_800_000_000)],
        ["T8/2026", vnd(8_200_000_000)],
        ["T9/2026", vnd(8_500_000_000)],
        ["Tổng Q3", vnd(24_500_000_000)],
    ]
    rbm_t = Table(rbm, colWidths=[70 * mm, 70 * mm], repeatRows=1)
    rbm_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("FONTNAME", (0, 4), (-1, 4), FONT_BOLD),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#DDE8F3")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(rbm_t)
    story.append(Spacer(1, 6 * mm))

    # --- Net cash flow by month ---
    story.append(Paragraph("3. Dòng tiền thuần theo tháng (Q3/2026)", h2))
    story.append(Spacer(1, 2 * mm))
    ncf = [
        ["Tháng", "Dòng tiền thuần"],
        ["T7/2026", vnd(-700_000_000)],
        ["T8/2026", vnd(-850_000_000)],
        ["T9/2026", vnd(-1_000_000_000)],
        ["Tổng Q3", vnd(-2_550_000_000)],
    ]
    ncf_t = Table(ncf, colWidths=[70 * mm, 70 * mm], repeatRows=1)
    ncf_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B2E2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor("#B00000")),
                ("FONTNAME", (0, 4), (-1, 4), FONT_BOLD),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#F3DDDD")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(ncf_t)
    story.append(Spacer(1, 6 * mm))

    # --- Balance / liquidity snapshot ---
    story.append(Paragraph("4. Chỉ tiêu tài chính cuối kỳ", h2))
    story.append(Spacer(1, 2 * mm))
    bs = [
        ["Chỉ tiêu", "Giá trị", "Ghi chú"],
        ["Tiền và tương đương tiền cuối kỳ", vnd(cash_end), "Cash end of period"],
        ["Khoản phải thu khách hàng", vnd(receivables), "Receivables"],
        ["Ngân sách OPEX quý", vnd(budget_opex), "Budget OPEX"],
    ]
    bs_t = Table(bs, colWidths=[62 * mm, 55 * mm, 48 * mm], repeatRows=1)
    bs_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1F8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(bs_t)
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Nhận xét: Lợi nhuận quý đạt dương, tuy nhiên dòng tiền thuần âm 3 tháng liên tiếp "
            "do khoản phải thu cao (13 tỷ đ) và tốc độ thu hồi chậm. Đề xuất siết hạn thanh toán "
            "và kiểm soát OPEX về trong ngân sách ở Q4/2026.",
            small,
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            f"— Hết báo cáo — {COMPANY}, MST {COMPANY_TAX}. Lập ngày {REF_DATE}.",
            small,
        )
    )

    doc.build(story)
    return (
        f"DOC-01: P&L Q3/2026, doanh thu={num(revenue)}, LN sau thuế={num(net_profit)}, "
        f"{path.name}"
    )


# ===========================================================================
# DOC-02 — Invoice list T9/2026 (openpyxl)
# ===========================================================================
# (STT, Số HĐ, Ngày, Khách hàng, MST, Subtotal, VAT, Đã thu, Hạn TT, Trạng thái)
INVOICES: Final[list[tuple]] = [
    (1, "HV-001", "02/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 260_000_000, 0.10, 0, "02/10", "UNPAID"),
    (2, "HV-002", "03/09", "Công ty TNHH TechSoft", "0305551234", 250_000_000, 0.10, 275_000_000, "18/10", "PAID"),
    (3, "HV-003", "04/09", "Công ty TNHH Giải pháp Số", "0304445678", 150_000_000, 0.08, 0, "19/10", "UNPAID"),
    (4, "HV-004", "05/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 95_000_000, 0.10, 104_500_000, "20/10", "PAID"),
    (5, "HV-005", "06/09", "Công ty TNHH Minh Phát", "0306667778", 320_000_000, 0.10, 0, "05/11", "UNPAID"),
    (6, "HV-006", "07/09", "Công ty Cổ phần ABC Retail", "0302223334", 165_000_000, 0.08, 178_200_000, "22/10", "PAID"),
    (7, "HV-007", "08/09", "Công ty TNHH Đại Lợi", "0307778889", 240_000_000, 0.10, 0, "23/10", "UNPAID"),
    (8, "HV-008", "09/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 140_000_000, 0.10, 0, "09/10", "UNPAID"),
    (9, "HV-009", "10/09", "Công ty TNHH An Khang", "0308889990", 85_000_000, 0.08, 91_800_000, "25/10", "PAID"),
    (10, "HV-010", "11/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 195_000_000, 0.10, 0, "26/10", "UNPAID"),
    (11, "HV-011", "12/09", "Công ty TNHH FPT Trading", "0303334445", 290_000_000, 0.10, 319_000_000, "27/10", "PAID"),
    (12, "HV-012", "13/09", "Công ty TNHH Giải pháp Số", "0304445678", 140_000_000, 0.08, 0, "28/10", "UNPAID"),
    (13, "HV-013", "14/09", "Công ty Cổ phần Thương mại Quốc tế", "0305556677", 200_000_000, 0.10, 220_000_000, "29/10", "PAID"),
    (14, "HV-014", "15/09", "Công ty TNHH Minh Phát", "0306667778", 175_000_000, 0.10, 0, "14/11", "UNPAID"),
    (15, "HV-015", "16/09", "Công ty Cổ phần TechVN", "0301119988", 185_000_000, 0.10, 203_500_000, "31/10", "PAID"),
    (16, "HV-016", "17/09", "Công ty TNHH Đầu tư Đại Cường", "0302228877", 270_000_000, 0.10, 0, "01/11", "UNPAID"),
    (17, "HV-017", "18/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 130_000_000, 0.08, 140_400_000, "18/10", "PAID"),
    (18, "HV-018", "19/09", "Công ty TNHH Thương mại Lộc Phát", "0303332211", 190_000_000, 0.10, 0, "03/11", "UNPAID"),
    (19, "HV-019", "20/09", "Công ty Cổ phần Bút Tre VN", "0304443322", 100_000_000, 0.08, 108_000_000, "04/11", "PAID"),
    (20, "HV-020", "21/09", "Công ty TNHH An Khang", "0308889990", 145_000_000, 0.10, 0, "05/11", "UNPAID"),
    (21, "HV-021", "22/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 240_000_000, 0.10, 264_000_000, "06/11", "PAID"),
    (22, "HV-022", "23/09", "Công ty TNHH FPT Trading", "0303334445", 190_000_000, 0.10, 0, "07/11", "UNPAID"),
    (23, "HV-023", "24/09", "Công ty Cổ phần ABC Retail", "0302223334", 160_000_000, 0.08, 172_800_000, "08/11", "PAID"),
    (24, "HV-024", "25/09", "Công ty TNHH Giải pháp Số", "0304445678", 230_000_000, 0.10, 0, "09/11", "UNPAID"),
    (25, "HV-025", "26/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 175_000_000, 0.10, 192_500_000, "26/10", "PAID"),
    (26, "HV-026", "27/09", "Công ty TNHH Minh Phát", "0306667778", 120_000_000, 0.08, 0, "26/11", "UNPAID"),
    (27, "HV-027", "28/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 195_000_000, 0.10, 214_500_000, "12/11", "PAID"),
    (28, "HV-028", "29/09", "Công ty TNHH Đầu tư Đại Cường", "0302228877", 185_000_000, 0.10, 0, "13/11", "UNPAID"),
    (29, "HV-029", "30/09", "Công ty Cổ phần TechVN", "0301119988", 140_000_000, 0.08, 151_200_000, "14/11", "PAID"),
    (30, "HV-030", "01/09", "Công ty TNHH An Khang", "0308889990", 220_000_000, 0.10, 0, "16/10", "UNPAID"),
    (31, "HV-031", "02/09", "Công ty Cổ phần Bút Tre VN", "0304443322", 130_000_000, 0.10, 143_000_000, "17/10", "PAID"),
    (32, "HV-032", "03/09", "Công ty TNHH Thương mại Lộc Phát", "0303332211", 200_000_000, 0.10, 0, "18/10", "UNPAID"),
    (33, "HV-033", "04/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 155_000_000, 0.08, 167_400_000, "04/10", "PAID"),
    (34, "HV-034", "05/09", "Công ty TNHH FPT Trading", "0303334445", 230_000_000, 0.10, 0, "20/10", "UNPAID"),
    (35, "HV-035", "06/09", "Công ty Cổ phần ABC Retail", "0302223334", 110_000_000, 0.08, 118_800_000, "21/10", "PAID"),
    (36, "HV-036", "07/09", "Công ty TNHH Minh Phát", "0306667778", 210_000_000, 0.10, 0, "06/11", "UNPAID"),
    (37, "HV-037", "08/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 145_000_000, 0.10, 159_500_000, "23/10", "PAID"),
    (38, "HV-038", "09/09", "Công ty TNHH Giải pháp Số", "0304445678", 195_000_000, 0.10, 0, "24/10", "UNPAID"),
    (39, "HV-039", "10/09", "Công ty Cổ phần TechVN", "0301119988", 160_000_000, 0.08, 172_800_000, "25/10", "PAID"),
    (40, "HV-040", "11/09", "Công ty TNHH Đầu tư Đại Cường", "0302228877", 225_000_000, 0.10, 0, "26/10", "UNPAID"),
    (41, "HV-041", "12/09", "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 135_000_000, 0.10, 148_500_000, "12/10", "PAID"),
    (42, "HV-042", "13/09", "Công ty TNHH An Khang", "0308889990", 205_000_000, 0.10, 0, "28/10", "UNPAID"),
    (43, "HV-043", "14/09", "Công ty Cổ phần Bút Tre VN", "0304443322", 125_000_000, 0.08, 135_000_000, "29/10", "PAID"),
    (44, "HV-044", "15/09", "Công ty TNHH Thương mại Lộc Phát", "0303332211", 170_000_000, 0.10, 0, "30/10", "UNPAID"),
    (45, "HV-045", "16/09", "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 195_000_000, 0.10, 214_500_000, "31/10", "PAID"),
    (46, "HV-046", "17/09", "Công ty TNHH FPT Trading", "0303334445", 160_000_000, 0.08, 100_000_000, "01/11", "PARTIAL"),
    (47, "HV-047", "18/09", "Công ty Cổ phần ABC Retail", "0302223334", 170_000_000, 0.10, 100_000_000, "02/11", "PARTIAL"),
]

INVOICE_SUBTOTAL_TARGET: Final[int] = 8_500_000_000
INVOICE_VAT_TARGET: Final[int] = 812_000_000
INVOICE_TOTAL_TARGET: Final[int] = 9_312_000_000


def _style_header(ws: Worksheet, ncols: int, row: int = 1) -> None:
    fill = PatternFill("solid", fgColor="1F4E79")
    font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
        cell.border = border


def gen_doc02(path: Path) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Hóa đơn T9"
    headers = [
        "STT", "Số HĐ", "Ngày", "Khách hàng", "MST khách",
        "Subtotal (VND)", "VAT %", "Đã thu (VND)", "Hạn TT", "Trạng thái",
    ]
    ws.append(headers)
    _style_header(ws, len(headers))

    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    subtotal_sum = 0
    for row in INVOICES:
        stt, so_hd, ngay, kh, mst, subtotal, vat, da_thu, han, trang_thai = row
        subtotal_sum += subtotal
        ws.append(
            [stt, so_hd, f"{ngay}/2026", kh, mst, subtotal, vat, da_thu, f"{han}/2026", trang_thai]
        )
        r = ws.max_row
        ws.cell(row=r, column=6).number_format = "#,##0"
        ws.cell(row=r, column=7).number_format = "0%"
        ws.cell(row=r, column=8).number_format = "#,##0"
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = border
        # Status colour cue
        st_cell = ws.cell(row=r, column=10)
        if trang_thai == "PAID":
            st_cell.font = Font(color="1E7D32", bold=True)
        elif trang_thai == "UNPAID":
            st_cell.font = Font(color="C62828", bold=True)
        else:  # PARTIAL
            st_cell.font = Font(color="E65100", bold=True)

    # TỔNG row
    total_row = ["", "", "", "TỔNG", "", subtotal_sum, "", "", "", ""]
    ws.append(total_row)
    r = ws.max_row
    ws.cell(row=r, column=6).number_format = "#,##0"
    for c in range(1, len(headers) + 1):
        ws.cell(row=r, column=c).font = Font(bold=True)
        ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor="DDE8F3")
        ws.cell(row=r, column=c).border = border

    # Column widths
    widths = [6, 10, 12, 38, 14, 18, 8, 16, 12, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.freeze_panes = "A2"

    # Sheet 2 — Tổng hợp
    ws2 = wb.create_sheet("Tổng hợp")
    ws2.append(["Chỉ tiêu", "Giá trị (VND)"])
    _style_header(ws2, 2)
    ws2.append(["Tổng subtotal", INVOICE_SUBTOTAL_TARGET])
    ws2.append(["Tổng VAT", INVOICE_VAT_TARGET])
    ws2.append(["Tổng thanh toán", INVOICE_TOTAL_TARGET])
    for row_i in range(2, 5):
        ws2.cell(row=row_i, column=2).number_format = "#,##0"
    ws2.append([])
    ws2.append(["Số hóa đơn", len(INVOICES)])
    ws2.append(["Kỳ", "Tháng 9/2026"])
    ws2.column_dimensions["A"].width = 24
    ws2.column_dimensions["B"].width = 20

    _save_wb(wb, path)
    return (
        f"DOC-02: {len(INVOICES)} invoices, Σsubtotal={num(subtotal_sum)}, "
        f"Σvat={num(INVOICE_VAT_TARGET)}, {path.name}"
    )


# ===========================================================================
# DOC-03 — Sales report T9/2026 (reportlab)
# ===========================================================================
def gen_doc03(path: Path) -> str:
    _register_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VNTitle3", parent=styles["Title"], fontName=FONT_BOLD, fontSize=15, leading=19
    )
    h2 = ParagraphStyle(
        "VNH23", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=12, leading=15
    )
    body = ParagraphStyle(
        "VNBody3", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14
    )
    small = ParagraphStyle(
        "VNSmall3", parent=styles["Normal"], fontName=FONT_OBLIQUE, fontSize=8.5, leading=12
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="BÁO CÁO KINH DOANH T9/2026",
    )
    story: list = []
    story.append(Paragraph("BÁO CÁO KINH DOANH T9/2026", title_style))
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            f"{COMPANY} — MST {COMPANY_TAX}. Kỳ: Tháng 9/2026. Ngày lập: {REF_DATE}.", body
        )
    )
    story.append(Spacer(1, 5 * mm))

    # KPI summary block
    story.append(Paragraph("1. Chỉ số tổng hợp", h2))
    story.append(Spacer(1, 2 * mm))
    kpi_rows = [
        ["Chỉ số", "Giá trị"],
        ["Deal thắng (số lượng)", "12 deal"],
        ["Deal thắng (giá trị)", vnd(3_200_000_000)],
        ["Deal thua (số lượng)", "38 deal"],
        ["Deal thua (giá trị)", vnd(6_840_000_000)],
        ["Điểm NPS", "+32"],
        ["Mục tiêu doanh số (Sales target)", vnd(9_600_000_000)],
        ["Doanh thu Q4 đã ghi nhận tới nay", vnd(5_500_000_000)],
    ]
    kpi_t = Table(kpi_rows, colWidths=[90 * mm, 84 * mm], repeatRows=1)
    kpi_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1F8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(kpi_t)
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Tỷ lệ chuyển đổi deal (win rate) = 12 / (12 + 38) = 24,0%. "
            "Doanh số T9 đạt 8,5 tỷ đ, tương đương 88,5% mục tiêu tháng 9,6 tỷ đ.",
            small,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # Pipeline table
    story.append(Paragraph("2. Pipeline cơ hội (Stage)", h2))
    story.append(Spacer(1, 2 * mm))
    pipe = [
        ["Stage", "Deal count", "Value", "Probability", "Weighted"],
        ["Prospecting", "15", vnd(12_000_000_000), "0,10", vnd(1_200_000_000)],
        ["Qualification", "10", vnd(10_000_000_000), "0,25", vnd(2_500_000_000)],
        ["Proposal", "8", vnd(12_000_000_000), "0,40", vnd(4_800_000_000)],
        ["Negotiation", "6", vnd(13_500_000_000), "0,60", vnd(8_100_000_000)],
        ["Cộng stage mở", "39", vnd(47_500_000_000), "—", vnd(16_600_000_000)],
    ]
    pipe_t = Table(
        pipe, colWidths=[34 * mm, 22 * mm, 40 * mm, 24 * mm, 40 * mm], repeatRows=1
    )
    pipe_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#EAF1F8")]),
                ("FONTNAME", (0, 5), (-1, 5), FONT_BOLD),
                ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#DDE8F3")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(pipe_t)
    story.append(Spacer(1, 6 * mm))

    # Revenue by customer table
    story.append(Paragraph("3. Doanh thu theo khách hàng (T9/2026)", h2))
    story.append(Spacer(1, 2 * mm))
    # (#, full name, mst, revenue, invoice count, share)
    custs: list[tuple[int, str, str, int, int, str]] = [
        (1, "Công ty Cổ phần Văn phòng Phẩm", "0301112223", 1_065_000_000, 6, "12,5%"),
        (2, "Công ty Cổ phần Giáo dục Việt Nam", "0309876543", 995_000_000, 6, "11,7%"),
        (3, "Công ty TNHH FPT Trading", "0303334445", 870_000_000, 4, "10,2%"),
        (4, "Công ty TNHH Minh Phát", "0306667778", 825_000_000, 4, "9,7%"),
        (5, "Công ty TNHH Giải pháp Số", "0304445678", 715_000_000, 4, "8,4%"),
        (6, "Công ty TNHH Đầu tư Đại Cường", "0302228877", 680_000_000, 3, "8,0%"),
        (7, "Công ty TNHH An Khang", "0308889990", 655_000_000, 4, "7,7%"),
        (8, "Công ty Cổ phần ABC Retail", "0302223334", 605_000_000, 4, "7,1%"),
        (9, "Công ty TNHH Thương mại Lộc Phát", "0303332211", 560_000_000, 3, "6,6%"),
        (10, "Công ty Cổ phần TechVN", "0301119988", 485_000_000, 3, "5,7%"),
        (11, "Công ty Cổ phần Bút Tre VN", "0304443322", 355_000_000, 3, "4,2%"),
        (12, "Công ty TNHH TechSoft", "0305551234", 250_000_000, 1, "2,9%"),
        (13, "Công ty TNHH Đại Lợi", "0307778889", 240_000_000, 1, "2,8%"),
        (14, "Công ty Cổ phần Thương mại Quốc tế", "0305556677", 200_000_000, 1, "2,4%"),
    ]
    rbc = [["#", "Khách hàng", "MST", "Doanh thu T9", "Số HĐ", "Tỷ trọng"]]
    for c in custs:
        rbc.append([str(c[0]), c[1], c[2], vnd(c[3]), str(c[4]), c[5]])
    rbc.append(["", "Tổng", "", vnd(8_500_000_000), "47", "100%"])
    rbc_t = Table(
        rbc, colWidths=[9 * mm, 62 * mm, 24 * mm, 40 * mm, 16 * mm, 23 * mm], repeatRows=1
    )
    rbc_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ALIGN", (4, 0), (5, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#EAF1F8")]),
                ("FONTNAME", (0, len(rbc) - 1), (-1, len(rbc) - 1), FONT_BOLD),
                ("BACKGROUND", (0, len(rbc) - 1), (-1, len(rbc) - 1), colors.HexColor("#DDE8F3")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(rbc_t)
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            "Top 3 khách hàng chiếm 34,4% doanh thu T9. Mức tập trung dưới ngưỡng cảnh báo 40%. "
            f"— {COMPANY}, lập ngày {REF_DATE}.",
            small,
        )
    )

    doc.build(story)
    return f"DOC-03: sales report T9, 4 pipeline stages, 14 customers, {path.name}"


# ===========================================================================
# DOC-04 — Sample contracts (reportlab, 2 contracts)
# ===========================================================================
def _contract_clauses(value: int, payment_days: int) -> list[tuple[str, str]]:
    return [
        (
            "Điều 1. Đối tượng hợp đồng",
            "Bên A đồng ý cung cấp và Bên B đồng ý nhận các thiết bị văn phòng (máy in, máy "
            "photocopy, vật tư tiêu hao và dịch vụ bảo trì kèm theo) theo đơn đặt hàng được hai "
            "bên xác nhận bằng văn bản trong suốt thời hạn hiệu lực của hợp đồng.",
        ),
        (
            "Điều 2. Giá trị hợp đồng và phương thức thanh toán",
            f"Tổng giá trị hợp đồng (đã bao gồm thuế GTGT) là {vnd(value)}. Bên B thanh toán "
            f"bằng chuyển khoản trong vòng {payment_days} ngày kể từ ngày nhận đủ hàng và hóa đơn "
            "GTGT hợp lệ. Thanh toán chậm chịu lãi 0,05%/ngày trên số tiền chậm trả.",
        ),
        (
            "Điều 3. Giao hàng và nghiệm thu",
            "Bên A giao hàng tại địa điểm do Bên B chỉ định trong phạm vi nội thành. Hai bên lập "
            "biên bản giao nhận và nghiệm thu; hàng hóa được coi là nghiệm thu nếu Bên B không có "
            "ý kiến bằng văn bản trong vòng 05 (năm) ngày làm việc kể từ ngày nhận.",
        ),
        (
            "Điều 4. Bảo hành và trách nhiệm",
            "Thiết bị được bảo hành 12 tháng theo tiêu chuẩn nhà sản xuất. Bên vi phạm nghĩa vụ "
            "hợp đồng phải bồi thường thiệt hại thực tế, trực tiếp phát sinh; tổng mức bồi thường "
            "không vượt quá giá trị hợp đồng.",
        ),
        (
            "Điều 5. Hiệu lực và giải quyết tranh chấp",
            "Hợp đồng có hiệu lực kể từ ngày hiệu lực ghi trên hợp đồng. Mọi tranh chấp được ưu "
            "tiên giải quyết thông qua thương lượng; nếu không đạt được thỏa thuận, tranh chấp "
            "được đưa ra Tòa án có thẩm quyền tại TP. Hồ Chí Minh giải quyết. Hợp đồng được lập "
            "thành 02 bản có giá trị pháp lý như nhau, mỗi bên giữ 01 bản.",
        ),
    ]


def gen_doc04(path: Path) -> str:
    _register_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VNTitle4", parent=styles["Title"], fontName=FONT_BOLD, fontSize=14, leading=18
    )
    h2 = ParagraphStyle(
        "VNH24", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=11.5, leading=15
    )
    body = ParagraphStyle(
        "VNBody4", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14,
        alignment=4,  # justify
    )
    center = ParagraphStyle(
        "VNCenter4", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10.5,
        leading=14, alignment=1,
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        title="HỢP ĐỒNG MẪU",
    )
    story: list = []

    contracts = [
        {
            "no": "HD-2026-001",
            "party_b": "Công ty Cổ phần Giáo dục Việt Nam",
            "party_b_mst": "0309876543",
            "value": 5_000_000_000,
            "sign": "15/01/2026",
            "effective": "01/02/2026",
            "expiry": "31/01/2027",
            "payment_days": 30,
        },
        {
            "no": "HD-2026-002",
            "party_b": "Công ty TNHH Minh Phát",
            "party_b_mst": "0306667778",
            "value": 3_000_000_000,
            "sign": "20/03/2026",
            "effective": "01/04/2026",
            "expiry": "30/09/2026",
            "payment_days": 60,
        },
    ]

    for idx, k in enumerate(contracts):
        story.append(Paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", center))
        story.append(Paragraph("Độc lập – Tự do – Hạnh phúc", center))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("HỢP ĐỒNG CUNG CẤP THIẾT BỊ VĂN PHÒNG", title_style))
        story.append(Paragraph(f"Số: {k['no']}", center))
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                f"Hôm nay, ngày {k['sign']}, tại TP. Hồ Chí Minh, chúng tôi gồm:", body
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("BÊN A (Bên bán):", h2))
        story.append(
            Paragraph(
                f"{COMPANY} — Mã số thuế: {COMPANY_TAX}.<br/>"
                "Đại diện: Ông Nguyễn Văn An — Chức vụ: Tổng Giám đốc (CEO).",
                body,
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("BÊN B (Bên mua):", h2))
        story.append(
            Paragraph(
                f"{k['party_b']} — Mã số thuế: {k['party_b_mst']}.<br/>"
                "Đại diện: Ông/Bà (theo giấy ủy quyền) — Chức vụ: Giám đốc.",
                body,
            )
        )
        story.append(Spacer(1, 3 * mm))
        info = [
            ["Số hợp đồng", k["no"], "Giá trị hợp đồng", vnd(k["value"])],
            ["Ngày ký", k["sign"], "Điều khoản thanh toán", f"{k['payment_days']} ngày"],
            ["Ngày hiệu lực", k["effective"], "Ngày hết hạn", k["expiry"]],
        ]
        info_t = Table(
            info, colWidths=[34 * mm, 42 * mm, 42 * mm, 48 * mm]
        )
        info_t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                    ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                    ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F8")),
                    ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EAF1F8")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(info_t)
        story.append(Spacer(1, 4 * mm))

        for heading, text in _contract_clauses(k["value"], k["payment_days"]):
            story.append(Paragraph(heading, h2))
            story.append(Paragraph(text, body))
            story.append(Spacer(1, 2 * mm))

        story.append(Spacer(1, 4 * mm))
        sign_tbl = [
            ["ĐẠI DIỆN BÊN A", "ĐẠI DIỆN BÊN B"],
            ["(Ký, ghi rõ họ tên, đóng dấu)", "(Ký, ghi rõ họ tên, đóng dấu)"],
            ["Nguyễn Văn An — CEO", "Giám đốc Bên B"],
        ]
        sign_t = Table(sign_tbl, colWidths=[83 * mm, 83 * mm])
        sign_t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, -1), FONT_OBLIQUE),
                    ("FONTNAME", (0, 2), (-1, 2), FONT_BOLD),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, 0), 2),
                    ("TOPPADDING", (0, 2), (-1, 2), 16),
                ]
            )
        )
        story.append(sign_t)

        if idx == 0:
            # Page break between the two contracts
            from reportlab.platypus import PageBreak

            story.append(PageBreak())

    doc.build(story)
    return (
        f"DOC-04: 2 contracts (HD-2026-001={num(5_000_000_000)}, "
        f"HD-2026-002={num(3_000_000_000)}), {path.name}"
    )


# ===========================================================================
# DOC-05 — Meeting minutes (python-docx, 3 meetings, 15 action items)
# ===========================================================================
def _set_doc_font(document: Document) -> None:  # type: ignore[valid-type]
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)


def gen_doc05(path: Path) -> str:
    document = Document()
    _set_doc_font(document)

    # action item status counts required: 9 DONE-on-time, 2 DONE-late, 4 OPEN-overdue
    STATUS_DONE: Final[str] = "DONE (đúng hạn)"
    STATUS_LATE: Final[str] = "DONE (trễ hạn)"
    STATUS_OPEN: Final[str] = "OPEN (quá hạn)"

    title = document.add_heading("", level=0)
    run = title.add_run("BIÊN BẢN HỌP GIAO BAN — Công ty TNHH TM&DV ABC")
    run.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = document.add_paragraph()
    p.add_run(f"MST: {COMPANY_TAX} — {COMPANY_DESC}. Tài liệu lập ngày {REF_DATE}.").italic = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    meetings: list[dict] = [
        {
            "title": "Giao ban tuần 1 T9",
            "date": "05/09/2026",
            "chair": "Ông Nguyễn Văn An (CEO)",
            "attendees": ["Ông Lê Hoàng Giang", "Cô Phạm Thị Hạnh", "Bà Trần Thị Minh"],
            "decisions": [
                "Phê duyệt kế hoạch doanh số tháng 9/2026 ở mức 9,6 tỷ đồng.",
                "Đồng ý siết hạn thanh toán khách hàng mới xuống tối đa 30 ngày.",
            ],
            "actions": [
                ("Rà soát 47 hóa đơn T9 và cập nhật trạng thái thu hồi công nợ",
                 "Bà Trần Thị Minh", "12/09/2026", STATUS_DONE),
                ("Gửi báo giá cho 4 khách hàng nhóm Proposal",
                 "Ông Lê Hoàng Giang", "10/09/2026", STATUS_DONE),
                ("Hoàn thiện kế hoạch tuyển dụng bổ sung 2 nhân sự CUS",
                 "Cô Phạm Thị Hạnh", "15/09/2026", STATUS_DONE),
                ("Chuẩn hóa quy trình nghiệm thu giao hàng nội thành",
                 "Ông Lê Hoàng Giang", "11/09/2026", STATUS_LATE),
                ("Lập báo cáo dòng tiền dự kiến Q4/2026",
                 "Bà Trần Thị Minh", "18/09/2026", STATUS_DONE),
            ],
        },
        {
            "title": "Giao ban tuần 2 T9",
            "date": "12/09/2026",
            "chair": "Ông Nguyễn Văn An (CEO)",
            "attendees": ["Ông Lê Hoàng Giang", "Cô Phạm Thị Hạnh", "Ông Vũ Đức Thắng"],
            "decisions": [
                "Phê duyệt ngân sách OPEX tháng 9 tối đa 1,15 tỷ đồng.",
            ],
            "actions": [
                ("Triển khai giao hàng cho 3 hợp đồng ký mới trong tuần",
                 "Ông Vũ Đức Thắng", "16/09/2026", STATUS_DONE),
                ("Cập nhật pipeline cơ hội lên hệ thống CRM",
                 "Ông Lê Hoàng Giang", "14/09/2026", STATUS_DONE),
                ("Rà soát định mức công việc trên đầu người phòng OPS",
                 "Ông Vũ Đức Thắng", "17/09/2026", STATUS_OPEN),
                ("Xây dựng bảng lương tháng 9 cho 45 nhân sự",
                 "Cô Phạm Thị Hạnh", "20/09/2026", STATUS_DONE),
            ],
        },
        {
            "title": "Giao ban tuần 3 T9",
            "date": "19/09/2026",
            "chair": "Ông Nguyễn Văn An (CEO)",
            "attendees": ["Bà Trần Thị Minh", "Cô Phạm Thị Hạnh", "Ông Vũ Đức Thắng"],
            "decisions": [
                "Thông qua kế hoạch thu hồi công nợ quá hạn trước 31/10/2026.",
                "Phê duyệt mục tiêu KPI/OKR Q4/2026 cho 4 phòng ban.",
            ],
            "actions": [
                ("Đối chiếu công nợ phải thu 13 tỷ đồng với từng khách hàng",
                 "Bà Trần Thị Minh", "25/09/2026", STATUS_DONE),
                ("Gửi thư nhắc thanh toán cho nhóm hóa đơn UNPAID",
                 "Bà Trần Thị Minh", "24/09/2026", STATUS_DONE),
                ("Lập kế hoạch đào tạo nội bộ Q4 cho phòng CUS",
                 "Cô Phạm Thị Hạnh", "30/09/2026", STATUS_OPEN),
                ("Tối ưu lịch giao hàng để giảm số dự án trễ",
                 "Ông Vũ Đức Thắng", "28/09/2026", STATUS_OPEN),
                ("Hoàn tất kiểm kê kho thiết bị cuối quý 3",
                 "Ông Vũ Đức Thắng", "26/09/2026", STATUS_LATE),
                ("Rà soát nhân sự quá tải và đề xuất điều phối",
                 "Cô Phạm Thị Hạnh", "29/09/2026", STATUS_OPEN),
            ],
        },
    ]

    status_counter: dict[str, int] = {STATUS_DONE: 0, STATUS_LATE: 0, STATUS_OPEN: 0}
    total_actions = 0

    for i, m in enumerate(meetings, start=1):
        document.add_heading(f"Cuộc họp {i}: {m['title']} — {m['date']}", level=1)
        document.add_paragraph(f"Chủ trì: {m['chair']}")
        document.add_paragraph("Thành phần tham dự: " + ", ".join(m["attendees"]))

        document.add_heading("Quyết định", level=2)
        for d in m["decisions"]:
            document.add_paragraph(d, style="List Number")

        document.add_heading("Hạng mục hành động (Action items)", level=2)
        table = document.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Nội dung"
        hdr[1].text = "Người phụ trách"
        hdr[2].text = "Hạn"
        hdr[3].text = "Trạng thái"
        for cell in hdr:
            for par in cell.paragraphs:
                for r in par.runs:
                    r.bold = True
        for content, owner, due, status in m["actions"]:
            row = table.add_row().cells
            row[0].text = content
            row[1].text = owner
            row[2].text = due
            row[3].text = status
            status_counter[status] += 1
            total_actions += 1
        document.add_paragraph("")

    # Summary
    document.add_heading("Tổng hợp trạng thái action items", level=1)
    document.add_paragraph(
        f"Tổng số action items: {total_actions}. "
        f"DONE đúng hạn: {status_counter[STATUS_DONE]}; "
        f"DONE trễ hạn: {status_counter[STATUS_LATE]}; "
        f"OPEN quá hạn: {status_counter[STATUS_OPEN]}."
    )

    # Assert the required distribution 9 / 2 / 4
    assert total_actions == 15, f"DOC-05: expected 15 action items, got {total_actions}"
    assert status_counter[STATUS_DONE] == 9, (
        f"DOC-05: expected 9 DONE-on-time, got {status_counter[STATUS_DONE]}"
    )
    assert status_counter[STATUS_LATE] == 2, (
        f"DOC-05: expected 2 DONE-late, got {status_counter[STATUS_LATE]}"
    )
    assert status_counter[STATUS_OPEN] == 4, (
        f"DOC-05: expected 4 OPEN-overdue, got {status_counter[STATUS_OPEN]}"
    )

    _save_docx(document, path)
    return (
        f"DOC-05: 3 meetings, {total_actions} action items "
        f"(9 done/2 late/4 open), {path.name}"
    )


# ===========================================================================
# DOC-06 — Staff list (openpyxl, 45 active + 6 terminated)
# ===========================================================================
ACTIVE_PAYROLL_TARGET: Final[int] = 855_000_000


def _build_active_employees() -> list[tuple[str, str, str, str, str, str, str, int]]:
    """Return 45 ACTIVE employees. Salaries sum EXACTLY to 855,000,000 VND.

    Columns: Mã NV | Họ tên | Chức danh | Phòng ban | Ngày vào | Ngày nghỉ | Trạng thái | Lương
    Distribution: FIN=8, CUS=12, OPS=10, HR=5, ADMIN=10.
    """
    # (name, role, dept, start_date, salary)  — explicitly chosen; sum verified below.
    rows: list[tuple[str, str, str, str, int]] = [
        # ADMIN (10) — includes CEO
        ("Nguyễn Văn An", "Tổng Giám đốc (CEO)", "ADMIN", "01/03/2019", 60_000_000),
        ("Đỗ Thị Lan", "Trợ lý Tổng Giám đốc", "ADMIN", "15/06/2020", 26_000_000),
        ("Hoàng Minh Tuấn", "Chuyên viên Hành chính", "ADMIN", "02/01/2021", 14_000_000),
        ("Phan Thị Thu", "Chuyên viên Pháp chế", "ADMIN", "10/09/2021", 20_000_000),
        ("Lê Quốc Dũng", "Chuyên viên IT nội bộ", "ADMIN", "05/04/2022", 18_000_000),
        ("Trần Văn Hùng", "Lái xe", "ADMIN", "12/07/2019", 11_000_000),
        ("Nguyễn Thị Hoa", "Lễ tân", "ADMIN", "03/02/2023", 10_000_000),
        ("Bùi Đức Mạnh", "Nhân viên Bảo vệ", "ADMIN", "20/08/2020", 9_000_000),
        ("Vũ Thị Nga", "Thủ quỹ", "ADMIN", "18/11/2021", 15_000_000),
        ("Đặng Văn Thành", "Chuyên viên Mua hàng", "ADMIN", "09/05/2022", 17_000_000),
        # FIN (8) — includes CFO Trần Thị Minh
        ("Trần Thị Minh", "Giám đốc Tài chính (CFO)", "FIN", "01/04/2019", 55_000_000),
        ("Ngô Thị Bích", "Kế toán trưởng", "FIN", "15/02/2020", 38_000_000),
        ("Lý Văn Khoa", "Kế toán tổng hợp", "FIN", "08/08/2021", 20_000_000),
        ("Phạm Thị Yến", "Kế toán công nợ", "FIN", "11/03/2022", 16_000_000),
        ("Trịnh Văn Long", "Kế toán thuế", "FIN", "22/06/2021", 17_000_000),
        ("Hồ Thị Duyên", "Kế toán kho", "FIN", "30/09/2022", 14_000_000),
        ("Đoàn Minh Khôi", "Chuyên viên Phân tích tài chính", "FIN", "05/01/2023", 23_000_000),
        ("Cao Thị Ngọc", "Kế toán thanh toán", "FIN", "14/10/2023", 13_000_000),
        # CUS (12) — includes Sales Director Lê Hoàng Giang
        ("Lê Hoàng Giang", "Giám đốc Kinh doanh (Sales Director)", "CUS", "01/05/2019", 50_000_000),
        ("Nguyễn Thị Thủy", "Trưởng nhóm Kinh doanh", "CUS", "12/03/2020", 33_000_000),
        ("Trần Văn Nam", "Nhân viên Kinh doanh", "CUS", "20/07/2021", 16_000_000),
        ("Phạm Văn Sơn", "Nhân viên Kinh doanh", "CUS", "03/09/2021", 15_000_000),
        ("Vũ Thị Hương", "Nhân viên Kinh doanh", "CUS", "15/01/2022", 15_000_000),
        ("Đinh Văn Phúc", "Nhân viên Kinh doanh", "CUS", "28/04/2022", 14_000_000),
        ("Bùi Thị Linh", "Chuyên viên Chăm sóc KH", "CUS", "10/06/2022", 13_000_000),
        ("Lương Văn Tài", "Nhân viên Kinh doanh", "CUS", "19/08/2022", 15_000_000),
        ("Hà Thị Trang", "Chuyên viên Chăm sóc KH", "CUS", "07/11/2022", 12_000_000),
        ("Trương Văn Bình", "Nhân viên Kinh doanh", "CUS", "02/02/2023", 14_000_000),
        ("Nguyễn Văn Đạt", "Nhân viên Kinh doanh", "CUS", "16/05/2023", 13_000_000),
        ("Phan Thị Mai", "Chuyên viên Chăm sóc KH", "CUS", "21/09/2023", 12_000_000),
        # OPS (10) — includes Ops lead Vũ Đức Thắng
        ("Vũ Đức Thắng", "Trưởng phòng Vận hành (Ops Lead)", "OPS", "01/06/2019", 32_000_000),
        ("Nguyễn Văn Kiên", "Giám sát Kho", "OPS", "14/02/2020", 18_000_000),
        ("Trần Thị Hồng", "Nhân viên Kho", "OPS", "09/07/2021", 11_000_000),
        ("Lê Văn Toàn", "Nhân viên Giao nhận", "OPS", "22/09/2021", 11_000_000),
        ("Phạm Văn Lộc", "Nhân viên Giao nhận", "OPS", "05/01/2022", 11_000_000),
        ("Đỗ Văn Hải", "Kỹ thuật viên Bảo trì", "OPS", "18/03/2022", 15_000_000),
        ("Ngô Văn Tân", "Kỹ thuật viên Bảo trì", "OPS", "27/06/2022", 14_000_000),
        ("Hoàng Thị Vân", "Điều phối Vận hành", "OPS", "11/10/2022", 13_000_000),
        ("Bùi Văn Quang", "Nhân viên Kho", "OPS", "03/03/2023", 11_000_000),
        ("Trần Văn Lâm", "Nhân viên Giao nhận", "OPS", "19/07/2023", 11_000_000),
        # HR (5) — includes HR Manager Phạm Thị Hạnh
        ("Phạm Thị Hạnh", "Trưởng phòng Nhân sự (HR Manager)", "HR", "01/07/2019", 30_000_000),
        ("Nguyễn Thị Diệu", "Chuyên viên Tuyển dụng", "HR", "12/04/2020", 16_000_000),
        ("Lê Thị Oanh", "Chuyên viên C&B", "HR", "08/08/2021", 17_000_000),
        ("Trần Văn Hoàng", "Chuyên viên Đào tạo", "HR", "15/02/2022", 15_000_000),
        ("Vũ Thị Kim", "Nhân viên Hành chính Nhân sự", "HR", "20/06/2023", 12_000_000),
    ]

    salaries_sum = sum(r[4] for r in rows)
    assert len(rows) == 45, f"DOC-06: expected 45 active employees, got {len(rows)}"
    assert salaries_sum == ACTIVE_PAYROLL_TARGET, (
        f"DOC-06: active payroll sum {salaries_sum} != {ACTIVE_PAYROLL_TARGET}"
    )

    out: list[tuple[str, str, str, str, str, str, str, int]] = []
    for i, (name, role, dept, start, salary) in enumerate(rows, start=1):
        code = f"NV-{i:03d}"
        out.append((code, name, role, dept, start, "", "ACTIVE", salary))
    return out


def _build_terminated_employees() -> list[tuple[str, str, str, str, str, str, str, int]]:
    """6 TERMINATED leavers NV-046..NV-051, Ngày nghỉ within last 12 months."""
    data: list[tuple[str, str, str, str, str, int]] = [
        ("Nguyễn Văn Phú", "Nhân viên Kinh doanh", "CUS", "10/03/2021", "15/11/2025", 14_000_000),
        ("Lê Thị Hạnh", "Kế toán kho", "FIN", "22/07/2020", "31/01/2026", 13_000_000),
        ("Trần Văn Kỳ", "Nhân viên Giao nhận", "OPS", "05/05/2022", "28/02/2026", 11_000_000),
        ("Phạm Thị Nhung", "Chuyên viên Chăm sóc KH", "CUS", "18/09/2021", "30/04/2026", 12_000_000),
        ("Đỗ Văn Chung", "Chuyên viên IT nội bộ", "ADMIN", "12/01/2020", "30/06/2026", 18_000_000),
        ("Vũ Thị Lệ", "Chuyên viên Tuyển dụng", "HR", "03/11/2022", "31/08/2026", 15_000_000),
    ]
    out: list[tuple[str, str, str, str, str, str, str, int]] = []
    for i, (name, role, dept, start, leave, salary) in enumerate(data, start=46):
        code = f"NV-{i:03d}"
        out.append((code, name, role, dept, start, leave, "TERMINATED", salary))
    return out


DEPT_NAMES: Final[dict[str, str]] = {
    "ADMIN": "Hành chính", "FIN": "Tài chính — Kế toán", "CUS": "Kinh doanh",
    "OPS": "Vận hành", "HR": "Nhân sự",
}
# Department heads (Quản lý trực tiếp of their staff); the CEO NV-001 heads ADMIN.
DEPT_HEADS: Final[dict[str, str]] = {
    "ADMIN": "NV-001", "FIN": "NV-011", "CUS": "NV-019", "OPS": "NV-031", "HR": "NV-041",
}
# T-641 / 08 §4.6: intentional error rows for the C5 import demo (split into a fix file).
DOC06_ERROR_ROWS: Final[list[list[object]]] = [
    # 1. unknown manager ("thiếu quản lý": NV-999 is not in the file nor in the company)
    ["CUS", "Kinh doanh", "Nhân viên Kinh doanh", "NV-052", "Mai Văn Lực", "NV-999",
     "01/09/2026", "active", 14_000_000],
    # 2. wrong date format (month 13)
    ["OPS", "Vận hành", "Nhân viên Kho", "NV-053", "Tạ Thị Hiền", "NV-031",
     "15/13/2026", "active", 11_000_000],
    # 3. department not in the company: no department code, unknown department name
    [None, "Phòng Marketing", "Chuyên viên Marketing", "NV-054", "Kiều Văn Tú", "NV-001",
     "01/10/2026", "active", 16_000_000],
]
DOC06_HEADERS: Final[list[str]] = [
    "Mã phòng ban", "Phòng ban", "Chức danh", "Mã NV", "Họ tên", "Quản lý trực tiếp",
    "Ngày vào làm", "Trạng thái", "Lương",
]


def _doc06_row(e: tuple[str, str, str, str, str, str, str, int]) -> list[object]:
    code, name, role, dept, start, _leave, _status, salary = e
    head = DEPT_HEADS[dept]
    manager = None if code == "NV-001" else ("NV-001" if code == head else head)
    return [dept, DEPT_NAMES[dept], role, code, name, manager, start, "active", salary]


def gen_doc06(path: Path) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Nhân sự"
    ws.append(DOC06_HEADERS)
    _style_header(ws, len(DOC06_HEADERS))
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    active = _build_active_employees()
    terminated = _build_terminated_employees()
    active_sum = sum(e[7] for e in active)
    dist: dict[str, int] = {}
    for e in active:
        dist[e[3]] = dist.get(e[3], 0) + 1
    expected = {"FIN": 8, "CUS": 12, "OPS": 10, "HR": 5, "ADMIN": 10}
    assert dist == expected, f"DOC-06: dept distribution {dist} != {expected}"
    assert all(DEPT_HEADS[d] in {e[0] for e in active if e[3] == d} for d in DEPT_HEADS)
    rows = [_doc06_row(e) for e in active] + [list(r) for r in DOC06_ERROR_ROWS]
    assert len(DOC06_ERROR_ROWS) >= 3, "DOC-06: needs ≥ 3 intentional error rows"
    for row in rows:
        ws.append(row)
        r = ws.max_row
        ws.cell(row=r, column=9).number_format = "#,##0"
        for c in range(1, len(DOC06_HEADERS) + 1):
            ws.cell(row=r, column=c).border = border
    for i, w in enumerate([14, 22, 36, 10, 24, 18, 14, 12, 16], start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.freeze_panes = "A2"
    # Leavers on a second sheet (the import reads the first sheet with data).
    left = wb.create_sheet("Đã nghỉ việc")
    left.append(["Mã NV", "Họ tên", "Chức danh", "Phòng ban", "Ngày vào", "Ngày nghỉ",
                 "Trạng thái", "Lương"])
    _style_header(left, 8)
    for e in terminated:
        left.append(list(e))
    note = left.cell(row=left.max_row + 2, column=1)  # not on the import sheet (would be a row)
    note.value = "Tổng quỹ lương tháng (ACTIVE) = 855.000.000 đ"
    note.font = Font(bold=True, italic=True, color="1F4E79")
    _save_wb(wb, path)
    return (
        f"DOC-06: {len(active)} active (ΣLương={num(active_sum)}) + "
        f"{len(DOC06_ERROR_ROWS)} error rows + {len(terminated)} terminated (sheet 2), "
        f"dist={expected}, {path.name}"
    )


# ===========================================================================
# UC-07 — onboarding roster `ABC_DanhSachNhanSu_Onboarding.xlsx` (R-DEC-79, 08 §4.6, TC-M16-22)
# ===========================================================================
# A fresh roster for the SCR-66 wizard (fake data, DEC-136). Department / employee codes never
# collide with the seed (BOD/SAL/…, NV-0001…) nor DOC-06 (NV-001…), so the E2E import creates
# rows instead of reusing them. Columns follow #4 HR_ROSTER aliases (Email = level 3, Lương =
# level 4 → dropped for ADM). Intentional error rows: unknown manager, wrong date format,
# duplicate email. Valid / invalid counts are computed by `uc07_expectations()`.
UC07_FILE: Final[str] = "ABC_DanhSachNhanSu_Onboarding.xlsx"
UC07_HEADERS: Final[list[str]] = [
    "Mã phòng ban", "Phòng ban", "Chức danh", "Mã NV", "Họ tên", "Quản lý trực tiếp",
    "Ngày vào làm", "Trạng thái", "Email", "Lương",
]
UC07_DEPTS: Final[list[tuple[str, str, int]]] = [  # (code, name, headcount incl. the head)
    ("OB-BGD", "Ban Giám đốc", 2), ("OB-KD", "Kinh doanh", 8), ("OB-VH", "Vận hành", 7),
    ("OB-TC", "Tài chính — Kế toán", 4), ("OB-NS", "Nhân sự", 3),
]
_UC07_FIRST: Final[list[str]] = ["An", "Bình", "Chi", "Dũng", "Giang", "Hà", "Khánh", "Linh",
                                 "Minh", "Nam", "Oanh", "Phúc", "Quân", "Sơn", "Thảo", "Uyên",
                                 "Vy", "Xuân", "Yến", "Hưng", "Lộc", "Mai", "Nga", "Tâm"]
_UC07_LAST: Final[list[str]] = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi"]


def _uc07_valid_rows() -> list[list[object]]:
    rows: list[list[object]] = []
    seq = 0
    ceo = "OB0001"
    for code, name, size in UC07_DEPTS:
        head = None
        for i in range(size):
            seq += 1
            emp = f"OB{seq:04d}"
            if code == "OB-BGD" and i == 0:
                title, manager = "Tổng Giám đốc", None
            elif i == 0:
                title, manager = f"Trưởng phòng {name}", ceo
            else:
                title, manager = f"Chuyên viên {name}", head or ceo
            if i == 0:
                head = emp
            full = f"{_UC07_LAST[seq % len(_UC07_LAST)]} Văn {_UC07_FIRST[seq % len(_UC07_FIRST)]}"
            start = f"{1 + seq % 27:02d}/{1 + seq % 9:02d}/2025"
            rows.append([code, name, title, emp, full, manager, start, "active",
                         f"ob{seq:04d}@abc-e2e.demo", 12_000_000 + 500_000 * (seq % 9)])
    return rows


UC07_ERROR_ROWS: Final[list[list[object]]] = [
    # 1. "thiếu quản lý": OB9999 is neither in the file nor in the company
    ["OB-KD", "Kinh doanh", "Chuyên viên Kinh doanh", "OB0901", "Tạ Văn Lực", "OB9999",
     "01/09/2025", "active", "ob0901@abc-e2e.demo", 13_000_000],
    # 2. wrong date format (day 31 of month 02)
    ["OB-VH", "Vận hành", "Chuyên viên Vận hành", "OB0902", "Kiều Thị Hiền", "OB0011",
     "31/02/2025", "active", "ob0902@abc-e2e.demo", 11_000_000],
    # 3. duplicate email (same as OB0003, an earlier valid row)
    ["OB-KD", "Kinh doanh", "Chuyên viên Kinh doanh", "OB0903", "Lương Văn Tú", "OB0003",
     "01/10/2025", "active", "ob0003@abc-e2e.demo", 12_500_000],
]


def uc07_expectations() -> dict[str, int]:
    """Counts the E2E checks against (TC-M16-23) — computed, not typed in."""
    valid = _uc07_valid_rows()
    return {"rows_total": len(valid) + len(UC07_ERROR_ROWS), "rows_valid": len(valid),
            "rows_invalid": len(UC07_ERROR_ROWS), "departments": len({r[0] for r in valid}),
            "employees": len(valid)}


def gen_uc07(path: Path) -> str:
    valid = _uc07_valid_rows()
    emails = [str(r[8]) for r in valid]
    assert len(set(emails)) == len(emails), "UC-07: valid rows must have unique emails"
    assert sum(d[2] for d in UC07_DEPTS) == len(valid)
    assert any(r[8] in emails for r in UC07_ERROR_ROWS), "UC-07: needs a duplicate email row"
    wb = Workbook()
    ws = wb.active
    ws.title = "Nhân sự"
    ws.append(UC07_HEADERS)
    _style_header(ws, len(UC07_HEADERS))
    for row in valid + [list(r) for r in UC07_ERROR_ROWS]:
        ws.append(row)
        ws.cell(row=ws.max_row, column=10).number_format = "#,##0"
    for i, w in enumerate([14, 22, 30, 10, 22, 18, 14, 12, 26, 14], start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.freeze_panes = "A2"
    _save_wb(wb, path)
    e = uc07_expectations()
    return (f"UC-07: {e['rows_total']} rows = {e['rows_valid']} valid + {e['rows_invalid']} "
            f"intentional errors, {e['departments']} departments, {path.name}")


# ===========================================================================
# DOC-07 — KPI/OKR Q4/2026 (doc type #2 PLAN_KPI_OKR): .xlsx plan + .docx narrative
# ===========================================================================
DOC07_PERIOD: Final[str] = "2026-Q4"
DOC07_HEADERS: Final[list[str]] = [
    "Kỳ", "Mục tiêu", "Kết quả then chốt", "Đơn vị", "Giá trị nền", "Chỉ tiêu",
    "Người phụ trách", "Mã KPI", "Tên KPI", "Chỉ tiêu kỳ",
]
# (objective, key result, unit, baseline, target, owner code, kpi code, kpi name, kpi target)
# Owner codes = seeded department heads (NV-0004 Sales, NV-0088 CFO, NV-0041 Ops, NV-0100 HR,
# NV-0108 Product); KPI codes = seeded KPIs → the plan upserts targets on existing KPIs.
DOC07_ROWS: Final[list[tuple[str, str, str, int, int, str, str, str, float]]] = [
    ("Tăng trưởng doanh thu Q4", "Doanh thu thuần Q4 đạt 80 tỷ", "tỷ VND", 72, 80,
     "NV-0004", "KPI-CO-01", "Doanh thu thuần (tỷ)", 27),
    ("Tăng trưởng doanh thu Q4", "Ký mới 12 khách hàng lớn", "khách hàng", 7, 12,
     "NV-0004", "KPI-SAL-01", "Doanh số mới khách hàng lớn (tỷ)", 6),
    ("Tăng trưởng doanh thu Q4", "Tạo 90 cơ hội mới", "cơ hội", 60, 90,
     "NV-0004", "KPI-SAL-02", "Số cơ hội mới", 30),
    ("Lành mạnh tài chính", "Giảm DSO xuống 40 ngày", "ngày", 52, 40,
     "NV-0088", "KPI-FIN-01", "DSO (ngày)", 40),
    ("Lành mạnh tài chính", "Chi phí vận hành ≤ 18% doanh thu", "%", 21, 18,
     "NV-0088", "KPI-FIN-02", "Chi phí vận hành / doanh thu (%)", 18),
    ("Lành mạnh tài chính", "Biên lợi nhuận gộp ≥ 18%", "%", 16, 18,
     "NV-0088", "KPI-CO-02", "Biên lợi nhuận gộp (%)", 18),
    ("Dịch vụ đúng hẹn", "Bảo trì đúng SLA 95%", "%", 88, 95,
     "NV-0041", "KPI-SVC-01", "Tỷ lệ bảo trì đúng SLA (%)", 95),
    ("Dịch vụ đúng hẹn", "Giao hàng trung bình ≤ 2 ngày", "ngày", 3, 2,
     "NV-0041", "KPI-SVC-02", "Thời gian giao hàng TB (ngày)", 2),
    ("Đội ngũ đủ người", "Thời gian tuyển dụng ≤ 30 ngày", "ngày", 42, 30,
     "NV-0100", "KPI-HR-01", "Thời gian tuyển dụng TB (ngày)", 30),
    ("Số hóa bán hàng", "40% đơn hàng qua ABC Order", "%", 28, 40,
     "NV-0108", "KPI-PRD-01", "Đơn hàng qua ABC Order (%)", 40),
    ("Số hóa bán hàng", "Không quá 1 sự cố nghiêm trọng / tháng", "sự cố", 3, 1,
     "NV-0108", "KPI-PRD-02", "Sự cố nghiêm trọng / tháng", 1),
]


def _doc07_check() -> tuple[int, int]:
    objectives = {r[0] for r in DOC07_ROWS}
    assert len(DOC07_ROWS) == 11, f"DOC-07: expected 11 KR rows, got {len(DOC07_ROWS)}"
    assert len(objectives) == 5, f"DOC-07: expected 5 objectives, got {len(objectives)}"
    assert len({r[6] for r in DOC07_ROWS}) == len(DOC07_ROWS), "DOC-07: KPI code repeated"
    return len(objectives), len(DOC07_ROWS)


def gen_doc07(path: Path) -> str:
    n_obj, n_kr = _doc07_check()
    wb = Workbook()
    ws = wb.active
    ws.title = "OKR KPI Q4 2026"
    ws.append(DOC07_HEADERS)
    _style_header(ws, len(DOC07_HEADERS))
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in DOC07_ROWS:
        ws.append([DOC07_PERIOD, *row])
        for c in range(1, len(DOC07_HEADERS) + 1):
            ws.cell(row=ws.max_row, column=c).border = border
    for i, w in enumerate([10, 26, 36, 12, 12, 10, 16, 12, 34, 12], start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    ws.freeze_panes = "A2"
    _save_wb(wb, path)
    return f"DOC-07: {n_obj} objectives / {n_kr} KR + KPI target rows ({DOC07_PERIOD}), {path.name}"


def gen_doc07_docx(path: Path) -> str:
    """Same plan as a Word document: one heading per objective + a KR/KPI table."""
    n_obj, n_kr = _doc07_check()
    document = Document()
    _set_doc_font(document)
    document.core_properties.author = COMPANY
    document.add_heading("KẾ HOẠCH OKR / KPI QUÝ 4/2026", level=1)
    document.add_paragraph(f"{COMPANY}. Kỳ: {DOC07_PERIOD}. Ngày lập: {REF_DATE}.")
    seen: list[str] = []
    for r in DOC07_ROWS:
        if r[0] not in seen:
            seen.append(r[0])
    for objective in seen:
        document.add_heading(f"Mục tiêu: {objective}", level=2)
        table = document.add_table(rows=1, cols=len(DOC07_HEADERS))
        table.style = "Table Grid"
        for i, h in enumerate(DOC07_HEADERS):
            table.rows[0].cells[i].text = h
        for r in (x for x in DOC07_ROWS if x[0] == objective):
            cells = table.add_row().cells
            for i, v in enumerate([DOC07_PERIOD, *r]):
                cells[i].text = f"{v:g}" if isinstance(v, float) else str(v)
    _save_docx(document, path)
    return f"DOC-07 (.docx): {n_obj} objectives / {n_kr} KR tables, {path.name}"


# ===========================================================================
# DOC-08 — Period results report Q3/2026 (doc type #3 PERIOD_REPORT, reportlab)
# ===========================================================================
DOC08_HEADERS: Final[list[str]] = ["Mã KPI", "Kỳ", "Thực tế", "Ghi chú"]
# (kpi code, period, actual, note) — monthly actuals for Q3/2026 on seeded KPIs.
DOC08_ROWS: Final[list[tuple[str, str, float, str]]] = [
    ("KPI-CO-01", "2026-07", 24.8, "Doanh thu thuần tháng 7"),
    ("KPI-CO-01", "2026-08", 25.6, "Doanh thu thuần tháng 8"),
    ("KPI-CO-01", "2026-09", 26.1, "Doanh thu thuần tháng 9"),
    ("KPI-FIN-01", "2026-09", 48, "DSO cuối quý"),
    ("KPI-SVC-01", "2026-09", 91.5, "Bảo trì đúng SLA"),
    ("KPI-SAL-02", "2026-09", 27, "Cơ hội mới tháng 9"),
    ("KPI-HR-01", "2026-09", 38, "Thời gian tuyển dụng TB"),
    ("KPI-PRD-01", "2026-09", 31.2, "Đơn qua ABC Order"),
]
DOC08_REVENUE_Q3: Final[float] = 76.5  # Σ KPI-CO-01 Q3 (tỷ VND)


def gen_doc08(path: Path) -> str:
    q3 = round(sum(r[2] for r in DOC08_ROWS if r[0] == "KPI-CO-01"), 1)
    assert q3 == DOC08_REVENUE_Q3, f"DOC-08: Σ revenue Q3 {q3} != {DOC08_REVENUE_Q3}"
    assert len(DOC08_ROWS) == 8, f"DOC-08: expected 8 rows, got {len(DOC08_ROWS)}"
    _register_fonts()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("VNTitle8", parent=styles["Title"], fontName=FONT_BOLD, fontSize=15)
    body = ParagraphStyle("VNBody8", parent=styles["Normal"], fontName=FONT_REGULAR,
                          fontSize=10, leading=14)
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=20 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title="BÁO CÁO KẾT QUẢ QUÝ 3/2026")
    data = [DOC08_HEADERS] + [[c, k, f"{v:g}".replace(".", ","), n] for c, k, v, n in DOC08_ROWS]
    table = Table(data, colWidths=[30 * mm, 25 * mm, 25 * mm, 90 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))
    story = [
        Paragraph("BÁO CÁO KẾT QUẢ QUÝ 3/2026", title),
        Paragraph(f"{COMPANY} — MST {COMPANY_TAX}. Kỳ báo cáo: 2026-Q3. Ngày lập: {REF_DATE}.",
                  body),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph(f"Tổng doanh thu thuần Q3: {f'{q3:g}'.replace('.', ',')} tỷ VND.", body),
    ]
    doc.build(story)
    return f"DOC-08: {len(DOC08_ROWS)} KPI actuals Q3/2026 (Σ doanh thu {q3} tỷ), {path.name}"


# ===========================================================================
# main
# ===========================================================================
def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Global asserts on the hard invariants (fail fast, clear messages) ---
    invoice_subtotal = sum(row[5] for row in INVOICES)
    if invoice_subtotal != INVOICE_SUBTOTAL_TARGET:
        raise AssertionError(
            f"Σ of the 47 invoice subtotals = {invoice_subtotal:,}, "
            f"expected {INVOICE_SUBTOTAL_TARGET:,}"
        )
    if len(INVOICES) != 47:
        raise AssertionError(f"Expected 47 invoices, got {len(INVOICES)}")

    active_salary_sum = sum(e[7] for e in _build_active_employees())
    if active_salary_sum != ACTIVE_PAYROLL_TARGET:
        raise AssertionError(
            f"Σ of 45 ACTIVE salaries = {active_salary_sum:,}, "
            f"expected {ACTIVE_PAYROLL_TARGET:,}"
        )

    targets = [
        (DATA_DIR / "DOC-01-bao-cao-tai-chinh-q3-2026.pdf", gen_doc01),
        (DATA_DIR / "DOC-02-danh-sach-hoa-don-t9-2026.xlsx", gen_doc02),
        (DATA_DIR / "DOC-03-bao-cao-sales-t9-2026.pdf", gen_doc03),
        (DATA_DIR / "DOC-04-hop-dong-mau.pdf", gen_doc04),
        (DATA_DIR / "DOC-05-bien-ban-hop-giao-ban.docx", gen_doc05),
        (DATA_DIR / "DOC-06-danh-sach-nhan-su.xlsx", gen_doc06),
        (DATA_DIR / "DOC-07-kpi-okr-q4-2026.xlsx", gen_doc07),
        (DATA_DIR / "DOC-07-kpi-okr-q4-2026.docx", gen_doc07_docx),
        (DATA_DIR / "DOC-08-bao-cao-ket-qua-q3-2026.pdf", gen_doc08),
        (DATA_DIR / UC07_FILE, gen_uc07),
    ]

    print(f"Σ invoice subtotals = {invoice_subtotal:,} (OK)")
    print(f"Σ active salaries   = {active_salary_sum:,} (OK)")
    print(f"Writing {len(targets)} documents into {DATA_DIR} ...\n")

    for path, fn in targets:
        if path.exists():
            path.unlink()  # idempotent overwrite
        summary = fn(path)
        size = path.stat().st_size
        print(f"  ✓ {path}  ({size:,} bytes)")
        print(f"    {summary}")

    print(f"\nAll {len(targets)} demo documents generated successfully.")


if __name__ == "__main__":
    main()
