"""P0 agent catalog (R-DEC-71, 05 §2.8, 10 §4.2) — 6 `AGT-*` seeded into `ai.agent_profiles`.

Catalog is fixed at P0 (no create/delete API — EP-AI-17 only edits). `allowed_tools` follows
05 §2.8 verbatim; `seed_tools()` keeps only names present in the registry (APPROVAL / frozen
excluded) so the seed always satisfies `allowed_tools ⊆ registry`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ai.tools import get_tool

CHAT_AGENT = "ceo"  # M1.6: chat runs the CEO agent for every role (Orchestrator = M2.4)
LEGACY_AGENT = "assistant"  # v2.1 hard-coded code, kept on old log rows


@dataclass(frozen=True)
class AgentSpec:
    code: str
    name_vi: str
    name_en: str
    description_vi: str
    description_en: str
    model_task: str
    tools: tuple[str, ...]

    @property
    def agent_ref(self) -> str:
        return f"AGT-{self.code.upper()}"


def _t(*names: str) -> tuple[str, ...]:
    return tuple(f"TOOL-{n}" for n in names)


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        "ceo", "CEO Agent", "CEO Agent",
        "Tổng hợp liên domain, briefing, khuyến nghị chiến lược",
        "Cross-domain synthesis, briefing, strategic recommendations", "chat",
        _t("get_finance_dashboard", "get_sales_dashboard", "get_hr_dashboard",
           "get_execution_dashboard", "get_kpi_status", "get_okr_status", "get_project_status",
           "get_metric", "list_alerts", "get_lineage", "get_org_tree", "search_documents",
           "get_source_document", "generate_report", "record_decision", "create_task",
           "request_approval"),
    ),
    AgentSpec(
        "data_capture", "Agent Thu thập dữ liệu", "Data Capture Agent",
        "Phân loại, trích xuất, kiểm tra, đề xuất ghi (không tự ghi tài chính)",
        "Classify, extract, validate, propose writes (never writes finance itself)", "extract",
        _t("search_documents", "get_source_document", "get_lineage", "submit_document",
           "create_department", "create_team"),
    ),
    AgentSpec(
        "performance", "Agent Hiệu suất", "Performance Agent",
        "KPI/OKR, check-in, phân tích khoảng cách",
        "KPI/OKR, check-ins, gap analysis", "chat",
        _t("get_kpi_status", "get_okr_status", "list_objectives", "get_metric",
           "record_kpi_measurement", "record_kr_checkin", "upsert_kpi", "upsert_objective"),
    ),
    AgentSpec(
        "task", "Agent Công việc", "Task Agent",
        "Task, workload, nhắc việc, follow-up",
        "Tasks, workload, reminders, follow-up", "chat",
        _t("list_tasks", "get_overdue_tasks", "get_project_status", "get_workload",
           "get_org_tree", "create_task", "assign_task", "update_task", "send_notification"),
    ),
    AgentSpec(
        "meeting", "Agent Cuộc họp", "Meeting Agent",
        "Biên bản, quyết định, action item",
        "Minutes, decisions, action items", "chat",
        _t("record_decision", "create_meeting", "create_task", "send_notification",
           "get_org_tree"),
    ),
    AgentSpec(
        "reporting", "Agent Báo cáo", "Reporting Agent",
        "Báo cáo định kỳ / theo yêu cầu",
        "Periodic / on-demand reports", "report",
        _t("get_execution_dashboard", "get_metric", "list_alerts", "get_kpi_status",
           "get_okr_status", "generate_report"),
    ),
)  # fmt: skip

AGENT_CODES: frozenset[str] = frozenset(a.code for a in AGENTS)


def assignable(tool_name: str) -> bool:
    """A tool an agent may hold: registered, not APPROVAL (server-only), not `p1_frozen`."""
    t = get_tool(tool_name)
    return t is not None and t.kind != "APPROVAL" and not t.p1_frozen


def seed_tools(spec: AgentSpec) -> list[str]:
    return [n for n in spec.tools if assignable(n)]


def agents_for_tool(tool_name: str) -> list[str]:
    """Agent codes whose catalog lists the tool (EP-AI-14 `agents[]` fallback)."""
    return [a.code for a in AGENTS if tool_name in a.tools]
