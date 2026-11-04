/** TC-M8-03 (unit) — CRM helpers on the existing sales model (BRD §2.6/2.8/2.9). */
import { describe, expect, it } from "vitest";
import { canMoveTo, dealRisk, forecast, funnel, quarterOptions } from "./crm";

describe("canMoveTo mirrors the API stage rule", () => {
  it.each([
    ["lead", "qualified", true], ["lead", "negotiation", true], ["proposal", "qualified", false],
    ["qualified", "qualified", false], ["negotiation", "closed_won", true], ["lead", "closed_lost", true],
    ["closed_won", "negotiation", false], ["closed_lost", "closed_won", false],
  ])("%s → %s = %s", (from, to, ok) => expect(canMoveTo(from, to)).toBe(ok));
});

describe("funnel (Method A, BRD L910–923)", () => {
  it("conversion = N_current / N_previous, drop-off = 100 − conversion; lost is not a step", () => {
    const steps = funnel([
      { stage: "lead", count: 50, value: 0, weighted_value: 0 },
      { stage: "qualified", count: 30, value: 0, weighted_value: 0 },
      { stage: "proposal", count: 10, value: 0, weighted_value: 0 },
      { stage: "negotiation", count: 0, value: 0, weighted_value: 0 },
      { stage: "closed_won", count: 5, value: 0, weighted_value: 0 },
      { stage: "closed_lost", count: 9, value: 0, weighted_value: 0 },
    ]);
    expect(steps.map((s) => s.stage)).toEqual(["lead", "qualified", "proposal", "negotiation", "closed_won"]);
    expect(steps.map((s) => s.conversionPct)).toEqual([null, 60, 33.3, 0, null]); // ÷0 → null, never Infinity
    expect(steps[1]!.dropOffPct).toBe(40);
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
