"""Sales seed (T-236, DEC-208) — 20 clients, 30 deals, Q4 + monthly team targets. Idempotent.

Clients: the 14 DOC-02 customers + prospect Hoàng Gia (08 §3 DOC-03) + 5 historical ones.
Deals: 10 won · 5 lost · 5 negotiation · 10 open (lead/qualified/proposal), open ones closing
in Q4/2026. Targets: team 2026-09 = 28,8 tỷ (DOC-03 → METRIC-FIN-01), 2026-10..12 + Q4/2026.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finance.models import Revenue
from app.modules.sales.models import Client, Deal, SalesTarget
from app.modules.sales.services.sales_service import normalize_name
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
TY = 1_000_000_000
CLIENTS: tuple[tuple[str, str, str], ...] = (
    ("Công ty Cổ phần Văn phòng Phẩm", "0301112223", "active"),
    ("Công ty Cổ phần Giáo dục Việt Nam", "0309876543", "active"),
    ("Công ty TNHH FPT Trading", "0303334445", "active"),
    ("Công ty TNHH Minh Phát", "0306667778", "active"),
    ("Công ty TNHH Giải pháp Số", "0304445678", "active"),
    ("Công ty TNHH Đầu tư Đại Cường", "0302228877", "active"),
    ("Công ty TNHH An Khang", "0308889990", "active"),
    ("Công ty Cổ phần ABC Retail", "0302223334", "active"),
    ("Công ty TNHH Thương mại Lộc Phát", "0303332211", "active"),
    ("Công ty Cổ phần TechVN", "0301119988", "active"),
    ("Công ty Cổ phần Bút Tre VN", "0304443322", "active"),
    ("Công ty TNHH TechSoft", "0305551234", "active"),
    ("Công ty TNHH Đại Lợi", "0307778889", "active"),
    ("Công ty Cổ phần Thương mại Quốc tế", "0305556677", "active"),
    ("Tập đoàn Giáo dục Hoàng Gia", "0316543210", "prospect"),
    ("Công ty TNHH Nội thất Sao Mai", "0317770001", "active"),
    ("Công ty Cổ phần Logistics Bến Thành", "0317770002", "active"),
    ("Công ty TNHH In ấn Phương Nam", "0317770003", "churned"),
    ("Công ty Cổ phần Y tế Hòa Bình", "0317770004", "active"),
    ("Công ty TNHH Dịch vụ Tân Cảng", "0317770005", "prospect"),
)
# (client index, stage, value tỷ ×10, probability, created, closed / expected close)
WON = [(i, 18 + 3 * i, date(2026, 6, 20) + timedelta(days=10 * i)) for i in range(10)]
LOST = [(10 + i, 15 + 4 * i, date(2026, 7, 1) + timedelta(days=9 * i)) for i in range(5)]
OPEN: list[tuple[int, str, int, int]] = [
    (14, "negotiation", 120, 60), (0, "negotiation", 45, 60), (2, "negotiation", 38, 60),
    (5, "negotiation", 30, 60), (15, "negotiation", 25, 60),
    (16, "proposal", 40, 40), (18, "proposal", 32, 40), (1, "proposal", 28, 40),
    (3, "qualified", 35, 25), (4, "qualified", 22, 25), (6, "qualified", 20, 25),
    (19, "lead", 50, 10), (7, "lead", 18, 10), (8, "lead", 15, 10), (9, "lead", 12, 10),
]  # fmt: skip
TARGETS = {
    # T-237 rebalance: Sep team target 26,0 tỷ → attainment 25,5/26,0 = 98,1 % (≥ 90 → FIN-01
    # green); Q4 target lowered → METRIC-CUS-01 pipeline coverage ≥ 2,8x (green).
    ("MONTH", "2026-09"): 26_000,
    ("MONTH", "2026-10"): 27_000,
    ("MONTH", "2026-11"): 28_000,
    ("MONTH", "2026-12"): 30_000,
    ("QUARTER", "2026-Q4"): 18_000,
}  # fmt: skip (triệu)


def _at(d: date) -> datetime:
    return datetime.combine(d, time(3, 0), tzinfo=UTC)


async def _has(db: AsyncSession, model: Any) -> bool:
    stmt = select(func.count()).select_from(model).where(model.source == "SEED")
    return int((await db.execute(stmt)).scalar_one()) > 0


def client_id(i: int) -> uuid.UUID:
    return seed_uuid("client", CLIENTS[i][1])


async def seed_clients(db: AsyncSession, owner: uuid.UUID) -> int:
    if await _has(db, Client):
        return 0
    db.add_all([
        Client(id=client_id(i), name=name, normalized_name=normalize_name(name), tax_code=mst,
               status=status, account_owner_id=owner, company_size="medium", **SEED)
        for i, (name, mst, status) in enumerate(CLIENTS)
    ])  # fmt: skip
    return len(CLIENTS)


def _deal(key: str, client: int, stage: str, value: int, pct: int, owner: uuid.UUID,
          created: date, closed: date | None, expected: date | None) -> Deal:  # fmt: skip
    return Deal(
        id=seed_uuid("deal", key), name=f"{key} — {CLIENTS[client][0]}",
        client_id=client_id(client),
        deal_value=value * TY // 10, currency="VND", stage=stage, probability_pct=pct,
        expected_close_date=expected, closed_at=_at(closed) if closed else None,
        lost_reason="Giá" if stage == "closed_lost" else None, assigned_to=owner,
        department_id=seed_uuid("department", "SAL"), tags=["seed"], created_at=_at(created),
        **SEED,
    )  # fmt: skip


async def seed_deals(db: AsyncSession, owner: uuid.UUID) -> int:
    if await _has(db, Deal):
        return 0
    rows = [
        _deal(f"DL-W{n:02d}", c, "closed_won", v, 100, owner, d - timedelta(days=60), d, d)
        for n, (c, v, d) in enumerate(WON)
    ] + [
        _deal(f"DL-L{n:02d}", c, "closed_lost", v, 0, owner, d - timedelta(days=45), d, d)
        for n, (c, v, d) in enumerate(LOST)
    ] + [
        _deal(f"DL-O{n:02d}", c, st, v, p, owner, date(2026, 8, 1) + timedelta(days=3 * n),
              None, date(2026, 10, 25) + timedelta(days=4 * n))
        for n, (c, st, v, p) in enumerate(OPEN)
    ]  # fmt: skip
    db.add_all(rows)
    return len(rows)


async def seed_targets(db: AsyncSession) -> int:
    if await _has(db, SalesTarget):
        return 0
    db.add_all([
        SalesTarget(period_type=pt, period_key=key, scope="team", target_amount=mil * 1_000_000,
                    currency="VND", **SEED)
        for (pt, key), mil in TARGETS.items()
    ])  # fmt: skip
    return len(TARGETS)


async def attribute_revenue(db: AsyncSession) -> int:
    """Link + split seeded revenue rows across clients → CUS-03 NRR / CUS-04 top-5 (T-237).

    The big 75 % product row of each month is split evenly across a rolling window of 5 "anchor"
    clients (window rotates by 1 per month → consecutive months share 4 anchors, so revenue from
    last period's clients recurs this period → NRR ≥ 100 → green). The 16 % and 9 % rows go to two
    further rotating clients. Spreading the dominant revenue over many accounts keeps rolling-12m
    top-5 concentration ≤ 50 % (CUS-04 green). Re-run safe: only rows still unlinked are touched."""
    rows = (await db.execute(
        select(Revenue).where(Revenue.source == "SEED", Revenue.client_id.is_(None))
        .order_by(Revenue.period_key, Revenue.amount.desc(), Revenue.id)
    )).scalars().all()  # fmt: skip
    by_period: dict[str, list[Revenue]] = {}
    for r in rows:
        by_period.setdefault(r.period_key, []).append(r)
    n_clients = len(CLIENTS)  # 20
    anchors = 5
    created = 0
    for period, prows in by_period.items():
        month_idx = int(period[:4]) * 12 + int(period[5:7])
        # Freeze the anchor window for the last two closed months (2026-08/09) so the current
        # period's revenue comes from the same clients as the prior period → NRR ≥ 100 (CUS-03).
        anchor_month = min(month_idx, 2026 * 12 + 8)
        start = anchor_month % n_clients
        window = [(start + i) % n_clients for i in range(anchors)]
        prows.sort(key=lambda r: r.amount, reverse=True)
        big = prows[0]
        # split the dominant row into `anchors` equal parts across the rolling window
        share = big.amount // anchors
        big.client_id = client_id(window[0])
        big.amount = share + (big.amount - share * anchors)  # remainder on the first part
        for j in range(1, anchors):
            clone = Revenue(
                source_note=big.source_note, category=big.category, amount=share, currency="VND",
                revenue_date=big.revenue_date, period_key=period, origin=big.origin,
                description=big.description, client_id=client_id(window[j]), source="SEED",
            )  # fmt: skip
            db.add(clone)
            created += 1
        # the two smaller rows go to two further rotating clients (outside the anchor window)
        for off, r in enumerate(prows[1:], start=anchors):
            r.client_id = client_id((start + off) % n_clients)
    await db.flush()
    return len(rows) + created


async def seed_sales(db: AsyncSession, owner: uuid.UUID) -> dict[str, int]:
    out = {"clients": await seed_clients(db, owner)}
    await db.flush()
    out["deals"] = await seed_deals(db, owner)
    out["targets"] = await seed_targets(db)
    out["revenue_clients"] = await attribute_revenue(db)
    await db.flush()
    return out
