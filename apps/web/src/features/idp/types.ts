/** EP-28 queue / review detail / EP-30..35 shapes (10 §3.3, idp schemas). */
export interface ReviewQueueItem {
  document_id: string;
  filename: string | null;
  document_type: string | null;
  status: string;
  confidence_avg: number | null;
  critical_fields_count: number;
  validation_error_count: number;
  routing_reason: string | null;
  age_hours: number;
  assigned_to: string | null;
  due_at: string | null;
  locked_by: string | null;
  locked_until: string | null;
}

export type ConfidenceBand = "HIGH" | "MEDIUM" | "LOW";

export interface ValidationResult {
  rule: string;
  status: "pass" | "fail" | "warn";
  message: string;
}

export interface ReviewField {
  id: string;
  field_name: string;
  row_index: number | null;
  value_type: string;
  ai_value: unknown;
  corrected_value: unknown;
  effective_value: unknown;
  confidence: number | null;
  confidence_band: ConfidenceBand | null;
  is_critical: boolean;
  is_confirmed: boolean;
  source_location: { kind?: string; page?: number; bbox?: number[] } | null;
  validation: ValidationResult[];
  correction_reason: string | null;
}

export interface DocumentOut {
  id: string;
  original_filename: string | null;
  mime_type: string | null;
  page_count: number | null;
  status: string;
  submitted_at: string;
  /** R-DEC-60bis optimistic lock. */
  version: number;
  document_type?: string | null;
  undo_deadline?: string | null;
}

export interface ReviewPage {
  id: string;
  page_number: number;
  text_content: string | null;
  text_layer_exists: boolean;
}

export interface ReviewDetail {
  document: DocumentOut;
  job_id: string | null;
  pages: ReviewPage[];
  fields: ReviewField[];
  validation_errors: Array<{ rule?: string; field?: string; message?: string }>;
  document_confidence: number | null;
  routing_decision: string | null;
  routing_reasons: string[];
  assigned_to: string | null;
  locked_by: string | null;
  locked_until: string | null;
  /** EP-DC-05: table documents grouped by `row_index`. */
  rows: Array<{ row_index: number; fields: ReviewField[] }>;
  planned_actions: PlannedAction[];
  can_commit: boolean;
}

/** EP-DC-05 dry-run of the ACT-* the approval will run. */
export interface PlannedAction {
  action_name: string;
  count: number;
  required_permission: string;
  permitted: boolean;
}

export interface FieldPatchOut {
  fields: ReviewField[];
  validation_errors: ReviewDetail["validation_errors"];
  validations_ok: boolean;
}

export interface ApproveOut {
  document: DocumentOut;
  actions: Array<{ action_name: string; ids: string[]; table: string }>;
  undo_deadline: string | null;
}

export const DOC_TYPES = [
  "INVOICE", "FINANCIAL_REPORT", "SALES_REPORT", "CONTRACT", "MEETING_MINUTES",
  "EMPLOYEE_LIST", "KPI_OKR", "PRODUCT_REPORT", "RISK_REGISTER",
] as const;
export const QUEUE_STATUSES = ["NEEDS_REVIEW", "IN_REVIEW", "APPROVED"] as const;
