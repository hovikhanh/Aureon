"""EP-49 `/execution/dashboard` (10 §4 row EP-49, §5 domain dashboard contract)."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel


class ExecPeriodOut(BaseModel):
    key: str
    type: str
    start_date: date
    end_date: date


class ExecutionSummary(BaseModel):
    tasks_on_time_pct: float | None
    projects_late: int
    decision_execution_pct: float | None
    overloaded_count: int


class HeatCell(BaseModel):
    employee_ref: str
    week: str  # ISO week "2026-W42"
    load_pct: float


class OnTimePoint(BaseModel):
    period_key: str
    tasks_on_time_pct: float | None


class ExecutionDashboardOut(BaseModel):
    pillar: Literal["O"] = "O"
    status: Literal["ok", "warning", "critical", "no_data"]
    period: ExecPeriodOut
    summary: ExecutionSummary
    metrics: list[dict[str, Any]]
    workload_heatmap: list[HeatCell]
    ontime_trend: list[OnTimePoint]
    open_alerts: int | None = None
