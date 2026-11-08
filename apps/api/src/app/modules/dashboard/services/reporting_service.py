"""M2.1 D28 Reporting v3 — 3 cấp dashboard (EP-RPT-01..03, 10 §7.2.6).

Aggregator: đọc metric store (dashboard.metrics), approval inbox (platform), AI actions (ai),
execution department dashboard (execution). Scope theo role (R-DEC-85): CEO/DIR executive;
DIR/MGR department; EMP employee. Số đều từ MetricValue/service có sẵn (grounding P05).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_activity import recent_ai_actions
from app.core.clock import business_today
from app.core.deps import Principal
from app.core.errors import PermissionDeniedError
from app.core.pagination import PageParams
from app.core.periods import resolve_period
from app.modules.dashboard.schemas.reporting import (
    AiActionBriefOut,
    CountedActions,
    CountedAlerts,
    CountedApprovals,
    DepartmentDashboardOut,
    DueTasks,
    EmployeeDashboardOut,
    ExecutiveDashboardOut,
    GoalSummary,
    OkrSummary,
    PendingCheckin,
    WorkloadSummary,
)
from app.modules.dashboard.services.dashboard_service import DashboardService
from app.modules.platform.services.approval_service import ApprovalService
from app.modules.platform.services.preference_service import UserPreferenceService

SEI_CODE = "METRIC-STR-02"
SUMMARY_KEY = "reporting.executiveSummary"


class ReportingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.dash = DashboardService(db)
        self.prefs = UserPreferenceService(db)

    # ---------- EP-RPT-01 executive ----------
    async def executive(self, user: Principal) -> ExecutiveDashboardOut:
        if user.role not in ("CEO", "DIR"):
            raise PermissionDeniedError("executive dashboard is CEO/DIR only")
        metrics = await self.dash.metrics(user)
        by_code = {m.metric_code: m for m in metrics}
        tile_codes, _ = await self.prefs.executive_tiles(user)
        tiles = [by_code[c] for c in tile_codes if c in by_code]  # lọc ngoài scope (im lặng)
        sei = by_code.get(SEI_CODE)
        approvals, total, _ = await ApprovalService(self.db).inbox(
            user, PageParams(limit=5, offset=0), status="PENDING",
            rule_code=None, target_kind=None,
        )  # fmt: skip
        alerts = await self.dash.alerts(
            user, status="open", severity=None, pillar=None, limit=5, offset=0
        )
        briefs, ai_total = await recent_ai_actions(self.db, user.user_id, limit=5)
        ai_items = [AiActionBriefOut(**vars(b)) for b in briefs]
        return ExecutiveDashboardOut(
            summary_line=_summary(total, alerts.total, sei),
            summary_key=SUMMARY_KEY,
            summary_params=_summary_params(total, alerts.total, sei),
            tiles=tiles,
            sei=sei,
            decisions_waiting=CountedApprovals(count=total, items=approvals),
            open_risks=CountedAlerts(count=alerts.total, items=alerts.items),
            ai_done=CountedActions(count=ai_total, items=ai_items),
            generated_at=datetime.now(UTC),
        )

    # ---------- EP-RPT-02 department / EP-RPT-03 employee: tiếp ở phần 2 ----------
    async def department(
        self, user: Principal, department_id: Any = None
    ) -> DepartmentDashboardOut:
        return await _department(self, user, department_id)

    async def employee(self, user: Principal) -> EmployeeDashboardOut:
        return await _employee(self, user)


def _summary_params(decisions: int, risks: int, sei: Any) -> dict[str, int]:
    """Parameters of `SUMMARY_KEY`; `sei_pct` only when the store has SEI (CLAUDE.md §5.2)."""
    has_sei = sei is not None and sei.value is not None
    return {"decisions": decisions, "risks": risks} | (
        {"sei_pct": round(sei.value)} if has_sei else {}
    )


def _summary(decisions: int, risks: int, sei: Any) -> str:
    """Deprecated display line, kept until the FE renders `summary_key` + `summary_params`."""
    sei_txt = f", SEI {sei.value:.0f}%" if sei and sei.value is not None else ""
    return f"{decisions} việc cần quyết, {risks} rủi ro mở{sei_txt}"


async def _department(
    svc: ReportingService, user: Principal, department_id: Any
) -> DepartmentDashboardOut:
    from app.modules.execution.services.dashboard_service import ExecutionDashboardService
    from app.modules.execution.services.goal_summary import GoalSummaryService

    if user.role not in ("CEO", "DIR", "MGR"):
        raise PermissionDeniedError("department dashboard is DIR/MGR only")
    today = business_today()
    period = resolve_period(None, today)
    # ExecutionDashboardService kiểm scope phòng ban (subtree) + raise FORBIDDEN_SCOPE
    exe = await ExecutionDashboardService(svc.db).dashboard(user, period, today, department_id)
    kpis = [m for m in await svc.dash.metrics(user) if m.group in ("OPS", "STR", "PPL")]
    goals = GoalSummaryService(svc.db)
    scoped = ExecutionDashboardService.department(user, department_id)
    at_risk, total = await goals.department_okrs(scoped, today)
    due_tasks = await goals.department_due(scoped, today)
    due = exe.summary
    return DepartmentDashboardOut(
        department_id=str(department_id) if department_id else None,
        kpis=kpis,
        okrs=OkrSummary(at_risk_count=at_risk, total=total),
        workload=WorkloadSummary(
            overloaded_count=due.overloaded_count,
            heatmap_ref="/work/workload",
        ),
        late_projects=due.projects_late,
        due_tasks=DueTasks(
            overdue=due_tasks.overdue, today=due_tasks.today, this_week=due_tasks.this_week
        ),
        generated_at=datetime.now(UTC),
    )


async def _employee(svc: ReportingService, user: Principal) -> EmployeeDashboardOut:
    from datetime import timedelta

    from app.modules.execution.services.goal_summary import GoalSummaryService
    from app.modules.execution.services.task_service import TaskService

    today = business_today()
    ts = TaskService(svc.db)
    page = PageParams(limit=1, offset=0)
    _, overdue = await ts.list_tasks(user, page, filters={}, overdue=True, mine=True)
    _, due_today = await ts.list_tasks(
        user, page, filters={}, overdue=None, mine=True, due_from=today, due_to=today
    )
    _, due_week = await ts.list_tasks(
        user,
        page,
        filters={},
        overdue=None,
        mine=True,
        due_from=today,
        due_to=today + timedelta(days=7),
    )
    goals = GoalSummaryService(svc.db)
    kpis, krs = await goals.my_goals(user, today)
    pending = await goals.pending_checkins(user, today)
    return EmployeeDashboardOut(
        my_tasks=DueTasks(overdue=overdue, today=due_today, this_week=due_week),
        my_goals=GoalSummary(kpis=kpis, krs=krs),
        pending_checkins=[PendingCheckin(**vars(p)) for p in pending],
        workload_week_pct=await goals.workload_week_pct(user, today),
        generated_at=datetime.now(UTC),
    )
