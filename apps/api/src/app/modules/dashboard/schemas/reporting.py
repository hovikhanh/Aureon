"""M2.1 D28 Reporting v3 — 3 cấp dashboard (EP-RPT-01..05, 10 §7.2.6).

Tái dùng DTO sẵn có: MetricValueOut (tiles/sei/kpis), AlertOut (rủi ro), ApprovalRequestOut
(cần quyết), AIActionOut (AI đã làm). Trụ/đơn vị ngoài scope vắng mặt (R-DEC-85, 03 §1.2).
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.modules.dashboard.schemas import AlertOut, MetricValueOut
from app.modules.platform.schemas import ApprovalRequestOut

DashboardLevel = ("executive", "department", "employee")


class AiActionBriefOut(BaseModel):
    """Tóm tắt AI action đã làm (neutral; dashboard không import `ai`, DEC-125)."""

    id: uuid.UUID
    action_name: str
    status: str
    executed_at: datetime | None = None
    result_refs: list[dict[str, Any]] = Field(default_factory=list)


class CountedApprovals(BaseModel):
    count: int
    items: list[ApprovalRequestOut] = Field(default_factory=list)


class CountedAlerts(BaseModel):
    count: int
    items: list[AlertOut] = Field(default_factory=list)


class CountedActions(BaseModel):
    count: int
    items: list[AiActionBriefOut] = Field(default_factory=list)


class ExecutiveDashboardOut(BaseModel):
    """EP-RPT-01 — CEO toàn DN / DIR theo khối (scope_pillars)."""

    summary_line: str
    tiles: list[MetricValueOut] = Field(default_factory=list)  # ≤ 4, theo preference
    sei: MetricValueOut | None = None  # METRIC-STR-02
    decisions_waiting: CountedApprovals
    open_risks: CountedAlerts
    ai_done: CountedActions
    generated_at: datetime


class OkrSummary(BaseModel):
    at_risk_count: int
    total: int


class WorkloadSummary(BaseModel):
    overloaded_count: int
    heatmap_ref: str


class DueTasks(BaseModel):
    overdue: int
    today: int
    this_week: int


class DepartmentDashboardOut(BaseModel):
    """EP-RPT-02 — DIR/MGR theo phòng + phòng con (department_subtree)."""

    department_id: str | None = None
    kpis: list[MetricValueOut] = Field(default_factory=list)
    okrs: OkrSummary
    workload: WorkloadSummary
    late_projects: int
    due_tasks: DueTasks
    generated_at: datetime


class GoalSummary(BaseModel):
    kpis: int
    krs: int


class PendingCheckin(BaseModel):
    target_type: str
    target_id: str
    label: str
    period_key: str


class EmployeeDashboardOut(BaseModel):
    """EP-RPT-03 — của chính người gọi (employee_id từ JWT)."""

    my_tasks: DueTasks
    my_goals: GoalSummary
    pending_checkins: list[PendingCheckin] = Field(default_factory=list)
    workload_week_pct: float | None = None
    generated_at: datetime


class ExecutiveTilesOut(BaseModel):
    """EP-RPT-04/05 — 4 ô Executive (R-DEC-87)."""

    tiles: list[str] = Field(default_factory=list)
    version: int


class ExecutiveTilesIn(BaseModel):
    tiles: list[str] = Field(max_length=4)
    version: int
