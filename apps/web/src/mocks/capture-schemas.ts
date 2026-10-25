/**
 * Mock M1.5 doc types + ExtractionSchema v1 (R-DEC-65, 05 §2.7 JSONB shape) + row validator.
 * The real seed lands in BE migration 0019 — the field sets here mirror the demo files
 * DOC-06 (`HR_ROSTER`) / DOC-07 (`PLAN_KPI_OKR`) so the C5 heuristic mapping matches headers.
 */
export interface FieldDef {
  name: string; label_key: string; value_type: string; required: boolean; is_critical: boolean; sensitivity_level: number;
  group: "row" | null; target: { action: string; param: string } | null; enum: string[] | null; master_ref: string | null; header_aliases: string[];
}
export interface DocTypeSeed { code: string; name_vi: string; name_en: string; pillars: string[]; channels: string[]; keywords: string[] }

export const DOC_TYPES: readonly DocTypeSeed[] = [
  { code: "PLAN_KPI_OKR", name_vi: "Kế hoạch / OKR / KPI", name_en: "Plan / OKR / KPI", pillars: ["F", "O", "C", "U", "S"], channels: ["C1", "C3", "C5"], keywords: ["okr", "kpi", "mục tiêu", "key result", "kết quả then chốt", "kế hoạch"] },
  { code: "PERIOD_REPORT", name_vi: "Báo cáo kết quả định kỳ", name_en: "Periodic results report", pillars: ["F", "O", "C", "U", "S"], channels: ["C1", "C3", "C5"], keywords: ["báo cáo kết quả", "báo cáo tháng", "báo cáo quý", "thực hiện", "kết quả kỳ"] },
  { code: "HR_ROSTER", name_vi: "Danh sách nhân sự / sơ đồ tổ chức", name_en: "HR roster / org chart", pillars: ["O"], channels: ["C1", "C3", "C5"], keywords: ["danh sách nhân sự", "sơ đồ tổ chức", "mã nv", "phòng ban", "chức danh", "employee list"] },
  { code: "INVOICE", name_vi: "Hóa đơn", name_en: "Invoice", pillars: ["F"], channels: ["C3"], keywords: ["hóa đơn", "vat"] },
  { code: "OTHER", name_vi: "Khác", name_en: "Other", pillars: [], channels: ["C3"], keywords: [] },
];

const f = (name: string, value_type: string, o: Partial<FieldDef> = {}): FieldDef => ({
  name, label_key: `capture.field.${name}`, value_type, required: false, is_critical: false, sensitivity_level: 2,
  group: null, target: null, enum: null, master_ref: null, header_aliases: [], ...o,
});
const row = (name: string, type: string, action: string, aliases: string[], o: Partial<FieldDef> = {}) =>
  f(name, type, { group: "row", target: { action, param: name }, header_aliases: aliases, ...o });

const EMP = "ACT-create_employee";
const DEPT = "ACT-create_department";
const POS = "ACT-create_position";
/** Untargeted row context (BE `catalog/goals.py` `ctx`): every ACT step of the row reads it by name. */
const ctx = (name: string, type: string, aliases: string[], o: Partial<FieldDef> = {}) => f(name, type, { group: "row", header_aliases: aliases, ...o });
const at = (name: string, type: string, action: string, param: string, aliases: string[], o: Partial<FieldDef> = {}) =>
  f(name, type, { group: "row", target: { action, param }, header_aliases: aliases, ...o });
// Mirror of the BE seed catalog (`idp/services/catalog/{org,goals}.py`, migration 0019) — names, targets, aliases, enums.
export const SCHEMA_FIELDS: Record<string, FieldDef[]> = {
  HR_ROSTER: [
    at("department_code", "text", DEPT, "code", ["mã phòng ban", "mã pb", "department code"], { required: true, master_ref: "hr.department_code" }),
    at("department_name", "text", DEPT, "name", ["phòng ban", "tên phòng ban", "department"], { required: true }),
    at("team_code", "text", "ACT-create_team", "code", ["mã team", "mã tổ", "team code"]),
    at("team_name", "text", "ACT-create_team", "name", ["team", "tổ", "nhóm"]),
    at("title", "text", POS, "title", ["chức danh", "vị trí", "title", "position"]),
    row("employee_code", "text", EMP, ["mã nv", "mã nhân viên", "employee code"], { required: true, master_ref: "hr.employee_code" }),
    row("full_name", "person_name", EMP, ["họ tên", "họ và tên", "full name"], { required: true, sensitivity_level: 3 }),
    row("manager_code", "text", EMP, ["mã quản lý", "quản lý trực tiếp", "manager"], { master_ref: "hr.employee_code" }),
    row("hire_date", "date", EMP, ["ngày vào", "ngày vào làm", "hire date"], { required: true }),
    row("status", "enum", EMP, ["trạng thái", "status"], { enum: ["probation", "active", "on_leave", "terminated"] }),
    row("salary", "money", EMP, ["lương", "lương cơ bản", "salary"], { is_critical: true, sensitivity_level: 4 }),
  ],
  PLAN_KPI_OKR: [
    ctx("period_key", "period", ["kỳ", "period"], { required: true }),
    ctx("owner_code", "text", ["mã owner", "người phụ trách", "owner"], { required: true }),
    ctx("unit", "text", ["đơn vị", "unit"]),
    ctx("baseline", "number", ["baseline", "giá trị nền"]),
    ctx("target", "number", ["target", "mục tiêu số", "chỉ tiêu"]),
    at("objective_title", "text", "ACT-upsert_objective", "title", ["mục tiêu", "objective"]),
    at("kr_title", "text", "ACT-upsert_key_result", "title", ["kết quả then chốt", "key result", "kr"]),
    at("kpi_code", "text", "ACT-upsert_kpi", "code", ["mã kpi", "kpi code"], { master_ref: "execution.kpi_code" }),
    at("kpi_name", "text", "ACT-upsert_kpi", "name", ["tên kpi", "kpi"]),
    at("kpi_period_target", "number", "ACT-upsert_kpi_target", "target", ["chỉ tiêu kỳ", "target kỳ", "period target"]),
    at("task_title", "text", "ACT-create_task", "title", ["việc cần làm", "công việc", "task"]),
    row("assignee_code", "text", "ACT-create_task", ["người thực hiện", "assignee"], { master_ref: "hr.employee_code" }),
    at("task_due_date", "date", "ACT-create_task", "due_date", ["hạn", "hạn chót", "due date"]),
  ],
  PERIOD_REPORT: [
    row("kpi_code", "text", "ACT-record_kpi_measurement", ["mã kpi", "kpi code"], { master_ref: "execution.kpi_code" }),
    row("period_key", "period", "ACT-record_kpi_measurement", ["kỳ", "kỳ báo cáo", "period"]),
    row("actual_value", "number", "ACT-record_kpi_measurement", ["thực tế", "actual"]),
    row("kr_ref", "text", "ACT-record_kr_checkin", ["mã kr", "kr id"]),
    row("value", "number", "ACT-record_kr_checkin", ["giá trị kr", "kr value"]),
    row("confidence", "enum", "ACT-record_kr_checkin", ["độ tự tin", "confidence"], { enum: ["HIGH", "MEDIUM", "LOW"] }),
    row("note", "text", "ACT-record_kr_checkin", ["ghi chú", "note"]),
  ],
  INVOICE: [
    f("invoice_number", "text", { required: true, target: { action: "ACT-create_invoice", param: "invoice_number" } }),
    f("issue_date", "date", { required: true, target: { action: "ACT-create_invoice", param: "issue_date" } }),
    f("seller_tax_code", "tax_code", { is_critical: true, target: { action: "ACT-create_invoice", param: "seller_tax_code" } }),
    f("total_amount", "money", { required: true, is_critical: true, target: { action: "ACT-create_invoice", param: "total_amount" } }),
  ],
  OTHER: [],
};

/** ACT → required permission (bảng ACT 10 §7.2.4; create_employee any-of R-DEC-61). */
export const ACT_PERMISSION: Record<string, readonly string[]> = {
  "ACT-create_department": ["hr:admin"], "ACT-create_team": ["hr:admin"], "ACT-create_position": ["hr:admin"],
  "ACT-create_employee": ["hr:write", "hr:admin"], "ACT-upsert_kpi": ["execution:write"], "ACT-upsert_kpi_target": ["execution:write"],
  "ACT-record_kpi_measurement": ["execution:write"], "ACT-upsert_objective": ["execution:write"], "ACT-upsert_key_result": ["execution:write"],
  "ACT-record_kr_checkin": ["execution:write"], "ACT-create_task": ["execution:write"], "ACT-create_invoice": ["finance:write"],
};
export const ACT_TABLE: Record<string, string> = {
  "ACT-create_department": "hr.departments", "ACT-create_team": "hr.teams", "ACT-create_position": "hr.positions", "ACT-create_employee": "hr.employees", "ACT-upsert_kpi": "execution.kpis",
  "ACT-upsert_objective": "execution.objectives", "ACT-upsert_key_result": "execution.key_results", "ACT-upsert_kpi_target": "execution.kpi_targets", "ACT-record_kr_checkin": "execution.check_ins",
  "ACT-record_kpi_measurement": "execution.kpi_measurements", "ACT-create_task": "execution.tasks", "ACT-create_invoice": "finance.invoices",
};
/** Run order inside one document (#4: department → employee; #2: kpi → task). */
/** Row fields that must be filled once any field of the same ACT is filled in that row. */
export const ACT_REQUIRED: Record<string, readonly string[]> = {
  "ACT-create_department": ["department_code", "department_name"], "ACT-create_position": ["title", "department_code"],
  "ACT-create_employee": ["employee_code", "full_name", "department_code", "hire_date"], "ACT-upsert_kpi": ["kpi_code", "kpi_name", "unit", "owner_code"], "ACT-create_task": ["task_title"],
};
/** Plan order = schema `action_names` order (BE `build_plan`), per doc type. */
export const ACT_ORDER = ["ACT-create_department", "ACT-create_team", "ACT-create_position", "ACT-create_employee", "ACT-upsert_objective", "ACT-upsert_key_result", "ACT-upsert_kpi",
  "ACT-upsert_kpi_target", "ACT-create_task", "ACT-record_kpi_measurement", "ACT-record_kr_checkin", "ACT-create_invoice"];
export const VALIDATOR_OPS = ["required", "date_not_future", "in", "gt", "gte", "lt", "lte", "sum_equals"];
export const CRITICAL_FIELD_NAMES = ["total_amount", "subtotal", "vat_amount", "seller_tax_code", "buyer_tax_code", "salary", "bank_account", "contract_value"];
