/**
 * API error → i18n message for capture screens. Rule codes map to `capture.errors.<code>`;
 * 413 uses `details.limit` (rows / sheets / columns / size); 422 `details.reason` wins over the code.
 */
import { ApiError } from "@/lib/api-client";

type T = { (key: string, values?: Record<string, string | number>): string; has: (key: string) => boolean };

export function ruleMessage(t: T, rule_code: string, params: Record<string, unknown> = {}): string {
  const key = `capture.errors.${rule_code}`;
  const values = Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v ?? "")]));
  return t.has(key) ? t(key, { value: "", ...values }) : t("capture.errors.unknown", { code: rule_code });
}

export function captureError(t: T, e: unknown): string {
  if (!(e instanceof ApiError)) return t("errors.generic");
  const d = e.details ?? {};
  if (e.code === "FILE_TOO_LARGE" && typeof d.limit === "string" && t.has(`capture.errors.FILE_TOO_LARGE_${d.limit}`)) return t(`capture.errors.FILE_TOO_LARGE_${d.limit}`);
  if (typeof d.reason === "string" && t.has(`capture.errors.${d.reason}`)) return t(`capture.errors.${d.reason}`);
  if (Array.isArray(d.missing)) return t("capture.errors.missing", { perms: d.missing.join(", ") });
  if (t.has(`capture.errors.${e.code}`)) return t(`capture.errors.${e.code}`);
  if (t.has(`errors.${e.code}`)) return t(`errors.${e.code}`);
  return t("errors.generic");
}
