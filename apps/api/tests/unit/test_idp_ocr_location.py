"""F-H3 (scanned PDF OCR, real status), F-H4 (real page or null), F-H7 (keyword hints)."""

import io
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.idp.services import preprocess
from app.modules.idp.services.classifier import invoice_score
from app.modules.idp.services.extractor import Extractor, locate_page
from app.modules.idp.services.mime import EXT_MIME
from app.modules.idp.services.preprocess import extract_pages

PDF = EXT_MIME[".pdf"]


def _scan_pdf(pages: int = 1) -> bytes:
    """A real scanned PDF: pages that are only an embedded raster image, no text layer."""
    from PIL import Image

    imgs = [Image.new("RGB", (200, 300), (255, 255, 255)) for _ in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def _vector_pdf() -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.fixture
def paddle(monkeypatch: pytest.MonkeyPatch) -> Any:
    """`OCR_PROVIDER=paddle` with a fake engine; `calls` holds each array it received."""
    calls: list[Any] = []

    class _Engine:
        def ocr(self, img: Any, cls: bool = True) -> list[Any]:
            calls.append(img)
            return [[[None, (f"dòng {len(calls)}", 0.8)]]]

    monkeypatch.setattr(preprocess, "get_config",
                        lambda: SimpleNamespace(ocr_provider="paddle"))  # fmt: skip
    monkeypatch.setattr(preprocess, "_paddle_engine", lambda: _Engine())
    return calls


def test_scanned_pdf_page_is_ocred_from_its_embedded_image(paddle: Any) -> None:
    r = extract_pages(_scan_pdf(2), PDF)
    assert len(paddle) == 2, "one OCR per page image, not one on the raw PDF bytes"
    assert [p.page_number for p in r.pages] == [1, 2]
    assert r.pages[0].text_content == "dòng 1" and r.pages[1].text_content == "dòng 2"
    assert r.pages[0].ocr_used and not r.pages[0].text_layer_exists
    assert r.pages[0].ocr_status == "ok" and r.pages[0].ocr_confidence == pytest.approx(0.8)
    assert r.ocr_problems == []


def test_scanned_page_without_raster_reports_it(paddle: Any) -> None:
    r = extract_pages(_vector_pdf(), PDF)
    assert paddle == []
    assert r.ocr_problems == [(1, "no_raster")]


def test_ocr_exception_is_a_status_and_is_logged(
    paddle: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class _Boom:
        def ocr(self, img: Any, cls: bool = True) -> list[Any]:
            raise RuntimeError("boom secret text")

    monkeypatch.setattr(preprocess, "_paddle_engine", lambda: _Boom())
    with caplog.at_level("WARNING", logger=preprocess.__name__):
        r = extract_pages(_scan_pdf(), PDF)
    assert r.ocr_problems == [(1, "failed")]
    assert "RuntimeError" in caplog.text and "boom secret text" not in caplog.text


def test_ocr_reading_nothing_is_empty_not_ok(paddle: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Blank:
        def ocr(self, img: Any, cls: bool = True) -> list[Any]:
            return [None]

    monkeypatch.setattr(preprocess, "_paddle_engine", lambda: _Blank())
    assert extract_pages(_scan_pdf(), PDF).ocr_problems == [(1, "empty")]


def test_stub_backend_says_ocr_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preprocess, "get_config", lambda: SimpleNamespace(ocr_provider="stub"))
    r = extract_pages(_scan_pdf(), PDF)
    assert r.ocr_problems == [(1, "unavailable")]


PAGES = [(1, "Số hóa đơn HV-2026-0912\nNgày lập 12/09/2026"),
         (2, "Tổng tiền thanh toán 275.000.000 đ"),
         (3, "Bảng kê 275.000.000 đ")]  # fmt: skip


@pytest.mark.parametrize(
    ("value", "raw", "page"),
    [
        ("HV-2026-0912", None, 1),
        (275000000, None, 2),  # grouping ignored, first page that has it
        (275000000.0, "275.000.000 đ", 2),
        ("2026-09-12", None, 1),  # ISO value, printed dd/mm/yyyy
        (999, None, None),  # not in the document: unknown, not page 1
        ("Công ty không có trong tài liệu", None, None),
        (None, None, None),
        (True, None, None),
        ("x", None, None),  # too short to be evidence
    ],
)
def test_locate_page(value: Any, raw: Any, page: int | None) -> None:
    assert locate_page(PAGES, value, raw) == page


async def test_extractor_reports_the_real_page_or_null() -> None:
    from app.core.model_gateway import ChatResponse

    class _Gw:
        async def chat(self, req: Any) -> ChatResponse:
            data = {"a": {"value": 275000000, "confidence": 0.9},
                    "b": {"value": "khong co", "confidence": 0.9}}  # fmt: skip
            return ChatResponse(content="", provider="fake", model="m", data=data)

    specs = [{"name": "a", "value_type": "money"}, {"name": "b", "value_type": "text"}]
    out = await Extractor(_Gw()).extract(
        schema_fields=specs, page_text="x", sensitivity_level=3, pages=PAGES
    )
    assert out.fields[0].source_location == {"kind": "page", "page": 2}
    assert out.fields[1].source_location == {"kind": "page", "page": None}


def test_vat_hint_does_not_match_vat_tu() -> None:
    assert invoice_score("Biên bản nhập vật tư, vật liệu xây dựng cho kho MST") == 0.0
    assert invoice_score("hóa đơn VAT") > 0


@pytest.mark.parametrize(
    ("value", "kind", "expected"),
    [
        ("250.000.000 đ", "money", 250000000),
        ("275,000,000 VND", "money", 275000000),
        (250000000, "money", 250000000),
        ("khoảng 2 tỷ", "money", "khoảng 2 tỷ"),  # not a whole number: left for the reviewer
        ("10%", "percent", 10),
        ("12,5", "percent", 12.5),
        ("12/09/2026", "date", "2026-09-12"),
        ("2026-09-12", "date", "2026-09-12"),
        ("0305551234", "tax_code", "0305551234"),
        ("HV-2026-0912", "text", "HV-2026-0912"),
    ],
)
def test_normalize_value(value: Any, kind: str, expected: Any) -> None:
    from app.modules.idp.services.extractor import normalize_value

    assert normalize_value(value, kind) == expected


async def test_printed_form_stays_as_raw_text_and_still_locates() -> None:
    from app.core.model_gateway import ChatResponse

    class _Gw:
        async def chat(self, req: Any) -> ChatResponse:
            return ChatResponse(content="", provider="fake", model="m", data={
                "a": {"value": "275.000.000 đ", "confidence": 0.9},
            })  # fmt: skip

    out = await Extractor(_Gw()).extract(
        schema_fields=[{"name": "a", "value_type": "money"}], page_text="x",
        sensitivity_level=3, pages=PAGES,
    )  # fmt: skip
    assert out.fields[0].value == 275000000
    assert out.fields[0].raw_text == "275.000.000 đ"
    assert out.fields[0].source_location["page"] == 2
