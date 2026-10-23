import { describe, expect, it } from "vitest";
import { visiblePillars, worstStatus } from "./pillars";

describe("pillars", () => {
  it("worst status wins", () => {
    expect(worstStatus(["ok", "warning"])).toBe("warning");
    expect(worstStatus(["warning", "critical", "ok"])).toBe("critical");
    expect(worstStatus([])).toBe("no_data");
  });
  it("intersects role pillar scope with permissions (v3: DIR spans all five)", () => {
    // A DIR's khối is enforced server-side; the FE menu = role scope ∩ granted query perms.
    expect(visiblePillars("DIR", ["sales:query"]).map((p) => p.code)).toEqual(["C"]);
    expect(visiblePillars("DIR", ["finance:query", "risk:query"]).map((p) => p.code)).toEqual(["F", "S"]);
    expect(visiblePillars("CEO", ["finance:query", "hr:query", "execution:query", "sales:query", "product:query", "risk:query"])).toHaveLength(5);
    // Roles without an executive pillar see nothing.
    expect(visiblePillars("EMP", ["execution:query"])).toHaveLength(0);
  });
});
