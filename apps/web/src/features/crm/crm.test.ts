/** TC-M8-03 (unit) — CRM helpers on the existing sales model (BRD §2.6/2.8/2.9). */
import { describe, expect, it } from "vitest";
import { canMoveTo, dealRisk, forecast, funnelPct, quarterOptions } from "./crm";

describe("canMoveTo mirrors the API stage rule", () => {
  it.each([
    ["lead", "qualified", true], ["lead", "negotiation", true], ["proposal", "qualified", false],
    ["qualified", "qualified", false], ["negotiation", "closed_won", true], ["lead", "closed_lost", true],
    ["closed_won", "negotiation", false], ["closed_lost", "closed_won", false],
  ])("%s → %s = %s", (from, to, ok) => expect(canMoveTo(from, to)).toBe(ok));
});

describe("funnelPct (the API computes the cumulative funnel, D-09)", () => {
  it("shows a ratio as sent, nothing when there is none", () => {
    expect(funnelPct(75)).toBe("75%");
    expect(funnelPct(33.3)).toBe("33.3%");
    expect(funnelPct(0)).toBe("0%");
    expect(funnelPct(null)).toBe("—");
  });
});

describe("forecast (WP = Σ value × probability, BRD L1029)", () => {
  it("sums open stages' weighted value, adds won, excludes lost", () => {
    const f = forecast([
      { stage: "proposal", count: 1, value: 2_000_000_000, weighted_value: 800_000_000 },
      { stage: "negotiation", count: 2, value: 4_000_000_000, weighted_value: 2_600_000_000 },
      { stage: "closed_won", count: 1, value: 1_000_000_000, weighted_value: 1_000_000_000 },
      { stage: "closed_lost", count: 3, value: 9_000_000_000, weighted_value: 0 },
    ]);
    expect(f).toEqual({ pipeline: 6_000_000_000, weighted: 3_400_000_000, closedWon: 1_000_000_000, expected: 4_400_000_000 });
  });
});

describe("dealRisk + quarters", () => {
  it("overdue / due within 7 days / closed → none", () => {
    expect(dealRisk({ stage: "proposal", expected_close_date: "2026-11-01" }, "2026-11-04")).toBe("overdue");
    expect(dealRisk({ stage: "proposal", expected_close_date: "2026-11-10" }, "2026-11-04")).toBe("dueSoon");
    expect(dealRisk({ stage: "proposal", expected_close_date: "2026-12-30" }, "2026-11-04")).toBeNull();
    expect(dealRisk({ stage: "closed_won", expected_close_date: "2026-10-01" }, "2026-11-04")).toBeNull();
  });
  it("quarter keys wrap the year", () => {
    expect(quarterOptions("2026-11-04")).toEqual(["2026-Q3", "2026-Q4", "2027-Q1", "2027-Q2"]);
  });
});
