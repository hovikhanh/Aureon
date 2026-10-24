"""Tool executor (T-302, P06) — runs a `TOOL-*` with the asker's `Principal`, in-process.

Read/compute tools call the matching domain **service** (never another module's models — DEC-125)
with the asker's `Principal`, so RBAC + data scoping apply exactly as on the HTTP path. The result
is reduced to a compact, PII-safe payload plus `SourceRef`s (metric_code + lineage_url) — raw rows
are never returned to the model (SSE `tool_result` carries only sources — 10 §6). A permission the
asker lacks → `forbidden` (the turn stops looping on it, FR-AI-02); an unbound tool → `error`
`not_available`; a service raising `PermissionDeniedError` → `forbidden`.

Write tools are **not** executed here: they create an `ENT-AIAction` (T-310 / T-645b
`ActionService.propose`). This executor covers the READ surface used by chat + the E2E scenarios.

M1.6 (T-645): `get_org_tree` (hr `StructureService.tree`), `get_okr_status` (`OkrService`),
`get_overdue_tasks` (`TaskService.list_tasks overdue=true`), `get_project_status`
(`ProjectService`) — record-level, scoped by the service; payload = codes/titles/counts only
(no employee names, no level 3–4 fields), each row cited as a `record` `SourceRef`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.pagination import PageParams
from app.modules.ai.tools import get_tool
from app.modules.ai.tools.spec import ToolDef
from app.modules.dashboard.services.dashboard_service import DashboardService
from app.modules.execution.services.meeting_service import ProjectService
from app.modules.execution.services.okr_service import OkrService
from app.modules.execution.services.task_service import TaskService
from app.modules.hr.services.structure_service import StructureService, today

ToolStatus = str  # "ok" | "error" | "forbidden" | "timeout"

PILLAR_TOOLS: dict[str, str | None] = {
    "TOOL-get_finance_dashboard": "F",
    "TOOL-get_budget_status": "F",
    "TOOL-get_finance_forecast": "F",
    "TOOL-get_sales_dashboard": "C",
    "TOOL-get_sales_pipeline": "C",
    "TOOL-get_hr_dashboard": "O",
    "TOOL-get_workload": "O",
    "TOOL-get_product_dashboard": "U",
    "TOOL-get_product_metrics": "U",
    "TOOL-get_risk_dashboard": "S",
    "TOOL-get_execution_dashboard": None,  # all visible pillars
}


@dataclass(frozen=True)
class SourceRef:
    type: str  # metric_value | record | document_page | tool_result
    id: str
    label: str
    period_key: str | None = None
    value: float | int | None = None
    lineage_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type, "id": self.id, "label": self.label,
            "period_key": self.period_key, "value": self.value, "lineage_url": self.lineage_url,
        }  # fmt: skip


@dataclass
class ToolResult:
    tool: str
    status: ToolStatus
    latency_ms: int
    data: dict[str, Any] = field(default_factory=dict)
    sources: list[SourceRef] = field(default_factory=list)
    error_code: str | None = None

    def sources_as_dict(self) -> list[dict[str, Any]]:
        return [s.as_dict() for s in self.sources]


class ToolExecutor:
    def __init__(self, db: AsyncSession, user: Principal) -> None:
        self.db = db
        self.user = user
        self._dash = DashboardService(db)

    async def run(
        self, tool_name: str, arguments: dict[str, Any], *, allow_frozen: bool = False
    ) -> ToolResult:
        """Run one tool as the asker. `p1_frozen` tools (R-DEC-16) are refused unless the caller
        is a curated server-side script (`allow_frozen`, demo replay) — never for model calls."""
        started = time.monotonic()
        tool = get_tool(tool_name)
        if tool is None:
            return self._fail(tool_name, "error", "AI_UNKNOWN_TOOL", started)
        if tool.p1_frozen and not allow_frozen:
            return self._fail(tool_name, "error", "AI_TOOL_NOT_AVAILABLE", started)
        if not set(tool.required_permissions) <= self.user.permissions:
            return self._fail(tool_name, "forbidden", "FORBIDDEN_ROLE", started)
        if tool.is_write or tool.kind == "APPROVAL":
            # Write/approval tools are materialised as AIActions (T-310), not run here.
            return self._fail(tool_name, "error", "AI_WRITE_VIA_ACTION", started)
        try:
            return await self._dispatch(tool, arguments, started)
        except PermissionDeniedError:
            return self._fail(tool_name, "forbidden", "FORBIDDEN_ROLE", started)
        except NotFoundError:
            return self._fail(tool_name, "error", "AI_NO_DATA_AVAILABLE", started)
        except (ValueError, TypeError):
            return self._fail(tool_name, "error", "AI_INVALID_ARGUMENT", started)

    async def _dispatch(
        self, tool: ToolDef, arguments: dict[str, Any], started: float
    ) -> ToolResult:
        if tool.name in PILLAR_TOOLS:
            return await self._pillar(tool.name, PILLAR_TOOLS[tool.name], started)
        if tool.name in ("TOOL-get_metric",):
            return await self._metric(tool.name, str(arguments.get("metric_code", "")), started)
        if tool.name == "TOOL-list_alerts":
            return await self._alerts(tool.name, started)
        if tool.name in _RECORD_TOOLS:
            data, sources = await getattr(self, _RECORD_TOOLS[tool.name])(arguments)
            return self._done(tool.name, data, sources, started)
        # Record-level list tools: expose an aggregate count + sources, never raw rows.
        if tool.name in ("TOOL-list_risks", "TOOL-list_tasks", "TOOL-list_objectives",
                         "TOOL-list_deals", "TOOL-list_invoices", "TOOL-list_expenses",
                         "TOOL-list_hiring_plans", "TOOL-get_kpi_status"):  # fmt: skip
            return await self._pillar_fallback(tool, started)
        return self._fail(tool.name, "error", "AI_TOOL_NOT_AVAILABLE", started)

    async def _pillar(self, tool: str, pillar: str | None, started: float) -> ToolResult:
        rows = await self._dash.metrics(self.user, pillar=pillar)
        if not rows:
            return self._done(tool, {"metrics": [], "note": "no data in scope"}, [], started)
        sources = [
            SourceRef("metric_value", m.metric_code, m.metric_code, m.period_key,
                      m.value, m.lineage_url)
            for m in rows
        ]  # fmt: skip
        data = {
            "pillar": pillar,
            "metrics": [
                {"code": m.metric_code, "value": m.value, "unit": m.unit, "status": m.status,
                 "period": m.period_key}
                for m in rows
            ],
        }  # fmt: skip
        return self._done(tool, data, sources, started)

    async def _pillar_fallback(self, tool: ToolDef, started: float) -> ToolResult:
        """Record-list tools: return the owning pillar's aggregate metrics as citations."""
        pillar = {"finance": "F", "sales": "C", "hr": "O", "product": "U",
                  "risk": "S", "execution": None, "dashboard": None}.get(tool.domain)  # fmt: skip
        return await self._pillar(tool.name, pillar, started)

    async def _metric(self, tool: str, code: str, started: float) -> ToolResult:
        if not code:
            return self._fail(tool, "error", "AI_MISSING_ARGUMENT", started)
        try:
            detail = await self._dash.detail(self.user, code)
        except PermissionDeniedError:
            return self._fail(tool, "forbidden", "FORBIDDEN_ROLE", started)
        except NotFoundError:
            return self._fail(tool, "error", "AI_NO_DATA_AVAILABLE", started)
        src = SourceRef("metric_value", detail.metric_code, detail.name, detail.period_key,
                        detail.value, detail.lineage_url)  # fmt: skip
        return self._done(
            tool,
            {"metric": detail.metric_code, "value": detail.value, "status": detail.status},
            [src],
            started,
        )

    async def _alerts(self, tool: str, started: float) -> ToolResult:
        page = await self._dash.alerts(
            self.user, status="open", severity=None, pillar=None, limit=100, offset=0
        )
        alerts = page.items
        sources = [
            SourceRef("record", str(a.id), a.alert_code, a.period_key, a.value, None)
            for a in alerts
        ]
        data = {
            "open_alerts": page.total,
            "items": [
                {"code": a.alert_code, "metric": a.metric_code, "severity": a.severity,
                 "pillar": a.pillar}
                for a in alerts
            ],
        }  # fmt: skip
        return self._done(tool, data, sources, started)

    # ---------- M1.6 record READ tools (T-645) ----------
    async def _org_tree(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        as_of = date.fromisoformat(str(args["as_of"])) if args.get("as_of") else today()
        tree = await StructureService(self.db).tree(self.user, as_of, None)
        depts = [
            {"code": d.code, "name": d.name, "parent_id": str(d.parent_id) if d.parent_id
             else None, "headcount": d.headcount,
             "teams": [{"code": t.code, "name": t.name, "headcount": t.headcount}
                       for t in d.teams]}
            for d in tree.departments
        ]  # fmt: skip
        sources = [SourceRef("record", str(d.id), f"hr.departments:{d.code}", value=d.headcount)
                   for d in tree.departments]  # fmt: skip
        data = {"as_of": tree.as_of.isoformat(), "organization": tree.organization.code,
                "departments": depts,
                "headcount": sum(d.headcount for d in tree.departments)}  # fmt: skip
        return data, sources

    async def _okr_status(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        at_risk = args.get("at_risk")
        items, total = await OkrService(self.db).list_objectives(
            self.user, _page(args, "period_key"), period_key=args.get("period_key") or None,
            owner_id=None, at_risk=bool(at_risk) if at_risk is not None else None,
        )  # fmt: skip
        rows = [{"title": o.title, "period": o.period_key, "level": o.level,
                 "status": o.status, "progress_pct": o.progress_pct,
                 "at_risk_kr_count": o.at_risk_kr_count} for o in items]  # fmt: skip
        sources = [SourceRef("record", str(o.id), f"execution.objectives:{o.title[:60]}",
                             o.period_key, o.progress_pct) for o in items]  # fmt: skip
        return {"total": total, "objectives": rows}, sources

    async def _overdue_tasks(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        items, total = await TaskService(self.db).list_tasks(
            self.user, _page(args, "due_date", order="asc"), filters={}, overdue=True
        )
        rows = [{"id": str(t.id), "title": t.title, "status": t.status,
                 "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date
                 else None} for t in items]  # fmt: skip
        sources = [SourceRef("record", str(t.id), f"execution.tasks:{t.title[:60]}")
                   for t in items]  # fmt: skip
        return {"overdue_total": total, "tasks": rows}, sources

    async def _project_status(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        svc = ProjectService(self.db)
        if args.get("project_id"):
            one = await svc.detail(self.user, uuid.UUID(str(args["project_id"])))
            items: list[Any] = [one]
            total = 1
        else:
            listed, total = await svc.list_projects(
                self.user, _page(args, "planned_end_date", order="asc"), status=None,
                department_id=None,
            )  # fmt: skip
            items = list(listed)
        rows = [{"code": p.code, "name": p.name, "status": p.status,
                 "progress_pct": p.progress_pct, "planned_pct": p.planned_pct, "late": p.late,
                 "open_tasks": p.open_tasks, "overdue_tasks": p.overdue_tasks,
                 "due_date": p.due_date.isoformat() if p.due_date else None}
                for p in items]  # fmt: skip
        sources = [SourceRef("record", str(p.id), f"execution.projects:{p.code}",
                             value=p.progress_pct) for p in items]  # fmt: skip
        return {"total": total, "projects": rows}, sources

    # ---------- helpers ----------
    def _done(
        self, tool: str, data: dict[str, Any], sources: list[SourceRef], started: float
    ) -> ToolResult:
        return ToolResult(tool, "ok", _ms(started), data=data, sources=sources)

    def _fail(self, tool: str, status: str, code: str, started: float) -> ToolResult:
        return ToolResult(tool, status, _ms(started), error_code=code)


_RECORD_TOOLS = {
    "TOOL-get_org_tree": "_org_tree",
    "TOOL-get_okr_status": "_okr_status",
    "TOOL-get_overdue_tasks": "_overdue_tasks",
    "TOOL-get_project_status": "_project_status",
}


def _page(args: dict[str, Any], sort_by: str, order: str = "desc") -> PageParams:
    limit = max(1, min(int(args.get("limit") or 20), 50))
    return PageParams(limit=limit, offset=0, sort_by=sort_by, order=order)  # type: ignore[arg-type]


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
