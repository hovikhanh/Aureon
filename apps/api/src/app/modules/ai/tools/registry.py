"""Tool Registry — the 43 `TOOL-*` of 10 §7 (00 §4.8: 35 v2.0 + 8 v2.1). Metadata per §7.4.

`TOOLS` is the single source; `all_tools()`, `get_tool()`, and the filters below are the only
public API. A turn's available tools = tools whose `required_permissions` the asker holds
(`available_for`, P06, 02 §7.2) minus those removed by the autonomy / kill-switch layer (T-310).
`advertisable_for` additionally drops `declare_to_model=False` (APPROVAL layer never sent to the
model, §7.3) and `p1_frozen` tools (product/risk, R-DEC-16); for classification routing (§7.4,
07 §6.5) callers may further filter by `max_classification`. Adding a tool here is a contract
change (§7.2 rule 4): update 10 §7 + 00 §4.8 + 02 §7.3 first.
"""

from __future__ import annotations

from dataclasses import replace

from app.modules.ai.tools.spec import ToolDef

CLASSIFICATION_RANK = {"INTERNAL": 1, "CONFIDENTIAL": 2, "SECRET": 3}
# R-DEC-16: modules frozen at P1 — their tools carry `p1_frozen` and are not advertised.
P1_FROZEN_DOMAINS = frozenset({"product", "risk"})


def _read(
    name: str,
    endpoint: str,
    perm: str,
    *,
    kind: str = "READ",
    risk: str = "low",
    scope: str,
    classification: str = "INTERNAL",
    cost: str = "low",
    desc: str,
) -> ToolDef:
    return ToolDef(
        name=name,
        description=desc,
        domain=perm.split(":", 1)[0],
        endpoint=endpoint,
        kind=kind,  # type: ignore[arg-type]
        risk_level=risk,  # type: ignore[arg-type]
        autonomy_default="L0",
        autonomy_max="L0",
        required_permissions=(perm,),
        data_scope=scope,
        classification=classification,  # type: ignore[arg-type]
        reversible=None,
        cost_estimate=cost,  # type: ignore[arg-type]
    )


def _write(
    name: str,
    endpoint: str,
    domain: str,
    extra_perm: str | None,
    *,
    risk: str,
    default: str,
    maximum: str,
    scope: str,
    classification: str = "CONFIDENTIAL",
    reversible: bool = True,
    cost: str = "low",
    kind: str = "WRITE",
    desc: str,
) -> ToolDef:
    perms = ("ai:write",) + ((extra_perm,) if extra_perm else ())
    return ToolDef(
        name=name,
        description=desc,
        domain=domain,
        endpoint=endpoint,
        kind=kind,  # type: ignore[arg-type]
        risk_level=risk,  # type: ignore[arg-type]
        autonomy_default=default,  # type: ignore[arg-type]
        autonomy_max=maximum,  # type: ignore[arg-type]
        required_permissions=perms,
        data_scope=scope,
        classification=classification,  # type: ignore[arg-type]
        reversible=reversible,
        cost_estimate=cost,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------- §7.1 read / compute (25)
_READ_TOOLS: tuple[ToolDef, ...] = (
    _read(
        "TOOL-get_finance_dashboard",
        "EP-60",
        "finance:query",
        scope="finance:aggregate",
        desc="5-metric Finance pillar card (FIN-01..07 summary).",
    ),
    _read(
        "TOOL-get_finance_forecast",
        "EP-66.L",
        "finance:read",
        risk="medium",
        scope="finance:aggregate",
        cost="low",
        desc="Finance revenue / expense forecast.",
    ),
    _read(
        "TOOL-list_expenses",
        "EP-62.L",
        "finance:read",
        risk="medium",
        scope="finance:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List expense records (filtered, paginated).",
    ),
    _read(
        "TOOL-get_budget_status",
        "EP-64",
        "finance:query",
        scope="finance:aggregate",
        desc="Budget vs actual utilisation by department.",
    ),
    _read(
        "TOOL-list_invoices",
        "EP-67.L",
        "finance:read",
        risk="medium",
        scope="finance:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List invoices (filtered, paginated).",
    ),
    _read(
        "TOOL-get_runway_what_if",
        "EP-69",
        "finance:query",
        kind="COMPUTE",
        scope="finance:aggregate",
        cost="medium",
        desc="Runway what-if (no new revenue).",
    ),
    _read(
        "TOOL-get_sales_dashboard",
        "EP-70",
        "sales:query",
        scope="sales:aggregate",
        desc="Sales pillar card (pipeline, NRR, concentration).",
    ),
    _read(
        "TOOL-list_deals",
        "EP-72.L",
        "sales:read",
        risk="medium",
        scope="sales:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List deals (filtered).",
    ),
    _read(
        "TOOL-get_sales_pipeline",
        "EP-75",
        "sales:query",
        scope="sales:aggregate",
        desc="Sales pipeline coverage by stage.",
    ),
    _read(
        "TOOL-get_hr_dashboard",
        "EP-80",
        "hr:query",
        scope="hr:aggregate",
        desc="HR / Operations pillar card (turnover, hiring).",
    ),
    _read(
        "TOOL-list_hiring_plans",
        "EP-84.L",
        "hr:read",
        risk="medium",
        scope="hr:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List hiring plans (names pseudonymised EMP-xxxx).",
    ),
    _read(
        "TOOL-get_workload",
        "EP-87",
        "hr:query",
        scope="hr:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="Team workload summary.",
    ),
    _read(
        "TOOL-get_product_dashboard",
        "EP-90",
        "product:query",
        scope="product:aggregate",
        desc="Product / Innovation pillar card.",
    ),
    _read(
        "TOOL-get_product_metrics",
        "EP-95.L",
        "product:query",
        scope="product:aggregate",
        desc="Product metric history (churn, retention, NPS).",
    ),
    _read(
        "TOOL-get_risk_dashboard",
        "EP-100",
        "risk:query",
        scope="risk:aggregate",
        desc="Strategy / Risk pillar card.",
    ),
    _read(
        "TOOL-list_risks",
        "EP-101.L",
        "risk:read",
        risk="medium",
        scope="risk:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List risks in the register.",
    ),
    _read(
        "TOOL-run_risk_scenario",
        "EP-105",
        "risk:query",
        kind="COMPUTE",
        risk="medium",
        scope="risk:aggregate",
        cost="high",
        desc="Run a risk scenario (saves ENT-Scenario, no business write).",
    ),
    _read(
        "TOOL-get_execution_dashboard",
        "EP-49",
        "execution:query",
        scope="execution:aggregate",
        desc="Execution pillar / FOCUS dashboard snapshot.",
    ),
    _read(
        "TOOL-list_tasks",
        "EP-TASK-01",
        "execution:read",
        risk="medium",
        scope="execution:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List execution tasks (filtered).",
    ),
    _read(
        "TOOL-list_objectives",
        "EP-OKR-01",
        "execution:read",
        risk="medium",
        scope="execution:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="List OKR objectives.",
    ),
    _read(
        "TOOL-get_metric",
        "EP-12",
        "dashboard:read",
        scope="dashboard:aggregate",
        desc="One metric value + threshold + lineage url.",
    ),
    _read(
        "TOOL-list_alerts",
        "EP-15",
        "dashboard:read",
        scope="dashboard:aggregate",
        desc="Open alerts across visible pillars.",
    ),
    _read(
        "TOOL-get_lineage",
        "EP-14",
        "dashboard:read",
        risk="medium",
        scope="dashboard:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="Metric lineage (source documents, computation).",
    ),
    _read(
        "TOOL-search_documents",
        "EP-24",
        "idp:read",
        risk="medium",
        scope="idp:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="Search source documents (+ RAG SOP/policy).",
    ),
    _read(
        "TOOL-get_source_document",
        "EP-DC-02",
        "idp:read",
        risk="medium",
        scope="idp:record",
        classification="CONFIDENTIAL",
        cost="medium",
        desc="Get a source document (page + bbox, no raw url to LLM).",
    ),
)

# ---------------------------------------------------------------- §7.2 write via ACT-* (10)
_WRITE_TOOLS: tuple[ToolDef, ...] = (
    _write(
        "TOOL-create_task",
        "EP-TASK-02 / ACT-create_task",
        "execution",
        "execution:write",
        risk="medium",
        default="L3",
        maximum="L3",
        scope="execution:record",
        desc="Create an execution task.",
    ),
    _write(
        "TOOL-record_decision",
        "EP-43.C / ACT-record_decision",
        "execution",
        "execution:write",
        risk="medium",
        default="L3",
        maximum="L3",
        scope="execution:record",
        desc="Record a decision.",
    ),
    _write(
        "TOOL-create_meeting",
        "EP-42.C / ACT-create_meeting",
        "execution",
        "execution:write",
        risk="medium",
        default="L3",
        maximum="L3",
        scope="execution:record",
        desc="Create a meeting.",
    ),
    _write(
        "TOOL-record_kpi_measurement",
        "EP-KPI-07 / ACT-record_kpi_measurement",
        "execution",
        "execution:write",
        risk="medium",
        default="L2",
        maximum="L3",
        scope="execution:record",
        desc="Record a KPI measurement / check-in.",
    ),
    _write(
        "TOOL-record_expense",
        "EP-62.C / ACT-record_expense",
        "finance",
        "finance:write",
        risk="high",
        default="L2",
        maximum="L3",
        scope="finance:record",
        desc="Record an expense (<5M VND may be L3).",
    ),
    _write(
        "TOOL-create_invoice",
        "EP-67.C / ACT-create_invoice",
        "finance",
        "finance:write",
        risk="high",
        default="L2",
        maximum="L3",
        scope="finance:record",
        desc="Create an invoice.",
    ),
    _write(
        "TOOL-upsert_deal",
        "EP-72 / ACT-upsert_deal",
        "sales",
        "sales:write",
        risk="high",
        default="L2",
        maximum="L2",
        scope="sales:record",
        desc="Create or update a deal.",
    ),
    _write(
        "TOOL-upsert_risk",
        "EP-101 / ACT-upsert_risk",
        "risk",
        "risk:write",
        risk="medium",
        default="L2",
        maximum="L2",
        scope="risk:record",
        desc="Create or update a risk.",
    ),
    _write(
        "TOOL-create_mitigation",
        "EP-103.C / ACT-create_mitigation",
        "risk",
        "risk:write",
        risk="medium",
        default="L2",
        maximum="L2",
        scope="risk:record",
        desc="Create a risk mitigation.",
    ),
    _write(
        "TOOL-submit_document",
        "EP-DC-01",
        "idp",
        "idp:write",
        risk="medium",
        default="L2",
        maximum="L2",
        scope="idp:record",
        cost="medium",
        desc="Submit a document (C2 voice / attachment; always an action card).",
    ),
)

# ---------------------------------------------------------------- §7.3 v2.1 tools (8)
_V21_TOOLS: tuple[ToolDef, ...] = (
    _read(
        "TOOL-get_kpi_status",
        "EP-KPI-01",
        "execution:read",
        risk="low",
        scope="execution:aggregate",
        desc="KPI status + evaluation band + last check-in.",
    ),
    _read(
        "TOOL-get_cash_flow_forecast",
        "EP-128",
        "finance:read",
        risk="medium",
        scope="finance:aggregate",
        cost="low",
        desc="13-week cash-flow forecast (GET).",
    ),
    _write(
        "TOOL-assign_task",
        "EP-TASK-04",
        "execution",
        "execution:write",
        risk="medium",
        default="L2",
        maximum="L3",
        scope="execution:record",
        desc="Assign / reassign a task (undo via before-snapshot).",
    ),
    _write(
        "TOOL-generate_report",
        "EP-121",
        "dashboard",
        "dashboard:read",
        risk="low",
        default="L2",
        maximum="L2",
        scope="dashboard:aggregate",
        classification="INTERNAL",
        reversible=False,
        cost="high",
        desc="Generate a report (weekly / monthly / board).",
    ),
    _write(
        "TOOL-request_approval",
        "EP-123.C",
        "dashboard",
        "dashboard:read",
        risk="medium",
        default="L2",
        maximum="L2",
        scope="platform:record",
        desc="Open an approval request.",
    ),
    _write(
        "TOOL-send_notification",
        "platform.notify",
        "platform",
        None,
        risk="low",
        default="L3",
        maximum="L3",
        scope="platform:record",
        classification="INTERNAL",
        reversible=False,
        kind="EXECUTION",
        desc="Send a notification (in-app L3 / email channel EXECUTION L2).",
    ),
    ToolDef(
        name="TOOL-approve_request",
        description="Approve an approval request (server-only).",
        domain="platform",
        endpoint="EP-WF-03 decision=approve",
        kind="APPROVAL",
        risk_level="high",
        autonomy_default="L0",
        autonomy_max="L0",
        required_permissions=("platform:approve",),
        data_scope="platform:record",
        classification="CONFIDENTIAL",
        reversible=False,
        cost_estimate="low",
        declare_to_model=False,
    ),
    ToolDef(
        name="TOOL-reject_request",
        description="Reject an approval request (server-only).",
        domain="platform",
        endpoint="EP-WF-03 decision=reject",
        kind="APPROVAL",
        risk_level="medium",
        autonomy_default="L0",
        autonomy_max="L0",
        required_permissions=("platform:approve",),
        data_scope="platform:record",
        classification="CONFIDENTIAL",
        reversible=False,
        cost_estimate="low",
        declare_to_model=False,
    ),
)

TOOLS: tuple[ToolDef, ...] = tuple(
    replace(t, p1_frozen=True) if t.domain in P1_FROZEN_DOMAINS else t
    for t in (*_READ_TOOLS, *_WRITE_TOOLS, *_V21_TOOLS)
)

_BY_NAME: dict[str, ToolDef] = {t.name: t for t in TOOLS}
if len(_BY_NAME) != len(TOOLS):  # pragma: no cover - guards against a duplicate TOOL-* name
    raise RuntimeError("duplicate tool name in registry")


def all_tools() -> tuple[ToolDef, ...]:
    return TOOLS


def get_tool(name: str) -> ToolDef | None:
    return _BY_NAME.get(name)


def available_for(permissions: frozenset[str]) -> tuple[ToolDef, ...]:
    """Tools the asker may use this turn (holds ALL required_permissions — P06, 02 §7.2)."""
    return tuple(t for t in TOOLS if set(t.required_permissions) <= permissions)


def advertisable_for(
    permissions: frozenset[str], *, max_classification: str | None = None
) -> tuple[ToolDef, ...]:
    """Tools sent to the model: available, `declare_to_model`, not `p1_frozen` (R-DEC-16),
    within the classification ceiling."""
    ceiling = CLASSIFICATION_RANK.get(max_classification or "SECRET", 3)
    return tuple(
        t
        for t in available_for(permissions)
        if t.declare_to_model
        and not t.p1_frozen
        and CLASSIFICATION_RANK[t.classification] <= ceiling
    )
