/** Shared request helpers of the mock goals routes (10 §7.2.3 "Quy ước chung M1.4"). */
import { MockHttpError } from "./http";
import type { MockRequest } from "./router";

export const err = (status: number, code: string, message: string, details: Record<string, unknown> = {}) => new MockHttpError(status, code, message, details);
export const biz = (message: string, details: Record<string, unknown>) => err(422, "BUSINESS_RULE_VIOLATION", message, details);
export const invalid = (field: string, message = `${field} is invalid`) => err(422, "VALIDATION_ERROR", message, { field });
export const notFound = (what: string) => err(404, "NOT_FOUND", `${what} not found`);

export function requireIdem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) throw err(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}
export const body = (req: MockRequest): Record<string, unknown> => (req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {});

/** PATCH `version` (body) or `If-Match` — mismatch → 409 CONFLICT_STATE. */
export function expectVersion(req: MockRequest, current: number): void {
  const raw = body(req).version ?? req.headers.get("if-match")?.replace(/"/g, "");
  if (raw === undefined || raw === null || raw === "") return;
  if (Number(raw) !== current) throw err(409, "CONFLICT_STATE", "version mismatch", { expected: current, got: Number(raw) });
}

export const isDate = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v));
export const PILLARS = ["F", "O", "C", "U", "S"] as const;
export const CONFIDENCES = ["HIGH", "MEDIUM", "LOW"] as const;

export function str(b: Record<string, unknown>, field: string, required: boolean, max = 500): string | null {
  const v = b[field];
  if (v === undefined || v === null || v === "") {
    if (required) throw invalid(field, `${field} is required`);
    return null;
  }
  if (typeof v !== "string" || v.trim() === "" || v.length > max) throw invalid(field);
  return v.trim();
}
export function num(b: Record<string, unknown>, field: string, required: boolean): number | null {
  const v = b[field];
  if (v === undefined || v === null || v === "") {
    if (required) throw invalid(field, `${field} is required`);
    return null;
  }
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : Number.NaN;
  if (!Number.isFinite(n)) throw invalid(field);
  return n;
}
export function oneOf<T extends string>(b: Record<string, unknown>, field: string, allowed: readonly T[], dflt: T | null = null): T | null {
  const v = b[field];
  if (v === undefined || v === null) return dflt;
  if (!allowed.includes(v as T)) throw invalid(field);
  return v as T;
}
export const nowIso = () => new Date().toISOString();
export const strip = <T extends { deleted: boolean }>(r: T): Omit<T, "deleted"> => {
  const { deleted: _d, ...rest } = r;
  void _d;
  return rest;
};
