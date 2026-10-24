/** T-626F..T-628F — pure helpers of SCR-41/58/59/60 (filters, chart rows, week range, error keys, forms). */
import { describe, expect, it } from "vitest";
import { checkInSchema, measureSchema, targetSchema, toCheckInBody, toMeasureBody, toTargetBody } from "./forms";
import {
  chartRows, checkedInThisWeek, daysAgo, filterKpis, filterObjs, formatValue, goalErrorKey, kpiFlagged, objFlagged, periodKeyOf, soVisible, treeKrs, weekRangeOf,
  type GoalTree, type KpiNode, type ObjNode,
} from "./logic";

const ev = (period_key: string, band: "CRITICAL" | "MEETS") => ({ period_key, actual_value: 1, target: 2, achievement_pct: 50, band, previous_band: null, evaluated_at: "2026-10-01T00:00:00Z" });
const kr = (id: string, at_risk: boolean, last: string | null = null) => ({ id, title: id, unit: "%", baseline: 0, target: 10, current_value: 5, progress_pct: 50, confidence: null, at_risk, last_checked_in_at: last, owner_id: "u" });

describe("SCR-41 quick filter (at-risk / below threshold)", () => {
  const ok: KpiNode = { id: "a", latest_evaluation: ev("2026-09", "MEETS"), children: [] };
  const bad: KpiNode = { id: "b", latest_evaluation: ev("2026-09", "CRITICAL") };
  const parent: KpiNode = { id: "p", latest_evaluation: null, children: [bad] };
  it("keeps KPIs in BELOW/CRITICAL (or with such a child)", () => {
    expect(kpiFlagged(ok)).toBe(false);
    expect(kpiFlagged(parent)).toBe(true);
    expect(filterKpis([ok, bad, parent], true).map((k) => k.id)).toEqual(["b", "p"]);
    expect(filterKpis([ok, bad], false)).toHaveLength(2);
  });
  it("keeps objectives with an at-risk KR; SO visible when anything inside is flagged / late", () => {
    const o1: ObjNode = { id: "o1", key_results: [kr("k1", false)] };
    const o2: ObjNode = { id: "o2", at_risk_kr_count: 0, key_results: [kr("k2", true)] };
    expect(objFlagged(o1)).toBe(false);
    expect(filterObjs([o1, o2], true).map((o) => o.id)).toEqual(["o2"]);
    expect(soVisible({ id: "s", kpis: [ok], objectives: [o1], initiatives: [{ id: "i", on_track: false }] }, true)).toBe(true);
    expect(soVisible({ id: "s", kpis: [ok], objectives: [o1] }, true)).toBe(false);
    expect(soVisible({ id: "s" }, false)).toBe(true);
  });
  it("treeKrs walks SO objectives (+children) and unaligned", () => {
    const t: GoalTree = { strategies: [{ id: "st", strategic_objectives: [{ id: "so", objectives: [{ id: "o", key_results: [kr("a", false)], children: [{ id: "c", key_results: [kr("b", false)] }] }] }] }], unaligned: { objectives: [{ id: "u", key_results: [kr("c", false)] }] } };
    expect(treeKrs(t).map((k) => k.id)).toEqual(["a", "b", "c"]);
    expect(treeKrs(undefined)).toEqual([]);
  });
});

describe("SCR-58 chart rows (values from API evaluations, thresholds 90/70)", () => {
  const e = (period_key: string, actual_value: number, target: number) => ({ period_key, actual_value, target, band: "NEAR" as const }) as unknown as Parameters<typeof chartRows>[0][number];
  it("sorts by period and derives NEAR/BELOW lines per direction", () => {
    const rows = chartRows([e("2026-09", 3.9, 6), e("2026-07", 5.4, 6)], "HIGHER_IS_BETTER");
    expect(rows.map((r) => r.period_key)).toEqual(["2026-07", "2026-09"]);
    expect(rows[0]).toMatchObject({ actual: 5.4, target: 6, near: 5.4, below: 4.2 });
    const lower = chartRows([e("2026-09", 48, 45)], "LOWER_IS_BETTER");
    expect(lower[0]).toMatchObject({ near: 50, below: 64.286 });
  });
});

describe("dates / periods / formatting", () => {
  it("week range Mon..Sun, checked-in-this-week, days ago", () => {
    expect(weekRangeOf("2026-10-20")).toEqual({ from: "2026-10-19", to: "2026-10-25" });
    expect(checkedInThisWeek("2026-10-19T08:00:00Z", "2026-10-20")).toBe(true);
    expect(checkedInThisWeek("2026-10-16T08:00:00Z", "2026-10-20")).toBe(false);
    expect(checkedInThisWeek(null, "2026-10-20")).toBe(false);
    expect(daysAgo("2026-10-16T08:00:00Z", "2026-10-20")).toBe(4);
  });
  it("period key of a KPI period type", () => {
    expect(periodKeyOf("MONTH", "2026-10-20")).toBe("2026-10");
    expect(periodKeyOf("QUARTER", "2026-10-20")).toBe("2026-Q4");
    expect(periodKeyOf("YEAR", "2026-10-20")).toBe("2026");
  });
  it("formatValue keeps the free-text unit (P04)", () => {
    expect(formatValue(12.5, "%", "vi")).toBe("12,5%");
    expect(formatValue(3.9, "tỷ VND", "vi")).toBe("3,9 tỷ VND");
    expect(formatValue(2.52, "x", "vi")).toBe("2,52x");
    expect(formatValue(null, "%", "vi")).toBe("—");
  });
});

describe("error keys", () => {
  it.each([
    [{ code: "CONFLICT_STATE", details: { reason: "period_locked" } }, "periodLocked"],
    [{ code: "CONFLICT_STATE", details: { reason: "objective_not_active" } }, "objectiveNotActive"],
    [{ code: "CONFLICT_STATE", details: {} }, "conflict"],
    [{ code: "BUSINESS_RULE_VIOLATION", details: { field: "period_key" } }, "periodMismatch"],
    [{ code: "BUSINESS_RULE_VIOLATION", details: { field: "valid_from" } }, "validFrom"],
    [{ code: "BUSINESS_RULE_VIOLATION", details: { reason: "kr_count" } }, "krCount"],
    [{ code: "FORBIDDEN_SCOPE", details: {} }, "FORBIDDEN_SCOPE"],
    [{ code: "WEIRD", details: {} }, "generic"],
  ])("%o → %s", (e, key) => expect(goalErrorKey(e)).toBe(key));
});

describe("forms (zod)", () => {
  const msg = { valueRequired: "v", tooLong: "l", periodInvalid: "p", dateInvalid: "d" };
  it("check-in: number required (comma ok), confidence 3 steps, empty text → null", () => {
    const s = checkInSchema(msg);
    expect(s.safeParse({ value: "", confidence: "LOW", note: "", blocker: "" }).success).toBe(false);
    expect(s.safeParse({ value: "1", confidence: "NONE", note: "", blocker: "" }).success).toBe(false);
    const v = s.parse({ value: "2,52", confidence: "LOW", note: " ", blocker: "x" });
    expect(toCheckInBody(v)).toEqual({ value: 2.52, confidence: "LOW", note: null, blocker: "x" });
  });
  it("measurement / target: period format, numbers, optional valid_from", () => {
    expect(measureSchema(msg).safeParse({ period_key: "2026-13", actual_value: "1", note: "" }).success).toBe(false);
    expect(toMeasureBody(measureSchema(msg).parse({ period_key: "2026-10", actual_value: "1.8", note: "" }))).toEqual({ period_key: "2026-10", actual_value: 1.8, note: null, data_source: "manual" });
    const tv = targetSchema(msg).parse({ period_key: "2026-Q4", target: "6", valid_from: "", reason: "" });
    expect(toTargetBody(tv)).toEqual({ period_key: "2026-Q4", target: 6, valid_from: null, reason: null });
    expect(targetSchema(msg).safeParse({ period_key: "2026", target: "x", valid_from: "", reason: "" }).success).toBe(false);
  });
});
