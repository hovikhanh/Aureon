import { describe, expect, it } from "vitest";
import { CARDS, idpDocumentId, monthOf, trendOf } from "./drilldown";

describe("finance drill-down (T-511)", () => {
  it("defines the 6 brief cards in order", () => {
    expect(CARDS.map((c) => c.key)).toEqual(["revenue", "expense", "budget", "runway", "cash", "burn"]);
  });
  it("trend arrow from the last two points", () => {
    expect(trendOf([1, 2])).toBe("up");
    expect(trendOf([3, 2])).toBe("down");
    expect(trendOf([2, 2])).toBe("flat");
    expect(trendOf([2])).toBeNull();
  });
  it("month for list endpoints", () => {
    expect(monthOf({ key: "2026-09", end_date: "2026-09-30" })).toBe("2026-09");
    expect(monthOf({ key: "2026-Q3", end_date: "2026-09-30" })).toBe("2026-09");
  });
  it("extracts the IDP source document id", () => {
    expect(idpDocumentId("Committed from IDP document 54f3400e-e0f0-486b-a0db-86a1b970824e")).toBe("54f3400e-e0f0-486b-a0db-86a1b970824e");
    expect(idpDocumentId(null)).toBeNull();
  });
});
