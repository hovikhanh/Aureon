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
  { code: "PLAN_KPI_OKR", name_vi: "Kế hoạch KPI/OKR", name_en: "KPI/OKR plan", pillars: [], channels: ["C1", "C3", "C5"], keywords: ["kpi", "okr", "mục tiêu"] },
  { code: "PERIOD_REPORT", name_vi: "Báo cáo kỳ", name_en: "Period report", pillars: [], channels: ["C1", "C3", "C5"], keywords: ["báo cáo", "kết quả"] },
  { code: "HR_ROSTER", name_vi: "Danh sách nhân sự", name_en: "HR roster", pillars: ["O"], channels: ["C3", "C5"], keywords: ["nhân sự", "mã nv"] },
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
export const SCHEMA_FIELDS: Record<string, FieldDef[]> = {
  HR_ROSTER: [
    row("employee_code", "text", EMP, ["Mã NV", "Ma NV", "Employee code"], { required: true }),
    row("full_name", "text", EMP, ["Họ tên", "Họ và tên", "Full name"], { required: true }),
    row("title", "text", EMP, ["Chức danh", "Title"], { required: true }),
    row("department_code", "text", "ACT-create_department", ["Phòng ban", "Mã phòng", "Department"], { required: true }),
    row("hire_date", "date", EMP, ["Ngày vào", "Hire date"], { required: true }),
    row("end_date", "date", EMP, ["Ngày nghỉ", "End date"]),
    row("status", "enum", EMP, ["Trạng thái", "Status"], { required: true, enum: ["ACTIVE", "PROBATION", "ON_LEAVE", "TERMINATED"] }),
    row("salary", "money", EMP, ["Lương (VND)", "Lương", "Salary"], { is_critical: true, sensitivity_level: 4 }),
  ],
  PLAN_KPI_OKR: [
    f("period_key", "text", { target: { action: "ACT-upsert_kpi", param: "period_key" } }),
    row("kpi_code", "text", "ACT-upsert_kpi", ["Metric code", "Mã KPI", "KPI code"]),
    row("target", "number", "ACT-upsert_kpi", ["Mục tiêu Q4", "Mục tiêu", "Target"]),
    row("unit", "text", "ACT-upsert_kpi", ["Đơn vị", "Unit"]),
    row("owner_code", "text", "ACT-upsert_kpi", ["Owner", "Người phụ trách"]),
    row("note", "text", "ACT-upsert_kpi", ["Ghi chú", "Note"]),
    row("task_title", "text", "ACT-create_task", ["Việc cần làm", "Task"]),
    row("task_due_date", "date", "ACT-create_task", ["Hạn", "Due date"]),
  ],
  PERIOD_REPORT: [
    f("period_key", "text", { required: true, target: { action: "ACT-record_kpi_measurement", param: "period_key" } }),
    row("kpi_code", "text", "ACT-record_kpi_measurement", ["Mã KPI", "KPI code"], { required: true, master_ref: "execution.kpis" }),
    row("actual_value", "number", "ACT-record_kpi_measurement", ["Thực đạt", "Actual"], { required: true }),
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
  "ACT-create_department": "hr.departments", "ACT-create_employee": "hr.employees", "ACT-upsert_kpi": "execution.kpis",
  "ACT-record_kpi_measurement": "execution.kpi_measurements", "ACT-create_task": "execution.tasks", "ACT-create_invoice": "finance.invoices",
};
/** Run order inside one document (#4: department → employee; #2: kpi → task). */
/** Row fields that must be filled once any field of the same ACT is filled in that row. */
export const ACT_REQUIRED: Record<string, readonly string[]> = { "ACT-upsert_kpi": ["kpi_code", "target"], "ACT-create_task": ["task_title"] };
export const ACT_ORDER = ["ACT-create_department", "ACT-create_employee", "ACT-upsert_kpi", "ACT-record_kpi_measurement", "ACT-create_task", "ACT-create_invoice"];
export const VALIDATOR_OPS = ["required", "date_not_future", "in", "gt", "gte", "lt", "lte", "sum_equals"];
export const CRITICAL_FIELD_NAMES = ["total_amount", "subtotal", "vat_amount", "seller_tax_code", "buyer_tax_code", "salary", "bank_account", "contract_value"];
