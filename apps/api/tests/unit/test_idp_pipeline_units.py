"""Unit tests for IDP pipeline building blocks (T-401..T-405) — no DB.

Covers MIME whitelist + magic bytes, malware scan (EICAR), per-format text extraction,
the LLM extractor's confidence bands + classification routing, and the business validator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.modules.idp.services.extractor import (
    Extractor,
    classification_for_sensitivity,
    confidence_band,
)
from app.modules.idp.services.malware_scan import scan_bytes
from app.modules.idp.services.mime import EXT_MIME, resolve_mime
from app.modules.idp.services.preprocess import extract_pages
from app.modules.idp.services.schema_registry import INVOICE_FIELDS, INVOICE_RULES
from app.modules.idp.services.validator import Validator
from integration.idp import sample_docs as s


# ---------------- MIME (T-401) ----------------
def test_resolve_mime_accepts_four_core_types() -> None:
    assert resolve_mime("a.pdf", "application/pdf", s.invoice_pdf()[:64]) == EXT_MIME[".pdf"]
    assert resolve_mime("a.docx", "x", s.contract_docx()[:64]) == EXT_MIME[".docx"]
    assert resolve_mime("a.xlsx", "x", s.expenses_xlsx()[:64]) == EXT_MIME[".xlsx"]
    assert resolve_mime("a.png", "image/png", s.png_image()[:64]) == EXT_MIME[".png"]


def test_resolve_mime_rejects_unknown_and_mismatched_magic() -> None:
    assert resolve_mime("a.exe", "application/x-dosexec", b"MZ\x90\x00") is None
    # .pdf extension but PNG header → rejected
    assert resolve_mime("fake.pdf", "application/pdf", s.png_image()[:64]) is None


# ---------------- Malware scan (T-402) ----------------
def test_scan_detects_eicar() -> None:
    res = scan_bytes(s.eicar_txt())
    assert res.status == "INFECTED"
    assert res.signature


def test_scan_clean_file_passes_or_skips() -> None:
    # No ClamAV container in CI + CLAMAV_REQUIRED=false → SKIPPED (still "not infected").
    res = scan_bytes(s.invoice_pdf())
    assert res.status in ("CLEAN", "SKIPPED")


# ---------------- OCR / text extraction (T-403) ----------------
def test_extract_pdf_text_layer() -> None:
    r = extract_pages(s.invoice_pdf(), EXT_MIME[".pdf"])
    assert r.page_count == 1
    assert r.pages[0].text_layer_exists and not r.pages[0].ocr_used
    assert "10000000" in r.full_text


def test_extract_scan_pdf_uses_ocr_path() -> None:
    r = extract_pages(s.scan_pdf(), EXT_MIME[".pdf"])
    assert r.pages[0].ocr_used and not r.pages[0].text_layer_exists


def test_extract_docx_and_xlsx() -> None:
    assert "500" in extract_pages(s.contract_docx(), EXT_MIME[".docx"]).full_text
    rx = extract_pages(s.expenses_xlsx(), EXT_MIME[".xlsx"])
    assert rx.pages[0].sheet_name == "ChiPhi"
    assert "2500000" in rx.full_text


# ---------------- Extractor confidence/classification (T-404) ----------------
def test_confidence_bands() -> None:
    assert confidence_band(0.95) == "HIGH"
    assert confidence_band(0.75) == "MEDIUM"
    assert confidence_band(0.40) == "LOW"


def test_classification_routing_by_sensitivity() -> None:
    assert classification_for_sensitivity(4) == "SECRET"
    assert classification_for_sensitivity(3) == "CONFIDENTIAL"
    assert classification_for_sensitivity(2) == "INTERNAL"
    assert classification_for_sensitivity(1) == "PUBLIC"


class _FakeGateway:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.requests: list = []

    async def chat(self, req):
        from app.core.model_gateway import ChatResponse

        self.requests.append(req)
        return ChatResponse(content="", provider="fake", model="m", data=self.data)


@pytest.mark.asyncio
async def test_extractor_maps_five_fields_with_bands() -> None:
    data = {
        "invoice_number": {"value": "0001234", "raw_text": "0001234", "confidence": 0.97},
        "issue_date": {"value": "2026-09-15", "confidence": 0.93},
        "subtotal": {"value": 10000000, "confidence": 0.91},
        "vat_amount": {"value": 1000000, "confidence": 0.5},
        "total_amount": {"value": 11000000, "confidence": None and 0},
    }
    gw = _FakeGateway(data)
    out = await Extractor(gw).extract(
        schema_fields=INVOICE_FIELDS, page_text="x", sensitivity_level=2
    )
    by = {f.field_name: f for f in out.fields}
    assert by["invoice_number"].confidence_band == "HIGH"
    assert by["vat_amount"].confidence_band == "LOW"
    # a field absent from the model output is null with confidence 0 (never fabricated)
    assert by["seller_name"].value is None and by["seller_name"].confidence == 0.0
    assert by["subtotal"].is_critical is True
    assert gw.requests[0].task == "extract"
    assert gw.requests[0].classification == "INTERNAL"


@pytest.mark.asyncio
async def test_extractor_blocks_nothing_but_routes_secret() -> None:
    out_req_class = None
    gw = _FakeGateway({})
    await Extractor(gw).extract(schema_fields=INVOICE_FIELDS, page_text="x", sensitivity_level=4)
    out_req_class = gw.requests[0].classification
    assert out_req_class == "SECRET"


# ---------------- Validator (T-405) ----------------
def test_validator_rejects_negative_amount_and_future_date() -> None:
    from datetime import date

    v = Validator(INVOICE_RULES, today=date(2026, 10, 20))
    bad = {
        "subtotal": -5,
        "issue_date": "2027-01-01",
        "vat_rate_pct": 10,
        "vat_amount": 0,
        "total_amount": -5,
    }
    out = v.validate(bad)
    codes = {e["rule"] for e in out.errors}
    assert "VR-INV-SUB" in codes  # subtotal > 0 fails
    assert "VR-INV-02" in codes  # future date fails
    assert not out.ok


def test_validator_passes_valid_invoice_and_sum_rule() -> None:
    from datetime import date

    v = Validator(INVOICE_RULES, today=date(2026, 10, 20))
    good = {
        "subtotal": 10000000,
        "issue_date": "2026-09-15",
        "vat_rate_pct": 10,
        "vat_amount": 1000000,
        "total_amount": 11000000,
    }
    out = v.validate(good)
    assert out.ok, out.errors


def test_validator_required_fields_flag_missing() -> None:
    v = Validator([])
    out = v.validate({"a": None}, required={"a", "b"})
    fields = {e["field"] for e in out.errors}
    assert fields == {"a", "b"}


def test_validator_sum_rule_rejects_wrong_total() -> None:
    from datetime import date

    v = Validator(INVOICE_RULES, today=date(2026, 10, 20))
    out = v.validate(
        {
            "subtotal": 10000000,
            "vat_amount": 1000000,
            "total_amount": 9999999,
            "issue_date": "2026-09-15",
            "vat_rate_pct": 10,
        }
    )
    assert "VR-INV-05" in {e["rule"] for e in out.errors}
