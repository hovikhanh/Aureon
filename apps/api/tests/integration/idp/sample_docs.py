"""In-memory sample documents for IDP pipeline tests (04 §8, DEC-120). Built from runtime deps
only (pypdf text-layer PDF, python-docx, openpyxl) — no `reportlab`, so CI needs nothing extra.
All data is fake (Công ty ABC demo), never real PII."""

from __future__ import annotations

import io

from app.modules.idp.services.malware_scan import EICAR

INVOICE_TEXT = (
    "HOA DON GIA TRI GIA TANG\n"
    "So hoa don: 0001234\n"
    "Ngay: 2026-09-15\n"
    "Nguoi ban: Cong ty TNHH TM&DV ABC - MST: 0301234567\n"
    "Tien hang (subtotal): 10000000\n"
    "Thue suat: 10%\n"
    "Tien thue VAT: 1000000\n"
    "Tong cong: 11000000\n"
)


def _pdf_with_text(text: str) -> bytes:
    """Minimal single-page PDF carrying a text layer pypdf can extract.

    Hand-built so no PDF-authoring dependency is required; the content stream draws each line
    with `Tj`, which `PdfReader.extract_text()` reads back.
    """
    lines = text.splitlines()
    body_lines = "\n".join(
        f"({ln.replace('(', ' ').replace(')', ' ')}) Tj 0 -16 Td" for ln in lines
    )
    content = f"BT /F1 12 Tf 72 760 Td\n{body_lines}\nET".encode("latin-1", "replace")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
    )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
    out.write(trailer.encode())
    return out.getvalue()


def invoice_pdf() -> bytes:
    return _pdf_with_text(INVOICE_TEXT)


def scan_pdf() -> bytes:
    """A PDF with no text layer (image-only) → forces the OCR path (empty text in stub mode)."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>",
        b"<< /Length 8 >>\nstream\n        \nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
    out.write(trailer.encode())
    return out.getvalue()


def contract_docx() -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading("HOP DONG DICH VU", level=1)
    doc.add_paragraph("Ben A: Cong ty TNHH TM&DV ABC")
    doc.add_paragraph("Ben B: Cong ty XYZ")
    doc.add_paragraph("Gia tri hop dong: 500.000.000 VND")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def expenses_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "ChiPhi"
    ws.append(["Ngay", "Noi dung", "So tien"])
    ws.append(["2026-09-01", "Tiep khach", 2500000])
    ws.append(["2026-09-03", "Van phong pham", 1200000])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def eicar_txt() -> bytes:
    # Delivered as a PDF-typed payload so it passes MIME sniffing then trips the scanner.
    return b"%PDF-1.4\n" + EICAR + b"\n%%EOF"


def png_image() -> bytes:
    # 1x1 transparent PNG (valid magic) — exercises the image/OCR branch.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6360000002000154a24f1a0000000049454e44ae426082"
    )
