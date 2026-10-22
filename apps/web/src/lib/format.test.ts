import { describe, expect, it } from "vitest";
import { formatMetric, formatMoney, formatMoneyShort, formatPct, formatPeriod } from "./format";

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
