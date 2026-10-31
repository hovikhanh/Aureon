/** T-643 FE↔BE wiring: EP-DC-14 servable URLs, routing reason labels, BE rule codes → i18n (TC-M15-16). */
import { describe, expect, it } from "vitest";
import vi from "../../../messages/vi.json";
import { servable } from "./SourceDrawer";
import { routingLabel } from "../idp/RoutingReasons";
import { ruleMessage } from "./errors";

const flat = (o: Record<string, unknown>, p = ""): Record<string, string> =>
  Object.fromEntries(Object.entries(o).flatMap(([k, v]) => (typeof v === "object" && v ? Object.entries(flat(v as Record<string, unknown>, `${p}${k}.`)) : [[`${p}${k}`, String(v)]])));
const M = flat(vi as Record<string, unknown>);
const t = Object.assign((key: string, values: Record<string, string | number> = {}) => (M[key] ?? key).replace(/\{(\w+)\}/g, (_, k: string) => String(values[k] ?? "")), { has: (key: string) => key in M });

describe("T-643 wiring", () => {
  it("EP-DC-14b (R-DEC-80): the BFF file path is servable; absolute/data URLs too; others fall back", () => {
    // R-DEC-80: presigned URL now routes through the BFF → browser-loadable.
    expect(servable("/api/backend/files/documents/x?expires=1&signature=s")).toBe(true);
    expect(servable("https://minio.local/b/x?X-Amz-Signature=s")).toBe(true);
    expect(servable("data:image/svg+xml,<svg/>")).toBe(true);
    // a bare relative path with no serving prefix is not frameable → text-layer fallback
    expect(servable("/files/documents/x?expires=1&signature=s")).toBe(false);
  });

  it("routing reasons: every BE code has a VI label, LOW_CONFIDENCE carries the field", () => {
    for (const code of ["C5_REVIEW", "SUSPICIOUS_CONTENT", "CRITICAL_FIELD", "LOW_DOCUMENT_CONFIDENCE", "LOW_CLASSIFICATION_CONFIDENCE", "VALIDATION_FAILED", "MISSING_TARGET_PERMISSION"])
      expect(routingLabel(t as never, code)).toBe(M[`idp.routing.${code}`]);
    expect(routingLabel(t as never, "LOW_CONFIDENCE:salary")).toContain("salary");
    expect(routingLabel(t as never, "WHATEVER")).toContain("WHATEVER");
  });

  it("BE row rule codes (UPPERCASE) resolve to capture.errors.*", () => {
    for (const code of ["REQUIRED", "DATE_FORMAT", "NUMBER_FORMAT", "ENUM", "MASTER_NOT_FOUND", "UNKNOWN_FIELD"]) expect(t.has(`capture.errors.${code}`)).toBe(true);
    expect(ruleMessage(t, "MASTER_NOT_FOUND", { value: "NV-999" })).toContain("NV-999");
  });
});
