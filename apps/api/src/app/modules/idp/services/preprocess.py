"""Text-layer check + OCR + per-format text extraction (04 §3 steps 2–3, FR-DC-08c).

Produces one `ENT-DocumentPage` per page/sheet with `text_content`, `text_layer_exists`,
`ocr_used`, `ocr_confidence`. Order of preference per 04: check the text layer first and only
OCR pages that are missing/poor (`text_layer_exists == False`).

Backends by mime:
- PDF   → `pypdf` text layer; a page without one is OCRed from the raster images embedded in it.
  There is no PDF rasteriser in the dependency set, so a page drawn with vector operators and no
  text layer cannot be read: it is reported `no_raster`, never silently empty.
- DOCX  → `python-docx` (one logical page).
- XLSX  → `openpyxl` (one page per sheet; `sheet_name` set).
- CSV   → decoded text (one page).
- image → OCR (`OCR_PROVIDER`).

OCR backend `stub` (default) returns empty text with status `unavailable` so the pipeline is
testable without PaddleOCR; `paddle` is used only when the package is importable (DEC-049).

Every OCRed page carries `ocr_status`: `ok`, `empty` (ran, read nothing), `failed` (raised),
`unavailable` (stub backend), `no_raster` (scanned page without an embedded image). Anything but
`ok` reaches the routing reasons (`Pipeline`), so a reviewer sees why a document came back empty.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_config
from app.modules.idp.services.mime import EXT_MIME

PDF = EXT_MIME[".pdf"]
DOCX = EXT_MIME[".docx"]
XLSX = EXT_MIME[".xlsx"]
CSV = EXT_MIME[".csv"]
TXT = "text/plain"  # R-DEC-96: C2 natural-language text stored as a plain-text object
IMAGES = frozenset({"image/png", "image/jpeg", "image/webp", "image/heic"})
MIN_RASTER_PX = 64  # logos and rules embedded in a page are not the scan

log = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text_content: str
    text_layer_exists: bool
    ocr_used: bool
    ocr_confidence: float | None = None
    sheet_name: str | None = None
    ocr_status: str | None = None  # None when OCR did not run on this page


@dataclass
class PreprocessResult:
    pages: list[PageText] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def full_text(self) -> str:
        return "\n".join(p.text_content for p in self.pages if p.text_content)

    @property
    def ocr_problems(self) -> list[tuple[int, str]]:
        """`(page_number, status)` of every page OCR could not read."""
        return [(p.page_number, p.ocr_status) for p in self.pages
                if p.ocr_status not in (None, "ok")]  # fmt: skip


def _deskew_image(data: bytes) -> bytes:
    """FR-DC-08 (R-DEC-98): normalise a captured photo (C4) before OCR — EXIF auto-rotate,
    grayscale, autocontrast. Pillow is available transitively (pillow-heif, DEC-151); if it
    cannot be imported or the bytes are not a decodable image, return the input unchanged."""
    try:
        from PIL import Image, ImageOps
    except Exception:  # pragma: no cover - Pillow always present via pillow-heif
        return data
    try:
        with Image.open(io.BytesIO(data)) as opened:
            im = ImageOps.exif_transpose(opened) or opened  # correct orientation (phone capture)
            im = ImageOps.grayscale(im)
            im = ImageOps.autocontrast(im)  # lift faint ink / uneven lighting
            out = io.BytesIO()
            im.save(out, format="PNG")
            return out.getvalue()
    except Exception:
        return data


_PADDLE_ENGINE: Any = None  # lazily-built, process-wide singleton (model load is expensive)


def _paddle_engine() -> Any:  # pragma: no cover - optional paddle dependency, gated by R-DEC-146
    """Build the PaddleOCR engine once per process. Vietnamese model, angle classifier on.
    `show_log` is a legacy kwarg (ignored in paddleocr 2.10) kept for older versions.
    `paddleocr` ships no type stubs, hence the `Any` return."""
    global _PADDLE_ENGINE
    if _PADDLE_ENGINE is None:
        from paddleocr import PaddleOCR

        _PADDLE_ENGINE = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)
    return _PADDLE_ENGINE


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    status: str  # ok | empty | failed | unavailable | no_raster


def _ocr(data: bytes, *, preprocess: bool = False) -> OcrResult:
    """OCR a single image (R-DEC-146 — optional `ocr` extra). `preprocess=True` (C4 photo) runs
    `_deskew_image` first (FR-DC-08). A failure is logged and reported as a status, so the
    document goes to review knowing why; it never crashes the pipeline."""
    if preprocess:
        data = _deskew_image(data)
    if get_config().ocr_provider != "paddle":
        return OcrResult("", 0.0, "unavailable")
    try:
        import numpy as np
        from PIL import Image

        with Image.open(io.BytesIO(data)) as opened:
            img = np.asarray(opened.convert("RGB"))
        result = _paddle_engine().ocr(img, cls=True)
    except Exception as exc:
        log.warning("idp ocr: page failed (%s)", type(exc).__name__)  # no content in the log
        return OcrResult("", 0.0, "failed")
    lines = [line[1][0] for block in (result or []) if block for line in block]
    confs = [line[1][1] for block in (result or []) if block for line in block]
    if not lines:
        return OcrResult("", 0.0, "empty")
    return OcrResult("\n".join(lines), float(sum(confs) / len(confs)), "ok")


def _ocr_image(data: bytes, *, preprocess: bool = False) -> tuple[str, float]:
    """`(text, mean_confidence)` of `_ocr`."""
    out = _ocr(data, preprocess=preprocess)
    return out.text, out.confidence


def _raster_images(page: Any) -> list[bytes]:
    """The scan behind a page: its embedded raster images, largest kept, tiny ones dropped."""
    from PIL import Image

    found: list[bytes] = []
    for item in page.images:
        with Image.open(io.BytesIO(item.data)) as opened:
            if min(opened.size) >= MIN_RASTER_PX:
                found.append(item.data)
    return found


def _ocr_pdf_page(page: Any) -> OcrResult:
    if get_config().ocr_provider != "paddle":
        return OcrResult("", 0.0, "unavailable")
    try:
        images = _raster_images(page)
    except Exception as exc:
        log.warning("idp ocr: cannot read page images (%s)", type(exc).__name__)
        return OcrResult("", 0.0, "failed")
    if not images:
        return OcrResult("", 0.0, "no_raster")
    parts = [_ocr(raw) for raw in images]
    read = [r for r in parts if r.status == "ok"]
    if not read:
        status = "failed" if any(r.status == "failed" for r in parts) else "empty"
        return OcrResult("", 0.0, status)
    conf = sum(r.confidence for r in read) / len(read)
    return OcrResult("\n".join(r.text for r in read), conf, "ok")


def _pdf_pages(data: bytes) -> list[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages: list[PageText] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(PageText(i, text, text_layer_exists=True, ocr_used=False))
        else:
            ocr = _ocr_pdf_page(page)
            pages.append(PageText(
                i, ocr.text, text_layer_exists=False, ocr_used=True,
                ocr_confidence=ocr.confidence, ocr_status=ocr.status,
            ))  # fmt: skip
    if pages:
        return pages
    return [PageText(1, "", text_layer_exists=False, ocr_used=True, ocr_confidence=0.0,
                     ocr_status="empty")]  # fmt: skip


def _docx_pages(data: bytes) -> list[PageText]:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(c.text for c in row.cells))
    return [PageText(1, "\n".join(parts), text_layer_exists=True, ocr_used=False)]


def _xlsx_pages(data: bytes) -> list[PageText]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    pages: list[PageText] = []
    for idx, ws in enumerate(wb.worksheets, start=1):
        rows: list[str] = []
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c) for c in row]
            if any(cells):
                rows.append("\t".join(cells))
        pages.append(
            PageText(
                idx, "\n".join(rows), text_layer_exists=True, ocr_used=False, sheet_name=ws.title
            )
        )
    wb.close()
    return pages or [PageText(1, "", text_layer_exists=True, ocr_used=False, sheet_name="Sheet1")]


def _csv_pages(data: bytes) -> list[PageText]:
    text = data.decode("utf-8-sig", errors="replace")
    rows = ["\t".join(r) for r in csv.reader(io.StringIO(text))]
    return [PageText(1, "\n".join(rows), text_layer_exists=True, ocr_used=False)]


def _image_pages(data: bytes) -> list[PageText]:
    # a standalone image upload is a C4 photo capture → deskew/normalise before OCR (R-DEC-98)
    ocr = _ocr(data, preprocess=True)
    return [PageText(1, ocr.text, text_layer_exists=False, ocr_used=True,
                     ocr_confidence=ocr.confidence, ocr_status=ocr.status)]  # fmt: skip


def extract_pages(data: bytes, mime: str) -> PreprocessResult:
    if mime == PDF:
        return PreprocessResult(_pdf_pages(data))
    if mime == DOCX:
        return PreprocessResult(_docx_pages(data))
    if mime == XLSX:
        return PreprocessResult(_xlsx_pages(data))
    if mime == CSV:
        return PreprocessResult(_csv_pages(data))
    if mime == TXT:  # R-DEC-96: one page carrying the decoded C2 natural-language text
        text = data.decode("utf-8", errors="replace")
        return PreprocessResult([PageText(1, text, text_layer_exists=True, ocr_used=False)])
    if mime in IMAGES:
        return PreprocessResult(_image_pages(data))
    # legacy doc/xls not convertible without extra deps → single empty page (needs review)
    return PreprocessResult([PageText(1, "", text_layer_exists=False, ocr_used=False)])
