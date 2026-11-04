/**
 * Business-record resources editable from `/business/<domain>/records` (M7). Every path, field and
 * enum mirrors the existing API (10 EP-FIN-02..07, EP-SAL-01..04, EP-HR-02..05/08..10) — no new
 * endpoint. Level-4 fields (salary, date of birth, CCCD, bank account — 02 §6.2) are never edited
 * here. People fields (`owner_id`, `account_owner_id`, `hiring_manager_id`) are user ids, HR
 * `manager_id` is an employee id.
 */
import type { FieldSpec } from "./record-form";

export type Domain = "finance" | "sales" | "hr";
export type ColumnType = "text" | "money" | "pct" | "date" | "enum" | "ref" | "bool";
export interface ColumnSpec { name: string; type: ColumnType; ref?: FieldSpec["ref"] }

export interface ActionSpec {
  key: string;
  /** POST `${path}/${id}/${suffix}` */
  suffix: string;
  fields: readonly FieldSpec[];
  /** Permission besides `<domain>:write` (e.g. `hr:approve`). */
  permission?: string;
  /** Extra backend rule on who may run it (shown only to roles that pass it). */
  allowed?: (who: { role: string; scopePillars: readonly string[] }) => boolean;
  visible: (row: Record<string, unknown>) => boolean;
}

export interface ResourceSpec {
  key: string;
  domain: Domain;
  path: string;
  sortBy: string;
  /** default `desc` (newest first); names read better ascending */
  order?: "asc" | "desc";
  columns: readonly ColumnSpec[];
  fields: readonly FieldSpec[];
  /** The API has DELETE (soft, `deleted_at`) for this resource. */
  archivable: boolean;
  /** Free-text `q` filter supported by the list endpoint. */
  searchable?: boolean;
  /** Detail page of a row (first column becomes a link) — M8 CRM views. */
  detailHref?: (row: Record<string, unknown>) => string;
  actions?: readonly ActionSpec[];
}

const REVENUE_CATEGORIES = ["product_sales", "service", "consulting", "other"] as const;
const EXPENSE_CATEGORIES = ["cogs", "salary", "infrastructure", "marketing", "office", "travel", "other"] as const;
const DEAL_STAGES = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"] as const;

export const RESOURCES: readonly ResourceSpec[] = [
  // ---------------------------------------------------------------- finance (EP-FIN-02..07)
  {
    key: "revenues", domain: "finance", path: "/finance/revenues", sortBy: "recognized_on", archivable: true,
    columns: [{ name: "recognized_on", type: "date" }, { name: "category", type: "enum" }, { name: "amount", type: "money" }, { name: "description", type: "text" }],
    fields: [
      { name: "amount", type: "money", required: true },
      { name: "category", type: "select", required: true, options: REVENUE_CATEGORIES },
      { name: "recognized_on", type: "date", required: true },
      { name: "client_id", type: "ref", ref: "client" },
      { name: "description", type: "textarea" },
      { name: "source_note", type: "text" },
    ],
  },
  {
    key: "expenses", domain: "finance", path: "/finance/expenses", sortBy: "spent_on", archivable: true,
    columns: [{ name: "spent_on", type: "date" }, { name: "title", type: "text" }, { name: "category", type: "enum" }, { name: "amount", type: "money" }, { name: "vendor", type: "text" }],
    fields: [
      { name: "title", type: "text", required: true },
      { name: "amount", type: "money", required: true },
      { name: "category", type: "select", required: true, options: EXPENSE_CATEGORIES },
      { name: "spent_on", type: "date", required: true },
      { name: "department_id", type: "ref", ref: "department" },
      { name: "vendor", type: "text" },
      { name: "is_recurring", type: "boolean" },
      { name: "recurrence_period", type: "select", options: ["monthly", "quarterly", "yearly"] },
      { name: "description", type: "textarea" },
    ],
  },
  {
    key: "invoices", domain: "finance", path: "/finance/invoices", sortBy: "issued_on", archivable: true,
    columns: [{ name: "number", type: "text" }, { name: "direction", type: "enum" }, { name: "counterparty_name", type: "text" }, { name: "issued_on", type: "date" },
      { name: "due_date", type: "date" }, { name: "total_amount", type: "money" }, { name: "amount_due", type: "money" }, { name: "status", type: "enum" }],
    fields: [
      // OUT (sales) invoices need their client: picked here when the role reads sales clients,
      // else resolved by the backend from the customer's MST (`counterparty_tax_code`) — R-DEC-172
      { name: "direction", type: "select", required: true, options: ["IN", "OUT"], createOnly: true },
      { name: "client_id", type: "ref", ref: "client", createOnly: true },
      { name: "number", type: "text", required: true, createOnly: true, max: 50 },
      { name: "series", type: "text", createOnly: true, max: 20 },
      { name: "issued_on", type: "date", required: true, createOnly: true },
      { name: "due_date", type: "date", required: true },
      { name: "counterparty_name", type: "text", createOnly: true },
      { name: "counterparty_tax_code", type: "text", createOnly: true, max: 20 },
      { name: "status", type: "select", options: ["draft", "sent"] },
      { name: "lines", type: "lines", required: true },
      { name: "notes", type: "textarea" },
    ],
    actions: [{
      key: "pay", suffix: "pay", visible: (r) => !["paid", "cancelled", "draft"].includes(String(r.status)), // invoice_service.pay refuses these
      fields: [
        { name: "amount_paid", type: "money", required: true },
        { name: "paid_at", type: "date", required: true },
        { name: "method", type: "select", options: ["bank_transfer", "cash", "card", "other"] },
      ],
    }],
  },
  {
    key: "budgets", domain: "finance", path: "/finance/budgets", sortBy: "fiscal_year", archivable: true,
    columns: [{ name: "fiscal_year", type: "text" }, { name: "quarter", type: "text" }, { name: "department_id", type: "ref", ref: "department" }, { name: "category", type: "enum" }, { name: "allocated_amount", type: "money" }],
    fields: [
      { name: "department_id", type: "ref", ref: "department", required: true },
      { name: "fiscal_year", type: "number", required: true },
      { name: "quarter", type: "select", options: ["Q1", "Q2", "Q3", "Q4"] },
      { name: "allocated_amount", type: "money", required: true },
      { name: "category", type: "select", options: EXPENSE_CATEGORIES },
      { name: "notes", type: "textarea" },
    ],
  },
  {
    key: "cashPositions", domain: "finance", path: "/finance/cash-positions", sortBy: "period", archivable: false, // EP-FIN-04: no DELETE
    columns: [{ name: "period", type: "text" }, { name: "opening_balance", type: "money" }, { name: "closing_balance", type: "money" }, { name: "cash_source", type: "enum" }],
    fields: [
      { name: "period", type: "month", required: true, createOnly: true },
      { name: "closing_balance", type: "money", required: true },
      { name: "cash_source", type: "select", options: ["bank_statement", "manual", "imported"] },
      { name: "note", type: "textarea" },
    ],
  },
  // ------------------------------------------------------------------ sales (EP-SAL-01..04)
  {
    key: "clients", domain: "sales", path: "/sales/clients", sortBy: "name", order: "asc", archivable: true,
    detailHref: (r) => `/business/sales/clients/${String(r.id)}`,
    columns: [{ name: "name", type: "text" }, { name: "tax_code", type: "text" }, { name: "industry", type: "text" }, { name: "size", type: "enum" }, { name: "status", type: "enum" }],
    fields: [
      { name: "name", type: "text", required: true },
      { name: "tax_code", type: "text", max: 20 },
      { name: "industry", type: "text" },
      { name: "size", type: "select", options: ["startup", "small", "medium", "enterprise"] },
      { name: "status", type: "select", options: ["prospect", "active", "churned"] },
      { name: "address", type: "text" },
      { name: "website", type: "text" },
      { name: "account_owner_id", type: "ref", ref: "user" },
      { name: "notes", type: "textarea" },
    ],
  },
  {
    key: "deals", domain: "sales", path: "/sales/deals", sortBy: "expected_close_date", archivable: true,
    detailHref: (r) => `/business/sales/deals/${String(r.id)}`,
    columns: [{ name: "name", type: "text" }, { name: "client_id", type: "ref", ref: "client" }, { name: "stage", type: "enum" }, { name: "deal_value", type: "money" },
      { name: "probability_pct", type: "pct" }, { name: "expected_close_date", type: "date" }],
    fields: [
      { name: "name", type: "text", required: true },
      { name: "client_id", type: "ref", ref: "client", required: true },
      { name: "deal_value", type: "money", required: true },
      { name: "probability_pct", type: "pct", required: true },
      { name: "expected_close_date", type: "date", required: true },
      { name: "owner_id", type: "ref", ref: "user", required: true },
      { name: "description", type: "textarea" },
    ],
    actions: [{
      key: "stage", suffix: "stage", visible: (r) => !["closed_won", "closed_lost"].includes(String(r.stage)),
      fields: [{ name: "to_stage", type: "select", required: true, options: DEAL_STAGES }, { name: "lost_reason", type: "text" }],
    }],
  },
  {
    key: "contracts", domain: "sales", path: "/sales/contracts", sortBy: "effective_date", archivable: true,
    columns: [{ name: "contract_number", type: "text" }, { name: "client_id", type: "ref", ref: "client" }, { name: "contract_value", type: "money" },
      { name: "effective_date", type: "date" }, { name: "expiry_date", type: "date" }, { name: "status", type: "enum" }],
    fields: [
      { name: "contract_number", type: "text", required: true, max: 50 },
      { name: "client_id", type: "ref", ref: "client", required: true },
      { name: "contract_value", type: "money", required: true },
      { name: "signed_at", type: "date", required: true },
      { name: "effective_date", type: "date", required: true },
      { name: "expiry_date", type: "date" },
      { name: "renewal_notice_days", type: "number" },
      { name: "status", type: "select", options: ["draft", "active", "expired", "terminated"] },
      { name: "is_recurring", type: "boolean" },
    ],
  },
  {
    key: "targets", domain: "sales", path: "/sales/targets", sortBy: "period_key", archivable: true,
    columns: [{ name: "period_key", type: "text" }, { name: "period_type", type: "enum" }, { name: "scope", type: "enum" }, { name: "target_amount", type: "money" }],
    fields: [
      { name: "period_type", type: "select", required: true, options: ["month", "quarter", "year"], createOnly: true },
      { name: "period_key", type: "text", required: true, createOnly: true, max: 10 },
      { name: "scope", type: "select", required: true, options: ["team", "individual"], createOnly: true },
      { name: "owner_id", type: "ref", ref: "user", createOnly: true },
      { name: "target_amount", type: "money", required: true },
    ],
  },
  // --------------------------------------------------------------------- hr (EP-HR-02..10)
  {
    key: "employees", domain: "hr", path: "/hr/employees", sortBy: "full_name", order: "asc", archivable: true, searchable: true,
    columns: [{ name: "employee_code", type: "text" }, { name: "full_name", type: "text" }, { name: "title", type: "text" },
      { name: "department_id", type: "ref", ref: "department" }, { name: "status", type: "enum" }, { name: "hire_date", type: "date" }],
    fields: [
      { name: "employee_code", type: "text", required: true, max: 20 },
      { name: "full_name", type: "text", required: true },
      { name: "email", type: "text" },
      { name: "phone", type: "text", max: 20 },
      { name: "department_id", type: "ref", ref: "department", required: true },
      { name: "title", type: "text" },
      { name: "contract_type", type: "select", options: ["full_time", "part_time", "contract", "intern"] },
      { name: "status", type: "select", options: ["probation", "active", "on_leave", "terminated"] },
      { name: "hire_date", type: "date", required: true },
      { name: "termination_date", type: "date" },
      { name: "manager_id", type: "ref", ref: "employee" },
    ],
  },
  {
    key: "hiringPlans", domain: "hr", path: "/hr/hiring-plans", sortBy: "target_date", archivable: true,
    columns: [{ name: "position", type: "text" }, { name: "department_id", type: "ref", ref: "department" }, { name: "headcount", type: "text" },
      { name: "filled", type: "text" }, { name: "priority", type: "enum" }, { name: "status", type: "enum" }, { name: "target_date", type: "date" }],
    fields: [
      { name: "position", type: "text", required: true },
      { name: "title", type: "text" },
      { name: "department_id", type: "ref", ref: "department", required: true },
      { name: "headcount", type: "number", required: true },
      { name: "priority", type: "select", options: ["low", "medium", "high", "critical"] },
      { name: "start_date", type: "date", required: true },
      { name: "target_date", type: "date", required: true },
      { name: "budget_amount", type: "money" },
      { name: "hiring_manager_id", type: "ref", ref: "user" },
      { name: "requirements", type: "textarea" },
    ],
    actions: [
      { key: "submit", suffix: "submit", fields: [], visible: (r) => r.status === "draft" },
      {
        // R-DEC-173 (02 §7): HR-DIR (khối O) or the CEO decides — through the approval engine
        // (EP-86 for HR-DIR here; the CEO, without hr:approve, decides in /work/approvals)
        key: "approve", suffix: "approve", permission: "hr:approve", visible: (r) => r.status === "submitted",
        allowed: ({ role, scopePillars }) => role !== "DIR" || scopePillars.length === 0 || scopePillars.includes("O"),
        fields: [{ name: "decision", type: "select", required: true, options: ["approve", "reject"] }, { name: "reason", type: "text", required: true }],
      },
    ],
  },
];

export const resourcesOf = (d: Domain) => RESOURCES.filter((r) => r.domain === d);
