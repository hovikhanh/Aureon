import { describe, expect, it } from "vitest";
import { executivePillars, P1_FROZEN_PILLARS, visiblePillars, worstStatus } from "./pillars";

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
  it("narrows a DIR to its khối like the API visible_pillars (R-DEC-12a)", () => {
    const all = ["finance:query", "hr:query", "execution:query", "sales:query", "product:query", "risk:query"];
    const codes = (scope: string[]) => visiblePillars("DIR", all, scope).map((p) => p.code);
    expect(codes(["F"])).toEqual(["F"]);
    expect(codes(["C"])).toEqual(["F", "C"]); // F headline stays (public METRIC-FIN-01, 02 §6.1)
    expect(codes(["O"])).toEqual(["F", "O"]);
    expect(codes([])).toEqual(["F", "O", "C", "U", "S"]);
    expect(visiblePillars("DIR", ["sales:query"], ["C"]).map((p) => p.code)).toEqual(["C"]);
  });
});

describe("executivePillars (R-DEC-16)", () => {
  it("drops the frozen U/S pillars from the Executive default; visiblePillars keeps all five", () => {
    const all = ["finance:query", "hr:query", "execution:query", "sales:query", "product:query", "risk:query"];
    expect(executivePillars("CEO", all).map((p) => p.code)).toEqual(["F", "O", "C"]);
    expect(visiblePillars("CEO", all).map((p) => p.code)).toEqual(["F", "O", "C", "U", "S"]);
    expect(executivePillars("DIR", all, ["F"]).map((p) => p.code)).toEqual(["F"]);
    expect(P1_FROZEN_PILLARS).toEqual(["U", "S"]);
  });
});
