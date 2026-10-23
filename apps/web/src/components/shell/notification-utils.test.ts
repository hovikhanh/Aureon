/** T-617F (TC-M12-18) — Header bell badge / link / relative time. */
import { describe, expect, it } from "vitest";
import { badgeText, relativeTime, safeInAppLink } from "./notification-utils";
import { permissionRows } from "@/features/admin/RolesView";

describe("badgeText", () => {
  it.each([[0, null], [-1, null], [1, "1"], [99, "99"], [100, "99+"], [1234, "99+"]] as const)("%s → %s", (n, out) => {
    expect(badgeText(n)).toBe(out);
  });
});

describe("safeInAppLink", () => {
  it.each([["/work/approvals", "/work/approvals"], ["//evil.com", null], ["https://evil.com", null], ["javascript:alert(1)", null], ["/\\evil", null], [null, null]] as const)("%s → %s", (l, out) => {
    expect(safeInAppLink(l)).toBe(out);
  });
});

describe("relativeTime", () => {
  const now = Date.parse("2026-10-20T10:00:00Z");
  it("formats minutes / hours / days in vi and en", () => {
    expect(relativeTime("2026-10-20T09:57:00Z", "en", now)).toBe("3 minutes ago");
    expect(relativeTime("2026-10-20T07:00:00Z", "vi", now)).toBe("3 giờ trước");
    expect(relativeTime("2026-10-18T10:00:00Z", "en", now)).toBe("2 days ago");
  });
});

describe("roles matrix rows (SCR-54)", () => {
  it("dedupes and orders by domain then read/write/query/approve/admin", () => {
    expect(permissionRows([{ permissions: ["hr:admin", "hr:read"] }, { permissions: ["ai:query", "hr:read"] }])).toEqual(["ai:query", "hr:read", "hr:admin"]);
  });
});
