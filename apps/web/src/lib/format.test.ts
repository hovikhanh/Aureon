// @vitest-environment node
/**
 * TC-UI-001 — P04 format helpers (06 §7.1). Labels come from messages/vi.json so the
 * test exercises the real Vietnamese unit words without literals in src/.
 */
import { describe, expect, it } from "vitest";
import vi from "../../messages/vi.json";
import { createFormatter, type FormatLabels } from "./format";

const labels: FormatLabels = vi.format;
const f = createFormatter(labels, "vi");
const PH = labels.placeholder;

describe("TC-UI-001 P04 examples (06 §7.1)", () => {
  it("full currency: 1.250.000 đ", () => {
    expect(f.currency(1_250_000)).toBe(`1.250.000 ${labels.currencySuffix}`);
    expect(f.currency(1_250_000)).toBe("1.250.000 \u0111");
  });
  it("compact currency: 1,2 tỷ and 850 tr", () => {
    expect(f.compactCurrency(1_200_000_000)).toBe(`1,2 ${labels.billion}`);
    expect(f.compactCurrency(1_200_000_000)).toBe("1,2 t\u1ef7");
    expect(f.compactCurrency(850_000_000)).toBe(`850 ${labels.million}`);
  });
  it("percent: 12,5% and signed change +8,2%", () => {
    expect(f.percent(0.125)).toBe("12,5%");
    expect(f.percentChange(0.082)).toBe("+8,2%");
  });
  it("date: 05/10/2026 and date-time 05/10/2026 08:30", () => {
    expect(f.date("2026-10-05")).toBe("05/10/2026");
    expect(f.dateTime("2026-10-05T08:30:00+07:00")).toBe("05/10/2026 08:30");
  });
  it("periods: T9/2026 and Q3/2026", () => {
    expect(f.period("2026-09")).toBe("T9/2026");
    expect(f.period("2026-Q3")).toBe("Q3/2026");
  });
  it("plain number 5,4 and multiple 2,8x", () => {
    expect(f.number(5.4)).toBe("5,4");
    expect(f.multiple(2.8)).toBe("2,8x");
  });
});

describe("P04 edge cases", () => {
  it("null / undefined / NaN / Infinity → placeholder (06 §4.1 `—`)", () => {
    for (const v of [null, undefined, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(f.currency(v)).toBe(PH);
      expect(f.compactCurrency(v)).toBe(PH);
      expect(f.percent(v)).toBe(PH);
      expect(f.percentChange(v)).toBe(PH);
      expect(f.number(v)).toBe(PH);
      expect(f.multiple(v)).toBe(PH);
    }
    expect(f.date(null)).toBe(PH);
    expect(f.dateTime(undefined)).toBe(PH);
    expect(f.period(null)).toBe(PH);
    expect(f.period("")).toBe(PH);
  });

  it("zero", () => {
    expect(f.currency(0)).toBe(`0 ${labels.currencySuffix}`);
    expect(f.compactCurrency(0)).toBe(`0 ${labels.currencySuffix}`);
    expect(f.percent(0)).toBe("0,0%");
    expect(f.percentChange(0)).toBe("0,0%");
    expect(f.number(0)).toBe("0");
  });

  it("negative values", () => {
    expect(f.currency(-1_250_000)).toBe(`-1.250.000 ${labels.currencySuffix}`);
    expect(f.compactCurrency(-1_200_000_000)).toBe(`-1,2 ${labels.billion}`);
    expect(f.compactCurrency(-850_000_000)).toBe(`-850 ${labels.million}`);
    expect(f.percent(-0.034)).toBe("-3,4%");
    expect(f.percentChange(-0.034)).toBe("-3,4%");
    expect(f.number(-5.4)).toBe("-5,4");
  });

  it("rounding", () => {
    expect(f.currency(1_250_000.6)).toBe(`1.250.001 ${labels.currencySuffix}`);
    expect(f.compactCurrency(1_250_000_000)).toBe(`1,3 ${labels.billion}`);
    expect(f.compactCurrency(1_240_000_000)).toBe(`1,2 ${labels.billion}`);
    expect(f.compactCurrency(12_345_000_000)).toBe(`12,3 ${labels.billion}`);
    expect(f.compactCurrency(1_234_000_000_000)).toBe(`1.234 ${labels.billion}`);
    expect(f.compactCurrency(999_960_000)).toBe(`1 ${labels.billion}`);
    expect(f.compactCurrency(1_000_000_000)).toBe(`1 ${labels.billion}`);
    expect(f.compactCurrency(1_500_000)).toBe(`1,5 ${labels.million}`);
    expect(f.percent(0.12549)).toBe("12,5%");
    expect(f.percent(0.12551)).toBe("12,6%");
    expect(f.percent(1)).toBe("100,0%");
    expect(f.number(-0.04)).toBe("0");
    expect(f.percent(-0.0004)).toBe("0,0%");
    expect(f.percentChange(-0.0004)).toBe("0,0%");
    expect(f.currency(-0.4)).toBe(`0 ${labels.currencySuffix}`);
    expect(f.number(1234567.891, 2)).toBe("1.234.567,89");
  });

  it("compact below one million falls back to full currency", () => {
    expect(f.compactCurrency(950_000)).toBe(`950.000 ${labels.currencySuffix}`);
  });

  it("dates: Date objects in Asia/Ho_Chi_Minh, UTC instants, invalid input", () => {
    expect(f.date(new Date("2026-10-04T18:00:00Z"))).toBe("05/10/2026");
    expect(f.dateTime("2026-10-05T01:30:00Z")).toBe("05/10/2026 08:30");
    expect(f.dateTime("2026-10-05T23:05:00+07:00")).toBe("05/10/2026 23:05");
    expect(f.dateTime("2026-10-05")).toBe("05/10/2026");
    expect(f.date("2026-02-30")).toBe(PH);
    expect(f.date("not-a-date")).toBe(PH);
    expect(f.date(new Date(Number.NaN))).toBe(PH);
  });

  it("periods: all months/quarters, invalid keys", () => {
    expect(f.period("2026-01")).toBe("T1/2026");
    expect(f.period("2026-12")).toBe("T12/2026");
    expect(f.period("2026-Q1")).toBe("Q1/2026");
    expect(f.period("2026-13")).toBe(PH);
    expect(f.period("2026-Q5")).toBe(PH);
    expect(f.period("2026")).toBe(PH);
  });
});
