/** T-625F — business-date helpers (Asia/Ho_Chi_Minh, ISO weeks). */
import { describe, expect, it } from "vitest";
import { addDays, businessToday, isIsoDate, isIsoWeek, isoWeek, weekRange, weekStart, weeksEnding } from "./work-dates";

describe("work dates", () => {
  it("business today: demo reference date wins, else the VN calendar date", () => {
    expect(businessToday(new Date("2026-10-24T20:00:00Z"), "2026-10-20")).toBe("2026-10-20");
    expect(businessToday(new Date("2026-10-24T18:30:00Z"), undefined)).toBe("2026-10-25"); // 01:30 +07
    expect(businessToday(new Date("2026-10-24T03:00:00Z"), "bad")).toBe("2026-10-24");
  });
  it("addDays across months / years", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2027-01-01", -1)).toBe("2026-12-31");
  });
  it("validates dates and weeks", () => {
    expect(isIsoDate("2026-02-29")).toBe(false);
    expect(isIsoDate("2028-02-29")).toBe(true);
    expect(isIsoDate(null)).toBe(false);
    expect(isIsoWeek("2026-W43")).toBe(true);
    expect(isIsoWeek("2026-W54")).toBe(false);
  });
  it("ISO week math", () => {
    expect(weekStart("2026-10-25")).toBe("2026-10-19");
    expect(isoWeek("2026-10-20")).toBe("2026-W43");
    expect(isoWeek("2027-01-01")).toBe("2026-W53");
    expect(weekRange("2026-W43")).toEqual({ start: "2026-10-19", end: "2026-10-25" });
    expect(weeksEnding("2027-W02", 3)).toEqual(["2026-W53", "2027-W01", "2027-W02"]);
  });
});
