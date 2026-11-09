"""CRM demo set (R-DEC-176, D-08) — 8 leads, 1 contact per client, 12 activities. Idempotent.

Every row has a deterministic id (`seed_uuid`) and is only inserted when that id is missing, so
re-running the seed adds nothing. Contacts: a client's flat contact columns are copied when set
(R-DEC-176 g); seed clients without them get a fake contact (DEC-136: fake data only).
Codes (`LD-` / `CT-` / `SA-`) come from the DB sequences.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales.models import Client, Lead, SalesActivity, SalesContact
from app.modules.sales.services.crm_service import split_name
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
SAL = seed_uuid("department", "SAL")
TY = 1_000_000_000

# (key, full name, company, title, status, lead_source, score, budget tỷ×10, need)
LEADS: tuple[tuple[str, str, str, str, str, str, int, int | None, str], ...] = (
    ("L01", "Trần Thị Mai", "Công ty TNHH Văn phòng Xanh", "Trưởng phòng Hành chính", "new",
     "website", 20, None, "Bàn ghế văn phòng cho 40 chỗ ngồi"),
    ("L02", "Lê Văn Hùng", "Trường Quốc tế Á Châu", "Phó Hiệu trưởng", "contacted",
     "referral", 35, 8, "Máy chiếu và bảng tương tác cho 20 phòng học"),
    ("L03", "Phạm Minh Tuấn", "Công ty CP Kho vận Miền Nam", "Giám đốc Vận hành", "engaged",
     "event", 50, 15, "Máy in mã vạch + hợp đồng bảo trì 2 năm"),
    ("L04", "Võ Thị Lan", "Bệnh viện Đa khoa Tâm An", "Trưởng phòng Vật tư", "qualified",
     "partner", 75, 12, "Thiết bị văn phòng cho khu khám mới"),
    ("L05", "Đặng Quốc Bảo", "Công ty TNHH Kiến trúc Nhà Việt", "Giám đốc", "nurturing",
     "social", 40, 3, "Máy in khổ lớn A0"),
    ("L06", "Bùi Thanh Hà", "Công ty CP Dịch vụ Tài chính Sao Việt", "Giám đốc Hành chính",
     "qualified", "cold_call", 70, 20, "Trang bị 3 chi nhánh mới, đặt qua ABC Order"),
    ("L07", "Ngô Đức Long", "Công ty TNHH Nhựa Bình Dương", "Nhân viên mua hàng",
     "disqualified", "advertising", 10, None, "Hỏi giá lẻ, không có ngân sách năm nay"),
    ("L08", "Huỳnh Ngọc Ánh", "Trung tâm Ngoại ngữ Bình Minh", "Quản lý cơ sở", "engaged",
     "website", 55, 4, "Thuê máy photocopy theo tháng"),
)  # fmt: skip

# fake contacts for seed clients (index-aligned with `sales_seed.CLIENTS`)
CONTACT_NAMES = (
    "Nguyễn Văn An", "Trần Thị Bích", "Lê Hoàng Cường", "Phạm Thu Dung", "Hoàng Minh Đức",
    "Vũ Thị Giang", "Đỗ Quang Hải", "Bùi Thị Hạnh", "Đặng Văn Khoa", "Ngô Thị Lệ",
    "Dương Minh Nhật", "Lý Thị Oanh", "Mai Văn Phúc", "Trịnh Thị Quyên", "Phan Gia Huy",
    "Hồ Thị Thanh", "Tạ Văn Tùng", "Châu Thị Uyên", "Lương Văn Vinh", "Kiều Thị Yến",
)  # fmt: skip
TITLES = ("Trưởng phòng Mua hàng", "Giám đốc Hành chính", "Kế toán trưởng", "Giám đốc")
ROLES = (["decision_maker"], ["economic_buyer"], ["influencer", "user"], ["champion"])

# (key, type, subject, status, day offset from 2026-10-20, hour, link kind, link key, outcome)
ACTIVITIES: tuple[tuple[str, str, str, str, int, int, str, str, str | None], ...] = (
    ("A01", "call", "Gọi giới thiệu ABC Order", "completed", -18, 9, "lead", "L02",
     "Quan tâm, hẹn gửi catalogue"),
    ("A02", "email", "Gửi catalogue thiết bị giáo dục", "completed", -16, 14, "lead", "L02", None),
    ("A03", "meeting", "Khảo sát kho vận", "completed", -10, 10, "lead", "L03",
     "Cần 25 máy in mã vạch"),
    ("A04", "demo", "Demo ABC Order cho phòng vật tư", "completed", -6, 15, "lead", "L04",
     "Đồng ý báo giá"),
    ("A05", "proposal", "Gửi báo giá đợt 1", "planned", 3, 9, "lead", "L06", None),
    ("A06", "meeting", "Đàm phán điều khoản thanh toán", "completed", -5, 10, "deal", "DL-O00",
     "Khách đề nghị trả 3 đợt"),
    ("A07", "follow_up", "Chốt phụ lục bảo hành", "planned", 4, 14, "deal", "DL-O00", None),
    ("A08", "workshop", "Workshop nhu cầu in ấn", "completed", -12, 9, "deal", "DL-O05",
     "Xác định 3 tầng văn phòng"),
    ("A09", "poc", "Chạy thử máy in 2 tuần", "planned", 6, 8, "deal", "DL-O08", None),
    ("A10", "call", "Gọi nhắc gia hạn hợp đồng bảo trì", "completed", -3, 16, "contact", "0", None),
    ("A11", "meeting", "Họp quý với kế toán trưởng", "planned", 9, 10, "contact", "2", None),
    ("A12", "email", "Gửi đề xuất dịch vụ năm 2027", "cancelled", -1, 11, "client", "15",
     "Khách hoãn sang Q1"),
)  # fmt: skip
BASE_DAY = date(2026, 10, 20)  # DEMO_REFERENCE_DATE (08 §1)
DEAL_CLIENTS = {"DL-O00": 14, "DL-O05": 16, "DL-O08": 3}  # sales_seed.OPEN client index


def _at(offset: int, hour: int) -> datetime:
    return datetime.combine(BASE_DAY + timedelta(days=offset), time(hour - 7, 0), tzinfo=UTC)


async def _existing(db: AsyncSession, model: Any, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    rows = await db.execute(select(model.id).where(model.id.in_(ids)))
    return set(rows.scalars().all())


async def seed_leads(db: AsyncSession, owner: uuid.UUID) -> int:
    ids = [seed_uuid("lead", k[0]) for k in LEADS]
    have = await _existing(db, Lead, ids)
    rows = []
    for n, (key, name, company, title, status, src, score, budget, need) in enumerate(LEADS):
        if seed_uuid("lead", key) in have:
            continue
        rows.append(Lead(
            id=seed_uuid("lead", key), full_name=name, company_name=company, job_title=title,
            email=f"lead{n + 1:02d}@khachhang.demo", phone=f"0909 000 {n + 1:03d}",
            industry="Giáo dục" if "Trường" in company else None, lead_source=src, need=need,
            budget=budget * TY // 10 if budget else None, currency="VND", score=score,
            status=status, owner_id=owner, department_id=SAL,
            next_action=None if status == "disqualified" else "Gọi lại xác nhận nhu cầu",
            next_action_date=None if status == "disqualified" else BASE_DAY + timedelta(days=n),
            **SEED,
        ))  # fmt: skip
    db.add_all(rows)
    return len(rows)


def _contact_for(c: Client, index: int | None) -> SalesContact | None:
    """Copy the flat contact columns, else a fake contact for seed clients, else none."""
    if c.contact_person or c.contact_email or c.contact_phone:
        first, last = split_name(c.contact_person or "Liên hệ")
        email, phone = c.contact_email, c.contact_phone
        title, roles = None, []
    elif index is not None:
        first, last = split_name(CONTACT_NAMES[index % len(CONTACT_NAMES)])
        email, phone = f"lienhe{index + 1:02d}@khachhang.demo", f"0908 000 {index + 1:03d}"
        title, roles = TITLES[index % len(TITLES)], ROLES[index % len(ROLES)]
    else:
        return None
    return SalesContact(
        id=seed_uuid("contact", str(c.id)), client_id=c.id, first_name=first, last_name=last,
        job_title=title, email=email, phone=phone, roles=roles,
        influence_level="high" if "decision_maker" in roles else "medium",
        owner_id=c.account_owner_id, **SEED,
    )  # fmt: skip


async def seed_contacts(db: AsyncSession, client_ids: list[uuid.UUID]) -> int:
    clients = (await db.execute(select(Client).where(Client.deleted_at.is_(None)))).scalars().all()
    have = await _existing(db, SalesContact, [seed_uuid("contact", str(c.id)) for c in clients])
    rows = []
    for c in clients:
        if seed_uuid("contact", str(c.id)) in have:
            continue
        idx = client_ids.index(c.id) if c.source == "SEED" and c.id in client_ids else None
        if (row := _contact_for(c, idx)) is not None:
            rows.append(row)
    db.add_all(rows)
    return len(rows)


async def seed_activities(db: AsyncSession, owner: uuid.UUID, client_ids: list[uuid.UUID]) -> int:
    ids = [seed_uuid("sales_activity", a[0]) for a in ACTIVITIES]
    have = await _existing(db, SalesActivity, ids)
    contacts = await _existing(db, SalesContact, [seed_uuid("contact", str(c)) for c in client_ids])
    rows = []
    for key, kind, subject, status, offset, hour, link, ref, outcome in ACTIVITIES:
        if seed_uuid("sales_activity", key) in have:
            continue
        links: dict[str, Any] = {}
        if link == "lead":
            links["lead_id"] = seed_uuid("lead", ref)
        elif link == "deal":
            links = {"deal_id": seed_uuid("deal", ref),
                     "client_id": client_ids[DEAL_CLIENTS[ref]]}  # fmt: skip
        else:
            client = client_ids[int(ref)]
            links["client_id"] = client
            contact = seed_uuid("contact", str(client))
            if link == "contact" and contact in contacts:
                links["contact_id"] = contact
        start = _at(offset, hour)
        rows.append(SalesActivity(
            id=seed_uuid("sales_activity", key), type=kind, subject=subject, status=status,
            start_at=start, end_at=start + timedelta(hours=1), outcome=outcome,
            owner_id=owner, department_id=SAL, **links, **SEED,
        ))  # fmt: skip
    db.add_all(rows)
    return len(rows)


async def seed_crm(
    db: AsyncSession, owner: uuid.UUID, client_ids: list[uuid.UUID]
) -> dict[str, int]:
    out = {"leads": await seed_leads(db, owner)}
    out["contacts"] = await seed_contacts(db, client_ids)
    await db.flush()
    out["activities"] = await seed_activities(db, owner, client_ids)
    await db.flush()
    return out
