/**
 * Mock HTTP helpers (T-604) — same wire format as the FastAPI backend (10 §1.2–§1.5, DEC-130):
 * `{data, meta}` success, `{error: {code, message, details}}` errors, `limit/offset/sort_by/order`
 * pagination with `meta.pagination = {total, limit, offset, has_next}`, `X-Request-Id` on every
 * response, `Cache-Control: no-store`.
 */
export const MAX_LIMIT = 100;
export const DEFAULT_LIMIT = 20;

export class MockHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

function headers(extra: Record<string, string> = {}): Headers {
  return new Headers({
    "content-type": "application/json",
    "cache-control": "no-store",
    "x-request-id": globalThis.crypto.randomUUID(),
    "x-api-mode": "mock",
    ...extra,
  });
}

export function ok(data: unknown, status = 200, meta?: Record<string, unknown>): Response {
  if (status === 204) return new Response(null, { status, headers: headers() });
  const body = meta ? { data, meta } : { data };
  return new Response(JSON.stringify(body), { status, headers: headers() });
}

export function fail(status: number, code: string, message: string, details: Record<string, unknown> = {}): Response {
  return new Response(JSON.stringify({ error: { code, message, details } }), { status, headers: headers() });
}

export interface Page {
  limit: number;
  offset: number;
  sortBy: string | null;
  order: "asc" | "desc";
}

/** Parse + validate pagination exactly like `core/pagination.py` (400 BAD_REQUEST on bad input). */
export function parsePage(q: URLSearchParams, sortable: readonly string[] = []): Page {
  const int = (name: string, dflt: number): number => {
    const raw = q.get(name);
    if (raw === null || raw === "") return dflt;
    const n = Number(raw);
    if (!Number.isInteger(n)) throw new MockHttpError(400, "BAD_REQUEST", `${name} must be an integer`, { param: name });
    return n;
  };
  const limit = int("limit", DEFAULT_LIMIT);
  const offset = int("offset", 0);
  if (limit < 1 || limit > MAX_LIMIT) {
    throw new MockHttpError(400, "BAD_REQUEST", `limit must be 1..${MAX_LIMIT}`, { param: "limit", max: MAX_LIMIT });
  }
  if (offset < 0) throw new MockHttpError(400, "BAD_REQUEST", "offset must be >= 0", { param: "offset" });
  const sortBy = q.get("sort_by");
  if (sortBy && !sortable.includes(sortBy)) {
    throw new MockHttpError(400, "BAD_REQUEST", "sort_by not allowed", { param: "sort_by", allowed: sortable.join(",") });
  }
  const order = q.get("order") ?? "asc";
  if (order !== "asc" && order !== "desc") throw new MockHttpError(400, "BAD_REQUEST", "order must be asc|desc", { param: "order" });
  return { limit, offset, sortBy, order };
}

export function paginate<T extends Record<string, unknown>>(rows: readonly T[], page: Page): Response {
  const sorted = page.sortBy ? [...rows].sort((a, b) => cmp(a[page.sortBy as string], b[page.sortBy as string])) : [...rows];
  if (page.order === "desc") sorted.reverse();
  const data = sorted.slice(page.offset, page.offset + page.limit);
  const pagination = { total: rows.length, limit: page.limit, offset: page.offset, has_next: page.offset + data.length < rows.length };
  return ok(data, 200, { pagination });
}

function cmp(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined) return -1;
  if (b === null || b === undefined) return 1;
  return a < b ? -1 : 1;
}
