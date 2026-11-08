import { describe, expect, it } from "vitest";
import { formatFieldValue, formatMetric, formatMoney, formatMoneyShort, formatPct, formatPeriod, formatTime, formatWeekdayDate } from "./format";

describe("format (P04)", () => {
  it("formats VN money", () => {
    expect(formatMoney(1250000, "vi").replace(/\u00a0/g, " ")).toBe("1.250.000 đ");
    expect(formatMoneyShort(1_200_000_000, "vi")).toBe("1,2 tỷ");
    expect(formatMoneyShort(850_000_000, "vi")).toBe("850 tr");
    expect(formatMoneyShort(1_200_000_000, "en")).toBe("VND 1.2B");
  });
  it("formats pct and periods", () => {
    expect(formatPct(12.5, "vi")).toBe("12,5%");
    expect(formatPct(12.5, "en")).toBe("12.5%");
    expect(formatPeriod("2026-09", "vi")).toBe("T9/2026");
    expect(formatPeriod("2026-Q3", "en")).toBe("Q3 2026");
  });
  it("formats metrics by unit", () => {
    expect(formatMetric(null, "PCT", "vi")).toBe("—");
    expect(formatMetric(2.9, "RATIO", "vi")).toBe("2,9x");
    expect(formatMetric(13.6, "MONTHS", "vi", "tháng")).toBe("13,6 tháng");
  });
});

describe("format additions (U-12)", () => {
  it("ISO weeks read as weeks", () => {
    expect(formatPeriod("2026-W40", "vi")).toBe("Tuần 40/2026");
    expect(formatPeriod("2026-W04", "en")).toBe("Week 4, 2026");
  });

  it("calendar day + time follow the locale and the business time zone", () => {
    expect(formatWeekdayDate("2026-10-19T18:00:00Z", "vi")).toContain("20/10/2026");
    expect(formatWeekdayDate("2026-10-20T02:00:00Z", "en")).toContain("Oct 20, 2026");
    expect(formatTime("2026-10-20T02:05:00Z", "vi")).toBe("09:05");
  });

  it("field values by type; what does not parse stays verbatim", () => {
    expect(formatFieldValue("250000000", "money", "vi").replace(/\u00a0/g, " ")).toBe("250.000.000 đ");
    expect(formatFieldValue(1234.5, "number", "vi")).toBe("1.234,5");
    expect(formatFieldValue(10, "percent", "vi")).toBe("10%");
    expect(formatFieldValue("2026-09-12", "date", "vi")).toBe("12/09/2026");
    expect(formatFieldValue("12/09/2026", "date", "vi")).toBe("12/09/2026");
    expect(formatFieldValue("abc", "money", "vi")).toBe("abc");
    expect(formatFieldValue("0301234567", "tax_code", "vi")).toBe("0301234567");
    expect(formatFieldValue(null, "money", "vi")).toBe("");
  });
});
