/**
 * Shared DTO types between apps/web and apps/api.
 * Source of truth: docs/3.EXECUTION/10-API-SPECIFICATION.md (§1.2, §1.3, §1.4).
 */

/** Success envelope — 10 §1.2 */
export interface ApiSuccess<TData, TMeta = Record<string, unknown>> {
  data: TData;
  meta?: TMeta;
}

/** Error codes — 10 §1.3 */
export type ApiErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHENTICATED"
  | "INVALID_CREDENTIALS"
  | "FORBIDDEN_ROLE"
  | "FORBIDDEN_SCOPE"
  | "FORBIDDEN_SALARY"
  | "NOT_FOUND"
  | "CONFLICT_STATE"
  | "REVIEW_LOCKED"
  | "IDEMPOTENCY_CONFLICT"
  | "DUPLICATE_DOCUMENT"
  | "UNDO_EXPIRED"
  | "FILE_TOO_LARGE"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "VALIDATION_ERROR"
  | "ACTION_REJECTED"
  | "AI_DISABLED"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR"
  | "DEPENDENCY_UNAVAILABLE";

/** Error envelope — 10 §1.2 */
export interface ApiError {
  error: {
    code: ApiErrorCode;
    message: string;
    details?: Record<string, unknown>;
  };
}

/** Pagination meta — 10 §1.5 */
export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

/** Role codes — 10 §1.4 */
export type RoleCode = "ROLE-01" | "ROLE-02" | "ROLE-03" | "ROLE-04" | "ROLE-05";

/** EP-01 response data — 10 §2 */
export type CheckState = "ok" | "fail";
export interface HealthOut {
  status: "ok" | "degraded";
  version: string;
  checks: {
    database: CheckState;
    redis: CheckState;
    storage: CheckState;
    model_gateway: CheckState;
  };
  demo_mode: boolean;
}

/* ------------------------------------------------------------------------------------------
 * Dashboard / metric / alert DTOs — 10 §1.8 (DS3), §1.9, §3 (MetricValueOut, AlertOut,
 * EP-12 history). Enum values from 05 §4 (`metric_unit`). Added by T-109/T-110.
 * ---------------------------------------------------------------------------------------- */

/** Pillar codes — 03 §1, 10 §3 */
export type Pillar = "FIN" | "CUS" | "OPS" | "HR";

/** Metric value state — 10 §1.9 */
export type MetricValueState = "OK" | "NO_DATA" | "NOT_COMPUTABLE";

/** Reason when `value_state = NOT_COMPUTABLE` — 10 §1.9 */
export type NotComputableReason = "DENOMINATOR_ZERO" | "DENOMINATOR_NEGATIVE" | "UNDEFINED";

/** Threshold color — 10 §1.9 (`null` unless `value_state = OK`) */
export type MetricStatusColor = "GREEN" | "YELLOW" | "RED";

/** `metrics.unit` enum — 05 §4 `metric_unit` */
export type MetricUnit =
  | "VND"
  | "PERCENT"
  | "DAYS"
  | "MONTHS"
  | "RATIO"
  | "COUNT"
  | "SCORE"
  | "TASKS_PER_PERSON"
  | "VND_PER_PERSON";

/** Special display rule (10 §1.9), e.g. METRIC-FIN-03 net cash flow ≥ 0 → `> 24 months`. */
export type MetricDisplayHint = "GT_24_MONTHS";

/** Metric access level for the active role — 10 §3, 02 §3.2 */
export type MetricAccessLevel = "FULL" | "AGG";

/** Masked sensitive field (salary) — 10 §1.8 DS3: no `value` is ever sent. */
export interface MaskedField {
  masked: true;
}

/** Sparkline point — 10 §3 MetricValueOut.sparkline */
export interface MetricSparklinePoint {
  period_key: string;
  value: number | null;
}

/** Alert severity / status — 10 §3 AlertOut */
export type AlertSeverity = "WARNING" | "CRITICAL";
export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED" | "DISMISSED";

/** Compact alert reference embedded in MetricValueOut.open_alert — 10 §3 */
export interface MetricOpenAlertRef {
  id: string;
  alert_code: string;
  severity: AlertSeverity;
}

/** MetricValueOut — 10 §3 (EP-10..EP-12) */
export interface MetricValueOut {
  metric_code: string;
  pillar: Pillar;
  name_i18n_key: string;
  unit: MetricUnit;
  chart_type: string;
  access_level: MetricAccessLevel;
  period_key: string;
  value: number | null;
  value_state: MetricValueState;
  not_computable_reason: NotComputableReason | null;
  display_hint: MetricDisplayHint | null;
  target_value: number | null;
  status_color: MetricStatusColor | null;
  warning_threshold: number;
  critical_threshold: number;
  sparkline: MetricSparklinePoint[];
  computed_at: string;
  open_alert: MetricOpenAlertRef | null;
}

/** EP-12 `history[]` item — TrendChart input (10 §3 EP-12) */
export interface MetricHistoryPoint {
  period_key: string;
  value: number | null;
  target_value: number | null;
  value_state: MetricValueState;
  status_color: MetricStatusColor | null;
}

/** AlertOut — 10 §3 (EP-10 alerts_top, EP-15..EP-17) */
export interface AlertOut {
  id: string;
  alert_code: string;
  metric_code: string;
  pillar: Pillar;
  severity: AlertSeverity;
  status: AlertStatus;
  period_key: string;
  title_i18n_key: string;
  message_params: Record<string, unknown>;
  suggestion_level: "L1";
  suggested_action_i18n_key: string;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  dismissed_at: string | null;
  can_acknowledge: boolean;
}

/** AI autonomy / state level shown by AIStateBadge — 06 §6.3 (P02) */
export type AIStateLevel = "L0" | "L1" | "L2" | "L3";

/* ------------------------------------------------------------------------------------------
 * IDP Document & Review Queue DTOs — 10 §4 (EP-20..EP-35). Added by T-218.
 * ---------------------------------------------------------------------------------------- */

export type DocType =
  | "INVOICE"
  | "SALES_REPORT"
  | "KPI_OKR"
  | "MEETING_MINUTES"
  | "FINANCIAL_REPORT"
  | "CONTRACT"
  | "EMPLOYEE_LIST"
  | "OTHER";

export type DocumentStatus =
  | "UPLOADED"
  | "PREPROCESSING"
  | "CLASSIFYING"
  | "EXTRACTING"
  | "VALIDATING"
  | "NEEDS_REVIEW"
  | "IN_REVIEW"
  | "AUTO_APPROVED"
  | "APPROVED"
  | "COMMITTED"
  | "REJECTED"
  | "FAILED"
  | "DUPLICATE"
  | "ROLLED_BACK";

export type InputChannel = "C1" | "C2" | "C3" | "C4" | "C5";
export type DocumentKind = "FILE" | "SPREADSHEET" | "VIRTUAL";

export interface UserBrief {
  id: string;
  full_name: string;
}

export interface JobOut {
  id: string;
  attempt_no: number;
  doc_type: DocType | null;
  status: string;
  classification_confidence: number | null;
  routing_decision: string | null;
  routing_reason: string | null;
  error_code: string | null;
  avg_confidence: number | null;
  validation_summary: Record<string, unknown> | null;
  cross_doc_results: Record<string, unknown> | null;
  started_at: string;
  finished_at: string | null;
}

export interface DocumentOut {
  id: string;
  batch_id: string | null;
  channel: InputChannel;
  kind: DocumentKind;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  page_count: number;
  doc_type: DocType | null;
  pillars: Pillar[];
  status: DocumentStatus;
  status_reason: string | null;
  ai_state: AIStateLevel | null;
  autonomy_level: string | null;
  contains_salary: boolean;
  contains_pii: boolean;
  duplicate_of_id: string | null;
  uploaded_by: UserBrief;
  uploaded_at: string;
  committed_at: string | null;
  undo_deadline: string | null;
  locked_by: UserBrief | null;
  locked_until: string | null;
  retry_count: number;
  latest_job: JobOut | null;
}

export interface ReviewQueueItemOut {
  document: DocumentOut;
  routing_reason: string | null;
  avg_confidence: number | null;
  fields_to_check: number;
  has_conflict: boolean;
  locked_by: UserBrief | null;
  locked_until: string | null;
}

export interface ReviewQueueCountsOut {
  total: number;
  needs_review: number;
  in_review: number;
  failed: number;
}

export interface ReviewQueueMetaOut extends PageMeta {
  counts: ReviewQueueCountsOut;
}

export interface ReviewQueueResponse {
  data: ReviewQueueItemOut[];
  meta: ReviewQueueMetaOut;
}

