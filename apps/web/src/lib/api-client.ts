/**
 * API client stub — base path `/api/v1` (10 §1.1), envelopes `{ data, meta? }` /
 * `{ error: { code, message, details? } }` (10 §1.2) typed by @aureon/shared-types.
 * No endpoint is called yet; feature tasks build TanStack Query hooks on `apiFetch`.
 *
 * Base URL (07 §7: only `NEXT_PUBLIC_*` reach the browser and they hold no secrets):
 * - server: `API_BASE_URL` (.env.example), falling back to `NEXT_PUBLIC_API_BASE_URL`;
 * - browser: `NEXT_PUBLIC_API_BASE_URL`, falling back to same-origin `/api/v1`.
 */
import type { ApiError, ApiErrorCode, ApiSuccess } from "@aureon/shared-types";

const DEFAULT_BASE_PATH = "/api/v1";

export function getApiBaseUrl(): string {
  const isServer = typeof window === "undefined";
  const raw = isServer
    ? (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL)
    : process.env.NEXT_PUBLIC_API_BASE_URL;
  return (raw && raw.trim() !== "" ? raw.trim() : DEFAULT_BASE_PATH).replace(/\/+$/, "");
}

/** Error thrown for `{ error }` envelopes or non-JSON/transport failures. */
export class ApiClientError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(code: ApiErrorCode, message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isApiError(body: unknown): body is ApiError {
  return (
    isRecord(body) &&
    isRecord(body.error) &&
    typeof body.error.code === "string" &&
    typeof body.error.message === "string"
  );
}

export function isApiSuccess<TData, TMeta>(body: unknown): body is ApiSuccess<TData, TMeta> {
  return isRecord(body) && "data" in body;
}

/** Parse an HTTP status + JSON body into the success envelope or throw ApiClientError. */
export function parseEnvelope<TData, TMeta = Record<string, unknown>>(
  status: number,
  body: unknown,
): ApiSuccess<TData, TMeta> {
  if (isApiError(body)) {
    throw new ApiClientError(body.error.code, body.error.message, status, body.error.details);
  }
  if (status >= 200 && status < 300 && isApiSuccess<TData, TMeta>(body)) {
    return body;
  }
  throw new ApiClientError(
    status >= 500 ? "INTERNAL_ERROR" : "BAD_REQUEST",
    `Unexpected response (HTTP ${status})`,
    status,
  );
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  /** JSON-serialisable body. */
  json?: unknown;
}

/** Fetch `path` (relative to `/api/v1`) and return the parsed success envelope. */
export async function apiFetch<TData, TMeta = Record<string, unknown>>(
  path: string,
  { json, headers, ...init }: ApiFetchOptions = {},
): Promise<ApiSuccess<TData, TMeta>> {
  const url = `${getApiBaseUrl()}/${path.replace(/^\/+/, "")}`;
  const response = await fetch(url, {
    // Real-time dashboard data must not be cached by Next.js (CLAUDE.md § Next.js gotchas).
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
  });
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return parseEnvelope<TData, TMeta>(response.status, body);
}
