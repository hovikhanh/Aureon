"""Tool executor (T-302, P06) — runs a `TOOL-*` with the asker's `Principal`, in-process.

Read/compute tools call the matching domain **service** (never another module's models — DEC-125)
with the asker's `Principal`, so RBAC + data scoping apply exactly as on the HTTP path. The result
is reduced to a compact, PII-safe payload plus `SourceRef`s (metric_code + lineage_url) — raw rows
are never returned to the model (SSE `tool_result` carries only sources — 10 §6). A permission the
asker lacks → `forbidden` (the turn stops looping on it, FR-AI-02); an unbound tool → `error`
`not_available`; a service raising `PermissionDeniedError` → `forbidden`.

Write tools are **not** executed here: they create an `ENT-AIAction` (T-310 / T-645b
`ActionService.propose`). This executor covers the READ surface used by chat + the E2E scenarios.

Each READ runs inside a savepoint with `statement_timeout = TOOL_TIMEOUT_S` (CLAUDE.md §5.5):
Postgres cancels the query and the turn's transaction survives. `asyncio.wait_for` cannot do this
job, cancelling a query in flight invalidates the turn's connection. The bound is per statement;
the one non-SQL wait, the search embedding, has its own 3 s timeout. Over budget → status `timeout`.

`model_ready` is the honest surface: a tool with no binding here and no registered `ACT-*` is never
advertised to the model. `TOOL-get_finance_forecast` stays runnable for replay only: it returns the
Finance pillar metrics, which is not a forecast.

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

from psycopg.errors import QueryCanceled
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import NotFoundError, PermissionDeniedError, ScopeDeniedError
from app.core.pagination import PageParams
from app.modules.ai.services.action_registry import get_action
from app.modules.ai.tools import get_tool
from app.modules.ai.tools.spec import ToolDef
from app.modules.dashboard.services.dashboard_service import DashboardService
from app.modules.execution.services.kpi_service import KpiService
from app.modules.execution.services.meeting_service import ProjectService
from app.modules.execution.services.okr_service import OkrService
from app.modules.execution.services.task_service import TaskService
from app.modules.finance.services import scope as finance_scope
from app.modules.finance.services.budget_service import BudgetService
from app.modules.finance.services.finance_service import FinanceService
from app.modules.finance.services.invoice_service import InvoiceService
from app.modules.hr.services.dashboard_service import HrDashboardService
from app.modules.hr.services.hiring_service import HiringPlanService
from app.modules.hr.services.structure_service import StructureService, today
from app.modules.idp.services.inbox_service import InboxService
from app.modules.idp.services.lineage import read_lineage
from app.modules.platform.services.catalog import BY_CODE as METRIC_CATALOG
from app.modules.sales.services import scope as sales_scope
from app.modules.sales.services.analytics import SalesAnalytics
from app.modules.sales.services.sales_service import SalesService

ToolStatus = str  # "ok" | "error" | "forbidden" | "timeout"
TOOL_TIMEOUT_S = 5.0  # CLAUDE.md §5.5
SOURCE_PAGE_CHARS = 1500  # one page into a prompt; the local model has a 4096-token context

PILLAR_TOOLS: dict[str, str | None] = {
    "TOOL-get_finance_dashboard": "F",
    "TOOL-get_finance_forecast": "F",  # replay only, see REPLAY_ONLY
    "TOOL-get_sales_dashboard": "C",
    "TOOL-get_hr_dashboard": "O",
    "TOOL-get_product_dashboard": "U",
    "TOOL-get_risk_dashboard": "S",
    "TOOL-get_execution_dashboard": None,  # all visible pillars
}


REPLAY_ONLY = frozenset({"TOOL-get_finance_forecast"})


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
            async with self.db.begin_nested():
                await self._statement_timeout(int(TOOL_TIMEOUT_S * 1000))
                result = await self._dispatch(tool, arguments, started)
                await self._statement_timeout(0)
            return result
        except DBAPIError as exc:
            if isinstance(exc.orig, QueryCanceled):
                return self._fail(tool_name, "timeout", "AI_PROVIDER_TIMEOUT", started)
            raise
        except ScopeDeniedError:  # data scope (02 §5.3) — refused like REST, nothing returned
            return self._fail(tool_name, "forbidden", "FORBIDDEN_SCOPE", started)
        except PermissionDeniedError:
            return self._fail(tool_name, "forbidden", "FORBIDDEN_ROLE", started)
        except NotFoundError:
            return self._fail(tool_name, "error", "AI_NO_DATA_AVAILABLE", started)
        except (ValueError, TypeError):
            return self._fail(tool_name, "error", "AI_INVALID_ARGUMENT", started)

    async def _statement_timeout(self, ms: int) -> None:
        """Transaction-local (`is_local`); rolling the savepoint back also reverts it."""
        await self.db.execute(
            text("select set_config('statement_timeout', :v, true)"), {"v": str(ms)}
        )

    async def _dispatch(
        self, tool: ToolDef, arguments: dict[str, Any], started: float
    ) -> ToolResult:
        if tool.name in PILLAR_TOOLS:
            return await self._pillar(tool.name, PILLAR_TOOLS[tool.name], started)
        if tool.name in ("TOOL-get_metric",):
            return await self._metric(tool.name, str(arguments.get("metric_code", "")), started)
        if tool.name == "TOOL-list_alerts":
            return await self._alerts(tool.name, started)
        if tool.name == "TOOL-search_documents":
            return await self._search_documents(tool.name, arguments, started)
        if tool.name in _RECORD_TOOLS:
            data, sources = await getattr(self, _RECORD_TOOLS[tool.name])(arguments)
            return self._done(tool.name, data, sources, started)
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
        # `name`: a small local model cannot tell what METRIC-FIN-01 measures from the code alone
        # (D-19); the name is catalog text, not data, so grounding is unaffected.
        data = {
            "pillar": pillar,
            "metrics": [
                {"code": m.metric_code, "name": _metric_name(m.metric_code), "value": m.value,
                 "unit": m.unit, "status": m.status, "period": m.period_key}
                for m in rows
            ],
        }  # fmt: skip
        return self._done(tool, data, sources, started)

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

    async def _search_documents(
        self, tool: str, args: dict[str, Any], started: float
    ) -> ToolResult:
        """TOOL-search_documents (M3.4, R-DEC-141): Knowledge/RAG over document pages.

        Returns an aggregate hit count + page `SourceRef`s (document_id + page_number); never a raw
        storage URL to the LLM (05 §11). Scoped by `idp:read` + the caller's document scope inside
        the search service. Empty/no-data queries surface AI_NO_DATA_AVAILABLE (no fabrication).
        """
        from app.modules.idp.services.knowledge_search import KnowledgeSearchService

        query = str(args.get("query", "")).strip()
        if not query:
            return self._fail(tool, "error", "AI_MISSING_ARGUMENT", started)
        limit = int(args.get("limit") or 5)
        search = KnowledgeSearchService(self.db)
        hits, total = await search.search(self.user, query, limit=limit, max_sensitivity=3)
        sources = [
            SourceRef("document_page", f"{h.document_id}#p{h.page_number}",
                      f"{h.title} · tr.{h.page_number}")
            for h in hits
        ]  # fmt: skip
        data = {
            "matches": total,
            "search_mode": search.last_mode,
            "results": [
                {"document_id": str(h.document_id), "page_number": h.page_number,
                 "title": h.title, "doc_type": h.doc_type, "snippet": h.snippet}
                for h in hits
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

    # ---------- F-H8 record READ tools: real rows through the owning service ----------
    async def _invoices(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        # same scope as REST EP-67 (D-07 R-DEC-183, D-20): REV refused, MGR only own invoices
        finance_scope.require_reader(self.user)
        items, total = await InvoiceService(self.db).list_invoices(
            _page(args, "issued_on"), status=None, client_id=None, overdue=None,
            period=args.get("period") or None, direction=None,
            created_by=finance_scope.invoice_creator_filter(self.user),
        )  # fmt: skip
        rows = [{"number": i.number, "direction": i.direction,
                 "counterparty": i.client_name or i.counterparty_name,
                 "issued_on": i.issued_on.isoformat(), "total_amount": i.total_amount,
                 "amount_due": i.amount_due, "currency": i.currency, "status": i.status,
                 "overdue": i.overdue} for i in items]  # fmt: skip
        sources = [SourceRef("record", str(i.id), f"finance.invoices:{i.number}",
                             value=i.total_amount) for i in items]  # fmt: skip
        return {"total": total, "invoices": rows}, sources

    async def _expenses(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        finance_scope.require_reader(self.user)  # REV refused; MGR pinned by the service
        items, total = await FinanceService(self.db).list_expenses(
            self.user, _page(args, "spent_on"), period=args.get("period") or None,
            department_id=None, category=None,
        )  # fmt: skip
        rows = [{"title": e.title, "amount": e.amount, "currency": e.currency,
                 "category": e.category, "spent_on": e.spent_on.isoformat(), "vendor": e.vendor}
                for e in items]  # fmt: skip
        sources = [SourceRef("record", str(e.id), f"finance.expenses:{e.title[:60]}", e.period,
                             e.amount) for e in items]  # fmt: skip
        return {"total": total, "expenses": rows}, sources

    async def _deals(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        sales_scope.require_record_reader(self.user)  # REV refused; MGR pinned by the service
        items, total = await SalesService(self.db).list_deals(
            self.user, _page(args, "created_at"), stage=None, owner_id=None, client_id=None,
            close_from=None, close_to=None,
        )  # fmt: skip
        rows = [{"name": d.name, "stage": d.stage, "deal_value": d.deal_value,
                 "weighted_value": d.weighted_value, "probability_pct": d.probability_pct,
                 "currency": d.currency, "expected_close_date": d.expected_close_date.isoformat()
                 if d.expected_close_date else None} for d in items]  # fmt: skip
        sources = [SourceRef("record", str(d.id), f"sales.deals:{d.name[:60]}",
                             value=d.deal_value) for d in items]  # fmt: skip
        return {"total": total, "deals": rows}, sources

    async def _tasks(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        if any(args.get(k) for k in ("assignee_code", "department_code", "project_code")):
            raise ValueError("list_tasks filters by status only")
        status = args.get("status")
        items, total = await TaskService(self.db).list_tasks(
            self.user, _page(args, "due_date", order="asc"), filters={}, overdue=None,
            statuses=[status] if status else None,
        )  # fmt: skip
        rows = [{"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority,
                 "due_date": t.due_date.isoformat() if t.due_date else None}
                for t in items]  # fmt: skip
        sources = [SourceRef("record", str(t.id), f"execution.tasks:{t.title[:60]}")
                   for t in items]  # fmt: skip
        return {"total": total, "tasks": rows}, sources

    async def _hiring_plans(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        items, total = await HiringPlanService(self.db).list_plans(
            self.user, _page(args, "created_at"), department_id=None, status=None, delayed=None,
            today=today(),
        )  # fmt: skip
        rows = [{"title": p.title, "position": p.position, "headcount": p.headcount,
                 "filled": p.filled, "priority": p.priority, "status": p.status,
                 "target_date": p.target_date.isoformat()} for p in items]  # fmt: skip
        sources = [SourceRef("record", str(p.id), f"hr.hiring_plans:{p.title[:60]}",
                             value=p.headcount) for p in items]  # fmt: skip
        return {"total": total, "hiring_plans": rows}, sources

    async def _kpi_status(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        code = str(args.get("kpi_code") or "").strip()
        items, total = await KpiService(self.db).list_kpis(
            self.user, _page(args, "code", order="asc"), owner_id=None, metric_code=None,
        )  # fmt: skip
        rows, sources = [], []
        for k in items:
            if code and k.code != code:
                continue
            ev = k.latest_evaluation
            brief = ev.model_dump(mode="json", exclude_none=True) if ev is not None else None
            rows.append({"code": k.code, "name": k.name, "unit": k.unit, "target": k.target,
                         "status": k.status, "latest_evaluation": brief})  # fmt: skip
            sources.append(SourceRef("record", str(k.id), f"execution.kpis:{k.code}",
                                     value=k.target))  # fmt: skip
        return {"total": len(rows) if code else total, "kpis": rows}, sources

    async def _budget_status(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        finance_scope.require_reader(self.user)
        department = finance_scope.department_filter(self.user, None)
        items = await BudgetService(self.db).statuses(
            period=args.get("period") or None, department_id=department
        )
        rows = [{"period": b.period, "allocated_amount": b.allocated_amount,
                 "spent_amount": b.spent_amount, "utilization_pct": b.budget_utilization_pct,
                 "currency": b.currency, "status": b.status} for b in items]  # fmt: skip
        sources = [SourceRef("record", str(b.budget_id), f"finance.budgets:{b.period}",
                             b.period, b.budget_utilization_pct) for b in items]  # fmt: skip
        return {"budgets": rows}, sources

    async def _sales_pipeline(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        out = await SalesAnalytics(self.db).pipeline(self.user, args.get("period") or None, None)
        stages = [{"stage": s.stage, "count": s.count, "value": s.value,
                   "weighted_value": s.weighted_value} for s in out.stages]  # fmt: skip
        # the pillar metrics stay in the payload: the recorded replay answers read them
        pillar = await self._pillar("TOOL-get_sales_pipeline", "C", time.monotonic())
        data = {**pillar.data, "stages": stages, "coverage_ratio": out.coverage_ratio,
                "currency": out.currency}  # fmt: skip
        return data, pillar.sources

    async def _workload(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        if args.get("department_code") or args.get("team_code"):
            raise ValueError("get_workload has no department/team filter yet")
        items = await HrDashboardService(self.db).workload(
            self.user, department_id=None, as_of=today()
        )
        rows = [
            {"employee_ref": w.employee_ref, "open_tasks": w.open_tasks,
             "load_pct": w.load_pct, "overloaded": w.overloaded}
            for w in items[:20]
        ]  # fmt: skip
        data = {"employees": len(items), "overloaded": sum(1 for w in items if w.overloaded),
                "items": rows}  # fmt: skip
        return data, [SourceRef("tool_result", "TOOL-get_workload", "hr.workload",
                                value=len(items))]  # fmt: skip

    async def _lineage(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[SourceRef]]:
        """`ref` = `<entity>:<record uuid>`, as `SourceRef.label` + id give it."""
        entity, _, rid = str(args.get("ref", "")).partition(":")
        out = await read_lineage(self.db, self.user, entity.strip(), uuid.UUID(rid.strip()))
        if out.restricted:
            return {"restricted": True, "reason": out.reason}, []
        links = [{"document_id": str(k.source_document_id), "document_type": k.document_type,
                  "page_number": k.page_number, "field_name": k.field_name,
                  "action_name": k.action_name} for k in out.links or ()]  # fmt: skip
        sources = [SourceRef("document_page", f"{k['document_id']}#p{k['page_number']}",
                             f"{k['document_type']} · tr.{k['page_number']}")
                   for k in links]  # fmt: skip
        return {"restricted": False, "links": links}, sources

    async def _source_document(
        self, args: dict[str, Any]
    ) -> tuple[dict[str, Any], list[SourceRef]]:
        doc_id = uuid.UUID(str(args["document_id"]))
        page = int(args["page"]) if args.get("page") is not None else None
        doc, pages = await InboxService(self.db).source_for_model(
            self.user, doc_id, page, max_chars=SOURCE_PAGE_CHARS
        )
        sources = [SourceRef("document_page", f"{doc.id}#p{p.page_number}",
                             f"{doc.original_filename} · tr.{p.page_number}")
                   for p in pages]  # fmt: skip
        data = {"document_id": str(doc.id), "filename": doc.original_filename,
                "page_count": doc.page_count, "status": doc.status,
                "pages": [{"page_number": p.page_number, "text": p.text_content}
                          for p in pages]}  # fmt: skip
        return data, sources

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
    "TOOL-list_objectives": "_okr_status",
    "TOOL-list_invoices": "_invoices",
    "TOOL-list_expenses": "_expenses",
    "TOOL-list_deals": "_deals",
    "TOOL-list_tasks": "_tasks",
    "TOOL-list_hiring_plans": "_hiring_plans",
    "TOOL-get_kpi_status": "_kpi_status",
    "TOOL-get_budget_status": "_budget_status",
    "TOOL-get_sales_pipeline": "_sales_pipeline",
    "TOOL-get_workload": "_workload",
    "TOOL-get_lineage": "_lineage",
    "TOOL-get_source_document": "_source_document",
}
_BOUND = frozenset({*PILLAR_TOOLS, *_RECORD_TOOLS, "TOOL-get_metric", "TOOL-list_alerts",
                    "TOOL-search_documents"}) - REPLAY_ONLY  # fmt: skip


def _metric_name(code: str) -> str | None:
    metric = METRIC_CATALOG.get(code)
    return metric.name_vi if metric is not None else None


def model_ready(tool: ToolDef) -> bool:
    """The tool does what its name says: a READ with a binding, a WRITE with a registered ACT."""
    if tool.kind == "READ":
        return tool.name in _BOUND
    return tool.action_name is not None and get_action(tool.action_name) is not None


def _page(args: dict[str, Any], sort_by: str, order: str = "desc") -> PageParams:
    limit = max(1, min(int(args.get("limit") or 20), 50))
    return PageParams(limit=limit, offset=0, sort_by=sort_by, order=order)  # type: ignore[arg-type]


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
