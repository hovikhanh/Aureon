"""TC-SEC-PII (DEC-176) — content PII scanning: outbox rejects, audit masks."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import mask, record_audit
from app.core.events.outbox import PIIDetectedError, _check_payload, publish_in_tx
from app.core.pii import MASK, detect_content_pii, mask_text, mask_value, scan_payload

CCCD = "079123456789"
PHONE = "0901234567"
EMAIL = "nguyen.van.a@abc.vn"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (f"Khách CCCD {CCCD} đã xác minh", "CCCD"),
        (f"gọi lại {PHONE} chiều nay", "PHONE"),
        ("hotline 02838123456", "PHONE"),
        (f"liên hệ {EMAIL}", "EMAIL"),
        ("chuyển khoản tới 19036123456789", "BANK_ACCOUNT"),
    ],
)
def test_detects(text: str, kind: str) -> None:
    hits = detect_content_pii(text)
    assert [h.type for h in hits] == [kind]
    assert hits[0].offset == text.index(
        next(t for t in text.split() if any(c.isdigit() or c == "@" for c in t))
    )


@pytest.mark.parametrize(
    "text",
    [
        "khách hỏi về email hóa đơn",  # the word, no address
        "đơn giá 1.000.000 đ",
        "doanh thu 27.500.000.000 đ, tăng 12,5%",
        "tổng 1,250,000,000 VND",
        "INV-2026-000123 hạn 2026-10-20",
        f"ref {uuid.uuid4()}",
        "mã nhân viên EMP-0042, phòng KD",
        "số 123456789",  # 9 digits: CMND not scanned (too many false positives)
    ],
)
def test_no_false_positive(text: str) -> None:
    assert detect_content_pii(text) == []


def test_hits_never_carry_raw_value() -> None:
    hits = scan_payload({"note": f"{CCCD} / {PHONE} / {EMAIL}"})
    assert {h.type for h in hits} == {"CCCD", "PHONE", "EMAIL"}
    blob = repr(hits)
    assert CCCD not in blob
    assert PHONE not in blob
    assert "nguyen.van.a" not in blob
    assert mask_value(CCCD) == MASK + "6789"
    assert mask_value(EMAIL) == MASK + "@abc.vn"
    assert mask_value("12345") == MASK


def test_mask_text_keeps_context() -> None:
    assert mask_text(f"gọi {PHONE} hoặc {EMAIL}.") == f"gọi {MASK}4567 hoặc {MASK}@abc.vn."
    assert mask_text("không có gì") == "không có gì"


def test_scan_payload_paths_and_keys() -> None:
    hits = scan_payload(
        {"items": [{"comment": f"sđt {PHONE}"}], "meta": {"salary": 1}, "amount": 900_000_000_000},
        forbidden_keys=frozenset({"salary"}),
    )
    assert [(h.path, h.type) for h in hits] == [
        ("payload.items[0].comment", "PHONE"),
        ("payload.meta.salary", "FIELD"),
    ]  # integer amounts are aggregates — never scanned


@pytest.mark.parametrize(
    ("payload", "where"),
    [
        ({"note": f"CCCD {CCCD}"}, "payload.note (CCCD)"),
        ({"comment": f"gọi {PHONE}"}, "payload.comment (PHONE)"),
        ({"description": f"gửi {EMAIL}"}, "payload.description (EMAIL)"),
        ({"email": "x"}, "payload.email (FIELD)"),
    ],
)
def test_outbox_rejects_content_pii(payload: dict[str, str], where: str) -> None:
    with pytest.raises(PIIDetectedError) as exc:
        _check_payload(payload)
    msg = str(exc.value)
    assert where in msg
    assert CCCD not in msg
    assert PHONE not in msg
    assert EMAIL not in msg


@pytest.mark.parametrize(
    "payload",
    [
        {"note": "khách hỏi về email hóa đơn"},
        {"note": "giá 1.000.000 đ"},
        {"invoice_id": str(uuid.uuid4()), "amount_paid": 27_500_000, "currency": "VND"},
    ],
)
def test_outbox_accepts_clean(payload: dict[str, object]) -> None:
    _check_payload(payload)


def test_audit_mask_never_raises() -> None:
    masked = mask(
        {
            "salary": 15_000_000,
            "note": f"NV CCCD {CCCD}, sđt {PHONE}",
            "contacts": [EMAIL],
            "amount": 27_500_000,
        }
    )
    assert masked == {
        "salary": MASK,  # 10 §1.8: lương mask `••••`
        "note": f"NV CCCD {MASK}6789, sđt {MASK}4567",
        "contacts": [f"{MASK}@abc.vn"],
        "amount": 27_500_000,
    }


@pytest.mark.integration
async def test_audit_row_is_masked(db_session: AsyncSession) -> None:
    from app.modules.platform.models import AuditLog

    audit_id = await record_audit(
        db_session,
        action="hr.salary_update",
        before={"salary": 12_000_000},
        after={"salary": 15_000_000, "why_note": f"duyệt qua {EMAIL}"},
        metadata={"comment": f"liên hệ {PHONE}"},
    )
    row = (await db_session.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one()
    assert row.before == {"salary": MASK}
    assert row.after == {"salary": MASK, "why_note": f"duyệt qua {MASK}@abc.vn"}
    assert row.metadata_["comment"] == f"liên hệ {MASK}4567"


@pytest.mark.integration
async def test_publish_in_tx_rejects_content_pii(db_session: AsyncSession) -> None:
    with pytest.raises(PIIDetectedError, match="CCCD"):
        await publish_in_tx(
            db_session,
            event_type="hr.hiring_plan_delayed",
            producer="hr",
            aggregate_schema="hr",
            aggregate_table="test_events",
            aggregate_id=uuid.uuid4(),
            payload={"note": f"ứng viên {CCCD}"},
        )
