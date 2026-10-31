import { describe, expect, it } from "vitest";
import en from "../../../messages/en.json";
import vi from "../../../messages/vi.json";
import { CARDS, idpDocumentId, monthOf, trendOf } from "./drilldown";

describe("finance drill-down (T-511)", () => {
  it("defines the 6 brief cards in order", () => {
    expect(CARDS.map((c) => c.key)).toEqual(["revenue", "expense", "budget", "runway", "cash", "burn"]);
  });

  // FinanceDrillView renders `financeDrill.card.<key>` always and `financeDrill.hint.<key>` as the
  // fallback when a card has < 2 trend points. Every card key must resolve in both locales — a gap
  // throws `MISSING_MESSAGE: financeDrill.hint.<key>` on the client (the reported bug).
  it.each(["vi", "en"] as const)("%s has card + hint for every drill card", (loc) => {
    const fd = (loc === "vi" ? vi : en).financeDrill as { card: Record<string, string>; hint: Record<string, string> };
    for (const { key } of CARDS) {
      expect(fd.card[key], `financeDrill.card.${key} (${loc})`).toBeTruthy();
      expect(fd.hint[key], `financeDrill.hint.${key} (${loc})`).toBeTruthy();
    }
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
