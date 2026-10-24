"""Tool Registry — 53 `TOOL-*` (10 §7 + §7.2.5: 43 v2.0/v2.1 + 10 M1.6), 13 metadata (10 §2.1).

`TOOLS` is the single source; `all_tools()`, `get_tool()` and the filters below are the only
public API. Every `ToolDef` is validated when constructed (`spec.validate_tool`) so a tool with
a missing metadata never gets registered (`ToolRegistryError` at import — TC-M16-01).
A turn's available tools = tools whose `required_permissions` the asker holds (`available_for`,
P06) ∩ the agent's `allowed_tools` (T-646). `advertisable_for` additionally drops
`declare_to_model=False` (APPROVAL) and `p1_frozen` tools (product/risk, R-DEC-16) and applies
the classification ceiling (07 §6.5). Adding a tool is a contract change: 10 §7 + 00 §4.8 first.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Final

from app.modules.ai.tools.schemas import (
    APPROVAL_OUT,
    DATE,
    INT,
    LIMIT,
    NUM,
    PERIOD,
    READ_OUT,
    UUID,
    WRITE_OUT,
    S,
    enum,
    obj,
)  # fmt: skip
from app.modules.ai.tools.spec import ToolDef, ToolRegistryError

CLASSIFICATION_RANK = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "SECRET": 3}
# R-DEC-16: modules frozen at P1 — their tools carry `p1_frozen` and are not advertised.
P1_FROZEN_DOMAINS = frozenset({"product", "risk"})
# 10 §7.2.5 row 14 `owner`: role of the domain owner approving an autonomy raise.
OWNER_BY_DOMAIN = {
    "finance": "ROLE-DIR:F", "sales": "ROLE-DIR:C", "hr": "ROLE-DIR:O", "product": "ROLE-DIR:U",
    "risk": "ROLE-DIR:S", "execution": "ROLE-CEO", "dashboard": "ROLE-CEO",
    "platform": "ROLE-CEO", "idp": "ROLE-ADM", "ai": "ROLE-ADM",
}  # fmt: skip
CONF: Final = "CONFIDENTIAL"
INTERNAL: Final = "INTERNAL"

_LIST = obj(limit=LIMIT, period=PERIOD)
_PERIOD_ONLY = obj(period=PERIOD)


def _read(
    name: str, endpoint: str, perm: str, scope: str, desc: str, *, brd: str | None = None,
    risk: str = "low", cls: str = INTERNAL, cost: str = "low", compute: bool = False,
    args: dict[str, Any] | None = None,
) -> ToolDef:  # fmt: skip
    domain = perm.split(":", 1)[0]
    return ToolDef(
        name=name, description=desc, domain=domain, endpoint_ref=endpoint, kind="READ",
        risk_level=risk, autonomy_default="L0", autonomy_max="L0",  # type: ignore[arg-type]
        required_permissions=(perm,), data_scope=scope,
        data_classification=cls, reversible=None, cost_estimate=cost,  # type: ignore[arg-type]
        input_schema=args or _PERIOD_ONLY, output_schema=READ_OUT, approval_required="never",
        audit_required=False, owner=OWNER_BY_DOMAIN[domain], brd_name=brd, compute=compute,
    )  # fmt: skip


def _write(
    name: str, endpoint: str, domain: str, extra_perm: str | None, scope: str, desc: str, *,
    args: dict[str, Any], default: str, maximum: str, brd: str | None = None,
    risk: str = "medium", cls: str = CONF, reversible: bool = True, cost: str = "low",
    kind: str = "WRITE", approval: str = "never",
) -> ToolDef:  # fmt: skip
    perms = ("ai:write",) + ((extra_perm,) if extra_perm else ())
    return ToolDef(
        name=name, description=desc, domain=domain, endpoint_ref=endpoint,
        kind=kind, risk_level=risk,  # type: ignore[arg-type]
        autonomy_default=default, autonomy_max=maximum,  # type: ignore[arg-type]
        required_permissions=perms, data_scope=scope, data_classification=cls,  # type: ignore[arg-type]
        reversible=reversible, cost_estimate=cost,  # type: ignore[arg-type]
        input_schema=args, output_schema=WRITE_OUT,
        approval_required=approval,  # type: ignore[arg-type]
        audit_required=True, owner=OWNER_BY_DOMAIN[domain], brd_name=brd,
        action_name="ACT-" + name.removeprefix("TOOL-"),
    )  # fmt: skip


def _approval(name: str, decision: str, risk: str) -> ToolDef:
    return ToolDef(
        name=name, description=f"{decision.capitalize()} an approval request (server-only).",
        domain="platform", endpoint_ref=f"EP-WF-03 decision={decision}", kind="APPROVAL",
        risk_level=risk, autonomy_default="L0", autonomy_max="L0",  # type: ignore[arg-type]
        required_permissions=("platform:approve",), data_scope="platform:record",
        data_classification=CONF, reversible=False, cost_estimate="low",
        input_schema=obj(("request_id",), request_id=UUID, comment=S),
        output_schema=APPROVAL_OUT, approval_required="always", audit_required=True,
        owner="ROLE-CEO", declare_to_model=False,
    )  # fmt: skip


# ---------------------------------------------------------------- READ (31; 2 `compute`)
_METRIC_ARGS = obj(("metric_code",), metric_code=S, period=PERIOD)
_TASK_FILTER = obj(limit=LIMIT, assignee_code=S, department_code=S, project_code=S,
                   status=enum("todo", "in_progress", "blocked", "done", "cancelled"))  # fmt: skip
_READ_TOOLS: tuple[ToolDef, ...] = (
    _read(
        "TOOL-get_finance_dashboard",
        "EP-60",
        "finance:query",
        "finance:aggregate",
        "5-metric Finance pillar card (FIN-01..07 summary).",
        brd="get_financial_summary",
    ),
    _read(
        "TOOL-get_finance_forecast",
        "EP-66.L",
        "finance:read",
        "finance:aggregate",
        "Finance revenue / expense forecast.",
        brd="get_financial_summary",
        risk="medium",
    ),
    _read(
        "TOOL-list_expenses",
        "EP-62.L",
        "finance:read",
        "finance:record",
        "List expense records (filtered, paginated).",
        brd="get_financial_summary",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-get_budget_status",
        "EP-64",
        "finance:query",
        "finance:aggregate",
        "Budget vs actual utilisation by department.",
        brd="get_financial_summary",
    ),
    _read(
        "TOOL-list_invoices",
        "EP-67.L",
        "finance:read",
        "finance:record",
        "List invoices (filtered, paginated).",
        brd="get_financial_summary",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-get_runway_what_if",
        "EP-69",
        "finance:query",
        "finance:aggregate",
        "Runway what-if (no new revenue).",
        brd="get_financial_summary",
        cost="medium",
        compute=True,
        args=obj(monthly_burn_change_pct=NUM),
    ),
    _read(
        "TOOL-get_sales_dashboard",
        "EP-70",
        "sales:query",
        "sales:aggregate",
        "Sales pillar card (pipeline, NRR, concentration).",
        brd="get_sales_pipeline",
    ),
    _read(
        "TOOL-list_deals",
        "EP-72.L",
        "sales:read",
        "sales:record",
        "List deals (filtered).",
        brd="get_sales_pipeline",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-get_sales_pipeline",
        "EP-75",
        "sales:query",
        "sales:aggregate",
        "Sales pipeline coverage by stage.",
        brd="get_sales_pipeline",
    ),
    _read(
        "TOOL-get_hr_dashboard",
        "EP-80",
        "hr:query",
        "hr:aggregate",
        "HR / Operations pillar card (turnover, hiring).",
        brd="get_health_metrics",
    ),
    _read(
        "TOOL-list_hiring_plans",
        "EP-84.L",
        "hr:read",
        "hr:record",
        "List hiring plans (names pseudonymised EMP-xxxx).",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-get_workload",
        "EP-87",
        "hr:query",
        "hr:record",
        "Team workload summary.",
        brd="get_employee_workload",
        cls=CONF,
        cost="medium",
        args=obj(department_code=S, team_code=S),
    ),
    _read(
        "TOOL-get_product_dashboard",
        "EP-90",
        "product:query",
        "product:aggregate",
        "Product / Innovation pillar card.",
    ),
    _read(
        "TOOL-get_product_metrics",
        "EP-95.L",
        "product:query",
        "product:aggregate",
        "Product metric history (churn, retention, NPS).",
    ),
    _read(
        "TOOL-get_risk_dashboard",
        "EP-100",
        "risk:query",
        "risk:aggregate",
        "Strategy / Risk pillar card.",
    ),
    _read(
        "TOOL-list_risks",
        "EP-101.L",
        "risk:read",
        "risk:record",
        "List risks in the register.",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-run_risk_scenario",
        "EP-105",
        "risk:query",
        "risk:aggregate",
        "Run a risk scenario (saves ENT-Scenario, no business write).",
        risk="medium",
        cost="high",
        compute=True,
        args=obj(("scenario_code",), scenario_code=S),
    ),
    _read(
        "TOOL-get_execution_dashboard",
        "EP-49",
        "execution:query",
        "execution:aggregate",
        "Execution pillar / FOCUS dashboard snapshot.",
        brd="get_department_performance",
    ),
    _read(
        "TOOL-list_tasks",
        "EP-TASK-01",
        "execution:read",
        "execution:record",
        "List execution tasks (filtered).",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_TASK_FILTER,
    ),
    _read(
        "TOOL-list_objectives",
        "EP-OKR-01",
        "execution:read",
        "execution:record",
        "List OKR objectives.",
        brd="get_okr_status",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=_LIST,
    ),
    _read(
        "TOOL-get_metric",
        "EP-12",
        "dashboard:read",
        "dashboard:aggregate",
        "One metric value + threshold + lineage url.",
        brd="get_health_metrics",
        args=_METRIC_ARGS,
    ),
    _read(
        "TOOL-list_alerts",
        "EP-15",
        "dashboard:read",
        "dashboard:aggregate",
        "Open alerts across visible pillars.",
        brd="get_health_metrics",
        args=obj(),
    ),
    _read(
        "TOOL-get_lineage",
        "EP-14",
        "dashboard:read",
        "dashboard:record",
        "Metric / record lineage (source documents, computation).",
        brd="get_source_document",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=obj(("ref",), ref=S),
    ),
    _read(
        "TOOL-search_documents",
        "EP-24",
        "idp:read",
        "idp:document",
        "Search source documents (+ RAG SOP/policy).",
        brd="search_documents",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=obj(("query",), query=S, limit=LIMIT),
    ),
    _read(
        "TOOL-get_source_document",
        "EP-DC-02",
        "idp:read",
        "idp:document",
        "Get a source document (page + bbox, no raw url to LLM).",
        brd="get_source_document",
        risk="medium",
        cls=CONF,
        cost="medium",
        args=obj(("document_id",), document_id=UUID, page=INT),
    ),
    _read(
        "TOOL-get_kpi_status",
        "EP-KPI-01",
        "execution:read",
        "execution:aggregate",
        "KPI status + evaluation band + last check-in.",
        brd="get_kpi_status",
        args=obj(kpi_code=S, period=PERIOD),
    ),
    _read(
        "TOOL-get_cash_flow_forecast",
        "EP-128",
        "finance:read",
        "finance:aggregate",
        "13-week cash-flow forecast (GET).",
        brd="get_financial_summary",
        risk="medium",
        args=obj(),
    ),
    # ---- M1.6 (T-645, 10 §7.2.5) ----
    _read(
        "TOOL-get_org_tree",
        "EP-ORG-24",
        "hr:read",
        "hr:structure",
        "Organization tree (departments, teams, headcount) within the asker's scope.",
        args=obj(as_of=DATE),
    ),
    _read(
        "TOOL-get_okr_status",
        "EP-OKR-01/03/06",
        "execution:read",
        "execution:record",
        "OKR objectives status + progress + at-risk key results.",
        brd="get_okr_status",
        args=obj(period_key=PERIOD, at_risk={"type": "boolean"}, limit=LIMIT),
    ),
    _read(
        "TOOL-get_overdue_tasks",
        "EP-TASK-01 overdue=true",
        "execution:read",
        "execution:record",
        "Overdue open tasks within the asker's scope.",
        brd="get_overdue_tasks",
        args=obj(limit=LIMIT),
    ),
    _read(
        "TOOL-get_project_status",
        "EP-TASK-11",
        "execution:read",
        "execution:record",
        "Project status: progress, planned, late, open/overdue task counts.",
        brd="get_project_status",
        args=obj(project_id=UUID, limit=LIMIT),
    ),
)

# ---------------------------------------------------------------- WRITE / EXECUTION / APPROVAL
_TASK_ARGS = obj(("title",), title=S, assignee_code=S, due_date=DATE, project_code=S,
                 priority=enum("low", "medium", "high", "urgent"), description=S)  # fmt: skip
_WRITE_TOOLS: tuple[ToolDef, ...] = (
    _write(
        "TOOL-create_task",
        "EP-TASK-02",
        "execution",
        "execution:write",
        "execution:record",
        "Create an execution task.",
        brd="create_task",
        args=_TASK_ARGS,
        default="L3",
        maximum="L3",
    ),
    _write(
        "TOOL-record_decision",
        "EP-43.C",
        "execution",
        "execution:write",
        "execution:record",
        "Record a decision.",
        brd="log_decision",
        args=obj(("title",), title=S, meeting_id=UUID, rationale=S),
        default="L3",
        maximum="L3",
    ),
    _write(
        "TOOL-create_meeting",
        "EP-42.C",
        "execution",
        "execution:write",
        "execution:record",
        "Create an internal meeting.",
        brd="create_calendar_event",
        args=obj(
            ("title", "starts_at"), title=S, starts_at={"type": "string", "format": "date-time"}
        ),
        default="L3",
        maximum="L3",
    ),
    _write(
        "TOOL-record_kpi_measurement",
        "EP-KPI-07",
        "execution",
        "execution:write",
        "execution:record",
        "Record a KPI measurement / check-in.",
        brd="record_kpi_measurement",
        args=obj(
            ("kpi_code", "period_key", "actual_value"),
            kpi_code=S,
            period_key=PERIOD,
            actual_value=NUM,
        ),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-record_expense",
        "EP-62.C",
        "finance",
        "finance:write",
        "finance:record",
        "Record an expense (<5M VND may be L3).",
        risk="high",
        approval="threshold",
        args=obj(("amount", "category"), amount=INT, currency=S, category=S, spent_on=DATE),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-create_invoice",
        "EP-67.C",
        "finance",
        "finance:write",
        "finance:record",
        "Create an invoice.",
        risk="high",
        approval="threshold",
        args=obj(
            ("invoice_number", "total_amount"),
            invoice_number=S,
            total_amount=INT,
            currency=S,
            issue_date=DATE,
        ),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-upsert_deal",
        "EP-72",
        "sales",
        "sales:write",
        "sales:record",
        "Create or update a deal.",
        risk="high",
        args=obj(("name",), name=S, stage=S, amount=INT, currency=S),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-upsert_risk",
        "EP-101",
        "risk",
        "risk:write",
        "risk:record",
        "Create or update a risk.",
        args=obj(("title",), title=S, likelihood=INT, impact=INT),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-create_mitigation",
        "EP-103.C",
        "risk",
        "risk:write",
        "risk:record",
        "Create a risk mitigation.",
        args=obj(("risk_id", "title"), risk_id=UUID, title=S),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-submit_document",
        "EP-DC-01",
        "idp",
        "idp:write",
        "idp:document",
        "Submit a document (C2 voice / attachment; always an action card).",
        brd="upload_document",
        cost="medium",
        args=obj(("document_type",), document_type=S, note=S),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-assign_task",
        "EP-TASK-04",
        "execution",
        "execution:write",
        "execution:record",
        "Assign / reassign a task (undo via before-snapshot).",
        brd="assign_task",
        args=obj(("task_id", "assignee_code"), task_id=UUID, assignee_code=S),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-generate_report",
        "EP-121",
        "dashboard",
        "dashboard:read",
        "dashboard:aggregate",
        "Generate a report (weekly / monthly / board).",
        brd="generate_report",
        risk="low",
        cls=INTERNAL,
        reversible=False,
        cost="high",
        args=obj(("kind",), kind=enum("weekly", "monthly", "board"), period=PERIOD),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-request_approval",
        "EP-123.C",
        "dashboard",
        "dashboard:read",
        "platform:record",
        "Open an approval request.",
        brd="request_approval",
        args=obj(("subject", "reason"), subject=S, reason=S, amount=INT, currency=S),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-send_notification",
        "EP-NTF-01",
        "platform",
        None,
        "platform:record",
        "Send a notification (in-app L3 / email channel EXECUTION L2).",
        brd="send_notification",
        risk="low",
        cls=INTERNAL,
        reversible=False,
        kind="EXECUTION",
        args=obj(
            ("recipient_code", "message"),
            recipient_code=S,
            message=S,
            channel=enum("in_app", "email"),
        ),
        default="L3",
        maximum="L3",
    ),
    # ---- M1.6 (T-645, 10 §7.2.5) ----
    _write(
        "TOOL-update_task",
        "EP-TASK-04",
        "execution",
        "execution:write",
        "execution:record",
        "Update a task's title / description / due date / priority / status (undo: snapshot).",
        brd="update_task",
        args=obj(
            ("task_id",),
            task_id=UUID,
            title=S,
            description=S,
            due_date=DATE,
            priority=enum("low", "medium", "high", "urgent"),
            status=enum(
                "backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"
            ),
        ),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-record_kr_checkin",
        "EP-PRF-02",
        "execution",
        "execution:write",
        "execution:self",
        "Record a key-result check-in (value + confidence).",
        args=obj(
            ("kr_ref", "value", "confidence"),
            kr_ref=UUID,
            value=NUM,
            confidence=enum("HIGH", "MEDIUM", "LOW"),
            note=S,
        ),
        default="L2",
        maximum="L3",
    ),
    _write(
        "TOOL-upsert_kpi",
        "EP-KPI-02",
        "execution",
        "execution:write",
        "execution:record",
        "Create or update a KPI by code.",
        args=obj(
            ("code", "name", "unit", "target", "owner_code"),
            code=S,
            name=S,
            unit=S,
            target=NUM,
            owner_code=S,
            department_code=S,
            period_type=enum("MONTH", "QUARTER", "YEAR", "ROLLING_12M"),
            direction=enum("HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE", "BINARY"),
        ),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-upsert_objective",
        "EP-OKR-02",
        "execution",
        "execution:write",
        "execution:record",
        "Create or update an OKR objective (title + period + owner).",
        args=obj(
            ("title", "period_key", "owner_code"),
            title=S,
            period_key=PERIOD,
            owner_code=S,
            parent_title=S,
            level=enum("company", "department", "team", "individual"),
        ),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-create_department",
        "EP-ORG-07",
        "hr",
        "hr:admin",
        "hr:structure",
        "Create a department in the live organization.",
        cls=INTERNAL,
        args=obj(("code", "name"), code=S, name=S, parent_code=S),
        default="L2",
        maximum="L2",
    ),
    _write(
        "TOOL-create_team",
        "EP-ORG-12",
        "hr",
        "hr:admin",
        "hr:structure",
        "Create a team inside a department.",
        cls=INTERNAL,
        args=obj(("code", "name", "department_code"), code=S, name=S, department_code=S),
        default="L2",
        maximum="L2",
    ),
    _approval("TOOL-approve_request", "approve", "high"),
    _approval("TOOL-reject_request", "reject", "medium"),
)

TOOLS: tuple[ToolDef, ...] = tuple(
    replace(t, p1_frozen=True) if t.domain in P1_FROZEN_DOMAINS else t
    for t in (*_READ_TOOLS, *_WRITE_TOOLS)
)

_BY_NAME: dict[str, ToolDef] = {t.name: t for t in TOOLS}
if len(_BY_NAME) != len(TOOLS):
    raise ToolRegistryError("duplicate tool name in registry")


def all_tools() -> tuple[ToolDef, ...]:
    return TOOLS


def get_tool(name: str) -> ToolDef | None:
    return _BY_NAME.get(name)


def tool_kind(name: str) -> str:
    """`ToolCallLog.tool_kind` for a tool name (unknown / unregistered → `READ`, 05 §2.8)."""
    t = _BY_NAME.get(name)
    return t.kind if t else "READ"


def tool_for_action(action_name: str) -> ToolDef | None:
    """The WRITE/EXECUTION tool whose `action_name` is this `ACT-*` (policy backfill, EP-AI-19)."""
    return next((t for t in TOOLS if t.action_name == action_name), None)


def available_for(permissions: frozenset[str]) -> tuple[ToolDef, ...]:
    """Tools the asker may use this turn (holds ALL required_permissions — P06, 02 §7.2)."""
    return tuple(t for t in TOOLS if set(t.required_permissions) <= permissions)


def advertisable_for(
    permissions: frozenset[str], *, max_classification: str | None = None,
    allowed: frozenset[str] | None = None,
) -> tuple[ToolDef, ...]:  # fmt: skip
    """Tools sent to the model: available, `declare_to_model`, not `p1_frozen` (R-DEC-16),
    within the classification ceiling and — when given — the agent's `allowed_tools` (T-646)."""
    ceiling = CLASSIFICATION_RANK.get(max_classification or "SECRET", 3)
    return tuple(
        t
        for t in available_for(permissions)
        if t.declare_to_model
        and not t.p1_frozen
        and CLASSIFICATION_RANK[t.data_classification] <= ceiling
        and (allowed is None or t.name in allowed)
    )
