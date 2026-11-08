import { describe, expect, it } from "vitest";
import { codeLabel, humanizeKey } from "./humanize";

describe("humanizeKey", () => {
  it.each([
    ["seller_name", "Seller name"], ["vat_rate_pct", "Vat rate pct"], ["kpiName", "Kpi name"],
    ["on-leave", "On leave"], ["HIGH", "High"], ["", ""],
  ])("%s → %s", (key, out) => {
    expect(humanizeKey(key)).toBe(out);
  });
});

describe("codeLabel", () => {
  const t = Object.assign((k: string) => `tr:${k}`, { has: (k: string) => k === "x.paid" });
  it("uses the catalog, then a humanised fallback — never the raw code", () => {
    expect(codeLabel(t, "x", "paid")).toBe("tr:x.paid");
    expect(codeLabel(t, "x", "written_off")).toBe("Written off");
  });
});
