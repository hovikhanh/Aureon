"""Risk seed (T-236, DEC-208) — reduced 08 §10 register: 8 risks (5 open incl. 1 critical,
1 high without owner, 1 closed, 2 `proposed` from event/ai) and 4 mitigations (1 overdue).

Gives RSK-01 (2 high/critical → critical), RSK-02 (unowned high → critical), RSK-03 (high open
> 30 days without in-progress mitigation → critical), RSK-04 (mean score ≈ 11 → warning) and
RSK-05 (1 overdue mitigation → warning). Idempotent (`source='SEED'`).
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk.models import Mitigation, Risk
from app.modules.risk.services.rules import level_for
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}
# code, title, category, likelihood, impact, status, source, owned, identified, dept
RISKS = (
    ("R-01", "Dòng tiền thiếu hụt Q4 do công nợ phải thu tăng", "financial", 4, 5, "mitigating",
     "manual", True, date(2026, 8, 5), "FIN"),
    ("R-02", "Mất khách hàng lớn ngành giáo dục", "customer", 3, 4, "assessed", "manual", False,
     date(2026, 9, 2), "SAL"),
    ("R-03", "Thiếu kỹ thuật viên bảo trì (tuyển trễ)", "people", 3, 3, "identified", "event",
     True, date(2026, 9, 20), "SVC"),
    ("R-04", "Nhà cung cấp máy in tăng giá 8%", "partner_supplier", 2, 4, "monitoring",
     "manual", True, date(2026, 7, 1), "BOD"),
    ("R-05", "Rò rỉ dữ liệu khách hàng ABC Order", "security", 2, 5, "mitigating", "manual",
     True, date(2026, 6, 15), "PRD"),
    ("R-06", "Hợp đồng bảo trì hết hạn không gia hạn", "compliance", 2, 2, "closed", "manual",
     True, date(2026, 5, 10), "SVC"),
    ("R-12", "Churn ABC Order tăng bất thường", "business", 3, 4, "proposed", "event", False,
     date(2026, 10, 2), "PRD"),
    ("R-13", "Chi phí AI vượt ngân sách tháng", "ai", 2, 3, "proposed", "ai", False,
     date(2026, 10, 12), "BOD"),
)  # fmt: skip
# key, risk, title, status, due, progress
MITIGATIONS = (
    ("M-01", "R-01", "Đẩy nhanh thu hồi công nợ > 60 ngày", "in_progress", date(2026, 11, 15), 40),
    ("M-02", "R-04", "Đàm phán hợp đồng khung 12 tháng", "in_progress", date(2026, 10, 5), 60),
    ("M-03", "R-05", "Pentest + MFA cho tài khoản admin", "planned", date(2026, 11, 30), 0),
    ("M-04", "R-06", "Gia hạn hợp đồng", "done", date(2026, 6, 30), 100),
)  # fmt: skip


def _at(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 2, tzinfo=UTC)


async def seed_risk(db: AsyncSession, owner: uuid.UUID | None) -> dict[str, int]:
    has = select(func.count()).select_from(Risk).where(Risk.source == "SEED")
    if owner is None or int((await db.execute(has)).scalar_one()):
        return {"risks": 0}
    rows = []
    for code, title, cat, lik, imp, status, src, owned, ident, dept in RISKS:
        proposed = status == "proposed"
        rows.append(Risk(
            id=seed_uuid("risk", code), code=code, title=title, description=title,
            category=cat, likelihood=lik, impact=imp,
            severity=level_for(lik * imp), status=status, risk_source=src,
            owner_id=owner if owned else None, department_id=seed_uuid("department", dept),
            linked_entities={}, identified_at=_at(ident),
            proposed_at=_at(ident) if proposed or src != "manual" else None,
            confirmed_by=None if proposed or src == "manual" else owner,
            confirmed_at=None if proposed or src == "manual" else _at(ident),
            review_date=date(2026, 11, 30), **SEED,
        ))  # fmt: skip
    db.add_all(rows)
    await db.flush()
    db.add_all([
        Mitigation(id=seed_uuid("mitigation", key), risk_id=seed_uuid("risk", risk), title=title,
                   owner_id=owner, status=status, due_date=due, progress_pct=progress,
                   completed_at=_at(due) if status == "done" else None, **SEED)
        for key, risk, title, status, due, progress in MITIGATIONS
    ])  # fmt: skip
    await db.flush()
    return {"risks": len(RISKS) + len(MITIGATIONS)}
