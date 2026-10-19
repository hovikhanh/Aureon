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

/** EP-10 greeting block — 10 §3 */
export interface DashboardGreeting {
  full_name: string;
  salutation: string | null;
}

/** EP-10 AI summary — 10 §3 (`summary`). Numbers in `params` carry `metric_code`. */
export interface DashboardSummary {
  i18n_key: string;
  params: Record<string, unknown>;
  suggestion_level: "L1";
}

/** EP-10 pillar block — 10 §3 (`pillars[]`). */
export interface PillarBlock {
  pillar: Pillar;
  access_level: MetricAccessLevel;
  health_color: MetricStatusColor;
  open_alert_count: number;
  headline_metric: MetricValueOut | null;
  metrics: MetricValueOut[];
}

/** EP-10 GET /api/v1/dashboard `data` — 10 §3. */
export interface DashboardOut {
  role_code: string;
  greeting: DashboardGreeting;
  summary: DashboardSummary;
  pillars: PillarBlock[];
  alerts_top: AlertOut[];
}

/** EP-12 lineage panel (P01) — 10 §3. `source_*` present only for FULL access. */
export interface LineagePanelOut {
  formula_display: string;
  formula_expr: string;
  source_record_types: string[];
  computed_at: string | null;
  computation: string | null;
  source_record_count: number | null;
  source_documents:
    | {
        id: string;
        original_filename: string | null;
        doc_type: string | null;
        restricted: boolean;
        reason: string | null;
      }[]
    | null;
}

/** EP-12 breakdown row — 10 §3 (`breakdown.rows[]`). */
export interface MetricBreakdownRow {
  key: string;
  label: string;
  value: number | null;
  share: number | null;
  record_filter: string | null;
}

/** EP-12 breakdown — 10 §3 (`breakdown`); null when AGG (DS2). */
export interface MetricBreakdown {
  dimension: string;
  rows: MetricBreakdownRow[];
}

/** EP-12 GET /api/v1/metrics/{metric_code} `data` — 10 §3. */
export interface MetricDetailOut {
  metric: MetricValueOut;
  lineage_panel: LineagePanelOut;
  computation_inputs: { numerator: number | null; denominator: number | null } | null;
  history: MetricHistoryPoint[];
  breakdown: MetricBreakdown | null;
  alert: AlertOut | null;
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
// 10 §4 DocumentOut / 05 §4.3: FILE (C3/C4/C5), MANUAL (C1), TRANSCRIPT (C2).
export type DocumentKind = "FILE" | "MANUAL" | "TRANSCRIPT";

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
  // Virtual documents (C1 MANUAL, C2 TRANSCRIPT) have no file metadata → null.
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  page_count: number | null;
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

/* ------------------------------------------------------------------------------------------
 * IDP Review & Field Correction DTOs — 10 §4 (EP-26, EP-29..EP-35). Added by T-219.
 * ---------------------------------------------------------------------------------------- */

export type FieldValueType =
  | "STRING"
  | "NUMBER"
  | "DATE"
  | "CURRENCY"
  | "PERCENT"
  | "BOOLEAN"
  | "TABLE";

export type SensitivityLabel = "NONE" | "PII" | "SALARY" | "CONFIDENTIAL";

export interface ExtractedFieldOut {
  id: string;
  field_key: string;
  table_key: string | null;
  row_index: number | null;
  record_group: string | null;
  value: unknown;
  raw_text: string | null;
  value_type: FieldValueType;
  confidence: number;
  confidence_band: "HIGH" | "MEDIUM" | "LOW";
  source_location: Record<string, unknown> | null;
  document_page_id: string | null;
  validation: Record<string, unknown>[];
  sensitivity: SensitivityLabel;
  corrected: boolean;
  corrected_value: unknown;
  final_value: unknown;
  required: boolean;
  masked: boolean;
}

export interface ExtractionResultOut {
  document: DocumentOut;
  job: JobOut;
  fields: ExtractedFieldOut[];
  cross_doc_results: Record<string, unknown>[];
  validation_summary: Record<string, unknown>;
  suspicious_content: boolean;
}

export interface ReviewOpenOut {
  document: DocumentOut;
  review_id: string;
  extraction: ExtractionResultOut;
}

/** EP-27 page metadata for the SourceViewer + HighlightOverlay (10 §4). */
export interface DocumentPageDetailOut {
  page_number: number;
  image_url: string | null;
  width_px: number | null;
  height_px: number | null;
  ocr_used: boolean;
  ocr_confidence: number | null;
}

/** EP-27 GET /documents/{id}/source `data` — SCR-10 Source Viewer (10 §4). */
export interface DocumentSourceOut {
  url: string | null;
  expires_at: string | null;
  mime_type: string | null;
  page_count: number | null;
  pages: DocumentPageDetailOut[];
  /** Present for virtual C1/C2 documents instead of a file `url`. */
  manual_info?: { created_by_full_name: string; created_at: string } | null;
}

/** A `source_location` bounding box resolved from extracted_fields (05 §7.1). */
export interface SourceBoundingBox {
  kind: "BOUNDING_BOX" | string;
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

// EP-25 GET /documents/{id} — detail with jobs, status timeline, reviews, affected.
export interface StatusTimelineItem {
  status: DocumentStatus | string;
  at: string;
  actor_type: string;
}

export interface DocumentAffectedOut {
  business_record_ids: string[];
  metric_codes: string[];
}

export interface DocumentReviewOut {
  reviewer_full_name: string;
  decision: string | null;
  reject_reason_code: string | null;
  decided_at: string | null;
}

export interface DocumentDetailOut {
  document: DocumentOut;
  jobs: JobOut[];
  status_timeline: StatusTimelineItem[];
  affected: DocumentAffectedOut;
  reviews: DocumentReviewOut[];
}

export interface FieldCorrectionItem {
  id: string;
  corrected_value: unknown;
}

export interface UpdateDocumentFieldsRequest {
  doc_type?: DocType;
  fields?: FieldCorrectionItem[];
  confirmed_field_ids?: string[];
  split_ranges?: { from_page: number; to_page: number }[];
}

export interface AcceptedConflictItem {
  rule: string;
  note: string;
}

export interface ReviewApproveRequest {
  review_id: string;
  field_ids?: string[];
  accepted_conflicts?: AcceptedConflictItem[];
}

export interface ReviewApproveReviewOut {
  id: string;
  decision: string;
  decided_at: string;
  duration_ms: number | null;
  fields_corrected: number;
}

export interface CommitActionResult {
  action_name: string;
  business_record_ids: string[];
  metric_value_ids: string[];
}

export interface ReviewApproveCommitOut {
  actions: CommitActionResult[];
  affected_metric_codes: string[];
  recompute_job_id: string | null;
}

export interface ReviewApproveOut {
  document: DocumentOut;
  review: ReviewApproveReviewOut;
  commit: ReviewApproveCommitOut;
}

export interface ReviewRejectRequest {
  review_id: string;
  reject_reason_code: string;
  reject_note?: string;
}



// EP-52 GET /audit-logs — audit log entries (SCR-14; ROLE-01 only; salary masked).
export type ActorType = "USER" | "AI" | "SYSTEM";

export interface AuditActorOut {
  id: string;
  full_name: string;
}

export interface AuditLogOut {
  id: string;
  occurred_at: string;
  actor_type: ActorType;
  actor: AuditActorOut | null;
  actor_role_code: RoleCode | null;
  action: string;
  target_type: string;
  target_id: string | null;
  source_document_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
}
