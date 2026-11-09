/**
 * Business-record resources editable from `/business/<domain>/records` (M7). Every path, field and
 * enum mirrors the existing API (10 EP-FIN-02..07, EP-SAL-01..04, EP-HR-02..05/08..10) — no new
 * endpoint (product EP-PRD-*, risk EP-RSK-*: D-21 gives the CEO record management of the frozen
 * modules, R-DEC-16 keeps them out of the sidebar). Level-4 fields (salary, date of birth, CCCD, bank account — 02 §6.2) are never edited
 * here. People fields (`owner_id`, `account_owner_id`, `hiring_manager_id`) are user ids, HR
 * `manager_id` is an employee id.
 */
import type { FieldSpec } from "./record-form";

export type Domain = "finance" | "sales" | "hr" | "product" | "risk" | "execution";
export type ColumnType = "text" | "money" | "pct" | "date" | "datetime" | "enum" | "list" | "ref" | "bool";
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
  /** Columns the list endpoint can sort (its `page_params` whitelist ∩ `columns`). */
  sortable?: readonly string[];
  columns: readonly ColumnSpec[];
  fields: readonly FieldSpec[];
  /** The API has DELETE (soft, `deleted_at`) for this resource. */
  archivable: boolean;
  /** Free-text `q` filter supported by the list endpoint. */
  searchable?: boolean;
  /** Detail page of a row (first column becomes a link) — M8 CRM views. */
  detailHref?: (row: Record<string, unknown>) => string;
  actions?: readonly ActionSpec[];
  /** Row-level edit/archive gate (e.g. a converted lead is read-only — R-DEC-176); default all rows. */
  editable?: (row: Record<string, unknown>) => boolean;
}

const REVENUE_CATEGORIES = ["product_sales", "service", "consulting", "other"] as const;
const EXPENSE_CATEGORIES = ["cogs", "salary", "infrastructure", "marketing", "office", "travel", "other"] as const;
const DEAL_STAGES = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"] as const;
// CRM (R-DEC-176, D-08 defaults; EP-SAL-10..13) — `converted` is set only by the convert action
const LEAD_STATUSES = ["new", "contacted", "engaged", "qualified", "nurturing", "disqualified"] as const;
const LEAD_SOURCES = ["website", "referral", "event", "cold_call", "partner", "social", "advertising", "other"] as const;
const CONTACT_ROLES = ["decision_maker", "economic_buyer", "influencer", "user", "champion", "other"] as const;
const ACTIVITY_TYPES = ["call", "email", "meeting", "demo", "workshop", "poc", "proposal", "follow_up", "other"] as const;
const PRODUCT_STATUSES = ["active", "paused", "retired"] as const;
const LIFECYCLE_STAGES = ["idea", "development", "launched", "growth", "mature", "sunset"] as const;
const RISK_CATEGORIES = ["financial", "operational", "strategic", "people", "business", "customer", "product",
  "technology", "security", "compliance", "legal", "partner_supplier", "ai"] as const;

export const RESOURCES: readonly ResourceSpec[] = [
  // ---------------------------------------------------------------- finance (EP-FIN-02..07)
  {
    key: "revenues", domain: "finance", path: "/finance/revenues", sortBy: "recognized_on", archivable: true,
    sortable: ["recognized_on", "amount"],
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
    sortable: ["spent_on", "amount"],
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
    sortable: ["issued_on", "due_date", "total_amount"],
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
    sortable: ["fiscal_year", "allocated_amount"],
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
    sortable: ["period", "closing_balance"],
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
    sortable: ["name"],
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
    sortable: ["deal_value", "expected_close_date"],
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
    sortable: ["contract_value", "effective_date", "expiry_date"],
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
    sortable: ["period_key", "target_amount"],
    columns: [{ name: "period_key", type: "text" }, { name: "period_type", type: "enum" }, { name: "scope", type: "enum" }, { name: "target_amount", type: "money" }],
    fields: [
      { name: "period_type", type: "select", required: true, options: ["month", "quarter", "year"], createOnly: true },
      { name: "period_key", type: "text", required: true, createOnly: true, max: 10 },
      { name: "scope", type: "select", required: true, options: ["team", "individual"], createOnly: true },
      { name: "owner_id", type: "ref", ref: "user", createOnly: true },
      { name: "target_amount", type: "money", required: true },
    ],
  },
  // ------------------------------------------------- sales CRM (EP-SAL-10..13, R-DEC-176 / D-08)
  {
    key: "leads", domain: "sales", path: "/sales/leads", sortBy: "updated_at", archivable: true, searchable: true,
    sortable: ["code", "full_name", "company_name", "status", "score", "next_action_date"],
    editable: (r) => r.status !== "converted",
    columns: [{ name: "code", type: "text" }, { name: "full_name", type: "text" }, { name: "company_name", type: "text" }, { name: "status", type: "enum" },
      { name: "score", type: "text" }, { name: "next_action_date", type: "date" }],
    fields: [
      { name: "full_name", type: "text", required: true },
      { name: "company_name", type: "text", max: 300 },
      { name: "job_title", type: "text" },
      { name: "email", type: "text", max: 320 },
      { name: "phone", type: "text", max: 30 },
      { name: "industry", type: "text" },
      { name: "lead_source", type: "select", options: LEAD_SOURCES },
      { name: "status", type: "select", options: LEAD_STATUSES },
      { name: "score", type: "number" },
      { name: "budget", type: "money" },
      { name: "owner_id", type: "ref", ref: "user" },
      { name: "next_action", type: "text", max: 500 },
      { name: "next_action_date", type: "date" },
      { name: "need", type: "textarea" },
    ],
    actions: [{
      // Lead → Client (new, or `client_id` to link one) + Contact (+ Deal) in one transaction
      key: "convert", suffix: "convert", visible: (r) => !["converted", "disqualified"].includes(String(r.status)),
      fields: [
        { name: "client_id", type: "ref", ref: "client" },
        { name: "create_deal", type: "boolean" },
        { name: "deal_name", type: "text", max: 300 },
        { name: "deal_value", type: "money" },
        { name: "probability_pct", type: "pct" },
        { name: "expected_close_date", type: "date" },
      ],
    }],
  },
  {
    key: "contacts", domain: "sales", path: "/sales/contacts", sortBy: "updated_at", archivable: true, searchable: true,
    sortable: ["code"],
    columns: [{ name: "code", type: "text" }, { name: "full_name", type: "text" }, { name: "client_id", type: "ref", ref: "client" }, { name: "job_title", type: "text" },
      { name: "email", type: "text" }, { name: "roles", type: "list" }],
    fields: [
      { name: "client_id", type: "ref", ref: "client", required: true },
      { name: "last_name", type: "text", max: 100 },
      { name: "first_name", type: "text", required: true, max: 100 },
      { name: "job_title", type: "text" },
      { name: "department", type: "text" },
      { name: "email", type: "text", max: 320 },
      { name: "phone", type: "text", max: 30 },
      { name: "roles", type: "multi", options: CONTACT_ROLES },
      { name: "influence_level", type: "select", options: ["low", "medium", "high"] },
      { name: "decision_authority", type: "text", max: 500 },
      { name: "owner_id", type: "ref", ref: "user" },
      { name: "notes", type: "textarea" },
    ],
  },
  {
    key: "activities", domain: "sales", path: "/sales/activities", sortBy: "start_at", archivable: true, searchable: true,
    sortable: ["code", "type", "start_at", "status"],
    columns: [{ name: "code", type: "text" }, { name: "type", type: "enum" }, { name: "subject", type: "text" }, { name: "start_at", type: "datetime" },
      { name: "client_id", type: "ref", ref: "client" }, { name: "status", type: "enum" }],
    fields: [
      { name: "type", type: "select", required: true, options: ACTIVITY_TYPES },
      { name: "subject", type: "text", required: true, max: 300 },
      { name: "start_at", type: "datetime", required: true },
      { name: "end_at", type: "datetime" },
      { name: "status", type: "select", options: ["planned", "completed", "cancelled"] },
      { name: "lead_id", type: "ref", ref: "lead" },
      { name: "client_id", type: "ref", ref: "client" },
      { name: "contact_id", type: "ref", ref: "contact" },
      { name: "deal_id", type: "ref", ref: "deal" },
      { name: "owner_id", type: "ref", ref: "user" },
      { name: "outcome", type: "textarea" },
      { name: "next_action", type: "text", max: 500 },
      { name: "description", type: "textarea", max: 4000 },
    ],
  },
  // --------------------------------------------------------------------- hr (EP-HR-02..10)
  {
    key: "employees", domain: "hr", path: "/hr/employees", sortBy: "full_name", order: "asc", archivable: true, searchable: true,
    sortable: ["employee_code", "full_name", "hire_date"],
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
    sortable: ["priority", "status", "target_date"],
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
  // ---------------------------------------------------- product (frozen module R-DEC-16; D-21)
  {
    key: "products", domain: "product", path: "/product/products", sortBy: "name", order: "asc", archivable: true,
    sortable: ["code", "name"],
    columns: [{ name: "code", type: "text" }, { name: "name", type: "text" }, { name: "status", type: "enum" }, { name: "lifecycle_stage", type: "enum" },
      { name: "target_launch_date", type: "date" }, { name: "owner_id", type: "ref", ref: "user" }],
    fields: [
      { name: "code", type: "text", required: true, max: 50 },
      { name: "name", type: "text", required: true, max: 300 },
      { name: "status", type: "select", options: PRODUCT_STATUSES },
      { name: "lifecycle_stage", type: "select", options: LIFECYCLE_STAGES },
      { name: "target_launch_date", type: "date" },
      { name: "owner_id", type: "ref", ref: "user", required: true },
      { name: "description", type: "textarea", max: 4000 },
    ],
  },
  {
    key: "features", domain: "product", path: "/product/features", sortBy: "name", order: "asc", archivable: true,
    sortable: ["name"],
    columns: [{ name: "name", type: "text" }, { name: "product_id", type: "ref", ref: "product" }, { name: "status", type: "enum" }],
    fields: [
      { name: "product_id", type: "ref", ref: "product", required: true, createOnly: true },
      { name: "name", type: "text", required: true, max: 300 },
      { name: "status", type: "select", options: ["planned", "in_progress", "released", "deprecated"] },
    ],
  },
  {
    key: "roadmapItems", domain: "product", path: "/product/roadmap-items", sortBy: "quarter", archivable: true,
    sortable: ["quarter", "target_date"],
    columns: [{ name: "title", type: "text" }, { name: "product_id", type: "ref", ref: "product" }, { name: "quarter", type: "text" },
      { name: "target_date", type: "date" }, { name: "status", type: "enum" }],
    fields: [
      { name: "product_id", type: "ref", ref: "product", required: true, createOnly: true },
      { name: "title", type: "text", required: true, max: 300 },
      { name: "quarter", type: "text", required: true, max: 7 },
      { name: "target_date", type: "date" },
      { name: "status", type: "select", options: ["planned", "in_progress", "done", "delayed", "dropped"] },
    ],
  },
  {
    key: "releases", domain: "product", path: "/product/releases", sortBy: "release_version", archivable: false, // no DELETE: a release is history
    sortable: ["release_version"],
    columns: [{ name: "release_version", type: "text" }, { name: "product_id", type: "ref", ref: "product" }, { name: "status", type: "enum" }],
    fields: [
      { name: "product_id", type: "ref", ref: "product", required: true, createOnly: true },
      { name: "release_version", type: "text", required: true, max: 50 },
      { name: "status", type: "select", options: ["planned", "in_progress", "released", "rolled_back"] },
      { name: "release_notes", type: "textarea", max: 8000 },
    ],
  },
  // ------------------------------------------------------- risk (frozen module R-DEC-16; D-21)
  {
    // No DELETE: a risk leaves the register through its lifecycle (`closed` / `rejected`) — audit trail kept.
    key: "risks", domain: "risk", path: "/risk/risks", sortBy: "code", order: "asc", archivable: false,
    sortable: ["code", "risk_score"],
    columns: [{ name: "code", type: "text" }, { name: "title", type: "text" }, { name: "category", type: "enum" }, { name: "risk_score", type: "text" },
      { name: "status", type: "enum" }, { name: "review_date", type: "date" }],
    fields: [
      { name: "title", type: "text", required: true, max: 300 },
      { name: "category", type: "select", required: true, options: RISK_CATEGORIES },
      { name: "likelihood", type: "number", required: true, createOnly: true },
      { name: "impact", type: "number", required: true, createOnly: true },
      { name: "owner_id", type: "ref", ref: "user" },
      { name: "department_id", type: "ref", ref: "department" },
      { name: "review_date", type: "date" },
      { name: "description", type: "textarea", max: 4000 },
    ],
    actions: [
      { key: "assess", suffix: "assessments", visible: (r) => !["closed", "rejected"].includes(String(r.status)),
        fields: [{ name: "likelihood", type: "number", required: true }, { name: "impact", type: "number", required: true }, { name: "note", type: "textarea", max: 2000 }] },
      { key: "status", suffix: "status", visible: (r) => !["closed", "rejected"].includes(String(r.status)),
        fields: [{ name: "to_status", type: "select", required: true, options: ["identified", "assessed", "mitigating", "monitoring", "closed", "rejected"] },
          { name: "reason", type: "textarea", max: 2000 }] },
      { key: "accept", suffix: "accept", permission: "risk:approve", visible: (r) => !["accepted", "closed", "rejected"].includes(String(r.status)),
        fields: [{ name: "reason", type: "textarea", required: true, max: 2000 }] },
    ],
  },
  {
    // No DELETE: a mitigation is cancelled (status) so the risk keeps its history.
    key: "mitigations", domain: "risk", path: "/risk/mitigations", sortBy: "due_date", archivable: false,
    sortable: ["due_date", "progress_pct"],
    columns: [{ name: "title", type: "text" }, { name: "risk_id", type: "ref", ref: "risk" }, { name: "due_date", type: "date" },
      { name: "progress_pct", type: "pct" }, { name: "status", type: "enum" }],
    fields: [
      { name: "risk_id", type: "ref", ref: "risk", required: true, createOnly: true },
      { name: "title", type: "text", required: true, max: 300 },
      { name: "owner_id", type: "ref", ref: "user", required: true },
      { name: "due_date", type: "date", required: true },
      { name: "progress_pct", type: "pct" },
      { name: "status", type: "select", options: ["planned", "in_progress", "done", "cancelled"] },
    ],
  },
  // ------------------------------------------------- execution (D-21: meetings, decisions, projects)
  {
    key: "meetings", domain: "execution", path: "/execution/meetings", sortBy: "held_at", archivable: true,
    sortable: ["held_at", "title"],
    columns: [{ name: "held_at", type: "date" }, { name: "title", type: "text" }, { name: "chair_id", type: "ref", ref: "user" }, { name: "department_id", type: "ref", ref: "department" }],
    fields: [
      { name: "title", type: "text", required: true, max: 500 },
      { name: "held_at", type: "date", required: true },
      { name: "chair_id", type: "ref", ref: "user" },
      { name: "department_id", type: "ref", ref: "department" },
      { name: "summary", type: "textarea", max: 20000 },
    ],
  },
  {
    // No DELETE (EP-DEC): a decision is closed by status `cancelled` so its 30/60/90 review history stays.
    key: "decisions", domain: "execution", path: "/execution/decisions", sortBy: "decided_at", archivable: false,
    sortable: ["decided_at", "due_date"],
    columns: [{ name: "decided_at", type: "date" }, { name: "content", type: "text" }, { name: "owner_id", type: "ref", ref: "user" },
      { name: "due_date", type: "date" }, { name: "status", type: "enum" }],
    fields: [
      { name: "content", type: "textarea", required: true, max: 10000 },
      { name: "decided_at", type: "date", required: true, createOnly: true },
      { name: "owner_id", type: "ref", ref: "user" },
      { name: "due_date", type: "date" },
      { name: "status", type: "select", options: ["open", "in_progress", "done", "cancelled"] },
      { name: "rationale", type: "textarea", max: 10000 },
      { name: "expected_outcome", type: "textarea", max: 10000 },
      { name: "actual_outcome", type: "textarea", max: 10000 },
    ],
  },
  {
    key: "projects", domain: "execution", path: "/work/projects", sortBy: "name", order: "asc", archivable: true,
    sortable: ["name", "start_date"],
    detailHref: (r) => `/work/projects/${String(r.id)}`,
    columns: [{ name: "name", type: "text" }, { name: "code", type: "text" }, { name: "owner_id", type: "ref", ref: "user" }, { name: "start_date", type: "date" },
      { name: "due_date", type: "date" }, { name: "status", type: "enum" }],
    fields: [
      { name: "code", type: "text", required: true, max: 50 },
      { name: "name", type: "text", required: true, max: 500 },
      { name: "owner_id", type: "ref", ref: "user", required: true },
      { name: "department_id", type: "ref", ref: "department" },
      { name: "start_date", type: "date" },
      { name: "due_date", type: "date" },
      { name: "status", type: "select", options: ["planned", "active", "on_hold", "done", "cancelled"] },
      { name: "budget_amount", type: "money" },
    ],
  },
];

export const resourcesOf = (d: Domain) => RESOURCES.filter((r) => r.domain === d);

/** Reference kinds a resource uses (its form, row actions and columns) — only those lists are fetched. */
export function refKindsOf(r: ResourceSpec): ReadonlySet<NonNullable<FieldSpec["ref"]>> {
  const refs = [...r.fields, ...(r.actions ?? []).flatMap((a) => a.fields), ...r.columns].map((f) => f.ref);
  return new Set(refs.filter((k): k is NonNullable<FieldSpec["ref"]> => k !== undefined));
}
