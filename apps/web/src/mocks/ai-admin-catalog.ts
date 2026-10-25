/**
 * Mock catalog for M1.6 AI Control Center (10 §7.2.5, 05 §2.8): the 53 `TOOL-*` with the 13
 * metadata (`ai-tools.json` = BE registry T-644 dump + the 10 new tools of 10 §7.2.5) and the 6 P0
 * agents (R-DEC-71, mirror of `ai/services/agent_catalog.py`). Levels follow the M1 ceiling L2 (R-DEC-72).
 */
import TOOLS_JSON from "./ai-tools.json";

export type Level = "L0" | "L1" | "L2" | "L3";
export type ToolKind = "READ" | "WRITE" | "APPROVAL" | "EXECUTION";
export interface MTool {
  name: string; kind: ToolKind; autonomy_default: string; data_scope: string; classification: string; reversible: string; cost_estimate: string;
  tool_id: string; brd_name: string | null; description: string; domain: string; input_schema: Record<string, unknown>; output_schema: Record<string, unknown>;
  permission: string[]; risk_level: string; data_classification: string; autonomy_max: Level; approval_required: string; audit_required: boolean;
  owner: string; compute: boolean; p1_frozen: boolean; action_name: string | null; endpoint_ref: string;
}
export const TOOLS = TOOLS_JSON as unknown as MTool[];
export const toolByName = (name: string) => TOOLS.find((t) => t.name === name || t.name === `TOOL-${name}`);

export const CEILING: Level = "L2";
const ORDER: Level[] = ["L0", "L1", "L2", "L3"];
export const rank = (l: Level | string | null | undefined) => ORDER.indexOf((l ?? "L0") as Level);
export const minLevel = (a: Level, b: Level): Level => (rank(a) <= rank(b) ? a : b);

/** Finance ACT carrying a critical field (money) — `level` > L2 → 422 `critical_field` (FR-DC-16). */
export const CRITICAL_ACTS = new Set(["ACT-record_expense", "ACT-create_invoice", "ACT-upsert_deal"]);

const t = (...names: string[]) => names.map((n) => `TOOL-${n}`);
export interface AgentSpec { code: string; name_vi: string; name_en: string; description_vi: string; description_en: string; model_task: string; tools: string[] }
export const AGENTS: readonly AgentSpec[] = [
  { code: "ceo", name_vi: "CEO Agent", name_en: "CEO Agent", description_vi: "Tổng hợp liên domain, briefing, khuyến nghị chiến lược", description_en: "Cross-domain synthesis, briefing, strategic recommendations", model_task: "chat",
    tools: t("get_finance_dashboard", "get_sales_dashboard", "get_hr_dashboard", "get_execution_dashboard", "get_kpi_status", "get_okr_status", "get_project_status", "get_metric", "list_alerts", "get_lineage", "get_org_tree", "search_documents", "get_source_document", "generate_report", "record_decision", "create_task", "request_approval") },
  { code: "data_capture", name_vi: "Agent Thu thập dữ liệu", name_en: "Data Capture Agent", description_vi: "Phân loại, trích xuất, kiểm tra, đề xuất ghi (không tự ghi tài chính)", description_en: "Classify, extract, validate, propose writes (never writes finance itself)", model_task: "extract",
    tools: t("search_documents", "get_source_document", "get_lineage", "submit_document", "create_department", "create_team") },
  { code: "performance", name_vi: "Agent Hiệu suất", name_en: "Performance Agent", description_vi: "KPI/OKR, check-in, phân tích khoảng cách", description_en: "KPI/OKR, check-ins, gap analysis", model_task: "chat",
    tools: t("get_kpi_status", "get_okr_status", "list_objectives", "get_metric", "record_kpi_measurement", "record_kr_checkin", "upsert_kpi", "upsert_objective") },
  { code: "task", name_vi: "Agent Công việc", name_en: "Task Agent", description_vi: "Task, workload, nhắc việc, follow-up", description_en: "Tasks, workload, reminders, follow-up", model_task: "chat",
    tools: t("list_tasks", "get_overdue_tasks", "get_project_status", "get_workload", "get_org_tree", "create_task", "assign_task", "update_task", "send_notification") },
  { code: "meeting", name_vi: "Agent Cuộc họp", name_en: "Meeting Agent", description_vi: "Biên bản, quyết định, action item", description_en: "Minutes, decisions, action items", model_task: "chat",
    tools: t("record_decision", "create_meeting", "create_task", "send_notification", "get_org_tree") },
  { code: "reporting", name_vi: "Agent Báo cáo", name_en: "Reporting Agent", description_vi: "Báo cáo định kỳ / theo yêu cầu", description_en: "Periodic / on-demand reports", model_task: "report",
    tools: t("get_execution_dashboard", "get_metric", "list_alerts", "get_kpi_status", "get_okr_status", "generate_report") },
];
export const AGENT_CODES = new Set(AGENTS.map((a) => a.code));

/** Tool an agent may hold (EP-AI-17 `invalid_tool`): registered, not APPROVAL, not frozen. */
export const assignable = (name: string) => {
  const tool = toolByName(name);
  return tool !== undefined && tool.kind !== "APPROVAL" && !tool.p1_frozen;
};
/** Root default of a write ACT (04 §9.1 seed) before the ceiling — L3 shows struck-through on SCR-64. */
export const rootDefault = (tool: MTool): Level => (tool.autonomy_default as Level) ?? "L2";
