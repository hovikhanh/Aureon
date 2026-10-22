import { describe, expect, it } from "vitest";
import { visiblePillars, worstStatus } from "./pillars";

describe("pillars", () => {
  it("worst status wins", () => {
    expect(worstStatus(["ok", "warning"])).toBe("warning");
    expect(worstStatus(["warning", "critical", "ok"])).toBe("critical");
    expect(worstStatus([])).toBe("no_data");
  });
  it("hides out-of-scope pillars", () => {
    expect(visiblePillars("VP_SALES", ["sales:query", "finance:query"]).map((p) => p.code)).toEqual(["C"]);
    expect(visiblePillars("CFO", ["finance:query", "risk:query", "hr:query"]).map((p) => p.code)).toEqual(["F", "S"]);
    expect(visiblePillars("CEO", ["finance:query", "hr:query", "execution:query", "sales:query", "product:query", "risk:query"])).toHaveLength(5);
  });
});
