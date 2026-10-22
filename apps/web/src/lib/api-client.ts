/**
 * Browser fetch wrapper → BFF `/api/backend/*` (adds the JWT server-side from the httpOnly
 * session). Unwraps the `{data, meta}` envelope; maps `{error:{code,message}}` to `ApiError`;
 * 401 → redirect to /login (session expired).
 */
export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  has_next: boolean;
}
export interface Envelope<T> {
  data: T;
  meta?: { request_id?: string; generated_at?: string; pagination?: Pagination | null } & Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const API_PROXY = "/api/backend";

/** T-509: chat SSE budget (BE chat timeout 90 s + fallback model) and UI wait thresholds (ms). */
export const CHAT_STREAM_TIMEOUT_MS = 120_000;
export const CHAT_WAIT_THINKING_MS = 10_000;
export const CHAT_WAIT_SLOW_MS = 30_000;
export const CHAT_WAIT_GIVE_UP_MS = 90_000;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  headers?: Record<string, string>;
  /** Adds `Idempotency-Key` (required on POST create/commit/action — CLAUDE §5.2). */
  idempotent?: boolean;
  signal?: AbortSignal;
}

export function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return `${API_PROXY}${path.startsWith("/") ? path : `/${path}`}${s ? `?${s}` : ""}`;
}

export function newIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

function redirectToLogin(): void {
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.assign(`/login?callbackUrl=${next}`);
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  const json = (await res.json().catch(() => null)) as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null;
  const e = json?.error;
  return new ApiError(res.status, e?.code ?? `HTTP_${res.status}`, e?.message ?? res.statusText, e?.details ?? {});
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<Envelope<T>> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { accept: "application/json", ...opts.headers };
  if (opts.body !== undefined) headers["content-type"] = "application/json";
  if (opts.idempotent) headers["idempotency-key"] = newIdempotencyKey();
  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
      cache: "no-store",
      signal: opts.signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "NETWORK_ERROR", (err as Error).message);
  }
  if (res.status === 401) {
    redirectToLogin();
    throw await toApiError(res);
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return { data: undefined as T };
  return (await res.json()) as Envelope<T>;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    apiRequest<T>(path, { query, signal }).then((r) => r.data),
  page: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) => apiRequest<T>(path, { query, signal }),
  post: <T>(path: string, body: unknown = {}, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "POST", body, idempotent: true, headers }).then((r) => r.data),
  patch: <T>(path: string, body: unknown, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "PATCH", body, headers }).then((r) => r.data),
};
