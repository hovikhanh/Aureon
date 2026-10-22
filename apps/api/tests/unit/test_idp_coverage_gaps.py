"""Extra unit tests to lift modules/idp/services coverage ≥ 90% (S4a exit, 14 §1.3).

Covers validator operators + VN number/date parsing, MIME edge formats (webp/csv/doc/no-ext),
preprocess CSV/image/legacy branches, and malware-scan quarantine on a local store."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.modules.idp.services.malware_scan import MalwareScanService
from app.modules.idp.services.mime import EXT_MIME, resolve_mime, sniff
from app.modules.idp.services.preprocess import extract_pages
from app.modules.idp.services.validator import Validator


# ---------------- MIME ----------------
def test_mime_webp_and_csv_and_doc_and_noext() -> None:
    webp = b"RIFF\x00\x00\x00\x00WEBPxxxx"
    assert resolve_mime("a.webp", "image/webp", webp) == "image/webp"
    assert resolve_mime("a.csv", "text/csv", b"ngay,noi dung\n2026,abc") == EXT_MIME[".csv"]
    assert resolve_mime("a.doc", "application/msword", b"\xd0\xcf\x11\xe0abc") == EXT_MIME[".doc"]
    # no extension, declared type in whitelist
    assert resolve_mime(None, "application/pdf", b"%PDF-1.4") == EXT_MIME[".pdf"]
    # csv with a binary magic → rejected
    assert resolve_mime("a.csv", "text/csv", b"%PDF-1.4") is None


def test_sniff_known_headers() -> None:
    assert sniff(b"%PDF-xxx") == "application/pdf"
    assert sniff(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert sniff(b"nope") is None


# ---------------- preprocess ----------------
def test_preprocess_csv_and_image_and_legacy() -> None:
    csv_pages = extract_pages(b"a,b\n1,2\n", EXT_MIME[".csv"])
    assert "1\t2" in csv_pages.full_text

    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6360000002000154a24f1a0000000049454e44ae426082"
    )
    img = extract_pages(png, "image/png")
    assert img.pages[0].ocr_used is True

    legacy = extract_pages(b"\xd0\xcf\x11\xe0data", EXT_MIME[".doc"])
    assert legacy.page_count == 1 and legacy.pages[0].text_content == ""


# ---------------- validator ----------------
def test_validator_in_gt_lte_required_ops() -> None:
    rules = [
        {
            "code": "R-IN",
            "kind": "field",
            "severity": "fail",
            "expression": {"field": "rate", "op": "in", "values": [0, 10]},
        },
        {
            "code": "R-GTE",
            "kind": "field",
            "severity": "warn",
            "expression": {"field": "x", "op": "gte", "value": 5},
        },
        {
            "code": "R-LTE",
            "kind": "field",
            "severity": "fail",
            "expression": {"field": "y", "op": "lte", "value": 100},
        },
        {
            "code": "R-REQ",
            "kind": "field",
            "severity": "fail",
            "expression": {"field": "z", "op": "required"},
        },
        {
            "code": "R-UNKNOWN",
            "kind": "field",
            "severity": "fail",
            "expression": {"field": "w", "op": "nope"},
        },
    ]
    v = Validator(rules, today=date(2026, 10, 20))
    out = v.validate({"rate": 7, "x": 3, "y": 200, "z": None, "w": 1})
    codes = {e["rule"] for e in out.errors}
    assert "R-IN" in codes  # 7 not in {0,10}
    assert "R-LTE" in codes  # 200 > 100
    assert "R-REQ" in codes  # z missing
    assert "R-GTE" not in codes  # warn severity, not an error
    # warn + unsupported op still produce non-fail entries
    assert any(e.status == "warn" for e in v.validate({"x": 3}).entries)


def test_validator_vn_number_and_date_parsing() -> None:
    rules = [
        {
            "code": "R-SUM",
            "kind": "cross_field",
            "severity": "fail",
            "expression": {
                "op": "sum_equals",
                "target": "total",
                "addends": ["a", "b"],
                "tolerance": 1000,
            },
        },
        {
            "code": "R-DATE",
            "kind": "field",
            "severity": "fail",
            "expression": {"field": "d", "op": "date_not_future"},
        },
    ]
    v = Validator(rules, today=date(2026, 10, 20))
    # VN-formatted numbers "1.000.000" parse; dd/mm/yyyy date parses and is in the past
    out = v.validate(
        {"total": "11.000.000", "a": "10.000.000", "b": "1.000.000", "d": "15/09/2026"}
    )
    assert out.ok, out.errors
    # a missing addend makes the sum rule non-measurable (pass, covered by REQUIRED elsewhere)
    assert Validator(rules).validate({"total": 10, "a": None, "b": 1, "d": None}).ok


# ---------------- malware quarantine ----------------
def test_malware_quarantine_moves_file(tmp_path: Path) -> None:
    import app.core.storage as storage

    store = storage.LocalObjectStore(root=tmp_path)
    key = store.put_stream(iter([b"%PDF-1.4\ninfected"]))
    svc = MalwareScanService(store=store)
    new_key = svc.quarantine(key)
    assert new_key.startswith("quarantine/")
    assert store.exists(new_key)
    assert not store.exists(key)


def test_malware_scan_via_store(tmp_path: Path) -> None:
    import app.core.storage as storage
    from app.modules.idp.services.malware_scan import EICAR

    store = storage.LocalObjectStore(root=tmp_path)
    key = store.put_stream(iter([b"%PDF-1.4\n" + EICAR]))
    assert MalwareScanService(store=store).scan(key).status == "INFECTED"


def test_malware_live_clamd_found_and_clean(monkeypatch) -> None:
    """Fake a reachable ClamAV to cover the clamd FOUND / clean branches."""
    import sys
    import types

    from app.modules.idp.services import malware_scan as ms

    class _Client:
        def __init__(self, verdict: str) -> None:
            self._verdict = verdict

        def ping(self) -> None:
            return None

        def instream(self, _buf) -> dict:
            return {"stream": (self._verdict, "Test-Sig" if self._verdict == "FOUND" else None)}

    def _fake_module(verdict: str):
        mod = types.ModuleType("clamd")
        mod.ClamdNetworkSocket = lambda **kw: _Client(verdict)  # type: ignore[attr-defined]
        return mod

    monkeypatch.setitem(sys.modules, "clamd", _fake_module("FOUND"))
    assert ms.scan_bytes(b"%PDF-1.4\n harmless-looking").status == "INFECTED"

    monkeypatch.setitem(sys.modules, "clamd", _fake_module("OK"))
    assert ms.scan_bytes(b"%PDF-1.4\n harmless-looking").status == "CLEAN"


def test_malware_required_raises_when_unreachable(monkeypatch) -> None:
    from app.core.config import get_config
    from app.core.errors import DependencyUnavailableError
    from app.modules.idp.services import malware_scan as ms

    cfg = get_config()
    monkeypatch.setattr(cfg, "clamav_required", True, raising=False)
    monkeypatch.setattr(ms, "_scan_bytes_clamd", lambda data: None)
    try:
        ms.scan_bytes(b"%PDF-1.4\n clean")
        raised = False
    except DependencyUnavailableError:
        raised = True
    assert raised
