"""Execution seed v3 (T-603b, 08 §3 D07–D12, §4 UC-01/02/03/04/06) — data in `exec_data`.

Strategy tree (1 company objective → 4 initiatives), 10 projects, tasks for 25 assignees
(workload source of HR-03), the October "giao ban" meeting with 3 decisions whose action items
are the meeting tasks, a 12-KPI tree with 3 monthly measurements (band from `kpi_rules`) and
6 OKRs Q4/2026 with 15 KRs (progress from `kpi_rules`). `created_at` is explicit so workload
windows are deterministic. M1.3 (T-624): dependencies, a sub-task, `source_ref` (decision /
document), project milestones (1 late in PRJ-ERP) and 1 PENDING `task_reassign` approval in SVC.
Idempotent: skipped when SEED tasks already exist.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.execution.models import (
    Decision,
    Initiative,
    KeyResult,
    Kpi,
    KpiMeasurement,
    KpiTarget,
    Meeting,
    Milestone,
    Objective,
    Project,
    Task,
    TaskDependency,
)
from app.modules.execution.services import kpi_rules
from app.seed import exec_data as X
from app.seed.hr_seed import emp_id
from app.seed.ids import seed_uuid

SEED: dict[str, Any] = {"source": "SEED"}


def _dept(code: str | None) -> uuid.UUID | None:
    return seed_uuid("department", code) if code else None


def _strategy(owner: uuid.UUID) -> list[Any]:
    obj = seed_uuid("objective", "OBJ-2026")
    rows: list[Any] = [Objective(
        id=obj, title="Tăng trưởng bền vững 2026", period_key="2026", level="company",
        okr_type="committed", weight_pct=100, owner_id=owner, status="active", progress_pct=55,
        **SEED)]  # fmt: skip
    rows += [
        Initiative(id=seed_uuid("initiative", code), code=code, title=title, objective_id=obj,
                   pillar=pillar, owner_id=owner, department_id=_dept(dept), start_date=start,
                   planned_end_date=end, status="active", progress_pct=prog, weight_pct=w,
                   currency="VND", **SEED)
        for code, title, pillar, dept, start, end, prog, w in X.INITIATIVES
    ]  # fmt: skip
    rows += [
        Project(id=seed_uuid("project", code), code=code, name=name, owner_id=owner,
                department_id=_dept(dept), start_date=start, planned_end_date=end,
                status="active", currency="VND", **SEED)
        for code, name, dept, start, end, _, _ in X.PROJECTS
    ]  # fmt: skip
    return rows


def _meeting(owner: uuid.UUID) -> list[Any]:
    mid = seed_uuid("meeting", "GB-2026-10")
    attendees = sorted({emp_id(p.code) for p in X.ASSIGNEES[:8]})
    rows: list[Any] = [Meeting(
        id=mid, title=X.MEETING_TITLE, held_at=X.MEETING_AT, chair_id=owner,
        attendee_ids=attendees, summary="Giao ban tháng 10: dòng tiền, tuyển dụng, pipeline Q4.",
        **SEED)]  # fmt: skip
    day = X.MEETING_AT.date()
    rows += [
        Decision(id=seed_uuid("decision", str(i)), meeting_id=mid, content=content,
                 expected_outcome=outcome, owner_id=owner, decided_at=X.MEETING_AT,
                 due_date=day + timedelta(days=45),
                 review_at=[day + timedelta(days=n) for n in (30, 60, 90)], status="in_progress",
                 **SEED)
        for i, (content, _, outcome) in enumerate(X.DECISIONS)
    ]  # fmt: skip
    return rows


def _tasks(owner: uuid.UUID) -> list[Task]:
    mid = seed_uuid("meeting", "GB-2026-10")
    rows = [
        Task(id=seed_uuid("task", t.key), title=f"{t.key} — việc seed", owner_id=owner,
             assignee_id=emp_id(t.who.code), department_id=_dept(t.who.dept), priority="medium",
             status=t.status, due_date=t.due, done_at=t.done,
             blocked_reason="Chờ phê duyệt ngân sách" if t.status == "blocked" else None,
             estimate_hours=t.hours, is_critical=False, meeting_id=mid if t.meeting else None,
             decision_id=seed_uuid("decision", str(n % 3)) if t.meeting else None,
             task_source="meeting" if t.meeting else "manual", created_at=X.CREATED,
             source_ref={"kind": "decision", "id": str(seed_uuid("decision", str(n % 3)))}
             if t.meeting else None, **SEED)
        for n, t in enumerate(X.tasks())
    ]  # fmt: skip
    for code, _, dept, *_, done, total in X.PROJECTS:
        rows += [
            Task(id=seed_uuid("task", f"{code}-{i}"), title=f"{code} hạng mục {i + 1}",
                 owner_id=owner, department_id=_dept(dept), project_id=seed_uuid("project", code),
                 priority="medium", status="done" if i < done else "todo", is_critical=False,
                 task_source="manual", done_at=X.CREATED - timedelta(days=3) if i < done else None,
                 created_at=X.CREATED - timedelta(days=30), **SEED)
            for i in range(total)
        ]  # fmt: skip
    by_key = {r.id: r for r in rows}
    for child, parent in X.SUBTASKS:  # R-DEC-42
        by_key[seed_uuid("task", child)].parent_task_id = seed_uuid("task", parent)
    for key, doc, page in X.DOCUMENT_TASKS:
        t = by_key[seed_uuid("task", key)]
        t.task_source = "document"
        t.source_ref = {"kind": "document", "id": str(seed_uuid("source_document", doc)),
                        "page": page}  # fmt: skip
    return rows


def _links(_owner: uuid.UUID) -> list[Any]:
    """M1.3: dependencies (R-DEC-43) + project milestones (R-DEC-49)."""
    rows: list[Any] = [
        TaskDependency(id=seed_uuid("task_dependency", f"{a}>{b}"), task_id=seed_uuid("task", a),
                       depends_on_task_id=seed_uuid("task", b), **SEED)
        for a, b in X.DEPENDENCIES
    ]  # fmt: skip
    rows += [
        Milestone(id=seed_uuid("milestone", f"{code}:{title}"),
                  project_id=seed_uuid("project", code), title=title, due_date=due,
                  status=status, created_at=X.CREATED,
                  done_at=datetime(done.year, done.month, done.day, 9, tzinfo=UTC)
                  if done else None, **SEED)
        for code, title, due, status, done in X.MILESTONES
    ]  # fmt: skip
    return rows


async def _reassign_request(db: AsyncSession) -> int:
    """1 PENDING `task_reassign` in SVC (EP-TASK-19 → EP-WF-01 MGR inbox) via the public
    service, so rule / audit / outbox / notification are the real ones. Needs the auth seed."""
    from app.modules.auth.services.auth_service import AuthService
    from app.modules.platform.services.approval_service import ApprovalService

    key, to, reason = X.REASSIGN
    requester = X.ASSIGNEES[0]
    uid = await AuthService(db).user_id_for_employee(emp_id(requester.code))
    if uid is None:
        return 0
    await ApprovalService(db).create_for_task_reassign(
        task_id=seed_uuid("task", key), department_id=_dept(requester.dept), requested_by=uid,
        payload={"task_id": str(seed_uuid("task", key)),
                 "from_assignee_id": str(emp_id(requester.code)),
                 "to_assignee_id": str(emp_id(to.code)), "reason": reason, "task_version": 1},
    )  # fmt: skip
    return 1


def _kpis(owner: uuid.UUID) -> list[Any]:
    rows: list[Any] = []
    for code, name, dept, unit, direction, target, actuals, parent in X.KPIS:
        kid = seed_uuid("kpi", code)
        rows.append(Kpi(
            id=kid, code=code, name=name, unit=unit, period_type="MONTH", target_value=target,
            direction=direction, value_type="numeric", data_source_kind="manual",
            parent_kpi_id=seed_uuid("kpi", parent) if parent else None, weight_pct=100,
            owner_id=owner, department_id=_dept(dept), status="active", **SEED))  # fmt: skip
        for period, actual in zip(X.KPI_PERIODS, actuals, strict=True):
            tid = seed_uuid("kpi_target", f"{code}:{period}")
            ach = kpi_rules.achievement_pct(direction, Decimal(str(actual)), Decimal(str(target)))
            rows.append(KpiTarget(id=tid, kpi_id=kid, period_key=period, target=target, **SEED))
            rows.append(KpiMeasurement(
                id=seed_uuid("kpi_measurement", f"{code}:{period}"), kpi_id=kid,
                period_key=period, actual_value=actual, achievement_pct=ach,
                evaluation_band=kpi_rules.band(ach), kpi_target_id=tid,
                measured_at=datetime.fromisoformat(f"{period}-28T03:00:00+00:00")))  # fmt: skip
    return rows


def _okrs(owner: uuid.UUID) -> list[Any]:
    rows: list[Any] = []
    for code, title, dept, krs in X.OKRS:
        oid = seed_uuid("objective", code)
        progress = [kpi_rules.kr_progress_pct(Decimal(str(b)), Decimal(str(t)), Decimal(str(c)))
                    for _, _, b, t, c, _ in krs]  # fmt: skip
        rows.append(Objective(
            id=oid, title=title, period_key="2026-Q4", level="department" if dept else "company",
            okr_type="committed", weight_pct=100, owner_id=owner, department_id=_dept(dept),
            status="active", progress_pct=sum(progress) / len(progress), **SEED))  # fmt: skip
        w = Decimal(100) / len(krs)
        rows += [
            KeyResult(id=seed_uuid("key_result", f"{code}:{i}"), objective_id=oid, title=kr,
                      unit=unit, baseline=b, target=t, current_value=c, owner_id=owner,
                      status="active", confidence=conf, weight_pct=w.quantize(Decimal("0.01")),
                      **SEED)
            for i, (kr, unit, b, t, c, conf) in enumerate(krs)
        ]  # fmt: skip
    return rows


async def seed_execution(db: AsyncSession, owner: uuid.UUID | None) -> dict[str, int]:
    has = select(func.count()).select_from(Task).where(Task.source == "SEED")
    if owner is None or int((await db.execute(has)).scalar_one()):
        return {"execution": 0}
    total = 0
    for build in (_strategy, _meeting, _tasks, _links, _kpis, _okrs):
        rows = build(owner)
        for row in rows:
            db.add(row)
            await db.flush()
        total += len(rows)
    return {"execution": total, "approval_requests": await _reassign_request(db)}
