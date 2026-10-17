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
