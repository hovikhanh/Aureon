"""Execution consumers (10 §9.2, R-DEC-56/59) — T-629.

`execution.on_goal_alert`: `execution.kpi_below_threshold` / `execution.okr_at_risk` →
Notification kind `alert` through platform's public `NotificationService` in the consumer
transaction. Recipients (user ids, people refs mapped through the public `AuthService`):
- KPI: owner + MGR / DIR of the KPI's department (`users_with_roles`, exact department);
- KR: owner KR + owner Objective + MGR of the department.
Dedupe on top of `processed_events`: KPI per `(kpi_id, period_key, band)`, KR per
`(key_result_id, period_key, ISO week)` — a replayed / re-emitted event never notifies twice.
Title/body carry codes and numbers only (no level 3–4 data). Never re-publishes.
"""

import uuid
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.bus import consumer
from app.core.events.envelope import EventEnvelope
from app.modules.execution.services.at_risk import iso_week_start
from app.modules.execution.services.kpi_rules import LOCAL_TZ

EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


def _uuid(v: Any) -> uuid.UUID | None:
    return uuid.UUID(str(v)) if v else None


async def _recipients(
    session: AsyncSession, refs: tuple[uuid.UUID | None, ...], roles: tuple[str, ...],
    department_id: uuid.UUID | None,
) -> list[uuid.UUID]:  # fmt: skip
    from app.modules.auth.services.auth_service import AuthService

    auth = AuthService(session)
    out: list[uuid.UUID] = []
    for ref in refs:
        if ref is not None and (uid := await auth.user_id_for_ref(ref)) is not None:
            out.append(uid)
    if department_id is not None:  # exact department (no company-wide fallback)
        out += await auth.users_with_roles(roles, department_id=department_id)
    return list(dict.fromkeys(out))


async def _send(
    session: AsyncSession, users: list[uuid.UUID], *, title: str, body: str, link: str,
    ref_table: str, ref_id: uuid.UUID, since: datetime,
) -> int:  # fmt: skip
    from app.modules.platform.services.notification_service import NotificationService

    ntf, n = NotificationService(session), 0
    for uid in users:
        if await ntf.already_sent(uid, kind="alert", since=since, ref_table=ref_table,
                                  ref_id=ref_id, title=title):  # fmt: skip
            continue
        await ntf.create(recipient_id=uid, kind="alert", title=title, body=body, link=link,
                         ref_schema="execution", ref_table=ref_table, ref_id=ref_id)  # fmt: skip
        n += 1
    return n


async def kpi_alert(session: AsyncSession, p: dict[str, Any]) -> int:
    kpi_id = uuid.UUID(p["kpi_id"])
    users = await _recipients(session, (_uuid(p.get("owner_id")),), ("MGR", "DIR"),
                              _uuid(p.get("department_id")))  # fmt: skip
    title = f"KPI {p['kpi_code']} {p['band']} kỳ {p['period_key']}"  # dedupe key in the title
    body = f"{p['kpi_code']}: đạt {float(p['achievement_pct']):g}% kỳ {p['period_key']}"
    return await _send(session, users, title=title, body=body, link=f"/goals/kpis/{kpi_id}",
                       ref_table="kpis", ref_id=kpi_id, since=EPOCH)  # fmt: skip


async def kr_alert(session: AsyncSession, p: dict[str, Any], occurred: date) -> int:
    from app.modules.execution.repositories import ObjectiveRepository

    kr_id, oid = uuid.UUID(p["key_result_id"]), uuid.UUID(p["objective_id"])
    o = await ObjectiveRepository(session).get(oid)
    users = await _recipients(
        session, (_uuid(p.get("owner_id")), o.owner_id if o else None), ("MGR",),
        _uuid(p.get("department_id")))  # fmt: skip
    title = f"KR có rủi ro kỳ {p['period_key']}"
    body = (
        f"Tiến độ {float(p['progress_pct']):g}% (kế hoạch {float(p['expected_progress_pct']):g}%)"
    )
    week = datetime.combine(iso_week_start(occurred), time(), tzinfo=LOCAL_TZ)
    return await _send(session, users, title=title, body=body,
                       link=f"/goals/objectives/{oid}?kr={kr_id}", ref_table="key_results",
                       ref_id=kr_id, since=week)  # fmt: skip


@consumer("execution.on_goal_alert", "execution.kpi_below_threshold", "execution.okr_at_risk")
async def on_goal_alert(session: AsyncSession, event: EventEnvelope) -> None:
    if event.event_type == "execution.kpi_below_threshold":
        await kpi_alert(session, event.payload)
    else:
        await kr_alert(session, event.payload, event.occurred_at.astimezone(LOCAL_TZ).date())
