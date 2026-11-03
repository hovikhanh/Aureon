/**
 * API error → what the user is told (M6). A load that fails with 403 is a **permission** answer
 * (role / khối / scope), a 404 is "not there or outside your scope" (the API hides existence,
 * 10 §7.2.4), anything else is a system error — never the same "Đã có lỗi xảy ra" for all three.
 * Pure: `t` is passed in so the mapping is unit-tested.
 */
import { ApiError } from "./api-client";

type T = { (key: string): string; has: (key: string) => boolean };

export type ErrorKind = "forbidden" | "notFound" | "network" | "system";

export function errorKind(e: unknown): ErrorKind {
  if (e instanceof ApiError) {
    if (e.status === 403) return "forbidden";
    if (e.status === 404) return "notFound";
    return "system";
  }
  return e instanceof TypeError ? "network" : "system"; // fetch() rejects with TypeError offline
}

export function errorText(t: T, e: unknown): string {
  const kind = errorKind(e);
  if (e instanceof ApiError && t.has(`errors.${e.code}`)) return t(`errors.${e.code}`); // FORBIDDEN_ROLE / _SCOPE / _SALARY …
  if (kind === "forbidden") return t("errors.forbiddenData");
  if (kind === "notFound") return t("errors.notFoundData");
  if (kind === "network") return t("errors.network");
  return t("errors.generic");
}
